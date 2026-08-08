"""Combo box widget for searching Mixcloud users and cloudcasts simultaneously."""

from PySide6.QtCore import QEvent, QObject, Qt, QTimer, Signal, Slot
from PySide6.QtGui import QFont, QKeyEvent, QStandardItem, QStandardItemModel
from PySide6.QtWidgets import QApplication, QComboBox

from app.consts.api import MIXCLOUD_WWW_URL
from app.consts.ui import SEARCH_RESULT_LIMIT
from app.custom_widgets.dialogs.error_dialog import ErrorDialog
from app.data_classes import Cloudcast, MixcloudUser
from app.services.api_service import MixcloudAPIService, api_service
from app.threads.fetch_by_url_thread import FetchByUrlThread
from app.threads.search_artist_thread import SearchArtistThread
from app.threads.search_cloudcast_thread import SearchCloudcastThread


class SearchUserQComboBox(QComboBox):
    """Editable combo box for searching Mixcloud users and cloudcasts with auto-suggestions.

    Fires two parallel background searches on each debounced input — one for artists
    (users) and one for mixes (cloudcasts). The popup opens only once both searches
    have completed, presenting results in two labeled sections.

    Signals:
        artist_selected: Emitted when the user selects an artist result.
        cloudcast_selected: Emitted when the user selects a cloudcast result.
    """

    artist_selected: Signal = Signal(MixcloudUser)
    cloudcast_selected: Signal = Signal(Cloudcast)

    def __init__(self, api_service: MixcloudAPIService = api_service) -> None:
        """Initialize the search combo box with dual-search functionality.

        Args:
            api_service: Service for API operations.
        """
        super().__init__()

        self.setEditable(True)
        self.setCompleter(None)
        self.api_service = api_service

        # Must be set before setModel() to guard hidePopup() against AttributeError
        self._app_filter_installed: bool = False

        # Buffered results from both threads
        self._artist_results: list[MixcloudUser] = []
        self._cloudcast_results: list[Cloudcast] = []
        self._artists_done: bool = False
        self._cloudcasts_done: bool = False

        # Use QStandardItemModel to support non-selectable section header items
        self._model = QStandardItemModel()
        self.setModel(self._model)

        # Background search threads
        self.search_artist_thread = SearchArtistThread(api_service=self.api_service)
        self.search_cloudcast_thread = SearchCloudcastThread(api_service=self.api_service)
        self.fetch_by_url_thread = FetchByUrlThread(api_service=self.api_service)

        # Debounce timer — fires 750 ms after the user stops typing
        self.timer = QTimer()
        self.timer.setInterval(750)
        self.timer.setSingleShot(True)

        # Debounce and thread signal connections
        self.timer.timeout.connect(self.get_suggestions)
        self.lineEdit().textEdited.connect(self.timer.start)
        self.activated.connect(self._on_item_activated)

        self.search_artist_thread.new_result.connect(self._on_artist_result)
        self.search_artist_thread.error_signal.connect(self._show_error)
        self.search_artist_thread.finished.connect(self._on_artists_finished)

        self.search_cloudcast_thread.new_result.connect(self._on_cloudcast_result)
        self.search_cloudcast_thread.error_signal.connect(self._show_error)
        self.search_cloudcast_thread.finished.connect(self._on_cloudcasts_finished)

        self.fetch_by_url_thread.user_result.connect(self.artist_selected)
        self.fetch_by_url_thread.cloudcast_result.connect(self.cloudcast_selected)
        self.fetch_by_url_thread.error_signal.connect(self._show_error)

        # Focus policy
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.lineEdit().setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.lineEdit().setFocus()

    def showPopup(self) -> None:
        """Show the popup and install an application-level keyboard event filter."""
        super().showPopup()
        if not self._app_filter_installed:
            QApplication.instance().installEventFilter(self)
            self._app_filter_installed = True

    def hidePopup(self) -> None:
        """Hide the popup and remove the application-level keyboard event filter."""
        if self._app_filter_installed:
            QApplication.instance().removeEventFilter(self)
            self._app_filter_installed = False
        super().hidePopup()

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        """Forward typed characters from the popup view to the line edit.

        When the popup is visible, macOS routes all keyboard events to the
        Qt::Popup window rather than to the main-window line edit. This
        override intercepts those events from the popup's list view (where
        QComboBox already installed `self` as a filter) and delivers
        non-navigation keys directly to the line edit so the user can keep
        typing to refine the search.
        """
        if (
            event.type() == QEvent.Type.KeyPress
            and obj is not self.lineEdit()
            and self.view().isVisible()
        ):
            ke: QKeyEvent = event  # type: ignore[assignment]
            nav_keys = {
                Qt.Key.Key_Up,
                Qt.Key.Key_Down,
                Qt.Key.Key_PageUp,
                Qt.Key.Key_PageDown,
                Qt.Key.Key_Home,
                Qt.Key.Key_End,
                Qt.Key.Key_Return,
                Qt.Key.Key_Enter,
                Qt.Key.Key_Escape,
                Qt.Key.Key_Tab,
            }
            if ke.key() not in nav_keys and (
                ke.text()
                or ke.key()
                in {Qt.Key.Key_Backspace, Qt.Key.Key_Delete, Qt.Key.Key_Left, Qt.Key.Key_Right}
            ):
                QApplication.sendEvent(self.lineEdit(), event)
                return True

        return super().eventFilter(obj, event)

    @Slot()
    def get_suggestions(self) -> None:
        """Start dual search for artists and cloudcasts based on current input text.

        When the input text is a Mixcloud URL, resolves it directly via the API
        instead of performing a keyword search.
        """
        phrase = self.currentText().strip()
        if not phrase:
            return

        # If the user pasted a Mixcloud URL, resolve it directly instead of searching
        url_parts = self._parse_mixcloud_url(phrase)
        if url_parts is not None:
            username, slug = url_parts
            # Stop any in-flight search threads so their stale results don't appear
            if self.search_artist_thread.isRunning():
                self.search_artist_thread.stop()
            if self.search_cloudcast_thread.isRunning():
                self.search_cloudcast_thread.stop()
            if self.fetch_by_url_thread.isRunning():
                self.fetch_by_url_thread.stop()
            self.fetch_by_url_thread.username = username
            self.fetch_by_url_thread.slug = slug
            self.fetch_by_url_thread.start()
            return

        # Reset result buffers and completion flags
        self._artist_results.clear()
        self._cloudcast_results.clear()
        self._artists_done = False
        self._cloudcasts_done = False

        # Stop any threads still running from the previous search
        if self.search_artist_thread.isRunning():
            self.search_artist_thread.stop()
        if self.search_cloudcast_thread.isRunning():
            self.search_cloudcast_thread.stop()

        # Start both threads in parallel
        self.search_artist_thread.phrase = phrase
        self.search_cloudcast_thread.phrase = phrase
        self.search_artist_thread.start()
        self.search_cloudcast_thread.start()

    @Slot(MixcloudUser)
    def _on_artist_result(self, user: MixcloudUser) -> None:
        """Buffer an artist result from the search thread.

        Args:
            user: MixcloudUser result to buffer.
        """
        self._artist_results.append(user)

    @Slot(Cloudcast)
    def _on_cloudcast_result(self, cloudcast: Cloudcast) -> None:
        """Buffer a cloudcast result from the search thread.

        Args:
            cloudcast: Cloudcast result to buffer.
        """
        self._cloudcast_results.append(cloudcast)

    @Slot()
    def _on_artists_finished(self) -> None:
        """Handle artist search thread completion."""
        self._artists_done = True
        if self._cloudcasts_done:
            self._build_model_and_show()

    @Slot()
    def _on_cloudcasts_finished(self) -> None:
        """Handle cloudcast search thread completion."""
        self._cloudcasts_done = True
        if self._artists_done:
            self._build_model_and_show()

    def _make_header_item(self, text: str) -> QStandardItem:
        """Create a non-selectable, bold section header item.

        Args:
            text: Header label text.

        Returns:
            Configured QStandardItem for use as a section header.
        """
        item = QStandardItem(text)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        font = QFont()
        font.setBold(True)
        item.setData(font, Qt.ItemDataRole.FontRole)
        item.setData(None, Qt.ItemDataRole.UserRole)
        return item

    def _make_placeholder_item(self) -> QStandardItem:
        """Create a non-selectable '(no results)' placeholder item.

        Returns:
            Configured QStandardItem for use as an empty-section placeholder.
        """
        item = QStandardItem("(no results)")
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        item.setData(None, Qt.ItemDataRole.UserRole)
        return item

    def _make_artist_item(self, user: MixcloudUser) -> QStandardItem:
        """Create a selectable artist result item.

        Args:
            user: MixcloudUser to represent.

        Returns:
            Configured QStandardItem storing the user in UserRole.
        """
        item = QStandardItem(f"{user.name} ({user.username})")
        item.setData(user, Qt.ItemDataRole.UserRole)
        return item

    def _make_cloudcast_item(self, cloudcast: Cloudcast) -> QStandardItem:
        """Create a selectable cloudcast result item.

        Args:
            cloudcast: Cloudcast to represent.

        Returns:
            Configured QStandardItem storing the cloudcast in UserRole.
        """
        item = QStandardItem(f"{cloudcast.name} – {cloudcast.user.username}")
        item.setData(cloudcast, Qt.ItemDataRole.UserRole)
        return item

    def _build_model_and_show(self) -> None:
        """Build the result model from buffered data and open the popup.

        Called once both search threads have finished. Populates the model in a
        single pass — Artists section first, Mixes section second — then opens
        the dropdown. The user's typed text is preserved and focus is returned
        to the line edit so the user can keep typing to refine the search.
        """
        saved_text = self.lineEdit().text()
        self._model.clear()

        artists = self._artist_results[:SEARCH_RESULT_LIMIT]
        cloudcasts = self._cloudcast_results[:SEARCH_RESULT_LIMIT]

        # Artists section
        self._model.appendRow(self._make_header_item("Artists"))
        if artists:
            for user in artists:
                self._model.appendRow(self._make_artist_item(user))
        else:
            self._model.appendRow(self._make_placeholder_item())

        # Mixes section
        self._model.appendRow(self._make_header_item("Mixes"))
        if cloudcasts:
            for cloudcast in cloudcasts:
                self._model.appendRow(self._make_cloudcast_item(cloudcast))
        else:
            self._model.appendRow(self._make_placeholder_item())

        self.showPopup()
        self.lineEdit().setText(saved_text)
        QTimer.singleShot(0, self.lineEdit().setFocus)

    @Slot(int)
    def _on_item_activated(self, index: int) -> None:
        """Handle explicit user selection of a result item.

        Emits artist_selected or cloudcast_selected based on the type of the
        selected item. Non-result rows (headers, placeholders) are ignored.

        Args:
            index: Model row index of the activated item.
        """
        if index < 0 or index >= self._model.rowCount():
            return

        item = self._model.item(index)
        if not item:
            return

        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, MixcloudUser):
            self.artist_selected.emit(data)
        elif isinstance(data, Cloudcast):
            self.cloudcast_selected.emit(data)

    @Slot(str)
    def _show_error(self, msg: str) -> None:
        """Display an error dialog.

        Args:
            msg: Error message to display.
        """
        ErrorDialog(self, message=msg)

    @staticmethod
    def _parse_mixcloud_url(text: str) -> tuple[str, str | None] | None:
        """Parse text as a Mixcloud user or cloudcast URL.

        Args:
            text: Input string to inspect.

        Returns:
            ``(username, None)`` for a user profile URL,
            ``(username, slug)`` for a cloudcast URL,
            ``None`` if text is not a recognisable Mixcloud URL.
        """
        prefix = f"{MIXCLOUD_WWW_URL}/"
        if not text.startswith(prefix):
            return None
        path = text[len(prefix) :]
        parts = [p for p in path.split("/") if p]
        if len(parts) == 1:
            return (parts[0], None)
        if len(parts) == 2:
            return (parts[0], parts[1])
        return None

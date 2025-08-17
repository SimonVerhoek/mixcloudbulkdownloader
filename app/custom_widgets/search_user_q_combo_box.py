"""Combo box widget for searching and selecting Mixcloud users."""

from PySide6.QtCore import Qt, QTimer, Slot
from PySide6.QtWidgets import QComboBox

from app.custom_widgets.dialogs.error_dialog import ErrorDialog
from app.data_classes import MixcloudUser
from app.services.api_service import MixcloudAPIService
from app.threads import SearchArtistThread


class SearchUserQComboBox(QComboBox):
    """Editable combo box for searching Mixcloud users with auto-suggestions.

    This widget provides a search interface that displays suggestions as the user types,
    with a debounced search mechanism to avoid excessive API calls.
    """

    def __init__(self, api_service: MixcloudAPIService | None = None) -> None:
        """Initialize the search combo box with auto-complete functionality.

        Args:
            api_service: Service for API operations. If None, creates default.
        """
        super().__init__()

        self.setEditable(True)
        self.results: list[MixcloudUser] = []
        self.selected_result: MixcloudUser | None = None
        self.api_service = api_service or MixcloudAPIService()
        self.search_artist_thread = SearchArtistThread(api_service=self.api_service)

        # Configure search debounce timer (750ms delay)
        self.timer = QTimer()
        self.timer.setInterval(750)
        self.timer.setSingleShot(True)

        # Connect signals
        self.timer.timeout.connect(self.get_suggestions)
        self.lineEdit().textEdited.connect(self.timer.start)
        self.currentIndexChanged.connect(self.on_index_changed)
        self.search_artist_thread.new_result.connect(self.add_result)
        self.search_artist_thread.error_signal.connect(self.show_error)

        # Configure focus policy for better UX
        self.setFocusPolicy(Qt.StrongFocus)
        self.lineEdit().setFocusPolicy(Qt.StrongFocus)
        self.lineEdit().setFocus()

    @Slot()
    def get_suggestions(self) -> None:
        """Start searching for users based on current input text."""
        phrase = self.currentText().strip()

        if phrase:
            self.clear()
            self.results.clear()

            self.search_artist_thread.phrase = phrase
            self.search_artist_thread.start()

    @Slot(str)
    def show_error(self, msg: str) -> None:
        """Display error dialog with the given message.

        Args:
            msg: Error message to display
        """
        ErrorDialog(self, message=msg)

    @Slot(MixcloudUser)
    def add_result(self, user: MixcloudUser) -> None:
        """Add a search result to the dropdown list.

        Args:
            user: MixcloudUser to add to the results
        """
        self.results.append(user)

        # Auto-select first result for better UX
        if len(self.results) == 1:
            self.set_selected_result(index=0)

        self.addItem(f"{user.name} ({user.username})")

    @Slot(int)
    def on_index_changed(self, index: int) -> None:
        """Handle selection change in the dropdown.

        Args:
            index: Index of the selected item
        """
        if 0 <= index < len(self.results):
            self.set_selected_result(index)

    def set_selected_result(self, index: int) -> None:
        """Set the currently selected user result.

        Args:
            index: Index of the user in the results list
        """
        if 0 <= index < len(self.results):
            self.selected_result = self.results[index]

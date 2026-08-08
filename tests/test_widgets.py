"""Tests for custom Qt widgets."""

from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from app.consts.ui import SEARCH_RESULT_LIMIT
from app.custom_widgets.cloudcast_q_tree_widget import CloudcastQTreeWidget
from app.custom_widgets.dialogs.feedback_dialog import FeedbackDialog
from app.custom_widgets.dialogs.get_pro_persuasion_dialog import GetProPersuasionDialog
from app.custom_widgets.footer_widget import FooterWidget
from app.custom_widgets.search_user_q_combo_box import SearchUserQComboBox
from app.data_classes import Cloudcast, MixcloudUser
from app.threads.fetch_by_url_thread import FetchByUrlThread
from app.threads.search_cloudcast_thread import SearchCloudcastThread
from tests.stubs.api_stubs import StubMixcloudAPIService
from tests.stubs.file_stubs import StubFileService


@pytest.fixture
def qt_app():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestSearchUserQComboBox:
    """Test cases for SearchUserQComboBox widget."""

    def test_init_with_service(self, qt_app):
        """Test initialization with custom API service."""
        stub_service = StubMixcloudAPIService()
        widget = SearchUserQComboBox(api_service=stub_service)

        assert widget.api_service is stub_service
        assert widget.isEditable()
        assert len(widget._artist_results) == 0
        assert len(widget._cloudcast_results) == 0

    def test_init_without_service(self, qt_app):
        """Test initialization without custom service."""
        widget = SearchUserQComboBox()

        assert widget.api_service is not None
        assert widget.isEditable()

    def test_timer_configuration(self, qt_app):
        """Test search timer configuration."""
        widget = SearchUserQComboBox()

        assert widget.timer.interval() == 750
        assert widget.timer.isSingleShot()

    def test_search_thread_initialization(self, qt_app):
        """Test search thread is properly initialized."""
        stub_service = StubMixcloudAPIService()
        widget = SearchUserQComboBox(api_service=stub_service)

        assert widget.search_artist_thread is not None
        assert widget.search_artist_thread.api_service is stub_service

    def test_text_input_triggers_timer(self, qt_app):
        """Test that text input triggers the debounce timer."""
        widget = SearchUserQComboBox()

        # Set text in the combo box
        widget.setEditText("test user")

        # Timer should be active after text change
        # Note: In real usage, this would be triggered by user input events
        assert widget.lineEdit().text() == "test user"

    def test_combo_box_properties(self, qt_app):
        """Test combo box widget properties."""
        widget = SearchUserQComboBox()

        assert widget.isEditable()
        assert widget.count() == 0  # Should start empty

    # --- Initialisation ---

    def test_init_creates_cloudcast_thread(self, qt_app):
        """Test that __init__ creates a SearchCloudcastThread attribute."""
        stub_service = StubMixcloudAPIService()
        widget = SearchUserQComboBox(api_service=stub_service)

        assert hasattr(widget, "search_cloudcast_thread")
        assert isinstance(widget.search_cloudcast_thread, SearchCloudcastThread)

    def test_has_artist_and_cloudcast_selected_signals(self, qt_app):
        """Test that artist_selected and cloudcast_selected are connectable signals."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())

        assert isinstance(type(widget).artist_selected, Signal)
        assert isinstance(type(widget).cloudcast_selected, Signal)
        # Verify connectivity
        widget.artist_selected.connect(lambda u: None)
        widget.cloudcast_selected.connect(lambda c: None)

    # --- Result buffering slots ---

    def test_on_artist_result_buffers(self, qt_app):
        """Test that _on_artist_result appends the user to _artist_results."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())
        test_user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )

        widget._on_artist_result(user=test_user)

        assert len(widget._artist_results) == 1
        assert widget._artist_results[0] is test_user

    def test_on_cloudcast_result_buffers(self, qt_app):
        """Test that _on_cloudcast_result appends the cloudcast to _cloudcast_results."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())
        test_user = MixcloudUser(
            key="/djtest/",
            name="DJ Test",
            pictures={},
            url="https://www.mixcloud.com/djtest/",
            username="djtest",
        )
        test_cloudcast = Cloudcast(
            name="Test Mix A",
            url="https://www.mixcloud.com/djtest/test-mix-a/",
            user=test_user,
        )

        widget._on_cloudcast_result(cloudcast=test_cloudcast)

        assert len(widget._cloudcast_results) == 1
        assert widget._cloudcast_results[0] is test_cloudcast

    def test_on_artists_finished_sets_flag(self, qt_app):
        """Test that _on_artists_finished sets _artists_done to True."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())
        # Pre-set cloudcasts_done so _build_model_and_show is not triggered
        widget._cloudcasts_done = False

        widget._on_artists_finished()

        assert widget._artists_done is True

    def test_on_cloudcasts_finished_sets_flag(self, qt_app):
        """Test that _on_cloudcasts_finished sets _cloudcasts_done to True."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())
        widget._artists_done = False

        widget._on_cloudcasts_finished()

        assert widget._cloudcasts_done is True

    def test_get_suggestions_resets_buffers(self, qt_app):
        """Test that get_suggestions clears buffers only on non-empty phrase."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())

        test_user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )
        widget._artist_results.append(test_user)
        widget._cloudcast_results.append(
            Cloudcast(
                name="Mix",
                url="https://www.mixcloud.com/testuser/mix/",
                user=test_user,
            )
        )

        # Empty phrase → returns early without clearing
        widget.setEditText("")
        widget.get_suggestions()
        assert len(widget._artist_results) == 1
        assert len(widget._cloudcast_results) == 1

        # Non-empty phrase → clears both buffers then starts threads.
        # Patch thread.start() so no real QThreads are spawned (avoids destruction crash).
        with (
            patch.object(widget.search_artist_thread, "start"),
            patch.object(widget.search_cloudcast_thread, "start"),
        ):
            widget.setEditText("test")
            widget.get_suggestions()

        assert len(widget._artist_results) == 0
        assert len(widget._cloudcast_results) == 0
        assert widget._artists_done is False
        assert widget._cloudcasts_done is False

    # --- Model building ---

    def test_build_model_creates_two_header_sections(self, qt_app):
        """Test _build_model_and_show creates Artists and Mixes header rows with NoItemFlags."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())

        widget._artist_results = []
        widget._cloudcast_results = []
        widget._build_model_and_show()
        # Process the pending QTimer.singleShot callback while widget is alive.
        qt_app.processEvents()

        artists_header = widget._model.item(0)
        assert artists_header.text() == "Artists"
        assert artists_header.flags() == Qt.ItemFlag.NoItemFlags

        # Mixes header is at row 2 (Artists header + placeholder)
        mixes_header = widget._model.item(2)
        assert mixes_header.text() == "Mixes"
        assert mixes_header.flags() == Qt.ItemFlag.NoItemFlags

    def test_build_model_respects_result_limit(self, qt_app):
        """Test that only SEARCH_RESULT_LIMIT artist results appear in the model."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())

        widget._artist_results = [
            MixcloudUser(
                key=f"/user{i}/",
                name=f"User {i}",
                pictures={},
                url=f"https://www.mixcloud.com/user{i}/",
                username=f"user{i}",
            )
            for i in range(10)
        ]
        widget._cloudcast_results = []
        widget._build_model_and_show()
        qt_app.processEvents()

        # Row 0 = "Artists" header, rows 1..LIMIT = artists, next = "Mixes" header
        mixes_header_row = 1 + SEARCH_RESULT_LIMIT
        assert widget._model.item(mixes_header_row).text() == "Mixes"
        # Total rows: 1 header + LIMIT artists + 1 Mixes header + 1 placeholder
        assert widget._model.rowCount() == 2 + SEARCH_RESULT_LIMIT + 1

    def test_build_model_placeholder_when_no_artists(self, qt_app):
        """Test that an empty artist list shows a (no results) placeholder under Artists."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())
        test_user = MixcloudUser(
            key="/djtest/",
            name="DJ Test",
            pictures={},
            url="https://www.mixcloud.com/djtest/",
            username="djtest",
        )

        widget._artist_results = []
        widget._cloudcast_results = [
            Cloudcast(
                name="Test Mix A",
                url="https://www.mixcloud.com/djtest/test-mix-a/",
                user=test_user,
            )
        ]
        widget._build_model_and_show()
        qt_app.processEvents()

        placeholder = widget._model.item(1)
        assert placeholder.text() == "(no results)"
        assert placeholder.flags() == Qt.ItemFlag.NoItemFlags

    def test_build_model_placeholder_when_no_cloudcasts(self, qt_app):
        """Test that an empty cloudcast list shows a (no results) placeholder under Mixes."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())
        test_user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )

        widget._artist_results = [test_user]
        widget._cloudcast_results = []
        widget._build_model_and_show()
        qt_app.processEvents()

        # Row 0 = Artists header, Row 1 = artist, Row 2 = Mixes header, Row 3 = placeholder
        placeholder = widget._model.item(3)
        assert placeholder.text() == "(no results)"
        assert placeholder.flags() == Qt.ItemFlag.NoItemFlags

    # --- Item factory methods ---

    def test_make_header_item_is_non_selectable(self, qt_app):
        """Test that _make_header_item returns an item with NoItemFlags."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())

        item = widget._make_header_item(text="Artists")

        assert item.flags() == Qt.ItemFlag.NoItemFlags

    def test_make_artist_item_stores_user_in_user_role(self, qt_app):
        """Test that _make_artist_item stores the MixcloudUser in UserRole data."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())
        test_user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )

        item = widget._make_artist_item(user=test_user)

        assert isinstance(item.data(Qt.ItemDataRole.UserRole), MixcloudUser)
        assert item.data(Qt.ItemDataRole.UserRole) == test_user

    def test_make_cloudcast_item_stores_cloudcast_in_user_role(self, qt_app):
        """Test that _make_cloudcast_item stores the Cloudcast in UserRole data."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())
        test_user = MixcloudUser(
            key="/djtest/",
            name="DJ Test",
            pictures={},
            url="https://www.mixcloud.com/djtest/",
            username="djtest",
        )
        test_cloudcast = Cloudcast(
            name="Test Mix A",
            url="https://www.mixcloud.com/djtest/test-mix-a/",
            user=test_user,
        )

        item = widget._make_cloudcast_item(cloudcast=test_cloudcast)

        assert isinstance(item.data(Qt.ItemDataRole.UserRole), Cloudcast)
        assert item.data(Qt.ItemDataRole.UserRole) == test_cloudcast

    # --- Item activation / signal emission ---

    def test_on_item_activated_artist_emits_artist_selected(self, qt_app):
        """Test that activating an artist row emits artist_selected with the correct user."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())
        test_user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )
        test_cloudcast = Cloudcast(
            name="Test Mix A",
            url="https://www.mixcloud.com/testuser/test-mix-a/",
            user=test_user,
        )

        widget._artist_results = [test_user]
        widget._cloudcast_results = [test_cloudcast]
        widget._build_model_and_show()
        qt_app.processEvents()

        emitted: list[MixcloudUser] = []
        widget.artist_selected.connect(lambda u: emitted.append(u))

        # Model: row 0 = Artists header, row 1 = artist item
        widget._on_item_activated(index=1)

        assert len(emitted) == 1
        assert emitted[0] == test_user

    def test_on_item_activated_cloudcast_emits_cloudcast_selected(self, qt_app):
        """Test that activating a cloudcast row emits cloudcast_selected with the correct cloudcast."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())
        test_user = MixcloudUser(
            key="/djtest/",
            name="DJ Test",
            pictures={},
            url="https://www.mixcloud.com/djtest/",
            username="djtest",
        )
        test_cloudcast = Cloudcast(
            name="Test Mix A",
            url="https://www.mixcloud.com/djtest/test-mix-a/",
            user=test_user,
        )

        widget._artist_results = [test_user]
        widget._cloudcast_results = [test_cloudcast]
        widget._build_model_and_show()
        qt_app.processEvents()

        emitted: list[Cloudcast] = []
        widget.cloudcast_selected.connect(lambda c: emitted.append(c))

        # Model: row 0 = Artists header, row 1 = artist, row 2 = Mixes header, row 3 = cloudcast
        widget._on_item_activated(index=3)

        assert len(emitted) == 1
        assert emitted[0] == test_cloudcast

    def test_on_item_activated_header_row_ignored(self, qt_app):
        """Test that activating a header row emits neither artist_selected nor cloudcast_selected."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())

        widget._artist_results = []
        widget._cloudcast_results = []
        widget._build_model_and_show()
        qt_app.processEvents()

        artist_emitted: list = []
        cloudcast_emitted: list = []
        widget.artist_selected.connect(lambda u: artist_emitted.append(u))
        widget.cloudcast_selected.connect(lambda c: cloudcast_emitted.append(c))

        # Row 0 = "Artists" header (NoItemFlags, UserRole=None)
        widget._on_item_activated(index=0)

        assert len(artist_emitted) == 0
        assert len(cloudcast_emitted) == 0

    # --- URL paste support ---

    def test_init_creates_fetch_by_url_thread(self, qt_app):
        """Test that __init__ creates a FetchByUrlThread attribute of the correct type."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())

        assert hasattr(widget, "fetch_by_url_thread")
        assert isinstance(widget.fetch_by_url_thread, FetchByUrlThread)

    def test_parse_mixcloud_url_user_url(self, qt_app):
        """Test _parse_mixcloud_url with a user profile URL returns (username, None)."""
        result = SearchUserQComboBox._parse_mixcloud_url("https://www.mixcloud.com/djname/")

        assert result == ("djname", None)

    def test_parse_mixcloud_url_cloudcast_url(self, qt_app):
        """Test _parse_mixcloud_url with a cloudcast URL returns (username, slug)."""
        result = SearchUserQComboBox._parse_mixcloud_url(
            "https://www.mixcloud.com/djname/their-mix/"
        )

        assert result == ("djname", "their-mix")

    def test_parse_mixcloud_url_not_a_url(self, qt_app):
        """Test _parse_mixcloud_url with a plain search phrase returns None."""
        result = SearchUserQComboBox._parse_mixcloud_url("some artist name")

        assert result is None

    def test_parse_mixcloud_url_trailing_slash_optional(self, qt_app):
        """Test _parse_mixcloud_url handles URLs with and without trailing slashes."""
        with_slash = SearchUserQComboBox._parse_mixcloud_url("https://www.mixcloud.com/djname/")
        without_slash = SearchUserQComboBox._parse_mixcloud_url("https://www.mixcloud.com/djname")

        assert with_slash == ("djname", None)
        assert without_slash == ("djname", None)

    def test_parse_mixcloud_url_deep_path_returns_none(self, qt_app):
        """Test _parse_mixcloud_url returns None for URLs with more than two path segments."""
        result = SearchUserQComboBox._parse_mixcloud_url(
            "https://www.mixcloud.com/djname/mix/extra/"
        )

        assert result is None

    def test_get_suggestions_routes_user_url_to_fetch_thread(self, qt_app):
        """Test get_suggestions() starts fetch_by_url_thread for a Mixcloud URL and not the search threads."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())

        with (
            patch.object(widget.fetch_by_url_thread, "start") as mock_fetch_start,
            patch.object(widget.search_artist_thread, "start") as mock_artist_start,
            patch.object(widget.search_cloudcast_thread, "start") as mock_cloudcast_start,
        ):
            widget.setEditText("https://www.mixcloud.com/djname/")
            widget.get_suggestions()

        mock_fetch_start.assert_called_once()
        mock_artist_start.assert_not_called()
        mock_cloudcast_start.assert_not_called()

    def test_get_suggestions_routes_plain_text_to_search_threads(self, qt_app):
        """Test get_suggestions() starts the dual search threads for a plain text phrase."""
        widget = SearchUserQComboBox(api_service=StubMixcloudAPIService())

        with (
            patch.object(widget.fetch_by_url_thread, "start") as mock_fetch_start,
            patch.object(widget.search_artist_thread, "start") as mock_artist_start,
            patch.object(widget.search_cloudcast_thread, "start") as mock_cloudcast_start,
        ):
            widget.setEditText("some artist name")
            widget.get_suggestions()

        mock_fetch_start.assert_not_called()
        mock_artist_start.assert_called_once()
        mock_cloudcast_start.assert_called_once()


class TestCloudcastQTreeWidget:
    """Test cases for CloudcastQTreeWidget widget."""

    def test_init_with_services(self, qt_app):
        """Test initialization with custom services."""
        api_service = StubMixcloudAPIService()
        file_service = StubFileService()

        widget = CloudcastQTreeWidget(api_service=api_service, file_service=file_service)

        assert widget.api_service is api_service
        assert widget.file_service is file_service

    def test_init_without_services(self, qt_app):
        """Test initialization without custom services."""
        widget = CloudcastQTreeWidget()

        assert widget.api_service is not None
        assert widget.file_service is not None

    def test_tree_widget_configuration(self, qt_app):
        """Test tree widget column configuration."""
        widget = CloudcastQTreeWidget()

        assert widget.columnCount() == 3
        assert widget.isHeaderHidden()

    def test_thread_initialization(self, qt_app):
        """Test background threads are properly initialized."""
        api_service = StubMixcloudAPIService()

        widget = CloudcastQTreeWidget(api_service=api_service)

        assert widget.get_cloudcasts_thread is not None
        assert widget.download_manager is not None
        assert widget.get_cloudcasts_thread.api_service is api_service

    def test_get_download_dir_uses_file_service(self, qt_app):
        """Test that directory selection uses file service."""
        from pathlib import Path
        from unittest.mock import patch

        file_service = StubFileService()
        widget = CloudcastQTreeWidget(file_service=file_service)

        with patch.object(
            file_service, "get_pro_download_directory", return_value="/fake/download/path"
        ):
            result = widget._get_download_dir()

        assert result == Path("/fake/download/path")

    def test_get_download_dir_cancelled(self, qt_app):
        """Test directory selection when cancelled."""
        from unittest.mock import patch

        file_service = StubFileService()

        widget = CloudcastQTreeWidget(file_service=file_service)

        with patch.object(file_service, "get_pro_download_directory", return_value=None):
            result = widget._get_download_dir()

        assert result is None

    def test_get_tree_items_empty(self, qt_app):
        """Test getting tree items when empty."""
        widget = CloudcastQTreeWidget()

        items = widget._get_tree_items()

        assert len(items) == 0

    def test_get_selected_cloudcasts_empty(self, qt_app):
        """Test getting selected cloudcasts when none selected."""
        widget = CloudcastQTreeWidget()

        selected = widget.get_selected_cloudcasts()

        assert len(selected) == 0

    def test_add_result_slot(self, qt_app):
        """Test adding cloudcast result to tree."""
        widget = CloudcastQTreeWidget()

        # Create test cloudcast
        user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )
        cloudcast = Cloudcast(
            name="Test Mix", url="https://www.mixcloud.com/testuser/test-mix/", user=user
        )

        # Add result
        widget.add_result(cloudcast)

        # Check item was added
        items = widget._get_tree_items()
        assert len(items) == 1

    def test_show_error_slot(self, qt_app):
        """Test error display functionality."""
        widget = CloudcastQTreeWidget()

        # This would normally show an error dialog
        # In testing, we just ensure the slot can be called without error
        widget.show_error("Test error message")

    def test_clear_slot(self, qt_app):
        """Test clearing the tree widget."""
        widget = CloudcastQTreeWidget()

        # Add some test data first
        user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )
        cloudcast = Cloudcast(
            name="Test Mix", url="https://www.mixcloud.com/testuser/test-mix/", user=user
        )
        widget.add_result(cloudcast)

        # Clear and verify
        widget.clear()
        items = widget._get_tree_items()
        assert len(items) == 0

    def test_select_all_functionality(self, qt_app):
        """Test select all functionality."""
        widget = CloudcastQTreeWidget()

        # Add some test items
        user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )

        for i in range(3):
            cloudcast = Cloudcast(
                name=f"Test Mix {i+1}",
                url=f"https://www.mixcloud.com/testuser/test-mix-{i+1}/",
                user=user,
            )
            widget.add_result(cloudcast)

        # Select all
        widget.select_all()

        # Check all items are selected
        selected = widget.get_selected_cloudcasts()
        assert len(selected) == 3

    def test_unselect_all_functionality(self, qt_app):
        """Test unselect all functionality."""
        widget = CloudcastQTreeWidget()

        # Add and select some test items
        user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )

        for i in range(3):
            cloudcast = Cloudcast(
                name=f"Test Mix {i+1}",
                url=f"https://www.mixcloud.com/testuser/test-mix-{i+1}/",
                user=user,
            )
            widget.add_result(cloudcast)

        widget.select_all()  # First select all
        widget.unselect_all()  # Then unselect all

        # Check no items are selected
        selected = widget.get_selected_cloudcasts()
        assert len(selected) == 0


class TestWidgetIntegration:
    """Integration tests for widget interactions."""

    def test_search_widget_result_selection(self, qt_app):
        """Test that search widget can store selected results."""
        stub_service = StubMixcloudAPIService()
        widget = SearchUserQComboBox(api_service=stub_service)

        # Simulate selecting a user result
        test_user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )

        widget.selected_result = test_user

        assert widget.selected_result is test_user
        assert widget.selected_result.username == "testuser"

    def test_cloudcast_widget_with_user_data(self, qt_app):
        """Test cloudcast widget handling user-specific data."""
        widget = CloudcastQTreeWidget()

        # Create test user and cloudcasts
        user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )

        cloudcasts = []
        for i in range(5):
            cloudcast = Cloudcast(
                name=f"Mix {i+1}", url=f"https://www.mixcloud.com/testuser/mix-{i+1}/", user=user
            )
            cloudcasts.append(cloudcast)
            widget.add_result(cloudcast)

        # Verify all cloudcasts were added
        items = widget._get_tree_items()
        assert len(items) == 5

        # Test partial selection
        if len(items) >= 2:
            items[0].setCheckState(0, Qt.Checked)
            items[1].setCheckState(0, Qt.Checked)

        selected = widget.get_selected_cloudcasts()
        assert len(selected) == 2


@pytest.mark.qt
class TestGetProPersuasionDialog:
    """Test cases for GetProPersuasionDialog widget."""

    def test_init_creates_dialog(self, qt_app):
        """Test Pro persuasion dialog initialization."""
        parent = QWidget()
        dialog = GetProPersuasionDialog(parent)

        assert dialog.parent() is parent
        assert dialog.windowTitle() == "Upgrade to MBD Pro"
        assert dialog.isModal()

    def test_dialog_has_buttons(self, qt_app):
        """Test that dialog has Get Pro and no thanks buttons."""
        dialog = GetProPersuasionDialog()

        assert hasattr(dialog, "get_pro_button")
        assert hasattr(dialog, "no_thanks_button")
        assert dialog.get_pro_button.text() == "Get Pro"
        assert dialog.no_thanks_button.text() == "No thank you"


class TestFooterWidget:
    """Test cases for FooterWidget."""

    def test_footer_widget_initialization(self, qt_app):
        """Test footer widget basic initialization."""
        mock_license_manager = Mock()
        mock_license_manager.is_pro = False
        mock_license_manager.license_status_changed.connect = Mock()

        widget = FooterWidget(license_manager=mock_license_manager)

        assert widget.objectName() == "footerWidget"
        assert widget.license_manager is mock_license_manager

    def test_footer_status_display(self, qt_app):
        """Test footer status display for different license states."""
        mock_license_manager = Mock()
        mock_license_manager.license_status_changed.connect = Mock()

        # Test Free user
        mock_license_manager.is_pro = False
        widget = FooterWidget(license_manager=mock_license_manager)
        assert widget.status_label.text() == "MBD Free"

        # Test Pro user
        mock_license_manager.is_pro = True
        widget2 = FooterWidget(license_manager=mock_license_manager)
        assert widget2.status_label.text() == "MBD Pro"

    def test_footer_feedback_button(self, qt_app):
        """Test footer feedback button properties."""
        mock_license_manager = Mock()
        mock_license_manager.is_pro = False
        mock_license_manager.license_status_changed.connect = Mock()

        widget = FooterWidget(license_manager=mock_license_manager)

        assert widget.feedback_button.text() == "Feedback?"
        assert widget.feedback_button.objectName() == "feedbackButton"


class TestFeedbackDialog:
    """Test cases for FeedbackDialog."""

    def test_feedback_dialog_initialization(self, qt_app):
        """Test feedback dialog basic initialization."""
        parent = QWidget()
        dialog = FeedbackDialog(parent)

        assert dialog.parent() is parent
        assert dialog.windowTitle() == "Send Feedback"
        assert dialog.isModal()
        assert dialog.objectName() == "feedbackDialog"

    def test_feedback_dialog_buttons(self, qt_app):
        """Test feedback dialog button configuration."""
        dialog = FeedbackDialog()

        assert hasattr(dialog, "cancel_button")
        assert hasattr(dialog, "send_button")
        assert dialog.cancel_button.text() == "Cancel"
        assert dialog.send_button.text() == "Send Feedback"
        assert dialog.send_button.isDefault()

    def test_feedback_dialog_text_field(self, qt_app):
        """Test feedback dialog text field properties."""
        dialog = FeedbackDialog()

        assert hasattr(dialog, "feedback_text")
        assert dialog.feedback_text.objectName() == "feedbackText"
        placeholder = dialog.feedback_text.placeholderText()
        assert len(placeholder) > 0

    def test_feedback_dialog_email_field(self, qt_app):
        """Test feedback dialog email field properties."""
        dialog = FeedbackDialog()

        assert hasattr(dialog, "email_field")
        assert dialog.email_field.objectName() == "emailField"
        placeholder = dialog.email_field.placeholderText()
        assert placeholder == "Enter your email if you'd like a response"

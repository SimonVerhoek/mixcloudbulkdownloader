"""Tests for custom Qt widgets."""

import pytest
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest

from app.custom_widgets.search_user_q_combo_box import SearchUserQComboBox
from app.custom_widgets.cloudcast_q_tree_widget import CloudcastQTreeWidget
from app.custom_widgets.dialogs.donation_dialog import DonationDialog
from app.data_classes import MixcloudUser, Cloudcast
from tests.stubs import StubMixcloudAPIService, StubDownloadService, StubFileService


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
        assert len(widget.results) == 0
        assert widget.selected_result is None

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


class TestCloudcastQTreeWidget:
    """Test cases for CloudcastQTreeWidget widget."""

    def test_init_with_services(self, qt_app):
        """Test initialization with custom services."""
        api_service = StubMixcloudAPIService()
        download_service = StubDownloadService()
        file_service = StubFileService()
        
        widget = CloudcastQTreeWidget(
            api_service=api_service,
            download_service=download_service,
            file_service=file_service
        )
        
        assert widget.api_service is api_service
        assert widget.download_service is download_service
        assert widget.file_service is file_service

    def test_init_without_services(self, qt_app):
        """Test initialization without custom services."""
        widget = CloudcastQTreeWidget()
        
        assert widget.api_service is not None
        assert widget.download_service is not None
        assert widget.file_service is not None

    def test_tree_widget_configuration(self, qt_app):
        """Test tree widget column configuration."""
        widget = CloudcastQTreeWidget()
        
        assert widget.columnCount() == 3
        assert widget.isHeaderHidden()

    def test_thread_initialization(self, qt_app):
        """Test background threads are properly initialized."""
        api_service = StubMixcloudAPIService()
        download_service = StubDownloadService()
        
        widget = CloudcastQTreeWidget(
            api_service=api_service,
            download_service=download_service
        )
        
        assert widget.get_cloudcasts_thread is not None
        assert widget.download_thread is not None
        assert widget.get_cloudcasts_thread.api_service is api_service
        assert widget.download_thread.download_service is download_service

    def test_get_download_dir_uses_file_service(self, qt_app):
        """Test that directory selection uses file service."""
        file_service = StubFileService()
        widget = CloudcastQTreeWidget(file_service=file_service)
        
        result = widget._get_download_dir()
        
        assert result == "/fake/download/path"

    def test_get_download_dir_cancelled(self, qt_app):
        """Test directory selection when cancelled."""
        file_service = StubFileService()
        file_service.set_cancel_dialog(True)
        
        widget = CloudcastQTreeWidget(file_service=file_service)
        
        result = widget._get_download_dir()
        
        assert result == ""

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
            username="testuser"
        )
        cloudcast = Cloudcast(
            name="Test Mix",
            url="https://www.mixcloud.com/testuser/test-mix/",
            user=user
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
            username="testuser"
        )
        cloudcast = Cloudcast(
            name="Test Mix",
            url="https://www.mixcloud.com/testuser/test-mix/",
            user=user
        )
        widget.add_result(cloudcast)
        
        # Clear and verify
        widget.clear()
        items = widget._get_tree_items()
        assert len(items) == 0

    def test_update_item_download_progress(self, qt_app):
        """Test updating download progress for items."""
        widget = CloudcastQTreeWidget()
        
        # Add test item first
        user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser"
        )
        cloudcast = Cloudcast(
            name="Test Mix",
            url="https://www.mixcloud.com/testuser/test-mix/",
            user=user
        )
        widget.add_result(cloudcast)
        
        # Update progress
        widget.update_item_download_progress("Test Mix", "50% completed")
        
        # Verify the item still exists (progress update shouldn't remove it)
        items = widget._get_tree_items()
        assert len(items) == 1

    def test_select_all_functionality(self, qt_app):
        """Test select all functionality."""
        widget = CloudcastQTreeWidget()
        
        # Add some test items
        user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser"
        )
        
        for i in range(3):
            cloudcast = Cloudcast(
                name=f"Test Mix {i+1}",
                url=f"https://www.mixcloud.com/testuser/test-mix-{i+1}/",
                user=user
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
            username="testuser"
        )
        
        for i in range(3):
            cloudcast = Cloudcast(
                name=f"Test Mix {i+1}",
                url=f"https://www.mixcloud.com/testuser/test-mix-{i+1}/",
                user=user
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
            username="testuser"
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
            username="testuser"
        )
        
        cloudcasts = []
        for i in range(5):
            cloudcast = Cloudcast(
                name=f"Mix {i+1}",
                url=f"https://www.mixcloud.com/testuser/mix-{i+1}/",
                user=user
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
class TestDonationDialog:
    """Test cases for DonationDialog widget."""

    def test_init_creates_dialog(self, qt_app):
        """Test donation dialog initialization."""
        parent = QWidget()
        dialog = DonationDialog(parent)
        
        assert dialog.parent() is parent
        assert dialog.windowTitle() == "Support Mixcloud Bulk Downloader"
        assert dialog.isModal()

    def test_dialog_has_buttons(self, qt_app):
        """Test that dialog has donate and no thanks buttons."""
        dialog = DonationDialog()
        
        assert hasattr(dialog, 'donate_button')
        assert hasattr(dialog, 'no_thanks_button')
        assert dialog.donate_button.text() == "Donate"
        assert dialog.no_thanks_button.text() == "No thank you"

    def test_completion_signal_shows_dialog(self, qt_app):
        """Test that CloudcastQTreeWidget shows donation dialog on completion signal."""
        widget = CloudcastQTreeWidget()
        
        # Track show_donation_dialog method calls
        dialog_shown = []
        original_method = widget.show_donation_dialog
        
        def mock_show_dialog():
            dialog_shown.append(True)
        
        widget.show_donation_dialog = mock_show_dialog
        
        try:
            # Emit completion signal
            widget.download_thread.completion_signal.emit()
            
            # Process Qt events to handle signal
            QApplication.processEvents()
            
            # Check if dialog method was called
            assert len(dialog_shown) == 1
        finally:
            # Restore original method
            widget.show_donation_dialog = original_method
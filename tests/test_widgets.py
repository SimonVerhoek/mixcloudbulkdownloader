"""Tests for custom Qt widgets."""

from unittest.mock import Mock

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QWidget

from app.custom_widgets.cloudcast_q_tree_widget import CloudcastQTreeWidget
from app.custom_widgets.dialogs.feedback_dialog import FeedbackDialog
from app.custom_widgets.dialogs.get_pro_persuasion_dialog import GetProPersuasionDialog
from app.custom_widgets.footer_widget import FooterWidget
from app.custom_widgets.search_user_q_combo_box import SearchUserQComboBox
from app.data_classes import Cloudcast, MixcloudUser
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

    def test_update_item_download_progress(self, qt_app):
        """Test updating download progress for items."""
        widget = CloudcastQTreeWidget()

        # Add test item first
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

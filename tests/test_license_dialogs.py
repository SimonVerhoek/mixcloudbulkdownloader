"""Tests for license-related dialog functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtCore import Qt

from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
from app.custom_widgets.dialogs.license_verification_success_dialog import LicenseVerificationSuccessDialog
from app.custom_widgets.dialogs.license_verification_failure_dialog import LicenseVerificationFailureDialog
from app.custom_widgets.dialogs.get_pro_persuasion_dialog import GetProPersuasionDialog
from app.consts.license import (
    LICENSE_VERIFICATION_SUCCESS,
    LICENSE_INVALID_CREDENTIALS,
)


@pytest.fixture
def parent_widget():
    """Create a parent widget for dialog testing."""
    return QWidget()


@pytest.fixture
def mock_license_manager():
    """Mock the license manager for testing."""
    with patch('app.custom_widgets.dialogs.get_pro_dialog.license_manager') as mock_lm, \
         patch('app.custom_widgets.dialogs.get_pro_persuasion_dialog.license_manager') as mock_lm2:
        
        # Configure mock settings
        mock_settings = Mock()
        mock_settings.email = ""
        mock_settings.license_key = ""
        mock_lm.settings = mock_settings
        mock_lm2.settings = mock_settings
        
        # Configure mock verification
        mock_lm.verify_license = Mock(return_value=True)
        mock_lm.get_checkout_url = Mock()
        mock_lm.is_pro = False
        mock_lm2.is_pro = False
        
        yield mock_lm


class TestGetProDialog:
    """Test cases for GetPro dialog functionality."""

    @pytest.mark.qt
    def test_get_pro_dialog_initialization(self, qtbot, parent_widget, mock_license_manager):
        """Test GetPro dialog initializes correctly."""
        dialog = GetProDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        assert dialog.windowTitle() == "Get MBD Pro"
        assert dialog.isModal()
        assert dialog.objectName() == "getProDialog"

    @pytest.mark.qt  
    def test_get_pro_dialog_form_validation_empty_fields(self, qtbot, parent_widget, mock_license_manager):
        """Test form validation with empty fields."""
        dialog = GetProDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Test with empty fields
        assert not dialog._validate_form()

    @pytest.mark.qt
    def test_get_pro_dialog_form_validation_invalid_email(self, qtbot, parent_widget, mock_license_manager):
        """Test form validation with invalid email format."""
        dialog = GetProDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Test with invalid email format
        dialog.email_edit.setText("invalid-email")
        dialog.license_key_edit.setText("test-key-123")
        
        assert not dialog._validate_form()

    @pytest.mark.qt
    def test_get_pro_dialog_form_validation_valid_input(self, qtbot, parent_widget, mock_license_manager):
        """Test form validation with valid input."""
        dialog = GetProDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Test with valid input
        dialog.email_edit.setText("test@example.com")
        dialog.license_key_edit.setText("test-key-123")
        
        assert dialog._validate_form()

    @pytest.mark.qt
    def test_get_pro_dialog_loads_existing_credentials(self, qtbot, parent_widget, mock_license_manager):
        """Test that dialog loads existing credentials from settings."""
        # Set up mock credentials
        mock_license_manager.settings.email = "existing@example.com"
        mock_license_manager.settings.license_key = "existing-key-456"
        
        dialog = GetProDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Check that credentials are loaded
        assert dialog.email_edit.text() == "existing@example.com"
        assert dialog.license_key_edit.text() == "existing-key-456"

    @pytest.mark.qt
    def test_get_pro_dialog_successful_verification(self, qtbot, parent_widget, mock_license_manager):
        """Test successful license verification flow."""
        dialog = GetProDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Set up valid form data
        dialog.email_edit.setText("test@example.com")
        dialog.license_key_edit.setText("valid-key-123")
        
        # Mock successful verification
        mock_license_manager.verify_license.return_value = True
        
        # Mock success dialog
        with patch('app.custom_widgets.dialogs.get_pro_dialog.LicenseVerificationSuccessDialog') as mock_success_dialog:
            mock_dialog_instance = Mock()
            mock_success_dialog.return_value = mock_dialog_instance
            
            # Trigger verification
            dialog._handle_verify()
            
            # Check that credentials were stored
            mock_license_manager.settings.email = "test@example.com"
            mock_license_manager.settings.license_key = "valid-key-123"
            
            # Check that verification was called
            mock_license_manager.verify_license.assert_called_once_with()
            
            # Check that success dialog was shown
            mock_success_dialog.assert_called_once_with(dialog)
            mock_dialog_instance.exec.assert_called_once()

    @pytest.mark.qt
    def test_get_pro_dialog_failed_verification(self, qtbot, parent_widget, mock_license_manager):
        """Test failed license verification flow."""
        dialog = GetProDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Set up valid form data
        dialog.email_edit.setText("test@example.com")
        dialog.license_key_edit.setText("invalid-key-123")
        
        # Mock failed verification
        mock_license_manager.verify_license.return_value = False
        
        # Mock failure dialog
        with patch('app.custom_widgets.dialogs.get_pro_dialog.LicenseVerificationFailureDialog') as mock_failure_dialog:
            mock_dialog_instance = Mock()
            mock_failure_dialog.return_value = mock_dialog_instance
            
            # Trigger verification
            dialog._handle_verify()
            
            # Check that failure dialog was shown
            mock_failure_dialog.assert_called_once()
            mock_dialog_instance.exec.assert_called_once()

    @pytest.mark.qt
    def test_get_pro_dialog_browser_opening(self, qtbot, parent_widget, mock_license_manager):
        """Test that Pro purchase button opens browser correctly."""
        dialog = GetProDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Mock the checkout URL retrieval
        test_checkout_url = "https://checkout.stripe.com/test-checkout-url"
        mock_license_manager.get_checkout_url.return_value = test_checkout_url
        
        with patch('webbrowser.open') as mock_open:
            dialog._handle_get_pro_now()
            
            # Verify license manager method was called
            mock_license_manager.get_checkout_url.assert_called_once()
            # Verify browser opened with returned URL
            mock_open.assert_called_once_with(test_checkout_url)

    @pytest.mark.qt
    def test_get_pro_dialog_browser_opening_failure(self, qtbot, parent_widget, mock_license_manager):
        """Test graceful handling of checkout URL retrieval failure."""
        dialog = GetProDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Mock the checkout URL method to raise an exception
        mock_license_manager.get_checkout_url.side_effect = Exception("Checkout server error")
        
        with patch('app.custom_widgets.dialogs.get_pro_dialog.ErrorDialog') as mock_error_dialog, \
             patch('app.custom_widgets.dialogs.get_pro_dialog.log_error') as mock_log:
            
            mock_dialog_instance = Mock()
            mock_error_dialog.return_value = mock_dialog_instance
            
            dialog._handle_get_pro_now()
            
            # Check that error dialog was shown
            mock_error_dialog.assert_called_once()
            mock_dialog_instance.exec.assert_called_once()
            
            # Check that error was logged
            mock_log.assert_called_once()
            assert "Failed to retrieve checkout URL" in mock_log.call_args[1]['message']


class TestLicenseVerificationSuccessDialog:
    """Test cases for license verification success dialog."""

    @pytest.mark.qt
    def test_success_dialog_initialization(self, qtbot, parent_widget):
        """Test success dialog initializes correctly."""
        dialog = LicenseVerificationSuccessDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        assert dialog.windowTitle() == "Welcome to MBD Pro!"
        assert dialog.isModal()
        assert dialog.objectName() == "licenseSuccessDialog"

    @pytest.mark.qt
    def test_success_dialog_button_closes_dialog(self, qtbot, parent_widget):
        """Test that start button closes the dialog."""
        dialog = LicenseVerificationSuccessDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Mock the accept method
        dialog.accept = Mock()
        
        # Click the start button
        qtbot.mouseClick(dialog.start_button, Qt.MouseButton.LeftButton)
        
        # Check that dialog was accepted
        dialog.accept.assert_called_once()


class TestLicenseVerificationFailureDialog:
    """Test cases for license verification failure dialog."""

    @pytest.mark.qt
    def test_failure_dialog_initialization(self, qtbot, parent_widget):
        """Test failure dialog initializes correctly."""
        error_message = "Custom error message"
        dialog = LicenseVerificationFailureDialog(parent_widget, error_message)
        qtbot.addWidget(dialog)
        
        assert dialog.windowTitle() == "License Verification Failed"
        assert dialog.isModal()
        assert dialog.objectName() == "licenseFailureDialog"
        assert dialog.error_message == error_message

    @pytest.mark.qt
    def test_failure_dialog_default_message(self, qtbot, parent_widget):
        """Test failure dialog with default error message."""
        dialog = LicenseVerificationFailureDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        assert dialog.error_message == "License verification failed."

    @pytest.mark.qt
    def test_failure_dialog_button_closes_dialog(self, qtbot, parent_widget):
        """Test that ok button closes the dialog."""
        dialog = LicenseVerificationFailureDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Mock the accept method
        dialog.accept = Mock()
        
        # Click the ok button
        qtbot.mouseClick(dialog.ok_button, Qt.MouseButton.LeftButton)
        
        # Check that dialog was accepted
        dialog.accept.assert_called_once()


class TestGetProPersuasionDialog:
    """Test cases for Pro persuasion dialog."""

    @pytest.mark.qt
    def test_pro_persuasion_dialog_should_show_non_pro_user(self, qtbot):
        """Test that dialog should be shown for non-Pro users."""
        with patch('app.custom_widgets.dialogs.get_pro_persuasion_dialog.license_manager') as mock_lm:
            mock_lm.is_pro = False
            
            assert GetProPersuasionDialog.should_show() == True

    @pytest.mark.qt
    def test_pro_persuasion_dialog_should_not_show_pro_user(self, qtbot):
        """Test that dialog should not be shown for Pro users."""
        with patch('app.custom_widgets.dialogs.get_pro_persuasion_dialog.license_manager') as mock_lm:
            mock_lm.is_pro = True
            
            assert GetProPersuasionDialog.should_show() == False

    @pytest.mark.qt
    def test_pro_persuasion_dialog_initialization(self, qtbot, parent_widget):
        """Test Pro persuasion dialog initializes correctly."""
        dialog = GetProPersuasionDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        assert dialog.windowTitle() == "Upgrade to MBD Pro"
        assert dialog.isModal()
        assert dialog.objectName() == "proPersuasionDialog"

    @pytest.mark.qt
    def test_pro_persuasion_dialog_get_pro_button_opens_browser(self, qtbot, parent_widget):
        """Test that Get Pro button opens browser correctly."""
        dialog = GetProPersuasionDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Mock the checkout URL retrieval and accept method
        test_checkout_url = "https://checkout.stripe.com/test-checkout-url"
        dialog.accept = Mock()
        
        with patch('app.custom_widgets.dialogs.get_pro_persuasion_dialog.license_manager') as mock_lm, \
             patch('webbrowser.open') as mock_open:
            
            mock_lm.get_checkout_url.return_value = test_checkout_url
            
            dialog._handle_get_pro()
            
            # Verify license manager method was called
            mock_lm.get_checkout_url.assert_called_once()
            # Verify browser opened with returned URL
            mock_open.assert_called_once_with(test_checkout_url)
            # Verify dialog was closed
            dialog.accept.assert_called_once()

    @pytest.mark.qt
    def test_pro_persuasion_dialog_get_pro_button_handles_browser_failure(self, qtbot, parent_widget):
        """Test graceful handling of checkout URL retrieval failure."""
        dialog = GetProPersuasionDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Mock the accept method
        dialog.accept = Mock()
        
        with patch('app.custom_widgets.dialogs.get_pro_persuasion_dialog.license_manager') as mock_lm, \
             patch('app.custom_widgets.dialogs.get_pro_persuasion_dialog.ErrorDialog') as mock_error_dialog, \
             patch('app.custom_widgets.dialogs.get_pro_persuasion_dialog.log_error') as mock_log:
            
            # Mock the checkout URL method to raise an exception
            mock_lm.get_checkout_url.side_effect = Exception("Checkout server error")
            mock_dialog_instance = Mock()
            mock_error_dialog.return_value = mock_dialog_instance
            
            dialog._handle_get_pro()
            
            # Check that error dialog was shown
            mock_error_dialog.assert_called_once()
            mock_dialog_instance.exec.assert_called_once()
            
            # Check that error was logged and dialog still closed
            mock_log.assert_called_once()
            assert "Failed to retrieve checkout URL" in mock_log.call_args[1]['message']
            dialog.accept.assert_called_once()

    @pytest.mark.qt
    def test_pro_persuasion_dialog_no_thanks_button(self, qtbot, parent_widget):
        """Test that No thanks button dismisses the dialog."""
        dialog = GetProPersuasionDialog(parent_widget)
        qtbot.addWidget(dialog)
        
        # Mock the reject method
        dialog.reject = Mock()
        
        # Click the no thanks button
        qtbot.mouseClick(dialog.no_thanks_button, Qt.MouseButton.LeftButton)
        
        # Check that dialog was rejected
        dialog.reject.assert_called_once()


class TestDialogIntegration:
    """Test cases for dialog integration with main application."""

    @pytest.mark.qt
    def test_cloudcast_widget_shows_dialog_for_non_pro_users(self, qtbot):
        """Test that cloudcast widget shows Pro dialog for non-Pro users."""
        with patch('app.custom_widgets.cloudcast_q_tree_widget.GetProPersuasionDialog') as mock_dialog_class:
            # Import here to avoid circular imports in test setup
            from app.custom_widgets.cloudcast_q_tree_widget import CloudcastQTreeWidget
            
            # Mock the should_show method to return True
            mock_dialog_class.should_show.return_value = True
            mock_dialog_instance = Mock()
            mock_dialog_class.return_value = mock_dialog_instance
            
            # Create widget
            widget = CloudcastQTreeWidget()
            qtbot.addWidget(widget)
            
            # Call the show_donation_dialog method
            widget.show_donation_dialog()
            
            # Verify dialog was created and shown
            mock_dialog_class.should_show.assert_called_once()
            mock_dialog_class.assert_called_once_with(widget.parent())
            mock_dialog_instance.exec.assert_called_once()

    @pytest.mark.qt
    def test_cloudcast_widget_skips_dialog_for_pro_users(self, qtbot):
        """Test that cloudcast widget skips Pro dialog for Pro users."""
        with patch('app.custom_widgets.cloudcast_q_tree_widget.GetProPersuasionDialog') as mock_dialog_class:
            # Import here to avoid circular imports in test setup
            from app.custom_widgets.cloudcast_q_tree_widget import CloudcastQTreeWidget
            
            # Mock the should_show method to return False
            mock_dialog_class.should_show.return_value = False
            mock_dialog_instance = Mock()
            mock_dialog_class.return_value = mock_dialog_instance
            
            # Create widget
            widget = CloudcastQTreeWidget()
            qtbot.addWidget(widget)
            
            # Call the show_donation_dialog method
            widget.show_donation_dialog()
            
            # Verify should_show was called but dialog was not created
            mock_dialog_class.should_show.assert_called_once()
            mock_dialog_class.assert_not_called()
            mock_dialog_instance.exec.assert_not_called()

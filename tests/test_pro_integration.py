"""Integration tests for Pro license system main application integration."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest

from main import MainWindow
from app.custom_widgets.central_widget import CentralWidget
from app.threads.startup_verification_thread import StartupVerificationThread
from app.custom_widgets.dialogs.get_pro_dialog import GetProDialog
from app.services.license_manager import LicenseManager


@pytest.fixture
def app(qapp):
    """Provide QApplication instance for Qt tests."""
    return qapp


@pytest.fixture
def mock_license_manager():
    """Create a mock license manager for testing."""
    mock_manager = Mock(spec=LicenseManager)
    mock_manager.is_pro = False
    mock_manager.settings = Mock()
    mock_manager.settings.email = ""
    mock_manager.settings.license_key = ""
    mock_manager.settings.last_successful_verification = None
    mock_manager.verify_license = Mock(return_value=False)
    return mock_manager


@pytest.fixture
def mock_pro_license_manager():
    """Create a mock license manager for Pro user testing."""
    mock_manager = Mock(spec=LicenseManager)
    mock_manager.is_pro = True
    mock_manager.settings = Mock()
    mock_manager.settings.email = "pro@example.com"
    mock_manager.settings.license_key = "valid-key"
    mock_manager.settings.last_successful_verification = 1640995200  # Some timestamp
    mock_manager.verify_license = Mock(return_value=True)
    return mock_manager


class TestCentralWidgetProIntegration:
    """Test CentralWidget Pro integration functionality."""
    
    def test_central_widget_accepts_license_manager(self, app, mock_license_manager, qtbot):
        """Test that CentralWidget accepts license_manager parameter."""
        widget = CentralWidget(license_manager=mock_license_manager)
        qtbot.addWidget(widget)
        assert widget.license_manager == mock_license_manager

    def test_get_mbd_pro_button_created_for_non_pro_users(self, app, mock_license_manager, qtbot):
        """Test that Get MBD Pro button is created and visible for non-Pro users."""
        widget = CentralWidget(license_manager=mock_license_manager)
        qtbot.addWidget(widget)
        widget.show()
        
        assert hasattr(widget, 'get_mbd_pro_button')
        assert widget.get_mbd_pro_button.text() == "Get MBD Pro"
        assert widget.get_mbd_pro_button.objectName() == "primaryButton"
        assert widget.get_mbd_pro_button.isVisible()

    def test_get_mbd_pro_button_hidden_for_pro_users(self, app, mock_pro_license_manager, qtbot):
        """Test that Get MBD Pro button is hidden for Pro users."""
        widget = CentralWidget(license_manager=mock_pro_license_manager)
        qtbot.addWidget(widget)
        
        assert hasattr(widget, 'get_mbd_pro_button')
        assert not widget.get_mbd_pro_button.isVisible()

    @patch('app.custom_widgets.central_widget.GetProDialog')
    def test_get_mbd_pro_button_opens_dialog(self, mock_dialog_class, app, mock_license_manager, qtbot):
        """Test that clicking Get MBD Pro button opens GetProDialog."""
        mock_dialog = Mock()
        mock_dialog.exec.return_value = False
        mock_dialog_class.return_value = mock_dialog
        
        widget = CentralWidget(license_manager=mock_license_manager)
        qtbot.addWidget(widget)
        
        # Simulate button click
        QTest.mouseClick(widget.get_mbd_pro_button, Qt.LeftButton)
        
        mock_dialog_class.assert_called_once_with(widget)
        mock_dialog.exec.assert_called_once()

    def test_refresh_pro_ui_elements_updates_button_visibility(self, app, mock_license_manager, qtbot):
        """Test that refresh_pro_ui_elements updates button visibility."""
        widget = CentralWidget(license_manager=mock_license_manager)
        qtbot.addWidget(widget)
        widget.show()
        
        # Initially non-Pro, button should be visible
        assert widget.get_mbd_pro_button.isVisible()
        
        # Change to Pro status
        mock_license_manager.is_pro = True
        widget.refresh_pro_ui_elements()
        
        # Button should now be hidden
        assert not widget.get_mbd_pro_button.isVisible()


class TestMainWindowProIntegration:
    """Test MainWindow Pro integration functionality."""

    @patch('main.StartupVerificationThread')
    def test_main_window_creates_central_widget_with_license_manager(self, mock_thread_class, app, mock_license_manager, qtbot):
        """Test that MainWindow passes license_manager to CentralWidget."""
        with patch('main.license_manager', mock_license_manager):
            window = MainWindow()
            qtbot.addWidget(window)
            window.show()
            
            assert hasattr(window, 'central_widget')
            assert window.central_widget.license_manager == mock_license_manager

    @patch('main.StartupVerificationThread')
    def test_get_mbd_pro_menu_item_created_for_non_pro_users(self, mock_thread_class, app, mock_license_manager, qtbot):
        """Test that Get MBD Pro menu item is created and visible for non-Pro users."""
        with patch('main.license_manager', mock_license_manager):
            window = MainWindow()
            qtbot.addWidget(window)
            
            assert hasattr(window, 'get_mbd_pro_action')
            assert window.get_mbd_pro_action.text() == "Get MBD Pro..."
            assert window.get_mbd_pro_action.isVisible()

    @patch('main.StartupVerificationThread')
    def test_get_mbd_pro_menu_item_hidden_for_pro_users(self, mock_thread_class, app, mock_pro_license_manager, qtbot):
        """Test that Get MBD Pro menu item is hidden for Pro users."""
        with patch('main.license_manager', mock_pro_license_manager):
            window = MainWindow()
            qtbot.addWidget(window)
            
            assert hasattr(window, 'get_mbd_pro_action')
            assert not window.get_mbd_pro_action.isVisible()

    @patch('main.GetProDialog')
    @patch('main.StartupVerificationThread')
    def test_get_mbd_pro_menu_opens_dialog(self, mock_thread_class, mock_dialog_class, app, mock_license_manager, qtbot):
        """Test that Get MBD Pro menu item opens GetProDialog."""
        mock_dialog = Mock()
        mock_dialog.exec.return_value = False
        mock_dialog_class.return_value = mock_dialog
        
        with patch('main.license_manager', mock_license_manager):
            window = MainWindow()
            qtbot.addWidget(window)
            
            # Trigger menu action
            window.get_mbd_pro_action.trigger()
            
            mock_dialog_class.assert_called_once_with(window)
            mock_dialog.exec.assert_called_once()

    @patch('main.StartupVerificationThread')
    def test_dynamic_ui_updates_on_pro_status_change(self, mock_thread_class, app, mock_license_manager, qtbot):
        """Test that UI updates when Pro status changes."""
        with patch('main.license_manager', mock_license_manager):
            window = MainWindow()
            qtbot.addWidget(window)
            window.show()
            
            # Initially non-Pro, elements should be visible
            assert window.get_mbd_pro_action.isVisible()
            assert window.central_widget.get_mbd_pro_button.isVisible()
            
            # Change to Pro status
            mock_license_manager.is_pro = True
            window.refresh_pro_ui_elements()
            
            # Elements should now be hidden
            assert not window.get_mbd_pro_action.isVisible()
            assert not window.central_widget.get_mbd_pro_button.isVisible()


class TestStartupVerification:
    """Test startup license verification functionality."""

    def test_startup_verification_with_stored_credentials(self, app, mock_license_manager):
        """Test automatic verification with stored credentials."""
        mock_license_manager.settings.email = "user@example.com"
        mock_license_manager.settings.license_key = "test-key"
        mock_license_manager.verify_license.return_value = True
        
        thread = StartupVerificationThread(mock_license_manager)
        
        # Mock the signal emission
        with patch.object(thread, 'verification_completed') as mock_signal:
            thread.run()
            
            mock_license_manager.verify_license.assert_called_once_with(
                email="user@example.com", 
                license_key="test-key",
                timeout=10
            )
            mock_signal.emit.assert_called_once_with(True, False)

    def test_startup_verification_network_failure(self, app, mock_license_manager):
        """Test graceful startup when license server unreachable."""
        mock_license_manager.settings.email = "user@example.com"
        mock_license_manager.settings.license_key = "test-key"
        mock_license_manager.settings.last_successful_verification = 1640995200
        mock_license_manager.verify_license.return_value = False
        
        thread = StartupVerificationThread(mock_license_manager)
        
        with patch.object(thread, 'verification_completed') as mock_signal:
            thread.run()
            
            # Should use offline grace period
            assert mock_license_manager.is_pro == True
            mock_signal.emit.assert_called_once_with(False, False)

    def test_startup_verification_corrupted_credentials(self, app, mock_license_manager):
        """Test handling of invalid stored credentials."""
        mock_license_manager.settings.email = "invalid@example.com"
        mock_license_manager.settings.license_key = "invalid-key"
        mock_license_manager.settings.last_successful_verification = None
        mock_license_manager.verify_license.return_value = False
        
        thread = StartupVerificationThread(mock_license_manager)
        
        with patch.object(thread, 'verification_completed') as mock_signal:
            thread.run()
            
            # Should set is_pro to False and notify user
            assert mock_license_manager.is_pro == False
            mock_signal.emit.assert_called_once_with(False, True)

    def test_first_run_no_credentials(self, app, mock_license_manager):
        """Test startup behavior with no stored credentials."""
        mock_license_manager.settings.email = ""
        mock_license_manager.settings.license_key = ""
        
        thread = StartupVerificationThread(mock_license_manager)
        
        with patch.object(thread, 'verification_completed') as mock_signal:
            thread.run()
            
            # Should not attempt verification
            mock_license_manager.verify_license.assert_not_called()
            mock_signal.emit.assert_called_once_with(False, False)

    def test_startup_verification_failure_with_previous_success(self, app, mock_license_manager):
        """Test offline grace period when last_successful_verification exists."""
        mock_license_manager.settings.email = "user@example.com"
        mock_license_manager.settings.license_key = "test-key"
        mock_license_manager.settings.last_successful_verification = 1640995200
        mock_license_manager.verify_license.return_value = False
        
        thread = StartupVerificationThread(mock_license_manager)
        
        with patch.object(thread, 'verification_completed') as mock_signal:
            thread.run()
            
            # Should maintain Pro status and not notify user
            assert mock_license_manager.is_pro == True
            mock_signal.emit.assert_called_once_with(False, False)

    def test_startup_verification_failure_no_previous_success(self, app, mock_license_manager):
        """Test user notification when last_successful_verification is falsy."""
        mock_license_manager.settings.email = "user@example.com"
        mock_license_manager.settings.license_key = "test-key"
        mock_license_manager.settings.last_successful_verification = None
        mock_license_manager.verify_license.return_value = False
        
        thread = StartupVerificationThread(mock_license_manager)
        
        with patch.object(thread, 'verification_completed') as mock_signal:
            thread.run()
            
            # Should set is_pro to False and notify user
            assert mock_license_manager.is_pro == False
            mock_signal.emit.assert_called_once_with(False, True)


class TestMainWindowStartupIntegration:
    """Test MainWindow startup verification integration."""

    def test_startup_license_verification_thread_created(self, app, mock_license_manager, qtbot):
        """Test that startup verification thread is created and started."""
        with patch('main.license_manager', mock_license_manager), \
             patch('main.StartupVerificationThread') as mock_thread_class:
            
            mock_thread = Mock()
            mock_thread_class.return_value = mock_thread
            
            window = MainWindow()
            qtbot.addWidget(window)
            
            mock_thread_class.assert_called_once_with(mock_license_manager, window)
            mock_thread.verification_completed.connect.assert_called_once()
            mock_thread.start.assert_called_once()

    @patch('app.custom_widgets.dialogs.error_dialog.ErrorDialog')
    def test_handle_startup_verification_result_notify_user(self, mock_error_dialog, app, mock_license_manager, qtbot):
        """Test user notification when startup verification requires it."""
        with patch('main.license_manager', mock_license_manager), \
             patch('main.StartupVerificationThread'):
            
            window = MainWindow()
            qtbot.addWidget(window)
            
            # Simulate verification failure that requires notification
            window._handle_startup_verification_result(success=False, notify_user=True)
            
            mock_error_dialog.assert_called_once()
            args, kwargs = mock_error_dialog.call_args
            assert "License verification failed" in kwargs['message']

    def test_handle_startup_verification_result_no_notification(self, app, mock_license_manager, qtbot):
        """Test no user notification when using offline grace period."""
        with patch('main.license_manager', mock_license_manager), \
             patch('main.StartupVerificationThread'), \
             patch('app.custom_widgets.dialogs.error_dialog.ErrorDialog') as mock_error_dialog:
            
            window = MainWindow()
            qtbot.addWidget(window)
            
            # Simulate verification failure with offline grace period
            window._handle_startup_verification_result(success=False, notify_user=False)
            
            # Should not show error dialog
            mock_error_dialog.assert_not_called()
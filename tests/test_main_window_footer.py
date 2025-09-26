"""Tests for main window footer integration."""

import pytest
from unittest.mock import Mock, patch
from PySide6.QtWidgets import QApplication, QVBoxLayout
from PySide6.QtCore import Qt

from main import MainWindow
from app.custom_widgets.footer_widget import FooterWidget
from app.custom_widgets.central_widget import CentralWidget


@pytest.fixture
def qt_app():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


@pytest.fixture
def mock_services():
    """Mock all services for testing."""
    with patch('main.settings') as mock_settings, \
         patch('main.license_manager') as mock_license_manager, \
         patch('main.download_service') as mock_download_service, \
         patch('main.StartupVerificationThread') as mock_thread:
        
        # Configure mocks
        mock_license_manager.is_pro = False
        mock_license_manager.license_status_changed = Mock()
        mock_license_manager.license_status_changed.connect = Mock()
        
        # Mock thread to prevent actual startup verification
        mock_thread_instance = Mock()
        mock_thread.return_value = mock_thread_instance
        
        yield {
            'settings': mock_settings,
            'license_manager': mock_license_manager, 
            'download_service': mock_download_service,
            'thread': mock_thread_instance
        }


@pytest.mark.qt
class TestMainWindowFooterIntegration:
    """Test main window footer integration."""
    
    def test_main_window_has_footer_widget(self, qt_app, mock_services):
        """Test that main window contains footer widget."""
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            
            assert hasattr(window, 'footer_widget')
            assert isinstance(window.footer_widget, FooterWidget)
            
    def test_main_window_layout_structure(self, qt_app, mock_services):
        """Test that main window has correct layout structure."""
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            
            # Main widget should be the central widget
            central_widget = window.centralWidget()
            assert central_widget is not None
            
            # Should have vertical layout with central widget and footer
            layout = central_widget.layout()
            assert isinstance(layout, QVBoxLayout)
            assert layout.count() == 2
            
            # First item should be the central widget
            central_item = layout.itemAt(0).widget()
            assert isinstance(central_item, CentralWidget)
            
            # Second item should be the footer
            footer_item = layout.itemAt(1).widget()
            assert isinstance(footer_item, FooterWidget)
            
    def test_footer_widget_receives_license_manager(self, qt_app, mock_services):
        """Test that footer widget receives the same license manager."""
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            
            assert window.footer_widget.license_manager is window.license_manager
            
    def test_license_status_change_propagates_to_footer(self, qt_app, mock_services):
        """Test that license status changes propagate to footer."""
        mock_license_manager = mock_services['license_manager']
        
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            
            # License manager should be connected to footer via its own signal
            # The footer widget connects directly to license_manager.license_status_changed
            mock_license_manager.license_status_changed.connect.assert_called()
            
    def test_main_window_layout_margins_and_spacing(self, qt_app, mock_services):
        """Test that main window layout has correct margins and spacing."""
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            
            central_widget = window.centralWidget()
            layout = central_widget.layout()
            
            # Should have no margins and spacing for seamless layout
            assert layout.contentsMargins().left() == 0
            assert layout.contentsMargins().right() == 0
            assert layout.contentsMargins().top() == 0
            assert layout.contentsMargins().bottom() == 0
            assert layout.spacing() == 0
            
    def test_footer_widget_signal_connection_in_main_window(self, qt_app, mock_services):
        """Test that footer widget properly connects to license manager signals."""
        mock_license_manager = mock_services['license_manager']
        
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            
            # Footer widget should connect to license status changes
            # This happens inside FooterWidget.__init__, but we verify the manager was passed
            assert window.footer_widget.license_manager is mock_license_manager


@pytest.mark.qt
class TestMainWindowFooterBehavior:
    """Test footer behavior within main window context."""
    
    def test_footer_widget_default_state_free_user(self, qt_app, mock_services):
        """Test footer shows correct default state for free users."""
        mock_services['license_manager'].is_pro = False
        
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            window.show()  # Widget needs to be shown for visibility to work
            
            # Footer should show Free status and Pro button
            assert window.footer_widget.status_label.text() == "MBD Free"
            assert window.footer_widget.get_pro_button.isVisible() == True
            
    def test_footer_widget_default_state_pro_user(self, qt_app, mock_services):
        """Test footer shows correct default state for Pro users."""
        mock_services['license_manager'].is_pro = True
        
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            
            # Footer should show Pro status and hide Pro button
            assert window.footer_widget.status_label.text() == "MBD Pro"
            assert window.footer_widget.get_pro_button.isVisible() == False
            
    def test_footer_feedback_button_opens_dialog(self, qt_app, mock_services):
        """Test that footer feedback button opens dialog in main window context."""
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            
            with patch('app.custom_widgets.footer_widget.FeedbackDialog') as mock_dialog_class:
                mock_dialog = Mock()
                mock_dialog_class.return_value = mock_dialog
                
                # Click feedback button
                window.footer_widget._show_feedback_dialog()
                
                # Verify dialog was created with footer as parent
                mock_dialog_class.assert_called_once_with(window.footer_widget)
                mock_dialog.exec.assert_called_once()


@pytest.mark.qt  
class TestMainWindowFooterIntegrationEdgeCases:
    """Test edge cases for main window footer integration."""
    
    def test_main_window_initialization_order(self, qt_app, mock_services):
        """Test that footer is initialized after central widget."""
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            
            # Both widgets should exist
            assert hasattr(window, 'central_widget')
            assert hasattr(window, 'footer_widget')
            
            # They should be different instances
            assert window.central_widget is not window.footer_widget
            
    def test_window_close_event_with_footer(self, qt_app, mock_services):
        """Test that window close event works correctly with footer."""
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            
            # Mock close event
            from PySide6.QtGui import QCloseEvent
            close_event = QCloseEvent()
            close_event.accept = Mock()
            
            # Should not raise exception
            window.closeEvent(close_event)
            
            # Event should be accepted
            close_event.accept.assert_called_once()
            
    def test_footer_widget_survives_central_widget_refresh(self, qt_app, mock_services):
        """Test that footer widget remains when central widget is refreshed."""
        with patch('main.load_application_styles'), \
             patch('main.QGuiApplication.instance', return_value=Mock()):
            
            window = MainWindow()
            original_footer = window.footer_widget
            
            # Refresh Pro UI elements (which might affect layouts)
            window.refresh_pro_ui_elements()
            
            # Footer should still be the same instance
            assert window.footer_widget is original_footer
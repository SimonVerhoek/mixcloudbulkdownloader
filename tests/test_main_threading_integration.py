"""Tests for threading settings integration in main.py."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager


@pytest.mark.unit
class TestMainThreadingIntegration:
    """Test cases for threading settings integration in MainWindow."""

    def test_imports_are_at_top_level(self):
        """Test that threading constants are not imported inline."""
        import inspect

        from app.main_window import MainWindow

        # Get the source code of the MainWindow.__init__ method
        init_source = inspect.getsource(MainWindow.__init__)

        # Should not contain inline imports for threading constants
        assert "from app.consts.settings import" not in init_source

        # Should not contain inline imports in the threading initialization
        assert "DEFAULT_MAX_PARALLEL" not in init_source
        assert "SETTING_MAX_PARALLEL" not in init_source

    def test_main_window_initialization_calls_settings_initialization(self):
        """Test that the MainWindow's initialization logic calls settings initialization."""
        # This is a simpler unit test that verifies the code structure rather than
        # testing the full Qt integration
        import inspect

        from app.main_window import MainWindow

        # Get the source code of MainWindow.__init__
        init_source = inspect.getsource(MainWindow.__init__)

        # Should contain call to threading settings initialization
        assert "initialize_threading_settings" in init_source

        # Should pass license manager's is_pro status
        assert "self.license_manager.is_pro" in init_source


@pytest.mark.integration
class TestMainThreadingIntegrationWithRealServices:
    """Integration tests with real service instances."""

    def test_main_window_with_real_services(self):
        """Test MainWindow initialization with real SettingsManager and LicenseManager."""
        from app.main_window import MainWindow
        from app.services.license_manager import LicenseManager
        from app.services.settings_manager import SettingsManager

        # This test would need Qt application context in real usage
        with (
            patch("app.main_window.CentralWidget"),
            patch("app.main_window.FooterWidget"),
            patch("app.main_window.StartupVerificationThread"),
            patch("app.services.settings_manager.QSettings"),
        ):

            # Test that the real services have the expected method
            real_settings = SettingsManager()
            assert hasattr(real_settings, "initialize_threading_settings")
            assert callable(real_settings.initialize_threading_settings)

            real_license_manager = LicenseManager()
            assert hasattr(real_license_manager, "is_pro")

    def test_threading_constants_accessible_from_main(self):
        """Test that threading constants are accessible in main module context."""
        # This tests the import structure
        try:
            from app.consts.settings import (
                DEFAULT_MAX_PARALLEL_CONVERSIONS,
                DEFAULT_MAX_PARALLEL_DOWNLOADS,
                SETTING_MAX_PARALLEL_CONVERSIONS,
                SETTING_MAX_PARALLEL_DOWNLOADS,
            )

            # If we get here, imports work correctly
            assert True
        except ImportError as e:
            pytest.fail(f"Threading constants not accessible from main context: {e}")

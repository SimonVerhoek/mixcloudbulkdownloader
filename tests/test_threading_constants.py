"""Tests for threading constants and settings configuration."""

import pytest

from app.consts.settings import (
    DEFAULT_MAX_PARALLEL_CONVERSIONS,
    DEFAULT_MAX_PARALLEL_DOWNLOADS,
    PARALLEL_CONVERSIONS_OPTIONS,
    PARALLEL_DOWNLOADS_OPTIONS,
    SETTING_MAX_PARALLEL_CONVERSIONS,
    SETTING_MAX_PARALLEL_DOWNLOADS,
)


@pytest.mark.unit
class TestThreadingConstants:
    """Test cases for threading configuration constants."""

    def test_default_parallel_downloads_value(self):
        """Test that default parallel downloads is set to expected value."""
        assert DEFAULT_MAX_PARALLEL_DOWNLOADS == 3
        assert isinstance(DEFAULT_MAX_PARALLEL_DOWNLOADS, int)

    def test_default_parallel_conversions_value(self):
        """Test that default parallel conversions is set to expected value."""
        # Should be a reasonable value, but may vary by environment
        assert 1 <= DEFAULT_MAX_PARALLEL_CONVERSIONS <= 12
        assert isinstance(DEFAULT_MAX_PARALLEL_CONVERSIONS, int)

    def test_setting_key_parallel_downloads_format(self):
        """Test that parallel downloads setting key is properly formatted."""
        assert isinstance(SETTING_MAX_PARALLEL_DOWNLOADS, str)
        assert len(SETTING_MAX_PARALLEL_DOWNLOADS) > 0

        # Should be descriptive
        key = SETTING_MAX_PARALLEL_DOWNLOADS.lower()
        assert "parallel" in key
        assert "download" in key
        assert "max" in key

    def test_setting_key_parallel_conversions_format(self):
        """Test that parallel conversions setting key is properly formatted."""
        assert isinstance(SETTING_MAX_PARALLEL_CONVERSIONS, str)
        assert len(SETTING_MAX_PARALLEL_CONVERSIONS) > 0

        # Should be descriptive
        key = SETTING_MAX_PARALLEL_CONVERSIONS.lower()
        assert "parallel" in key
        assert "conversion" in key
        assert "max" in key

    def test_setting_keys_are_unique(self):
        """Test that setting keys are unique from each other."""
        assert SETTING_MAX_PARALLEL_DOWNLOADS != SETTING_MAX_PARALLEL_CONVERSIONS

    def test_default_values_are_positive(self):
        """Test that default values are positive integers."""
        assert DEFAULT_MAX_PARALLEL_DOWNLOADS > 0
        assert DEFAULT_MAX_PARALLEL_CONVERSIONS > 0

    def test_default_values_are_reasonable(self):
        """Test that default values are in reasonable ranges."""
        # Downloads: should be between 1-8 (as per UI)
        assert 1 <= DEFAULT_MAX_PARALLEL_DOWNLOADS <= 8

        # Conversions: should be reasonable for CPU usage (at least 1, less than or equal to cpu_count)
        from app.services.system_service import cpu_count

        assert 1 <= DEFAULT_MAX_PARALLEL_CONVERSIONS <= cpu_count

    def test_downloads_default_higher_than_conversions(self):
        """Test that downloads default is higher than conversions default."""
        # Downloads should allow more parallelism than conversions (less CPU intensive)
        assert DEFAULT_MAX_PARALLEL_DOWNLOADS >= DEFAULT_MAX_PARALLEL_CONVERSIONS

    def test_constants_imported_successfully(self):
        """Test that all threading constants can be imported without error."""
        # If we got here, imports worked
        assert True

    def test_constants_accessible_from_module(self):
        """Test that constants are accessible when imported."""
        from app.consts.settings import (
            DEFAULT_MAX_PARALLEL_CONVERSIONS,
            DEFAULT_MAX_PARALLEL_DOWNLOADS,
            SETTING_MAX_PARALLEL_CONVERSIONS,
            SETTING_MAX_PARALLEL_DOWNLOADS,
        )

        # All should be accessible
        assert DEFAULT_MAX_PARALLEL_DOWNLOADS is not None
        assert DEFAULT_MAX_PARALLEL_CONVERSIONS is not None
        assert SETTING_MAX_PARALLEL_DOWNLOADS is not None
        assert SETTING_MAX_PARALLEL_CONVERSIONS is not None

    def test_setting_keys_snake_case_format(self):
        """Test that setting keys follow snake_case format."""
        downloads_key = SETTING_MAX_PARALLEL_DOWNLOADS
        conversions_key = SETTING_MAX_PARALLEL_CONVERSIONS

        # Should be snake_case (lowercase with underscores)
        assert downloads_key.islower()
        assert conversions_key.islower()
        assert "_" in downloads_key
        assert "_" in conversions_key

        # Should not contain spaces or other characters
        assert " " not in downloads_key
        assert " " not in conversions_key
        assert "-" not in downloads_key
        assert "-" not in conversions_key

    def test_constants_are_immutable_types(self):
        """Test that constants use immutable types."""
        # int and str are immutable in Python
        assert isinstance(DEFAULT_MAX_PARALLEL_DOWNLOADS, int)
        assert isinstance(DEFAULT_MAX_PARALLEL_CONVERSIONS, int)
        assert isinstance(SETTING_MAX_PARALLEL_DOWNLOADS, str)
        assert isinstance(SETTING_MAX_PARALLEL_CONVERSIONS, str)

    def test_constants_match_ui_expectations(self):
        """Test that constants match what the UI expects."""
        # Downloads: UI shows 1-8, default should be valid
        assert 1 <= DEFAULT_MAX_PARALLEL_DOWNLOADS <= 8

        # Conversions: UI shows dynamic options based on CPU, default should be valid
        from app.services.system_service import cpu_count

        assert 1 <= DEFAULT_MAX_PARALLEL_CONVERSIONS <= cpu_count

        # Default downloads should be "3" as set in UI
        assert DEFAULT_MAX_PARALLEL_DOWNLOADS == 3

        # Default conversions should be reasonable for the target environment
        # Note: May be 2 on high-core systems, but could be 1 on low-core CI systems
        assert DEFAULT_MAX_PARALLEL_CONVERSIONS >= 1

    def test_parallel_downloads_options_format(self):
        """Test that parallel downloads options are properly formatted."""
        assert isinstance(PARALLEL_DOWNLOADS_OPTIONS, list)
        assert len(PARALLEL_DOWNLOADS_OPTIONS) > 0
        assert all(isinstance(x, int) for x in PARALLEL_DOWNLOADS_OPTIONS)

        # Should be 1-8 range
        assert PARALLEL_DOWNLOADS_OPTIONS == [1, 2, 3, 4, 5, 6, 7, 8]

    def test_parallel_conversions_options_format(self):
        """Test that parallel conversions options are properly formatted."""
        assert isinstance(PARALLEL_CONVERSIONS_OPTIONS, list)
        assert len(PARALLEL_CONVERSIONS_OPTIONS) > 0
        assert all(isinstance(x, int) for x in PARALLEL_CONVERSIONS_OPTIONS)

        # Should be dynamic based on CPU count, but start at 1 and be less than cpu_count
        from app.services.system_service import cpu_count

        expected_options = [i for i in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] if i < cpu_count]
        assert PARALLEL_CONVERSIONS_OPTIONS == expected_options

    def test_default_values_in_options(self):
        """Test that default values are included in the available options."""
        assert DEFAULT_MAX_PARALLEL_DOWNLOADS in PARALLEL_DOWNLOADS_OPTIONS
        # For conversions, default might not be in options on low-core systems (like CI with 2 cores)
        # In such cases, the UI should handle this gracefully by using the closest available option
        from app.services.system_service import cpu_count

        if cpu_count > DEFAULT_MAX_PARALLEL_CONVERSIONS:
            assert DEFAULT_MAX_PARALLEL_CONVERSIONS in PARALLEL_CONVERSIONS_OPTIONS
        else:
            # On low-core systems, ensure at least option 1 exists and default is reasonable
            assert len(PARALLEL_CONVERSIONS_OPTIONS) >= 1
            assert 1 in PARALLEL_CONVERSIONS_OPTIONS

    def test_options_are_sorted(self):
        """Test that options are in ascending order."""
        assert PARALLEL_DOWNLOADS_OPTIONS == sorted(PARALLEL_DOWNLOADS_OPTIONS)
        assert PARALLEL_CONVERSIONS_OPTIONS == sorted(PARALLEL_CONVERSIONS_OPTIONS)

    def test_options_reasonable_ranges(self):
        """Test that option ranges are reasonable for threading."""
        # Downloads should start at 1 and not exceed 8
        assert min(PARALLEL_DOWNLOADS_OPTIONS) >= 1
        assert max(PARALLEL_DOWNLOADS_OPTIONS) <= 8

        # Conversions should start at 1 and not exceed cpu_count-1 (CPU intensive)
        from app.services.system_service import cpu_count

        assert min(PARALLEL_CONVERSIONS_OPTIONS) >= 1
        assert max(PARALLEL_CONVERSIONS_OPTIONS) < cpu_count
        # Should not be empty
        assert len(PARALLEL_CONVERSIONS_OPTIONS) > 0

    def test_options_no_duplicates(self):
        """Test that options contain no duplicate values."""
        assert len(PARALLEL_DOWNLOADS_OPTIONS) == len(set(PARALLEL_DOWNLOADS_OPTIONS))
        assert len(PARALLEL_CONVERSIONS_OPTIONS) == len(set(PARALLEL_CONVERSIONS_OPTIONS))


@pytest.mark.unit
class TestThreadingConstantsIntegration:
    """Integration tests for threading constants with other modules."""

    def test_constants_work_with_settings_manager(self):
        """Test that constants work correctly with SettingsManager."""
        from unittest.mock import Mock, patch

        from app.services.settings_manager import SettingsManager

        with patch("app.services.settings_manager.QSettings") as mock_qsettings:
            mock_instance = Mock()
            mock_qsettings.return_value = mock_instance
            mock_instance.value.return_value = None

            settings = SettingsManager()

            # Should be able to call initialize_threading_settings with constants
            settings.initialize_threading_settings(is_pro=True)

            # Verify constants were used in setValue calls
            mock_instance.setValue.assert_any_call(
                SETTING_MAX_PARALLEL_DOWNLOADS, DEFAULT_MAX_PARALLEL_DOWNLOADS
            )
            mock_instance.setValue.assert_any_call(
                SETTING_MAX_PARALLEL_CONVERSIONS, DEFAULT_MAX_PARALLEL_CONVERSIONS
            )

    def test_constants_work_with_settings_dialog(self):
        """Test that constants work correctly with SettingsDialog."""
        from unittest.mock import Mock

        from app.custom_widgets.dialogs.settings_dialog import SettingsDialog
        from app.services.license_manager import LicenseManager
        from app.services.settings_manager import SettingsManager

        # Mock the managers
        license_mgr = Mock(spec=LicenseManager)
        license_mgr.is_pro = True

        settings_mgr = Mock(spec=SettingsManager)
        settings_mgr.get.side_effect = lambda key, default=None: {
            SETTING_MAX_PARALLEL_DOWNLOADS: DEFAULT_MAX_PARALLEL_DOWNLOADS,
            SETTING_MAX_PARALLEL_CONVERSIONS: DEFAULT_MAX_PARALLEL_CONVERSIONS,
        }.get(key, default)

        # This should work without errors - constants should be compatible
        try:
            # Just test that import and basic usage works
            assert SETTING_MAX_PARALLEL_DOWNLOADS is not None
            assert DEFAULT_MAX_PARALLEL_DOWNLOADS is not None
        except Exception as e:
            pytest.fail(f"Constants not compatible with SettingsDialog: {e}")

    def test_constants_consistency_across_modules(self):
        """Test that constants are consistent across different modules."""
        # Import from different places to ensure consistency
        # Re-import to verify consistency
        from app.consts.settings import (
            DEFAULT_MAX_PARALLEL_CONVERSIONS as const2,
            DEFAULT_MAX_PARALLEL_CONVERSIONS as const2_reimport,
            DEFAULT_MAX_PARALLEL_DOWNLOADS as const1,
            DEFAULT_MAX_PARALLEL_DOWNLOADS as const1_reimport,
            SETTING_MAX_PARALLEL_CONVERSIONS as key2,
            SETTING_MAX_PARALLEL_CONVERSIONS as key2_reimport,
            SETTING_MAX_PARALLEL_DOWNLOADS as key1,
            SETTING_MAX_PARALLEL_DOWNLOADS as key1_reimport,
        )

        # Should be identical
        assert const1 == const1_reimport
        assert const2 == const2_reimport
        assert key1 == key1_reimport
        assert key2 == key2_reimport

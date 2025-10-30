"""Tests for system service functionality."""

import pytest
from unittest.mock import patch, Mock
import multiprocessing

from app.services.system_service import get_cpu_count, cpu_count


@pytest.mark.unit
class TestCpuDetection:
    """Test cases for CPU detection functionality."""

    def test_get_cpu_count_returns_multiprocessing_value(self):
        """Test that get_cpu_count returns multiprocessing.cpu_count() when available."""
        with patch('app.services.system_service.multiprocessing.cpu_count', return_value=8):
            result = get_cpu_count()
            assert result == 8

    def test_get_cpu_count_handles_not_implemented_error(self):
        """Test that get_cpu_count returns fallback value when NotImplementedError occurs."""
        with patch('app.services.system_service.multiprocessing.cpu_count', side_effect=NotImplementedError):
            result = get_cpu_count()
            assert result == 4

    def test_get_cpu_count_handles_os_error(self):
        """Test that get_cpu_count returns fallback value when OSError occurs."""
        with patch('app.services.system_service.multiprocessing.cpu_count', side_effect=OSError):
            result = get_cpu_count()
            assert result == 4

    def test_get_cpu_count_handles_generic_exception(self):
        """Test that get_cpu_count returns fallback value for other exceptions."""
        with patch('app.services.system_service.multiprocessing.cpu_count', side_effect=RuntimeError):
            result = get_cpu_count()
            assert result == 4

    def test_cpu_count_module_singleton(self):
        """Test that cpu_count module variable is properly initialized."""
        # The module variable should be an integer
        assert isinstance(cpu_count, int)
        assert cpu_count >= 1  # Should be at least 1
        
        # Test that it matches what get_cpu_count() would return
        # (accounting for the fact that the module was already imported)
        with patch('multiprocessing.cpu_count', return_value=6):
            fresh_count = get_cpu_count()
            assert fresh_count == 6

    def test_cpu_count_realistic_range(self):
        """Test that CPU count is in a realistic range."""
        # Real systems should have between 1 and 256 cores
        assert 1 <= cpu_count <= 256
        
    def test_cpu_count_is_positive(self):
        """Test that CPU count is always positive."""
        # Even with fallback, should never be zero or negative
        assert cpu_count > 0

    @pytest.mark.integration
    def test_real_cpu_detection(self):
        """Integration test that verifies real CPU detection works."""
        # This should work on real systems without mocking
        real_count = multiprocessing.cpu_count()
        detected_count = get_cpu_count()
        
        # Should match the real count when no errors occur
        assert detected_count == real_count
        assert detected_count >= 1
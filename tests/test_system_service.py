"""Tests for system service functionality."""

import multiprocessing

import pytest

from app.services.system_service import cpu_count, get_cpu_count


@pytest.mark.unit
class TestCpuDetection:
    """Test cases for CPU detection functionality."""

    def test_get_cpu_count_returns_multiprocessing_value(self):
        """Test that get_cpu_count returns multiprocessing.cpu_count() when available."""
        result = get_cpu_count(cpu_count_fn=lambda: 8)
        assert result == 8

    def test_get_cpu_count_handles_not_implemented_error(self):
        """Test that get_cpu_count returns fallback value when NotImplementedError occurs."""

        def raise_not_implemented():
            raise NotImplementedError

        result = get_cpu_count(cpu_count_fn=raise_not_implemented)
        assert result == 4

    def test_get_cpu_count_handles_os_error(self):
        """Test that get_cpu_count returns fallback value when OSError occurs."""

        def raise_os_error():
            raise OSError

        result = get_cpu_count(cpu_count_fn=raise_os_error)
        assert result == 4

    def test_get_cpu_count_handles_generic_exception(self):
        """Test that get_cpu_count returns fallback value for other exceptions."""

        def raise_runtime_error():
            raise RuntimeError

        result = get_cpu_count(cpu_count_fn=raise_runtime_error)
        assert result == 4

    def test_cpu_count_module_singleton(self):
        """Test that cpu_count module variable is properly initialized."""
        # The module variable should be an integer
        assert isinstance(cpu_count, int)
        assert cpu_count >= 1  # Should be at least 1

        # Test that get_cpu_count() with an injected function returns the expected value
        fresh_count = get_cpu_count(cpu_count_fn=lambda: 6)
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

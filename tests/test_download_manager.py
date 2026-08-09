"""Comprehensive tests for DownloadManager using PyQt threading patterns."""

import tempfile
from collections.abc import Callable
from pathlib import Path
from unittest.mock import MagicMock, create_autospec

import pytest
from PySide6.QtCore import QRunnable

from app.consts.settings import (
    DEFAULT_ENABLE_AUDIO_CONVERSION,
    SETTING_ENABLE_AUDIO_CONVERSION,
)
from app.data_classes import Cloudcast, MixcloudUser
from app.services.download_manager import CallbackBridge, DownloadManager
from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager
from tests.stubs.license_server_stubs import StubLicenseManager


class StubDownloadWorker(QRunnable):
    """Stub download worker for testing."""

    def __init__(self, cloudcast, download_dir, callback_bridge, settings_manager, license_manager):
        """Initialize stub download worker."""
        super().__init__()
        self.cloudcast = cloudcast
        self.download_dir = download_dir
        self.callback_bridge = callback_bridge
        self.settings_manager = settings_manager
        self.license_manager = license_manager
        self.cancelled = False

    def run(self):
        """Mock run method for QRunnable."""
        pass

    def cancel(self):
        """Mock cancellation."""
        self.cancelled = True


class StubConversionWorker(QRunnable):
    """Stub conversion worker for testing."""

    def __init__(
        self,
        cloudcast_url,
        input_file,
        target_format,
        download_dir,
        callback_bridge,
        settings_manager,
        license_manager,
    ):
        """Initialize stub conversion worker."""
        super().__init__()
        self.cloudcast_url = cloudcast_url
        self.input_file = input_file
        self.target_format = target_format
        self.download_dir = download_dir
        self.callback_bridge = callback_bridge
        self.settings_manager = settings_manager
        self.license_manager = license_manager
        self.cancelled = False

    def run(self):
        """Mock run method for QRunnable."""
        pass

    def cancel(self):
        """Mock cancellation."""
        self.cancelled = True


class _RecordingSlot:
    """Simple callable that records all calls made to it.

    Used as a Qt signal slot substitute in tests.  Unlike ``Mock()``, this
    requires no spec because it intentionally accepts any arguments.
    """

    def __init__(self) -> None:
        """Initialise with empty call history."""
        self.calls: list[tuple] = []

    def __call__(self, *args) -> None:
        """Record positional arguments passed to this slot."""
        self.calls.append(args)

    def assert_called_once(self) -> None:
        """Assert that this slot was called exactly once."""
        assert len(self.calls) == 1, f"Expected 1 call, got {len(self.calls)}"

    def assert_called_once_with(self, *expected_args) -> None:
        """Assert that this slot was called exactly once with the given args."""
        assert len(self.calls) == 1, f"Expected 1 call, got {len(self.calls)}"
        assert (
            self.calls[0] == expected_args
        ), f"Expected call with {expected_args!r}, got {self.calls[0]!r}"

    def assert_not_called(self) -> None:
        """Assert that this slot was never called."""
        assert len(self.calls) == 0, f"Expected 0 calls, got {len(self.calls)}"

    def reset_mock(self) -> None:
        """Clear call history (mimics Mock.reset_mock interface)."""
        self.calls.clear()


def _make_stub_settings(
    *,
    max_parallel_downloads: int = 3,
    max_parallel_conversions: int = 2,
    preferred_audio_format: str = "mp3",
    enable_audio_conversion: bool = True,
) -> MagicMock:
    """Create a MagicMock with spec=SettingsManager and preset attribute values.

    Args:
        max_parallel_downloads: Value for ``max_parallel_downloads``.
        max_parallel_conversions: Value for ``max_parallel_conversions``.
        preferred_audio_format: Value for ``preferred_audio_format``.
        enable_audio_conversion: Value for ``enable_audio_conversion``.

    Returns:
        A ``MagicMock`` spec'd to ``SettingsManager`` with the given values.
    """
    stub = MagicMock(spec=SettingsManager)
    stub.max_parallel_downloads = max_parallel_downloads
    stub.max_parallel_conversions = max_parallel_conversions
    stub.preferred_audio_format = preferred_audio_format
    stub.enable_audio_conversion = enable_audio_conversion
    stub.get = MagicMock(
        spec=SettingsManager.get,
        side_effect=lambda key, default=None: {
            "max_parallel_downloads": max_parallel_downloads,
            "max_parallel_conversions": max_parallel_conversions,
            "preferred_audio_format": preferred_audio_format,
            SETTING_ENABLE_AUDIO_CONVERSION: enable_audio_conversion,
        }.get(key, default),
    )
    return stub


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def stub_settings_manager():
    """Create stub settings manager."""
    return _make_stub_settings()


@pytest.fixture
def stub_license_manager():
    """Create stub license manager."""
    return StubLicenseManager()


@pytest.fixture
def download_manager(stub_settings_manager, stub_license_manager):
    """Create DownloadManager instance for testing.

    Uses injected stub worker classes so no real downloads or conversions are
    started.  The ``invoke_method_fn`` is left as *None* so the real
    ``QMetaObject.invokeMethod`` is used — tests that need to intercept those
    calls should create their own ``DownloadManager`` instance with a stub.
    """
    return DownloadManager(
        settings_manager=stub_settings_manager,
        license_manager=stub_license_manager,
        download_worker_class=StubDownloadWorker,
        conversion_worker_class=StubConversionWorker,
    )


@pytest.fixture
def sample_cloudcasts():
    """Create sample cloudcasts for testing."""
    user1 = MixcloudUser(
        key="/test-artist-1/",
        name="Test Artist 1",
        pictures={"large": "https://example.com/pic1.jpg"},
        url="https://mixcloud.com/test-artist-1/",
        username="test-artist-1",
    )
    user2 = MixcloudUser(
        key="/test-artist-2/",
        name="Test Artist 2",
        pictures={"large": "https://example.com/pic2.jpg"},
        url="https://mixcloud.com/test-artist-2/",
        username="test-artist-2",
    )

    return [
        Cloudcast(name="Test Mix 1", url="https://mixcloud.com/test/mix1", user=user1),
        Cloudcast(name="Test Mix 2", url="https://mixcloud.com/test/mix2", user=user2),
    ]


class TestDownloadManagerStructure:
    """Test DownloadManager initialization and structure."""

    def test_download_manager_initialization(
        self, download_manager, stub_settings_manager, stub_license_manager
    ):
        """Test DownloadManager initializes with correct attributes."""
        from PySide6.QtCore import QThreadPool

        assert download_manager.settings_manager == stub_settings_manager
        assert download_manager.license_manager == stub_license_manager
        assert isinstance(download_manager.callback_bridge, CallbackBridge)
        assert isinstance(download_manager.download_pool, QThreadPool)
        assert isinstance(download_manager.conversion_pool, QThreadPool)
        assert download_manager.active_downloads == {}
        assert download_manager.active_conversions == {}
        assert not download_manager.cancelled

    def test_download_manager_signals(self, download_manager):
        """Test DownloadManager has required signals."""
        # Workflow signals
        _ = download_manager.workflow_started
        _ = download_manager.all_workflows_finished

        # Task signals
        _ = download_manager.task_progress
        _ = download_manager.task_result
        _ = download_manager.task_error
        _ = download_manager.task_cancelled
        _ = download_manager.task_finished

    def test_thread_pool_size_configuration(self, download_manager):
        """Test thread pool sizes are configured from settings."""
        # Settings mock returns max_downloads=3, max_conversions=2
        assert download_manager.download_pool.maxThreadCount() == 3
        assert download_manager.conversion_pool.maxThreadCount() == 2


class TestCallbackBridge:
    """Test CallbackBridge thread-safe signal emission."""

    def test_callback_bridge_initialization(self, download_manager):
        """Test CallbackBridge initializes correctly."""
        bridge = CallbackBridge(download_manager=download_manager)
        assert bridge.download_manager == download_manager

    def test_emit_progress(self, download_manager):
        """Test progress signal emission through CallbackBridge."""
        received_calls: list[tuple] = []

        def stub_invoke_method(*args):
            received_calls.append(args)

        bridge = CallbackBridge(
            download_manager=download_manager, invoke_method_fn=stub_invoke_method
        )

        bridge.emit_progress("https://mixcloud.com/test/mix", "Progress 50%", "download")

        assert len(received_calls) == 1
        call_args = received_calls[0]
        assert call_args[0] == download_manager
        assert call_args[1] == "_emit_progress_signal"

    def test_emit_completed(self, download_manager):
        """Test completion signal emission through CallbackBridge."""
        received_calls: list[tuple] = []

        def stub_invoke_method(*args):
            received_calls.append(args)

        bridge = CallbackBridge(
            download_manager=download_manager, invoke_method_fn=stub_invoke_method
        )

        bridge.emit_completed("https://mixcloud.com/test/mix", "/path/to/file.m4a", "download")

        assert len(received_calls) == 1
        call_args = received_calls[0]
        assert call_args[0] == download_manager
        assert call_args[1] == "_emit_completed_signal"

    def test_emit_error(self, download_manager):
        """Test error signal emission through CallbackBridge."""
        received_calls: list[tuple] = []

        def stub_invoke_method(*args):
            received_calls.append(args)

        bridge = CallbackBridge(
            download_manager=download_manager, invoke_method_fn=stub_invoke_method
        )

        bridge.emit_error("https://mixcloud.com/test/mix", "Download failed", "download")

        assert len(received_calls) == 1
        call_args = received_calls[0]
        assert call_args[0] == download_manager
        assert call_args[1] == "_emit_error_signal"


@pytest.mark.unit
class TestDownloadWorkflow:
    """Test download workflow management."""

    def test_start_downloads_single_cloudcast(self, download_manager, sample_cloudcasts, temp_dir):
        """Test starting downloads for single cloudcast."""
        signal_slot = _RecordingSlot()
        download_manager.workflow_started.connect(signal_slot)

        # Start with one cloudcast
        download_manager.start_downloads([sample_cloudcasts[0]], str(temp_dir))

        # Should emit workflow started signal
        signal_slot.assert_called_once()

        # Should track the active download
        assert len(download_manager.active_downloads) == 1
        assert sample_cloudcasts[0].url in download_manager.active_downloads
        assert not download_manager.cancelled

    def test_start_downloads_multiple_cloudcasts(
        self, download_manager, sample_cloudcasts, temp_dir
    ):
        """Test starting downloads for multiple cloudcasts."""
        download_manager.start_downloads(sample_cloudcasts, str(temp_dir))

        # Should track all active downloads
        assert len(download_manager.active_downloads) == 2
        assert sample_cloudcasts[0].url in download_manager.active_downloads
        assert sample_cloudcasts[1].url in download_manager.active_downloads

    def test_start_downloads_empty_list(self, download_manager, temp_dir):
        """Test starting downloads with empty cloudcast list."""
        signal_slot = _RecordingSlot()
        download_manager.workflow_started.connect(signal_slot)

        download_manager.start_downloads([], str(temp_dir))

        # Should not emit signal or track anything
        signal_slot.assert_not_called()
        assert len(download_manager.active_downloads) == 0

    def test_start_downloads_duplicate_prevention(
        self, download_manager, sample_cloudcasts, temp_dir
    ):
        """Test prevention of duplicate downloads."""
        # Start downloads twice
        download_manager.start_downloads([sample_cloudcasts[0]], str(temp_dir))
        download_manager.start_downloads([sample_cloudcasts[0]], str(temp_dir))

        # Should only track one instance
        assert len(download_manager.active_downloads) == 1


@pytest.mark.unit
class TestCancellationHandling:
    """Test download and conversion cancellation."""

    def test_cancel_all_downloads(self, download_manager, sample_cloudcasts, temp_dir):
        """Test cancelling all active downloads."""
        # Start some downloads
        download_manager.start_downloads(sample_cloudcasts, str(temp_dir))

        # Cancel all
        download_manager.cancel_all()

        # Should set cancellation flag
        assert download_manager.cancelled

        # Should cancel all active workers
        for worker in download_manager.active_downloads.values():
            assert worker.cancelled

    def test_cancel_all_conversions(self, download_manager, temp_dir):
        """Test cancelling all active conversions."""
        # Manually add some active conversions
        worker1 = StubConversionWorker("url1", "file1", "mp3", str(temp_dir), None, None, None)
        worker2 = StubConversionWorker("url2", "file2", "mp3", str(temp_dir), None, None, None)
        download_manager.active_conversions["url1"] = worker1
        download_manager.active_conversions["url2"] = worker2

        # Cancel all
        download_manager.cancel_all()

        # Should cancel all conversion workers
        assert worker1.cancelled
        assert worker2.cancelled


@pytest.mark.unit
class TestSignalEmissionSlots:
    """Test thread-safe signal emission slots."""

    def test_emit_progress_signal_slot(self, download_manager):
        """Test progress signal slot emission."""
        signal_slot = _RecordingSlot()
        download_manager.task_progress.connect(signal_slot)

        # Call the slot directly
        download_manager._emit_progress_signal(
            "https://mixcloud.com/test/mix", "Progress 50%", "download"
        )

        signal_slot.assert_called_once_with("https://mixcloud.com/test/mix", "Progress 50%")

    def test_emit_completed_signal_download_no_conversion(
        self, download_manager, stub_license_manager, temp_dir
    ):
        """Test completion signal for download without conversion needed."""
        # Configure as free user (no conversion)
        stub_license_manager.configure_as_free_user()

        # Set up active download (value is a sentinel — only the key is accessed)
        stub_worker = StubDownloadWorker(None, None, None, None, None)
        download_manager.active_downloads["https://mixcloud.com/test/mix"] = stub_worker

        # Recording signal slots
        result_signal = _RecordingSlot()
        finished_signal = _RecordingSlot()
        download_manager.task_result.connect(result_signal)
        download_manager.all_workflows_finished.connect(finished_signal)

        # Call completion slot
        download_manager._emit_completed_signal(
            "https://mixcloud.com/test/mix", str(temp_dir / "test.mp3"), "download"
        )

        # Should emit result signal and remove from tracking
        result_signal.assert_called_once_with(
            "https://mixcloud.com/test/mix", str(temp_dir / "test.mp3"), False
        )
        finished_signal.assert_called_once()  # All workflows finished
        assert "https://mixcloud.com/test/mix" not in download_manager.active_downloads

    def test_emit_completed_signal_download_with_conversion(
        self, download_manager, stub_license_manager, temp_dir
    ):
        """Test completion signal for download that triggers conversion."""
        # Configure as Pro user (conversion enabled)
        stub_license_manager.configure_as_pro_user()

        # Set up active download
        stub_worker = StubDownloadWorker(None, None, None, None, None)
        download_manager.active_downloads["https://mixcloud.com/test/mix"] = stub_worker

        # Recording signal slots
        result_signal = _RecordingSlot()
        finished_signal = _RecordingSlot()
        download_manager.task_result.connect(result_signal)
        download_manager.all_workflows_finished.connect(finished_signal)

        # Call completion slot for .m4a file (different from target mp3)
        download_manager._emit_completed_signal(
            "https://mixcloud.com/test/mix", str(temp_dir / "test.m4a"), "download"
        )

        # Should emit result signal immediately with will_convert=True
        result_signal.assert_called_once_with(
            "https://mixcloud.com/test/mix", str(temp_dir / "test.m4a"), True
        )
        finished_signal.assert_not_called()  # Still have active conversion

        # Should start conversion and track it
        assert "https://mixcloud.com/test/mix" in download_manager.active_conversions
        assert "https://mixcloud.com/test/mix" not in download_manager.active_downloads

    def test_emit_completed_signal_conversion(self, download_manager):
        """Test completion signal for conversion."""
        # Set up active conversion
        stub_worker = StubConversionWorker(None, None, None, None, None, None, None)
        download_manager.active_conversions["https://mixcloud.com/test/mix"] = stub_worker

        # Recording signal slots
        result_signal = _RecordingSlot()
        finished_signal = _RecordingSlot()
        download_manager.task_result.connect(result_signal)
        download_manager.all_workflows_finished.connect(finished_signal)

        # Call completion slot
        download_manager._emit_completed_signal(
            "https://mixcloud.com/test/mix", "/path/to/converted.mp3", "conversion"
        )

        # Should emit result signal and remove from tracking
        result_signal.assert_called_once_with(
            "https://mixcloud.com/test/mix", "/path/to/converted.mp3", False
        )
        finished_signal.assert_called_once()
        assert "https://mixcloud.com/test/mix" not in download_manager.active_conversions

    def test_emit_error_signal_download(self, download_manager):
        """Test error signal for download."""
        # Set up active download
        stub_worker = StubDownloadWorker(None, None, None, None, None)
        download_manager.active_downloads["https://mixcloud.com/test/mix"] = stub_worker

        # Recording signal slots
        error_signal = _RecordingSlot()
        finished_signal = _RecordingSlot()
        download_manager.task_error.connect(error_signal)
        download_manager.all_workflows_finished.connect(finished_signal)

        # Call error slot
        download_manager._emit_error_signal(
            "https://mixcloud.com/test/mix", "Download failed: Network error", "download"
        )

        # Should emit error signal and remove from tracking
        error_signal.assert_called_once_with(
            "https://mixcloud.com/test/mix", "Download failed: Network error"
        )
        finished_signal.assert_called_once()
        assert "https://mixcloud.com/test/mix" not in download_manager.active_downloads

    def test_emit_error_signal_conversion(self, download_manager):
        """Test error signal for conversion."""
        # Set up active conversion
        stub_worker = StubConversionWorker(None, None, None, None, None, None, None)
        download_manager.active_conversions["https://mixcloud.com/test/mix"] = stub_worker

        # Recording signal slots
        error_signal = _RecordingSlot()
        finished_signal = _RecordingSlot()
        download_manager.task_error.connect(error_signal)
        download_manager.all_workflows_finished.connect(finished_signal)

        # Call error slot
        download_manager._emit_error_signal(
            "https://mixcloud.com/test/mix", "Conversion failed: FFmpeg error", "conversion"
        )

        # Should emit error signal and remove from tracking
        error_signal.assert_called_once_with(
            "https://mixcloud.com/test/mix", "Conversion failed: FFmpeg error"
        )
        finished_signal.assert_called_once()
        assert "https://mixcloud.com/test/mix" not in download_manager.active_conversions


@pytest.mark.unit
class TestWorkflowManagement:
    """Test workflow start/finish coordination."""

    def test_workflow_started_emitted_from_idle(
        self, download_manager, sample_cloudcasts, temp_dir
    ):
        """Test workflow_started signal emitted when transitioning from idle."""
        signal_slot = _RecordingSlot()
        download_manager.workflow_started.connect(signal_slot)

        # Should emit when starting from idle state
        download_manager.start_downloads([sample_cloudcasts[0]], str(temp_dir))
        signal_slot.assert_called_once()

        # Should not emit again when already active
        signal_slot.reset_mock()
        download_manager.start_downloads([sample_cloudcasts[1]], str(temp_dir))
        signal_slot.assert_not_called()

    def test_all_workflows_finished_coordination(self, download_manager):
        """Test all_workflows_finished signal coordination."""
        signal_slot = _RecordingSlot()
        download_manager.all_workflows_finished.connect(signal_slot)

        # Manually add some active tasks (sentinels — only keys matter for _check_all_finished)
        download_manager.active_downloads["url1"] = StubDownloadWorker(None, None, None, None, None)
        download_manager.active_conversions["url2"] = StubConversionWorker(
            None, None, None, None, None, None, None
        )

        # Check when downloads finish but conversions remain
        download_manager._check_all_finished()
        signal_slot.assert_not_called()

        # Clear downloads, check again
        download_manager.active_downloads.clear()
        download_manager._check_all_finished()
        signal_slot.assert_not_called()

        # Clear conversions, now should emit
        download_manager.active_conversions.clear()
        download_manager._check_all_finished()
        signal_slot.assert_called_once()


@pytest.mark.integration
class TestDownloadManagerIntegration:
    """Integration tests for DownloadManager workflow scenarios."""

    def test_complete_pro_user_workflow(
        self, download_manager, stub_license_manager, sample_cloudcasts, temp_dir
    ):
        """Test complete workflow for Pro user with conversion."""
        # Configure as Pro user
        stub_license_manager.configure_as_pro_user()

        # Recording signal slots
        workflow_started = _RecordingSlot()
        workflow_finished = _RecordingSlot()
        task_progress = _RecordingSlot()
        task_result = _RecordingSlot()

        download_manager.workflow_started.connect(workflow_started)
        download_manager.all_workflows_finished.connect(workflow_finished)
        download_manager.task_progress.connect(task_progress)
        download_manager.task_result.connect(task_result)

        # Start downloads
        download_manager.start_downloads([sample_cloudcasts[0]], str(temp_dir))

        # Verify workflow started
        workflow_started.assert_called_once()
        assert len(download_manager.active_downloads) == 1

        # Simulate download completion (triggers conversion for Pro users)
        download_manager._emit_completed_signal(
            sample_cloudcasts[0].url, str(temp_dir / "test.m4a"), "download"
        )

        # Should emit download result with will_convert=True, then start conversion
        task_result.assert_called_once_with(
            sample_cloudcasts[0].url, str(temp_dir / "test.m4a"), True
        )
        workflow_finished.assert_not_called()  # Still have active conversion
        assert len(download_manager.active_conversions) == 1
        assert len(download_manager.active_downloads) == 0

        # Reset slot for conversion completion test
        task_result.reset_mock()

        # Simulate conversion completion
        download_manager._emit_completed_signal(
            sample_cloudcasts[0].url, str(temp_dir / "test.mp3"), "conversion"
        )

        # Now should emit final result and workflow finished
        task_result.assert_called_once_with(
            sample_cloudcasts[0].url, str(temp_dir / "test.mp3"), False
        )
        workflow_finished.assert_called_once()
        assert len(download_manager.active_conversions) == 0

    def test_complete_free_user_workflow(
        self, download_manager, stub_license_manager, sample_cloudcasts, temp_dir
    ):
        """Test complete workflow for free user without conversion."""
        # Configure as free user
        stub_license_manager.configure_as_free_user()

        # Recording signal slots
        workflow_started = _RecordingSlot()
        workflow_finished = _RecordingSlot()
        task_result = _RecordingSlot()

        download_manager.workflow_started.connect(workflow_started)
        download_manager.all_workflows_finished.connect(workflow_finished)
        download_manager.task_result.connect(task_result)

        # Start downloads
        download_manager.start_downloads([sample_cloudcasts[0]], str(temp_dir))

        # Verify workflow started
        workflow_started.assert_called_once()
        assert len(download_manager.active_downloads) == 1

        # Simulate download completion (no conversion for free users)
        download_manager._emit_completed_signal(
            sample_cloudcasts[0].url, str(temp_dir / "test.m4a"), "download"
        )

        # Should emit final result immediately
        task_result.assert_called_once_with(
            sample_cloudcasts[0].url, str(temp_dir / "test.m4a"), False
        )
        workflow_finished.assert_called_once()
        assert len(download_manager.active_downloads) == 0
        assert len(download_manager.active_conversions) == 0


@pytest.mark.unit
class TestConversionTriggerLogic:
    """Test logic for when conversions are triggered."""

    def test_conversion_needed_different_formats(
        self, download_manager, stub_license_manager, temp_dir
    ):
        """Test conversion triggered when formats differ."""
        stub_license_manager.configure_as_pro_user()

        # Enable conversion in settings
        download_manager.settings_manager.enable_audio_conversion = True
        download_manager.settings_manager.preferred_audio_format = "mp3"

        # Call with .m4a file (different from mp3 target)
        stub_worker = StubDownloadWorker(None, None, None, None, None)
        download_manager.active_downloads["test_url"] = stub_worker
        download_manager._emit_completed_signal("test_url", str(temp_dir / "test.m4a"), "download")

        # Should start conversion
        assert "test_url" in download_manager.active_conversions

    def test_conversion_skipped_same_formats(
        self, download_manager, stub_license_manager, temp_dir
    ):
        """Test conversion skipped when formats match."""
        stub_license_manager.configure_as_pro_user()

        # Enable conversion in settings
        download_manager.settings_manager.enable_audio_conversion = True
        download_manager.settings_manager.preferred_audio_format = "mp3"

        # Recording result signal
        result_signal = _RecordingSlot()
        download_manager.task_result.connect(result_signal)

        # Call with .mp3 file (same as target format)
        stub_worker = StubDownloadWorker(None, None, None, None, None)
        download_manager.active_downloads["test_url"] = stub_worker
        download_manager._emit_completed_signal("test_url", str(temp_dir / "test.mp3"), "download")

        # Should NOT start conversion, emit result immediately
        assert "test_url" not in download_manager.active_conversions
        result_signal.assert_called_once_with("test_url", str(temp_dir / "test.mp3"), False)

    def test_conversion_skipped_free_user(self, download_manager, stub_license_manager, temp_dir):
        """Test conversion skipped for free users regardless of format."""
        stub_license_manager.configure_as_free_user()

        # Recording result signal
        result_signal = _RecordingSlot()
        download_manager.task_result.connect(result_signal)

        # Call with .m4a file (different from mp3 target) as free user
        stub_worker = StubDownloadWorker(None, None, None, None, None)
        download_manager.active_downloads["test_url"] = stub_worker
        download_manager._emit_completed_signal("test_url", str(temp_dir / "test.m4a"), "download")

        # Should NOT start conversion, emit result immediately
        assert "test_url" not in download_manager.active_conversions
        result_signal.assert_called_once_with("test_url", str(temp_dir / "test.m4a"), False)


@pytest.mark.unit
class TestDownloadManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_thread_pool_size_updates(self, download_manager, stub_settings_manager):
        """Test thread pool sizes update when settings change."""
        # Update property values on the stub
        stub_settings_manager.max_parallel_downloads = 5
        stub_settings_manager.max_parallel_conversions = 3

        # Update thread pool sizes
        download_manager._update_thread_pool_sizes()

        # Should reflect new settings
        assert download_manager.download_pool.maxThreadCount() == 5
        assert download_manager.conversion_pool.maxThreadCount() == 3

    def test_error_handling_removes_from_tracking(self, download_manager):
        """Test error handling properly cleans up tracking."""
        # Set up active tasks
        download_manager.active_downloads["url1"] = StubDownloadWorker(None, None, None, None, None)
        download_manager.active_conversions["url2"] = StubConversionWorker(
            None, None, None, None, None, None, None
        )

        # Simulate errors
        download_manager._emit_error_signal("url1", "Error message", "download")
        download_manager._emit_error_signal("url2", "Error message", "conversion")

        # Should remove from tracking
        assert "url1" not in download_manager.active_downloads
        assert "url2" not in download_manager.active_conversions

    def test_conversion_disabled_pro_user(self, temp_dir):
        """Test Pro user with conversion disabled skips conversion."""
        # Set up settings with conversion disabled
        settings_manager = _make_stub_settings(enable_audio_conversion=False)
        license_manager = MagicMock(spec=LicenseManager)
        license_manager.is_pro = True

        download_manager = DownloadManager(
            settings_manager=settings_manager,
            license_manager=license_manager,
            conversion_worker_class=StubConversionWorker,
        )

        # Use patch.object on the test-provided instance to track _start_conversion calls
        start_conversion_calls: list[tuple] = []

        def _stub_start_conversion(cloudcast_url, downloaded_file):
            start_conversion_calls.append((cloudcast_url, downloaded_file))

        download_manager._start_conversion = _stub_start_conversion

        # Simulate download completion
        test_file = str(temp_dir / "test_file.webm")
        download_manager._emit_completed_signal("test_url", test_file, "download")

        # Conversion should not be started
        assert len(start_conversion_calls) == 0

    def test_conversion_enabled_pro_user(self, temp_dir):
        """Test Pro user with conversion enabled proceeds normally."""
        # Set up settings with conversion enabled
        settings_manager = _make_stub_settings(enable_audio_conversion=True)
        license_manager = MagicMock(spec=LicenseManager)
        license_manager.is_pro = True

        download_manager = DownloadManager(
            settings_manager=settings_manager,
            license_manager=license_manager,
            conversion_worker_class=StubConversionWorker,
        )

        # Track _start_conversion calls using a stub replacement
        start_conversion_calls: list[tuple] = []

        def _stub_start_conversion(cloudcast_url, downloaded_file):
            start_conversion_calls.append((cloudcast_url, downloaded_file))

        download_manager._start_conversion = _stub_start_conversion

        # Simulate download completion with different format
        test_file = str(temp_dir / "test_file.webm")
        download_manager._emit_completed_signal("test_url", test_file, "download")

        # Conversion should be started (webm != mp3)
        assert len(start_conversion_calls) == 1
        assert start_conversion_calls[0] == ("test_url", test_file)

    def test_conversion_setting_false_no_conversion(self, temp_dir):
        """Test that setting=False prevents conversion."""
        settings_manager = _make_stub_settings(enable_audio_conversion=False)
        license_manager = MagicMock(spec=LicenseManager)
        license_manager.is_pro = True

        download_manager = DownloadManager(
            settings_manager=settings_manager,
            license_manager=license_manager,
            conversion_worker_class=StubConversionWorker,
        )

        start_conversion_calls: list[tuple] = []

        def _stub_start_conversion(cloudcast_url, downloaded_file):
            start_conversion_calls.append((cloudcast_url, downloaded_file))

        download_manager._start_conversion = _stub_start_conversion

        # Set up active download tracking (required for _emit_completed_signal)
        download_manager.active_downloads["test_url"] = StubDownloadWorker(
            None, None, None, None, None
        )

        # Simulate download completion - this is where setting check happens
        test_file = str(temp_dir / "test_file.webm")
        download_manager._emit_completed_signal("test_url", test_file, "download")

        # Conversion should not be started due to setting=False
        assert len(start_conversion_calls) == 0

    def test_conversion_setting_true_allows_conversion(self, temp_dir):
        """Test that setting=True allows conversion."""
        settings_manager = _make_stub_settings(enable_audio_conversion=True)
        license_manager = MagicMock(spec=LicenseManager)
        license_manager.is_pro = True

        download_manager = DownloadManager(
            settings_manager=settings_manager,
            license_manager=license_manager,
            conversion_worker_class=StubConversionWorker,
        )

        start_conversion_calls: list[tuple] = []

        def _stub_start_conversion(cloudcast_url, downloaded_file):
            start_conversion_calls.append((cloudcast_url, downloaded_file))

        download_manager._start_conversion = _stub_start_conversion

        # Set up active download tracking (required for _emit_completed_signal)
        download_manager.active_downloads["test_url"] = StubDownloadWorker(
            None, None, None, None, None
        )

        # Simulate download completion with different format - this is where setting check happens
        test_file = str(temp_dir / "test_file.webm")
        download_manager._emit_completed_signal("test_url", test_file, "download")

        # Conversion should be started due to setting=True and format difference
        assert len(start_conversion_calls) == 1
        assert start_conversion_calls[0] == ("test_url", test_file)

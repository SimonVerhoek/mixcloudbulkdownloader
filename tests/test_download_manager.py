"""Comprehensive tests for DownloadManager using PyQt threading patterns."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from PySide6.QtCore import Q_ARG, QMetaObject, QObject, QRunnable, Qt, QThreadPool

from app.consts.settings import (
    DEFAULT_ENABLE_AUDIO_CONVERSION,
    SETTING_ENABLE_AUDIO_CONVERSION,
)
from app.data_classes import Cloudcast, MixcloudUser
from app.services.download_manager import CallbackBridge, DownloadManager
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


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def stub_settings_manager():
    """Create stub settings manager."""
    settings = Mock()
    settings.get = Mock(
        side_effect=lambda key, default=None: {
            "max_parallel_downloads": 3,
            "max_parallel_conversions": 2,
            "preferred_audio_format": "mp3",
            SETTING_ENABLE_AUDIO_CONVERSION: True,  # Enable by default for tests
        }.get(key, default)
    )

    # Add property attributes for new property-based interface
    settings.max_parallel_downloads = 3
    settings.max_parallel_conversions = 2
    settings.preferred_audio_format = "mp3"
    settings.enable_audio_conversion = True

    return settings


@pytest.fixture
def stub_license_manager():
    """Create stub license manager."""
    return StubLicenseManager()


@pytest.fixture
def download_manager(stub_settings_manager, stub_license_manager):
    """Create DownloadManager instance for testing."""
    return DownloadManager(
        settings_manager=stub_settings_manager, license_manager=stub_license_manager
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
        assert hasattr(download_manager, "workflow_started")
        assert hasattr(download_manager, "all_workflows_finished")

        # Task signals
        assert hasattr(download_manager, "task_progress")
        assert hasattr(download_manager, "task_result")
        assert hasattr(download_manager, "task_error")
        assert hasattr(download_manager, "task_cancelled")
        assert hasattr(download_manager, "task_finished")

    def test_thread_pool_size_configuration(self, download_manager):
        """Test thread pool sizes are configured from settings."""
        # Settings mock returns max_downloads=3, max_conversions=2
        assert download_manager.download_pool.maxThreadCount() == 3
        assert download_manager.conversion_pool.maxThreadCount() == 2


class TestCallbackBridge:
    """Test CallbackBridge thread-safe signal emission."""

    def test_callback_bridge_initialization(self, download_manager):
        """Test CallbackBridge initializes correctly."""
        bridge = CallbackBridge(download_manager)
        assert bridge.download_manager == download_manager

    @patch("app.services.download_manager.QMetaObject.invokeMethod")
    def test_emit_progress(self, mock_invoke, download_manager):
        """Test progress signal emission through CallbackBridge."""
        bridge = CallbackBridge(download_manager)

        bridge.emit_progress("https://mixcloud.com/test/mix", "Progress 50%", "download")

        # Verify the call was made with correct method and connection type
        mock_invoke.assert_called_once()
        call_args = mock_invoke.call_args
        assert call_args[0][0] == download_manager
        assert call_args[0][1] == "_emit_progress_signal"
        assert call_args[0][2] == Qt.QueuedConnection
        # Don't test Q_ARG objects directly as they're new instances each time

    @patch("app.services.download_manager.QMetaObject.invokeMethod")
    def test_emit_completed(self, mock_invoke, download_manager):
        """Test completion signal emission through CallbackBridge."""
        bridge = CallbackBridge(download_manager)

        bridge.emit_completed("https://mixcloud.com/test/mix", "/path/to/file.m4a", "download")

        # Verify the call was made with correct method and connection type
        mock_invoke.assert_called_once()
        call_args = mock_invoke.call_args
        assert call_args[0][0] == download_manager
        assert call_args[0][1] == "_emit_completed_signal"
        assert call_args[0][2] == Qt.QueuedConnection

    @patch("app.services.download_manager.QMetaObject.invokeMethod")
    def test_emit_error(self, mock_invoke, download_manager):
        """Test error signal emission through CallbackBridge."""
        bridge = CallbackBridge(download_manager)

        bridge.emit_error("https://mixcloud.com/test/mix", "Download failed", "download")

        # Verify the call was made with correct method and connection type
        mock_invoke.assert_called_once()
        call_args = mock_invoke.call_args
        assert call_args[0][0] == download_manager
        assert call_args[0][1] == "_emit_error_signal"
        assert call_args[0][2] == Qt.QueuedConnection


@pytest.mark.unit
class TestDownloadWorkflow:
    """Test download workflow management."""

    def test_start_downloads_single_cloudcast(self, download_manager, sample_cloudcasts, temp_dir):
        """Test starting downloads for single cloudcast."""
        with patch("app.services.download_worker.DownloadWorker", StubDownloadWorker):
            signal_mock = Mock()
            download_manager.workflow_started.connect(signal_mock)

            # Start with one cloudcast
            download_manager.start_downloads([sample_cloudcasts[0]], str(temp_dir))

            # Should emit workflow started signal
            signal_mock.assert_called_once()

            # Should track the active download
            assert len(download_manager.active_downloads) == 1
            assert sample_cloudcasts[0].url in download_manager.active_downloads
            assert not download_manager.cancelled

    def test_start_downloads_multiple_cloudcasts(
        self, download_manager, sample_cloudcasts, temp_dir
    ):
        """Test starting downloads for multiple cloudcasts."""
        with patch("app.services.download_worker.DownloadWorker", StubDownloadWorker):
            download_manager.start_downloads(sample_cloudcasts, str(temp_dir))

            # Should track all active downloads
            assert len(download_manager.active_downloads) == 2
            assert sample_cloudcasts[0].url in download_manager.active_downloads
            assert sample_cloudcasts[1].url in download_manager.active_downloads

    def test_start_downloads_empty_list(self, download_manager, temp_dir):
        """Test starting downloads with empty cloudcast list."""
        signal_mock = Mock()
        download_manager.workflow_started.connect(signal_mock)

        download_manager.start_downloads([], str(temp_dir))

        # Should not emit signal or track anything
        signal_mock.assert_not_called()
        assert len(download_manager.active_downloads) == 0

    def test_start_downloads_duplicate_prevention(
        self, download_manager, sample_cloudcasts, temp_dir
    ):
        """Test prevention of duplicate downloads."""
        with patch("app.services.download_worker.DownloadWorker", StubDownloadWorker):
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
        with patch("app.services.download_worker.DownloadWorker", StubDownloadWorker):
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
        signal_mock = Mock()
        download_manager.task_progress.connect(signal_mock)

        # Call the slot directly
        download_manager._emit_progress_signal(
            "https://mixcloud.com/test/mix", "Progress 50%", "download"
        )

        signal_mock.assert_called_once_with("https://mixcloud.com/test/mix", "Progress 50%")

    def test_emit_completed_signal_download_no_conversion(
        self, download_manager, stub_license_manager, temp_dir
    ):
        """Test completion signal for download without conversion needed."""
        # Configure as free user (no conversion)
        stub_license_manager.configure_as_free_user()

        # Set up active download
        download_manager.active_downloads["https://mixcloud.com/test/mix"] = Mock()

        # Mock signals
        result_signal = Mock()
        finished_signal = Mock()
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

    @patch("app.services.conversion_worker.ConversionWorker", StubConversionWorker)
    def test_emit_completed_signal_download_with_conversion(
        self, download_manager, stub_license_manager, temp_dir
    ):
        """Test completion signal for download that triggers conversion."""
        # Configure as Pro user (conversion enabled)
        stub_license_manager.configure_as_pro_user()

        # Set up active download
        download_manager.active_downloads["https://mixcloud.com/test/mix"] = Mock()

        # Mock signals - should NOT emit result yet (waiting for conversion)
        result_signal = Mock()
        finished_signal = Mock()
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
        download_manager.active_conversions["https://mixcloud.com/test/mix"] = Mock()

        # Mock signals
        result_signal = Mock()
        finished_signal = Mock()
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
        download_manager.active_downloads["https://mixcloud.com/test/mix"] = Mock()

        # Mock signals
        error_signal = Mock()
        finished_signal = Mock()
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
        download_manager.active_conversions["https://mixcloud.com/test/mix"] = Mock()

        # Mock signals
        error_signal = Mock()
        finished_signal = Mock()
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
        signal_mock = Mock()
        download_manager.workflow_started.connect(signal_mock)

        with patch("app.services.download_worker.DownloadWorker", StubDownloadWorker):
            # Should emit when starting from idle state
            download_manager.start_downloads([sample_cloudcasts[0]], str(temp_dir))
            signal_mock.assert_called_once()

            # Should not emit again when already active
            signal_mock.reset_mock()
            download_manager.start_downloads([sample_cloudcasts[1]], str(temp_dir))
            signal_mock.assert_not_called()

    def test_all_workflows_finished_coordination(self, download_manager):
        """Test all_workflows_finished signal coordination."""
        signal_mock = Mock()
        download_manager.all_workflows_finished.connect(signal_mock)

        # Manually add some active tasks
        download_manager.active_downloads["url1"] = Mock()
        download_manager.active_conversions["url2"] = Mock()

        # Check when downloads finish but conversions remain
        download_manager._check_all_finished()
        signal_mock.assert_not_called()

        # Clear downloads, check again
        download_manager.active_downloads.clear()
        download_manager._check_all_finished()
        signal_mock.assert_not_called()

        # Clear conversions, now should emit
        download_manager.active_conversions.clear()
        download_manager._check_all_finished()
        signal_mock.assert_called_once()


@pytest.mark.integration
class TestDownloadManagerIntegration:
    """Integration tests for DownloadManager workflow scenarios."""

    def test_complete_pro_user_workflow(
        self, download_manager, stub_license_manager, sample_cloudcasts, temp_dir
    ):
        """Test complete workflow for Pro user with conversion."""
        with patch("app.services.download_worker.DownloadWorker", StubDownloadWorker):
            with patch("app.services.conversion_worker.ConversionWorker", StubConversionWorker):
                # Configure as Pro user
                stub_license_manager.configure_as_pro_user()

                # Mock all relevant signals
                workflow_started = Mock()
                workflow_finished = Mock()
                task_progress = Mock()
                task_result = Mock()

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

                # Reset mock for conversion completion test
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
        with patch("app.services.download_worker.DownloadWorker", StubDownloadWorker):
            # Configure as free user
            stub_license_manager.configure_as_free_user()

            # Mock all relevant signals
            workflow_started = Mock()
            workflow_finished = Mock()
            task_result = Mock()

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
        download_manager.settings_manager.get = Mock(
            side_effect=lambda key, default=None: {
                "max_parallel_downloads": 3,
                "max_parallel_conversions": 2,
                "preferred_audio_format": "mp3",
                SETTING_ENABLE_AUDIO_CONVERSION: True,
            }.get(key, default)
        )

        # Add property attributes for new property-based interface
        download_manager.settings_manager.max_parallel_downloads = 3
        download_manager.settings_manager.max_parallel_conversions = 2
        download_manager.settings_manager.preferred_audio_format = "mp3"
        download_manager.settings_manager.enable_audio_conversion = True

        # Settings return mp3 as target format
        with patch("app.services.conversion_worker.ConversionWorker", StubConversionWorker):
            # Call with .m4a file (different from mp3 target)
            download_manager.active_downloads["test_url"] = Mock()
            download_manager._emit_completed_signal(
                "test_url", str(temp_dir / "test.m4a"), "download"
            )

            # Should start conversion
            assert "test_url" in download_manager.active_conversions

    def test_conversion_skipped_same_formats(
        self, download_manager, stub_license_manager, temp_dir
    ):
        """Test conversion skipped when formats match."""
        stub_license_manager.configure_as_pro_user()

        # Enable conversion in settings
        download_manager.settings_manager.get = Mock(
            side_effect=lambda key, default=None: {
                "max_parallel_downloads": 3,
                "max_parallel_conversions": 2,
                "preferred_audio_format": "mp3",
                SETTING_ENABLE_AUDIO_CONVERSION: True,
            }.get(key, default)
        )

        # Add property attributes for new property-based interface
        download_manager.settings_manager.max_parallel_downloads = 3
        download_manager.settings_manager.max_parallel_conversions = 2
        download_manager.settings_manager.preferred_audio_format = "mp3"
        download_manager.settings_manager.enable_audio_conversion = True

        # Mock result signal
        result_signal = Mock()
        download_manager.task_result.connect(result_signal)

        # Call with .mp3 file (same as target format)
        download_manager.active_downloads["test_url"] = Mock()
        download_manager._emit_completed_signal("test_url", str(temp_dir / "test.mp3"), "download")

        # Should NOT start conversion, emit result immediately
        assert "test_url" not in download_manager.active_conversions
        result_signal.assert_called_once_with("test_url", str(temp_dir / "test.mp3"), False)

    def test_conversion_skipped_free_user(self, download_manager, stub_license_manager, temp_dir):
        """Test conversion skipped for free users regardless of format."""
        stub_license_manager.configure_as_free_user()

        # Mock result signal
        result_signal = Mock()
        download_manager.task_result.connect(result_signal)

        # Call with .m4a file (different from mp3 target) as free user
        download_manager.active_downloads["test_url"] = Mock()
        download_manager._emit_completed_signal("test_url", str(temp_dir / "test.m4a"), "download")

        # Should NOT start conversion, emit result immediately
        assert "test_url" not in download_manager.active_conversions
        result_signal.assert_called_once_with("test_url", str(temp_dir / "test.m4a"), False)


@pytest.mark.unit
class TestDownloadManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_thread_pool_size_updates(self, download_manager, stub_settings_manager):
        """Test thread pool sizes update when settings change."""
        # Change settings mock return values
        stub_settings_manager.get.side_effect = lambda key, default=None: {
            "max_parallel_downloads": 5,
            "max_parallel_conversions": 3,
            "preferred_audio_format": "flac",
        }.get(key, default)

        # Update property attributes for new property-based interface
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
        download_manager.active_downloads["url1"] = Mock()
        download_manager.active_conversions["url2"] = Mock()

        # Simulate errors
        download_manager._emit_error_signal("url1", "Error message", "download")
        download_manager._emit_error_signal("url2", "Error message", "conversion")

        # Should remove from tracking
        assert "url1" not in download_manager.active_downloads
        assert "url2" not in download_manager.active_conversions

    def test_conversion_disabled_pro_user(self, temp_dir):
        """Test Pro user with conversion disabled skips conversion."""
        # Set up settings with conversion disabled
        settings_manager = Mock()
        settings_manager.get = Mock(
            side_effect=lambda key, default=None: {
                SETTING_ENABLE_AUDIO_CONVERSION: False,
                "preferred_audio_format": "mp3",
            }.get(key, default)
        )

        # Add property attributes for new property-based interface
        settings_manager.enable_audio_conversion = False
        settings_manager.preferred_audio_format = "mp3"
        settings_manager.max_parallel_downloads = 3
        settings_manager.max_parallel_conversions = 2

        # Set up Pro license manager
        license_manager = Mock()
        license_manager.is_pro = True

        download_manager = DownloadManager(
            settings_manager=settings_manager, license_manager=license_manager
        )

        # Mock _start_conversion to track calls
        with patch.object(download_manager, "_start_conversion") as mock_start_conversion:
            # Simulate download completion
            test_file = str(temp_dir / "test_file.webm")
            download_manager._emit_completed_signal("test_url", test_file, "download")

            # Conversion should not be started
            mock_start_conversion.assert_not_called()

    def test_conversion_enabled_pro_user(self, temp_dir):
        """Test Pro user with conversion enabled proceeds normally."""
        # Set up settings with conversion enabled
        settings_manager = Mock()
        settings_manager.get = Mock(
            side_effect=lambda key, default=None: {
                SETTING_ENABLE_AUDIO_CONVERSION: True,
                "preferred_audio_format": "mp3",
            }.get(key, default)
        )

        # Add property attributes for new property-based interface
        settings_manager.enable_audio_conversion = True
        settings_manager.preferred_audio_format = "mp3"
        settings_manager.max_parallel_downloads = 3
        settings_manager.max_parallel_conversions = 2

        # Set up Pro license manager
        license_manager = Mock()
        license_manager.is_pro = True

        download_manager = DownloadManager(
            settings_manager=settings_manager, license_manager=license_manager
        )

        # Mock _start_conversion to track calls
        with patch.object(download_manager, "_start_conversion") as mock_start_conversion:
            # Simulate download completion with different format
            test_file = str(temp_dir / "test_file.webm")
            download_manager._emit_completed_signal("test_url", test_file, "download")

            # Conversion should be started (webm != mp3)
            mock_start_conversion.assert_called_once_with("test_url", test_file)

    def test_conversion_setting_false_no_conversion(self, temp_dir):
        """Test that setting=False prevents conversion."""
        # Set up settings with conversion disabled
        settings_manager = Mock()
        settings_manager.get = Mock(
            side_effect=lambda key, default=None: {
                SETTING_ENABLE_AUDIO_CONVERSION: False,
                "preferred_audio_format": "mp3",
            }.get(key, default)
        )

        # Add property attributes for new property-based interface
        settings_manager.enable_audio_conversion = False
        settings_manager.preferred_audio_format = "mp3"
        settings_manager.max_parallel_downloads = 3
        settings_manager.max_parallel_conversions = 2

        license_manager = Mock()
        license_manager.is_pro = True

        download_manager = DownloadManager(
            settings_manager=settings_manager, license_manager=license_manager
        )

        # Mock _start_conversion to track calls (setting check happens in caller)
        with patch.object(download_manager, "_start_conversion") as mock_start_conversion:
            # Set up active download tracking (required for _emit_completed_signal)
            download_manager.active_downloads["test_url"] = Mock()

            # Simulate download completion - this is where setting check happens
            test_file = str(temp_dir / "test_file.webm")
            download_manager._emit_completed_signal("test_url", test_file, "download")

            # Conversion should not be started due to setting=False
            mock_start_conversion.assert_not_called()

    def test_conversion_setting_true_allows_conversion(self, temp_dir):
        """Test that setting=True allows conversion."""
        # Set up settings with conversion enabled
        settings_manager = Mock()
        settings_manager.get = Mock(
            side_effect=lambda key, default=None: {
                SETTING_ENABLE_AUDIO_CONVERSION: True,
                "preferred_audio_format": "mp3",
            }.get(key, default)
        )

        # Add property attributes for new property-based interface
        settings_manager.enable_audio_conversion = True
        settings_manager.preferred_audio_format = "mp3"
        settings_manager.max_parallel_downloads = 3
        settings_manager.max_parallel_conversions = 2

        license_manager = Mock()
        license_manager.is_pro = True

        download_manager = DownloadManager(
            settings_manager=settings_manager, license_manager=license_manager
        )

        # Mock _start_conversion to track calls (setting check happens in caller)
        with patch.object(download_manager, "_start_conversion") as mock_start_conversion:
            # Set up active download tracking (required for _emit_completed_signal)
            download_manager.active_downloads["test_url"] = Mock()

            # Simulate download completion with different format - this is where setting check happens
            test_file = str(temp_dir / "test_file.webm")
            download_manager._emit_completed_signal("test_url", test_file, "download")

            # Conversion should be started due to setting=True and format difference
            mock_start_conversion.assert_called_once_with("test_url", test_file)

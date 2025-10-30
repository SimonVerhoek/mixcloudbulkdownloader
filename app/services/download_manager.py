"""New download manager using proper PyQt threading patterns.

This module provides a replacement for DownloadOrchestrator that follows proper
PyQt threading patterns using QObject workers and thread-safe signal emission.
"""

from pathlib import Path
from typing import Dict

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt, QThreadPool, Signal, Slot

from app.consts.settings import (
    DEFAULT_MAX_PARALLEL_CONVERSIONS,
    DEFAULT_MAX_PARALLEL_DOWNLOADS,
    SETTING_MAX_PARALLEL_CONVERSIONS,
    SETTING_MAX_PARALLEL_DOWNLOADS,
)
from app.data_classes import Cloudcast
from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager


class CallbackBridge:
    """Thread-safe callback bridge for worker-to-main-thread signal emission.

    This class provides a safe way for QRunnable workers to emit signals back
    to the main thread without violating Qt's threading rules. It uses
    QMetaObject.invokeMethod with Qt.QueuedConnection for thread-safe operation.
    """

    def __init__(self, download_manager: "DownloadManager"):
        """Initialize callback bridge with target DownloadManager.

        Args:
            download_manager: DownloadManager instance to emit signals through
        """
        self.download_manager = download_manager

    def emit_progress(self, cloudcast_url: str, progress_text: str, task_type: str = "download"):
        """Emit progress update signal in thread-safe manner.

        Args:
            cloudcast_url: Cloudcast URL (task identifier)
            progress_text: Progress information to display
            task_type: Type of task ("download" or "conversion")
        """
        QMetaObject.invokeMethod(
            self.download_manager,
            "_emit_progress_signal",
            Qt.QueuedConnection,
            Q_ARG(str, cloudcast_url),
            Q_ARG(str, progress_text),
            Q_ARG(str, task_type),
        )

    def emit_completed(self, cloudcast_url: str, file_path: str, task_type: str = "download"):
        """Emit task completion signal in thread-safe manner.

        Args:
            cloudcast_url: Cloudcast URL (task identifier)
            file_path: Path to completed file
            task_type: Type of task ("download" or "conversion")
        """
        QMetaObject.invokeMethod(
            self.download_manager,
            "_emit_completed_signal",
            Qt.QueuedConnection,
            Q_ARG(str, cloudcast_url),
            Q_ARG(str, file_path),
            Q_ARG(str, task_type),
        )

    def emit_error(self, cloudcast_url: str, error_msg: str, task_type: str = "download"):
        """Emit task error signal in thread-safe manner.

        Args:
            cloudcast_url: Cloudcast URL (task identifier)
            error_msg: Error message
            task_type: Type of task ("download" or "conversion")
        """
        QMetaObject.invokeMethod(
            self.download_manager,
            "_emit_error_signal",
            Qt.QueuedConnection,
            Q_ARG(str, cloudcast_url),
            Q_ARG(str, error_msg),
            Q_ARG(str, task_type),
        )


class DownloadManager(QObject):
    """Modern download manager using proper PyQt threading patterns.

    This class replaces DownloadOrchestrator with a design that follows Qt best
    practices: QObject workers, thread-safe signal emission, and proper resource
    management using fixed thread pools.

    Key improvements:
    - Uses QRunnable workers with CallbackBridge for thread-safe signals
    - Maintains existing UI integration points (workflow_started/finished signals)
    - Preserves URL-based task identification for UI updates
    - Proper cancellation handling without ctypes interruption
    """

    # Signals matching existing DownloadOrchestrator interface
    workflow_started = Signal()  # Emitted when first download starts
    all_workflows_finished = Signal()  # Emitted when all downloads complete

    # Task-level signals matching existing TaskManager interface
    task_progress = Signal(str, str)  # cloudcast_url, progress_text
    task_result = Signal(str, str, bool)  # cloudcast_url, result_path, will_convert
    task_error = Signal(str, str)  # cloudcast_url, error_message
    task_cancelled = Signal(str)  # cloudcast_url
    task_finished = Signal(str)  # cloudcast_url

    def __init__(
        self,
        settings_manager: SettingsManager,
        license_manager: LicenseManager,
    ):
        """Initialize DownloadManager with thread pools and dependencies.

        Args:
            settings_manager: Settings manager for configuration
            license_manager: License manager for Pro features
        """
        super().__init__()

        self.settings_manager = settings_manager
        self.license_manager = license_manager

        # Create callback bridge for thread-safe signal emission
        self.callback_bridge = CallbackBridge(self)

        # Initialize thread pools with current settings
        self.download_pool = QThreadPool()
        self.conversion_pool = QThreadPool()
        self._update_thread_pool_sizes()

        # Track active tasks and workflows
        self.active_downloads: Dict[str, "DownloadWorker"] = {}  # cloudcast_url -> worker
        self.active_conversions: Dict[str, "ConversionWorker"] = {}  # cloudcast_url -> worker
        self.cancelled = False

    def _update_thread_pool_sizes(self):
        """Update thread pool sizes from current settings."""
        max_downloads = self.settings_manager.get(
            SETTING_MAX_PARALLEL_DOWNLOADS, DEFAULT_MAX_PARALLEL_DOWNLOADS
        )
        max_conversions = self.settings_manager.get(
            SETTING_MAX_PARALLEL_CONVERSIONS, DEFAULT_MAX_PARALLEL_CONVERSIONS
        )

        self.download_pool.setMaxThreadCount(max_downloads)
        self.conversion_pool.setMaxThreadCount(max_conversions)

    def start_downloads(self, cloudcasts: list[Cloudcast], download_dir: str) -> None:
        """Start downloading multiple cloudcasts.

        Args:
            cloudcasts: List of cloudcasts to download
            download_dir: Target directory for downloads
        """
        if not cloudcasts:
            return

        # Update thread pool sizes from current settings
        self._update_thread_pool_sizes()

        # Reset cancellation flag
        self.cancelled = False

        # Emit workflow started signal for UI state management
        was_idle = len(self.active_downloads) == 0 and len(self.active_conversions) == 0
        if was_idle:
            self.workflow_started.emit()

        # Start download workers for all cloudcasts
        for cloudcast in cloudcasts:
            if cloudcast.url not in self.active_downloads:
                # Import here to avoid circular imports
                from app.services.download_worker import DownloadWorker

                worker = DownloadWorker(
                    cloudcast=cloudcast,
                    download_dir=download_dir,
                    callback_bridge=self.callback_bridge,
                    settings_manager=self.settings_manager,
                )

                self.active_downloads[cloudcast.url] = worker
                self.download_pool.start(worker)

    def cancel_all(self) -> None:
        """Cancel all active downloads and conversions."""
        self.cancelled = True

        # Set cancellation flags on all active workers
        for worker in self.active_downloads.values():
            worker.cancel()
        for worker in self.active_conversions.values():
            worker.cancel()

    def _start_conversion_if_needed(self, cloudcast_url: str, downloaded_file: str) -> None:
        """Start conversion worker for Pro users.

        Args:
            cloudcast_url: Cloudcast URL (task identifier)
            downloaded_file: Path to downloaded file
        """
        # Get target format from settings (ensure lowercase for AUDIO_FORMATS lookup)
        target_format = self.settings_manager.get("default_audio_format", "mp3").lower()
        downloaded_path = Path(downloaded_file)

        # Import here to avoid circular imports
        from app.services.conversion_worker import ConversionWorker

        worker = ConversionWorker(
            cloudcast_url=cloudcast_url,
            input_file=downloaded_file,
            target_format=target_format,
            download_dir=str(downloaded_path.parent),
            callback_bridge=self.callback_bridge,
            settings_manager=self.settings_manager,
            license_manager=self.license_manager,
        )

        self.active_conversions[cloudcast_url] = worker
        self.conversion_pool.start(worker)

    def _check_all_finished(self) -> None:
        """Check if all workflows are complete and emit signal if so."""
        if len(self.active_downloads) == 0 and len(self.active_conversions) == 0:
            self.all_workflows_finished.emit()

    # Thread-safe signal emission slots (called by QMetaObject.invokeMethod)
    @Slot(str, str, str)
    def _emit_progress_signal(self, cloudcast_url: str, progress_text: str, task_type: str):
        """Emit progress signal from main thread (called by CallbackBridge)."""
        self.task_progress.emit(cloudcast_url, progress_text)

    @Slot(str, str, str)
    def _emit_completed_signal(self, cloudcast_url: str, file_path: str, task_type: str):
        """Emit completion signal from main thread (called by CallbackBridge)."""
        if task_type == "download":
            # Remove from active downloads
            self.active_downloads.pop(cloudcast_url, None)

            # Determine if conversion will happen
            will_convert = False
            if self.license_manager.is_pro:
                # Get target format to determine if conversion is needed (ensure lowercase)
                target_format = self.settings_manager.get("default_audio_format", "mp3").lower()
                downloaded_path = Path(file_path)
                current_format = downloaded_path.suffix.lstrip(".")

                if current_format != target_format:
                    will_convert = True
                    self._start_conversion_if_needed(cloudcast_url, file_path)
                    # Note: Don't return early - still emit completion signal

            # Always emit completion signal with conversion decision
            self.task_result.emit(cloudcast_url, file_path, will_convert)
            self._check_all_finished()

        elif task_type == "conversion":
            # Remove from active conversions and emit final completion
            self.active_conversions.pop(cloudcast_url, None)
            self.task_result.emit(
                cloudcast_url, file_path, False
            )  # Conversion complete, no further conversion
            self._check_all_finished()

    @Slot(str, str, str)
    def _emit_error_signal(self, cloudcast_url: str, error_msg: str, task_type: str):
        """Emit error signal from main thread (called by CallbackBridge)."""
        # Remove from active tracking
        if task_type == "download":
            self.active_downloads.pop(cloudcast_url, None)
        elif task_type == "conversion":
            self.active_conversions.pop(cloudcast_url, None)

        self.task_error.emit(cloudcast_url, error_msg)
        self._check_all_finished()

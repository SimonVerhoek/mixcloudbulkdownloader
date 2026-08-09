"""New download manager using proper PyQt threading patterns.

This module provides a replacement for DownloadOrchestrator that follows proper
PyQt threading patterns using QObject workers and thread-safe signal emission.
"""

from collections.abc import Callable
from pathlib import Path
from typing import Dict

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt, QThreadPool, Signal, Slot

from app.consts.settings import (
    DEFAULT_ENABLE_AUDIO_CONVERSION,
    DEFAULT_MAX_PARALLEL_CONVERSIONS,
    DEFAULT_MAX_PARALLEL_DOWNLOADS,
    SETTING_ENABLE_AUDIO_CONVERSION,
    SETTING_MAX_PARALLEL_CONVERSIONS,
    SETTING_MAX_PARALLEL_DOWNLOADS,
)
from app.data_classes import Cloudcast
from app.services.conversion_worker import ConversionWorker
from app.services.download_worker import DownloadWorker
from app.services.license_manager import LicenseManager
from app.services.settings_manager import SettingsManager


class CallbackBridge:
    """Thread-safe callback bridge for worker-to-main-thread signal emission.

    This class provides a safe way for QRunnable workers to emit signals back
    to the main thread without violating Qt's threading rules. It uses
    QMetaObject.invokeMethod with Qt.QueuedConnection for thread-safe operation.
    """

    def __init__(
        self,
        download_manager: "DownloadManager",
        invoke_method_fn: Callable = QMetaObject.invokeMethod,
    ):
        """Initialize callback bridge with target DownloadManager.

        Args:
            download_manager: DownloadManager instance to emit signals through.
            invoke_method_fn: Callable that replaces ``QMetaObject.invokeMethod``
                for thread-safe slot invocation.  Inject a recording stub in tests
                to verify call arguments without relying on a running Qt event loop.
        """
        self.download_manager = download_manager
        self.shutting_down = False
        self._invoke_method = invoke_method_fn

    def emit_progress(self, cloudcast_url: str, progress_text: str, task_type: str = "download"):
        """Emit progress update signal in thread-safe manner.

        Args:
            cloudcast_url: Cloudcast URL (task identifier)
            progress_text: Progress information to display
            task_type: Type of task ("download" or "conversion")
        """
        if self.shutting_down:
            return
        self._invoke_method(
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
        if self.shutting_down:
            return
        self._invoke_method(
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
        if self.shutting_down:
            return
        self._invoke_method(
            self.download_manager,
            "_emit_error_signal",
            Qt.QueuedConnection,
            Q_ARG(str, cloudcast_url),
            Q_ARG(str, error_msg),
            Q_ARG(str, task_type),
        )

    def emit_cancelled(self, cloudcast_url: str, task_type: str = "download"):
        """Emit task cancelled signal in thread-safe manner.

        Args:
            cloudcast_url: Cloudcast URL (task identifier)
            task_type: Type of task ("download" or "conversion")
        """
        if self.shutting_down:
            return
        self._invoke_method(
            self.download_manager,
            "_emit_cancelled_signal",
            Qt.QueuedConnection,
            Q_ARG(str, cloudcast_url),
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
        download_worker_class: type = DownloadWorker,
        conversion_worker_class: type | None = None,
        invoke_method_fn: Callable = QMetaObject.invokeMethod,
    ):
        """Initialize DownloadManager with thread pools and dependencies.

        Args:
            settings_manager: Settings manager for configuration.
            license_manager: License manager for Pro features.
            download_worker_class: Class to use when creating download tasks.
                Defaults to ``DownloadWorker``.  Inject a stub class in tests
                to avoid real network downloads.
            conversion_worker_class: Optional class to use instead of the real
                ``ConversionWorker`` when creating conversion tasks.  Inject a
                stub class in tests to avoid real FFmpeg execution.
            invoke_method_fn: Callable passed through to ``CallbackBridge`` to
                replace ``QMetaObject.invokeMethod``.  Inject a recording stub in
                tests to verify signal emission without a running Qt event loop.
        """
        super().__init__()

        self.settings_manager = settings_manager
        self.license_manager = license_manager
        self._download_worker_class = download_worker_class
        self._conversion_worker_class = conversion_worker_class

        # Create callback bridge for thread-safe signal emission
        self.callback_bridge = CallbackBridge(
            download_manager=self, invoke_method_fn=invoke_method_fn
        )

        # Initialize thread pools with current settings
        self.download_pool = QThreadPool()
        self.conversion_pool = QThreadPool()
        self._update_thread_pool_sizes()

        # Track active tasks and workflows
        self.active_downloads: Dict[str, DownloadWorker] = {}  # cloudcast_url -> worker
        self.active_conversions: Dict[str, "ConversionWorker"] = {}  # cloudcast_url -> worker
        self.cancelled = False

    def _update_thread_pool_sizes(self):
        """Update thread pool sizes from current settings."""
        max_downloads = self.settings_manager.max_parallel_downloads
        max_conversions = self.settings_manager.max_parallel_conversions

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
                worker = self._download_worker_class(
                    cloudcast=cloudcast,
                    download_dir=download_dir,
                    callback_bridge=self.callback_bridge,
                    settings_manager=self.settings_manager,
                    license_manager=self.license_manager,
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

    def shutdown(self) -> None:
        """Gracefully shut down all workers and wait for thread pools to drain.

        Call this before the application exits to prevent crashes caused by
        workers running in custom QThreadPool instances after the manager is destroyed.
        """
        self.callback_bridge.shutting_down = True
        self.cancel_all()
        self.download_pool.waitForDone(5000)
        self.conversion_pool.waitForDone(5000)

    def _start_conversion(self, cloudcast_url: str, downloaded_file: str) -> None:
        """Start conversion worker for Pro users.

        Args:
            cloudcast_url: Cloudcast URL (task identifier)
            downloaded_file: Path to downloaded file
        """
        # Get target format from settings (ensure lowercase for AUDIO_FORMATS lookup)
        target_format = self.settings_manager.preferred_audio_format.lower()
        downloaded_path = Path(downloaded_file)

        # Resolve worker class: use injected class if provided, else default ConversionWorker
        conversion_cls = (
            self._conversion_worker_class
            if self._conversion_worker_class is not None
            else ConversionWorker
        )

        worker = conversion_cls(
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
                # Check if conversion is enabled
                conversion_enabled = self.settings_manager.enable_audio_conversion

                if conversion_enabled:
                    # Get target format to determine if conversion is needed (ensure lowercase)
                    target_format = self.settings_manager.preferred_audio_format.lower()
                    downloaded_path = Path(file_path)
                    current_format = downloaded_path.suffix.lstrip(".")

                    if current_format != target_format:
                        will_convert = True
                        self._start_conversion(cloudcast_url, file_path)
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

    @Slot(str, str)
    def _emit_cancelled_signal(self, cloudcast_url: str, task_type: str):
        """Emit cancellation signal from main thread (called by CallbackBridge)."""
        if task_type == "download":
            self.active_downloads.pop(cloudcast_url, None)
        elif task_type == "conversion":
            self.active_conversions.pop(cloudcast_url, None)

        self.task_cancelled.emit(cloudcast_url)
        self._check_all_finished()

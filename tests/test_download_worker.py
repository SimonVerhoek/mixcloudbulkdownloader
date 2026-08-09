"""Comprehensive unit tests for DownloadWorker."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from app.data_classes import Cloudcast, MixcloudUser
from app.services.download_manager import CallbackBridge
from app.services.download_worker import DownloadCancelled, DownloadWorker
from app.services.settings_manager import SettingsManager
from tests.stubs.license_server_stubs import StubLicenseManager


class StubYoutubeDL:
    """Stub for yt_dlp.YoutubeDL used in integration tests.

    Implements the context-manager interface used by DownloadWorker.run():
      with ydl_class(opts) as ydl:
          info = ydl.extract_info(url, download=False)
          ydl.download([url])
    """

    def __init__(self, opts: dict) -> None:
        """Initialize stub with yt-dlp options."""
        self.opts = opts
        self.params = dict(opts)
        # outtmpl must be a dict so DownloadWorker can write ydl.params["outtmpl"]["default"]
        if "outtmpl" in self.params and isinstance(self.params["outtmpl"], str):
            self.params["outtmpl"] = {"default": self.params["outtmpl"]}

        self._extract_info_result: dict | None = None
        self._extract_info_side_effect: BaseException | None = None
        self._download_calls: list[list[str]] = []

    def __enter__(self) -> "StubYoutubeDL":
        """Return self as the context manager object."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager without suppressing exceptions."""
        pass

    def extract_info(self, url: str, download: bool = True) -> dict | None:
        """Simulate extract_info call.

        Args:
            url: URL to extract info for
            download: Whether to download (unused in stub)

        Returns:
            Configured info dict

        Raises:
            Configured side effect exception if set
        """
        if self._extract_info_side_effect is not None:
            raise self._extract_info_side_effect
        return self._extract_info_result

    def download(self, urls: list[str]) -> None:
        """Record download call.

        Args:
            urls: List of URLs to download
        """
        self._download_calls.extend(urls)


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_path:
        yield Path(temp_path)


@pytest.fixture
def mock_settings_manager():
    """Create mock settings manager."""
    settings = Mock(spec=SettingsManager)
    settings.get.return_value = None
    return settings


@pytest.fixture
def mock_license_manager():
    """Create mock license manager."""
    return StubLicenseManager()


@pytest.fixture
def mock_callback_bridge():
    """Create mock callback bridge."""
    bridge = Mock(spec=CallbackBridge)
    return bridge


@pytest.fixture
def sample_cloudcast():
    """Create sample cloudcast for testing."""
    user = MixcloudUser(
        key="/testuser/",
        name="Test User",
        pictures={},
        url="https://www.mixcloud.com/testuser/",
        username="testuser",
    )

    return Cloudcast(name="Test Mix", url="https://www.mixcloud.com/testuser/test-mix/", user=user)


@pytest.fixture
def yt_dlp_info_responses():
    """Create various yt-dlp info responses for testing different formats."""
    return {
        "webm": {
            "ext": "webm",
            "format_id": "webm-1",
            "acodec": "opus",
            "title": "Test Mix",
            "uploader": "Test User",
        },
        "m4a": {
            "ext": "m4a",
            "format_id": "m4a-1",
            "acodec": "aac",
            "title": "Test Mix",
            "uploader": "Test User",
        },
        "mp3": {
            "ext": "mp3",
            "format_id": "mp3-1",
            "acodec": "mp3",
            "title": "Test Mix",
            "uploader": "Test User",
        },
        "flac": {
            "ext": "flac",
            "format_id": "flac-1",
            "acodec": "flac",
            "title": "Test Mix",
            "uploader": "Test User",
        },
        "no_ext": {
            "format_id": "unknown-1",
            "acodec": "unknown",
            "title": "Test Mix",
            "uploader": "Test User",
            # Deliberately missing 'ext' field
        },
    }


@pytest.mark.unit
class TestDownloadWorkerInitialization:
    """Test DownloadWorker initialization and filename generation."""

    def test_init_creates_correct_attributes(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test DownloadWorker initialization sets correct attributes."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        assert worker.cloudcast == sample_cloudcast
        assert worker.download_dir == str(temp_dir)
        assert worker.callback_bridge == mock_callback_bridge
        assert worker.settings_manager == mock_settings_manager
        assert worker.license_manager == mock_license_manager
        assert worker.cancelled is False

    def test_init_sanitizes_filename(
        self, temp_dir, mock_callback_bridge, mock_settings_manager, mock_license_manager
    ):
        """Test filename sanitization during initialization."""
        user = MixcloudUser(
            key="/testuser/",
            name="Test User",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser",
        )

        cloudcast = Cloudcast(
            name="Mix with <special> chars/and\\bad|ones?*",
            url="https://www.mixcloud.com/testuser/test-mix/",
            user=user,
        )

        worker = DownloadWorker(
            cloudcast=cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        # Should sanitize problematic characters
        assert worker.safe_title == "Mix with special charsandbadones"

    def test_init_sets_default_webm_filenames(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test that initial filenames default to .webm extension."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        assert worker.downloading_filename == "Test User - Test Mix.webm.downloading"
        assert worker.final_filename == "Test User - Test Mix.webm"
        assert worker.download_file_path == temp_dir / "Test User - Test Mix.webm.downloading"
        assert worker.final_file_path == temp_dir / "Test User - Test Mix.webm"


@pytest.mark.unit
class TestDownloadWorkerFilenameUpdate:
    """Test dynamic filename update functionality."""

    def test_update_filenames_with_extension_m4a(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test updating filenames with m4a extension."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        worker._update_filenames_with_extension("m4a")

        expected_downloading = "Test User - Test Mix.m4a.downloading"
        expected_final = "Test User - Test Mix.m4a"

        assert worker.downloading_filename == expected_downloading
        assert worker.final_filename == expected_final
        assert worker.download_file_path == temp_dir / expected_downloading
        assert worker.final_file_path == temp_dir / expected_final

    def test_update_filenames_with_extension_handles_empty(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test updating filenames handles empty extension gracefully."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        # Should fall back to webm for empty/None extension
        worker._update_filenames_with_extension("")
        assert worker.final_filename == "Test User - Test Mix.webm"

        worker._update_filenames_with_extension(None)
        assert worker.final_filename == "Test User - Test Mix.webm"

        # Should handle extension with leading dots
        worker._update_filenames_with_extension(".mp3")
        assert worker.final_filename == "Test User - Test Mix.mp3"


@pytest.mark.unit
class TestDownloadWorkerFormatDetection:
    """Test format detection and yt-dlp integration."""

    def test_format_detection_webm(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
        yt_dlp_info_responses,
    ):
        """Test format detection extracts webm extension correctly."""

        class StubYoutubeDLWebm(StubYoutubeDL):
            pass

        stub_instance = StubYoutubeDLWebm.__new__(StubYoutubeDLWebm)
        stub_instance._extract_info_result = yt_dlp_info_responses["webm"]
        stub_instance._extract_info_side_effect = None
        stub_instance._download_calls = []

        def stub_ydl_class(opts: dict) -> StubYoutubeDLWebm:
            stub_instance.opts = opts
            stub_instance.params = dict(opts)
            if "outtmpl" in stub_instance.params and isinstance(
                stub_instance.params["outtmpl"], str
            ):
                stub_instance.params["outtmpl"] = {"default": stub_instance.params["outtmpl"]}
            return stub_instance

        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
            ydl_class=stub_ydl_class,
        )

        # Mock the file creation for download
        (temp_dir / "Test User - Test Mix.webm.downloading").touch()

        worker.run()

        # Should extract info with download=False first, then use ydl.download()
        # The stub tracks calls via _download_calls; extract_info was called with the cloudcast url
        assert sample_cloudcast.url in stub_instance._download_calls

    def test_format_detection_m4a(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
        yt_dlp_info_responses,
    ):
        """Test format detection extracts m4a extension correctly."""

        stub_instance = StubYoutubeDL.__new__(StubYoutubeDL)
        stub_instance._extract_info_result = yt_dlp_info_responses["m4a"]
        stub_instance._extract_info_side_effect = None
        stub_instance._download_calls = []

        def stub_ydl_class(opts: dict) -> StubYoutubeDL:
            stub_instance.opts = opts
            stub_instance.params = dict(opts)
            if "outtmpl" in stub_instance.params and isinstance(
                stub_instance.params["outtmpl"], str
            ):
                stub_instance.params["outtmpl"] = {"default": stub_instance.params["outtmpl"]}
            return stub_instance

        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
            ydl_class=stub_ydl_class,
        )

        # Mock the file creation that yt-dlp would do
        (temp_dir / "Test User - Test Mix.m4a.downloading").touch()

        worker.run()

        # Should update filenames to use .m4a extension
        assert worker.final_filename == "Test User - Test Mix.m4a"

    def test_format_detection_fallback_on_missing_ext(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
        yt_dlp_info_responses,
    ):
        """Test format detection falls back to webm when ext field is missing."""

        stub_instance = StubYoutubeDL.__new__(StubYoutubeDL)
        stub_instance._extract_info_result = yt_dlp_info_responses["no_ext"]
        stub_instance._extract_info_side_effect = None
        stub_instance._download_calls = []

        def stub_ydl_class(opts: dict) -> StubYoutubeDL:
            stub_instance.opts = opts
            stub_instance.params = dict(opts)
            if "outtmpl" in stub_instance.params and isinstance(
                stub_instance.params["outtmpl"], str
            ):
                stub_instance.params["outtmpl"] = {"default": stub_instance.params["outtmpl"]}
            return stub_instance

        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
            ydl_class=stub_ydl_class,
        )

        # Should fall back to .webm when no extension is found
        (temp_dir / "Test User - Test Mix.webm.downloading").touch()

        worker.run()

        # Should maintain .webm as fallback
        assert worker.final_filename == "Test User - Test Mix.webm"


@pytest.mark.unit
class TestDownloadWorkerErrorHandling:
    """Test error handling in DownloadWorker."""

    def test_cancellation_before_start(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test cancellation before download starts."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        worker.cancel()
        worker.run()

        # Should emit cancellation and not attempt download
        mock_callback_bridge.emit_cancelled.assert_called_once_with(
            worker.cloudcast.url, "download"
        )
        mock_callback_bridge.emit_progress.assert_not_called()

    def test_format_detection_network_error(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test graceful handling of network errors during format detection."""

        stub_instance = StubYoutubeDL.__new__(StubYoutubeDL)
        stub_instance._extract_info_result = None
        stub_instance._extract_info_side_effect = Exception("Network error")
        stub_instance._download_calls = []

        def stub_ydl_class(opts: dict) -> StubYoutubeDL:
            stub_instance.opts = opts
            stub_instance.params = dict(opts)
            if "outtmpl" in stub_instance.params and isinstance(
                stub_instance.params["outtmpl"], str
            ):
                stub_instance.params["outtmpl"] = {"default": stub_instance.params["outtmpl"]}
            return stub_instance

        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
            ydl_class=stub_ydl_class,
        )

        worker.run()

        # Should emit error signal
        mock_callback_bridge.emit_error.assert_called_once()
        call_args = mock_callback_bridge.emit_error.call_args[0]
        assert sample_cloudcast.url in call_args[0]
        assert "failed" in call_args[1].lower()


@pytest.mark.unit
class TestDownloadWorkerCleanup:
    """Test cleanup functionality with dynamic extensions."""

    def test_cleanup_removes_downloading_file(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test cleanup removes downloading file."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        # Create fake downloading file
        downloading_file = temp_dir / worker.downloading_filename
        downloading_file.touch()

        assert downloading_file.exists()

        worker._cleanup()

        assert not downloading_file.exists()

    def test_cleanup_handles_missing_file(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test cleanup handles missing file gracefully."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        # Should not raise exception when file doesn't exist
        worker._cleanup()

    def test_cleanup_fragments_pattern_matching(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test fragment cleanup uses correct patterns."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        # Create fake fragment files
        base_name = "Test User - Test Mix"
        fragment_files = [
            temp_dir / f"{base_name}.part",
            temp_dir / f"{base_name}.webm.part-Frag1",
            temp_dir / f"{base_name}.webm.part-Frag2",
        ]

        for fragment_file in fragment_files:
            fragment_file.touch()
            assert fragment_file.exists()

        worker._cleanup_fragments()

        # All fragment files should be cleaned up
        for fragment_file in fragment_files:
            assert not fragment_file.exists()


@pytest.mark.unit
class TestDownloadWorkerSanitization:
    """Test filename sanitization methods."""

    def test_sanitize_filename_removes_special_chars(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test filename sanitization removes filesystem-unsafe characters."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        test_cases = [
            ("Mix with <special> chars", "Mix with special chars"),
            ("Mix/with\\bad|chars", "Mixwithbadchars"),
            ('Mix"with"quotes', "Mixwithquotes"),
            ("Mix?with*wild:cards", "Mixwithwild - cards"),
            ("Mix   with    spaces", "Mix with spaces"),
            ("Mix\twith\ttabs", "Mix with tabs"),
            ("UNICORN POWER: Seagulls", "UNICORN POWER - Seagulls"),
        ]

        for input_name, expected in test_cases:
            result = worker._sanitize_filename(input_name)
            assert result == expected

    def test_sanitize_filename_unicode_normalization(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test filename sanitization handles Unicode correctly."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        # Test Unicode normalization and accent removal
        test_cases = [
            ("Café Mix", "Cafe Mix"),
            ("Mix á é í ó ú", "Mix a e i o u"),
            ("Mix ñ ü ç", "Mix n u c"),
            ("Mix 中文", "Mix"),  # Non-ASCII should be removed, trailing space stripped
        ]

        for input_name, expected in test_cases:
            result = worker._sanitize_filename(input_name)
            assert result == expected


@pytest.mark.unit
class TestDownloadWorkerYtDlpOptions:
    """Test yt-dlp configuration options."""

    def test_generate_ydl_opts_structure(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test yt-dlp options have correct structure."""
        # Configure license manager as Pro user for this test
        mock_license_manager.configure_as_pro_user()

        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        opts = worker._generate_ydl_opts()

        # Check required options
        assert opts["format"] == "bestaudio/best"
        assert opts["outtmpl"] == str(worker.download_file_path)
        assert opts["verbose"] is False
        assert opts["quiet"] is True
        assert opts["no_warnings"] is True
        assert "progress_hooks" in opts
        assert len(opts["progress_hooks"]) == 1

    def test_generate_ydl_opts_progress_hook_cancellation(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test progress hook handles cancellation."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        opts = worker._generate_ydl_opts()
        progress_hook = opts["progress_hooks"][0]

        # Cancel the worker
        worker.cancel()

        # Progress hook should raise DownloadAborted when cancelled
        from app.services.download_worker import DownloadAborted

        with pytest.raises(DownloadAborted, match="aborted by user"):
            progress_hook({"status": "downloading"})

    def test_generate_ydl_opts_progress_hook_signals(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Test progress hook emits correct signals."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )

        opts = worker._generate_ydl_opts()
        progress_hook = opts["progress_hooks"][0]

        # Test downloading progress
        progress_data = {
            "status": "downloading",
            "_percent_str": "50%",
            "_speed_str": "1.2MB/s",
            "_total_bytes_estimate_str": "45MB",
            "info_dict": {"abr": 64.002},
        }

        progress_hook(progress_data)

        mock_callback_bridge.emit_progress.assert_called_once()
        call_args = mock_callback_bridge.emit_progress.call_args[0]
        assert sample_cloudcast.url == call_args[0]
        assert "50%" in call_args[1]
        assert "1.2MB/s" in call_args[1]
        assert "[64kbps]" in call_args[1]

        # Test finished status
        mock_callback_bridge.reset_mock()
        progress_hook({"status": "finished"})

        mock_callback_bridge.emit_progress.assert_called_once()
        call_args = mock_callback_bridge.emit_progress.call_args[0]
        assert "Complete" in call_args[1]

    def test_ydl_opts_fixup_is_never(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Regression guard: fixup must be 'never' to prevent FFmpegFixupM3u8PP from running."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
            ffmpeg_path=Path("/fake/ffmpeg"),
        )

        opts = worker._generate_ydl_opts()

        assert opts["fixup"] == "never"

    def test_ydl_opts_uses_bundled_ffmpeg_location(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Regression guard: ffmpeg_location must point to the bundled binary's parent directory."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
            ffmpeg_path=Path("/fake/bundled/ffmpeg"),
        )

        opts = worker._generate_ydl_opts()

        assert "ffmpeg_location" in opts
        assert opts["ffmpeg_location"] == str(Path("/fake/bundled/ffmpeg").parent)

    def test_ydl_opts_ffmpeg_location_omitted_on_unsupported_platform(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Regression guard: ffmpeg_location must be omitted when platform is unsupported (e.g. Linux)."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
        )
        worker._ffmpeg_path = None

        opts = worker._generate_ydl_opts()

        assert "ffmpeg_location" not in opts

    def test_ydl_opts_retries_and_fragment_retries(
        self,
        sample_cloudcast,
        temp_dir,
        mock_callback_bridge,
        mock_settings_manager,
        mock_license_manager,
    ):
        """Regression guard: retries and fragment_retries must be >= 1 to handle transient CDN errors."""
        worker = DownloadWorker(
            cloudcast=sample_cloudcast,
            download_dir=str(temp_dir),
            callback_bridge=mock_callback_bridge,
            settings_manager=mock_settings_manager,
            license_manager=mock_license_manager,
            ffmpeg_path=Path("/fake/ffmpeg"),
        )

        opts = worker._generate_ydl_opts()

        assert opts["retries"] >= 1
        assert opts["fragment_retries"] >= 1

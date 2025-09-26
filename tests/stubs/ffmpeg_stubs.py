"""FFmpeg test stubs for audio conversion testing."""

import re
import time
from pathlib import Path
from typing import Any, Callable, TextIO
from unittest.mock import Mock


class StubFFmpegProcess:
    """Stub for subprocess.Popen to simulate FFmpeg process behavior."""
    
    def __init__(
        self, 
        cmd: list[str], 
        stdout: Any = None, 
        stderr: Any = None, 
        text: bool = True,
        **kwargs
    ) -> None:
        """Initialize stub FFmpeg process.
        
        Args:
            cmd: FFmpeg command line arguments
            stdout: Output stream configuration
            stderr: Error stream configuration
            text: Text mode flag
            **kwargs: Additional process arguments
        """
        self.cmd = cmd
        self.stdout = MockTextIO()
        self.stderr = MockTextIO()
        self.returncode = 0
        self.text = text
        
        # Parse command for simulation
        self._parse_command()
        
        # Configuration for testing
        self.should_fail = False
        self.failure_code = 1
        self.failure_message = "FFmpeg conversion failed"
        self.simulate_duration = 180.0  # 3 minutes default
        self.conversion_speed = 1.0  # Real-time conversion
        self.progress_delay = 0.01  # Delay between progress updates (for testing speed)
        
        # Generate output immediately for iteration
        self._generate_output()
        
    def _parse_command(self) -> None:
        """Parse FFmpeg command to extract relevant information."""
        self.input_file = ""
        self.output_file = ""
        self.target_format = ""
        self.bitrate = None
        
        # Parse command line arguments
        for i, arg in enumerate(self.cmd):
            arg_str = str(arg)  # Convert to string to handle Path objects
            if arg_str == "-i" and i + 1 < len(self.cmd):
                self.input_file = str(self.cmd[i + 1])
            elif arg_str == "-b:a" and i + 1 < len(self.cmd):
                self.bitrate = str(self.cmd[i + 1])
            elif arg_str.endswith(('.mp3', '.flac', '.wav', '.aac', '.ogg')):
                self.output_file = arg_str
                self.target_format = Path(arg_str).suffix[1:]  # Remove dot
                
    def _generate_output(self) -> None:
        """Generate all FFmpeg output for the process."""
        if self.should_fail:
            self.stderr.lines = [self.failure_message]
            return
            
        # Generate initial banner and info
        banner_lines = self._generate_ffmpeg_output()
        self.stdout.lines.extend(banner_lines)
        
        # Generate progress updates
        progress_lines = self._generate_progress_updates()
        self.stdout.lines.extend(progress_lines)
                
    def _generate_ffmpeg_output(self) -> list[str]:
        """Generate realistic FFmpeg output for testing.
        
        Returns:
            List of output lines that FFmpeg would produce
        """
        lines = []
        
        # Initial FFmpeg banner and input information
        lines.extend([
            "ffmpeg version 4.4.0 Copyright (c) 2000-2021 the FFmpeg developers",
            "  built with Apple clang version 12.0.0",
            "  configuration: --enable-version3 --enable-nonfree",
            f"Input #0, mp3, from '{self.input_file}':",
            "  Metadata:",
            "    title           : Test Track",
            "    artist          : Test Artist",
            f"  Duration: {self._format_duration(self.simulate_duration)}, start: 0.000000, bitrate: 320 kb/s",
            "    Stream #0:0: Audio: mp3, 44100 Hz, stereo, fltp, 320 kb/s",
            f"Output #0, {self.target_format}, to '{self.output_file}':",
            "  Metadata:",
            "    title           : Test Track",
            "    artist          : Test Artist",
            "    encoder         : Lavf58.45.100"
        ])
        
        if self.target_format == "flac":
            lines.append("    Stream #0:0: Audio: flac, 44100 Hz, stereo, s16")
        elif self.target_format == "mp3":
            lines.append(f"    Stream #0:0: Audio: mp3, 44100 Hz, stereo, fltp, {self.bitrate or '192'} kb/s")
        else:
            lines.append(f"    Stream #0:0: Audio: {self.target_format}, 44100 Hz, stereo, fltp")
            
        lines.append("Stream mapping:")
        lines.append("  Stream #0:0 -> #0:0 (mp3 (native) -> flac (native))")
        lines.append("Press [q] to stop, [?] for help")
        
        return lines
        
    def _format_duration(self, seconds: float) -> str:
        """Format duration in FFmpeg format (HH:MM:SS.SS).
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        
    def _generate_progress_updates(self) -> list[str]:
        """Generate realistic progress updates during conversion.
        
        Returns:
            List of progress lines
        """
        lines = []
        duration_ms = int(self.simulate_duration * 1_000_000)  # Convert to microseconds
        
        # Simulate progress at various intervals
        progress_points = [0.1, 0.25, 0.5, 0.75, 0.9, 1.0]
        
        for progress in progress_points:
            current_ms = int(duration_ms * progress)
            
            # FFmpeg progress format
            lines.extend([
                f"frame=    {int(progress * 1000)}",
                f"fps={25.0 * self.conversion_speed:.1f}",
                f"stream_0_0_q=-0.0",
                f"size=    {int(progress * 8000)}kB",
                f"time={self._format_duration(self.simulate_duration * progress)}",
                f"bitrate={320.0 * (1 - progress * 0.1):.1f}kbits/s",
                f"speed={self.conversion_speed:.2f}x",
                f"out_time_ms={current_ms}",
                f"progress={'continue' if progress < 1.0 else 'end'}"
            ])
            
        return lines
        
    def wait(self) -> int:
        """Wait for process completion and return exit code.
        
        Returns:
            Process exit code
        """
        if self.should_fail:
            self.returncode = self.failure_code
            # Add error message to stderr
            if hasattr(self.stderr, 'lines'):
                self.stderr.lines.append(self.failure_message)
        else:
            self.returncode = 0
            
        return self.returncode
        
    def __enter__(self):
        """Context manager entry."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


class MockTextIO:
    """Mock text I/O stream for simulating FFmpeg output."""
    
    def __init__(self) -> None:
        """Initialize mock text I/O."""
        self.lines: list[str] = []
        self.position = 0
        
    def __iter__(self):
        """Iterate over lines in the stream."""
        return iter(self.lines)
        
    def readline(self) -> str:
        """Read a single line from the stream.
        
        Returns:
            Next line or empty string if at end
        """
        if self.position < len(self.lines):
            line = self.lines[self.position]
            self.position += 1
            return line
        return ""
        
    def read(self) -> str:
        """Read all remaining content.
        
        Returns:
            All remaining lines joined
        """
        remaining = self.lines[self.position:]
        self.position = len(self.lines)
        return "\n".join(remaining)
        
    def close(self) -> None:
        """Close the stream."""
        pass


class StubFFmpegService:
    """High-level stub for FFmpeg functionality in DownloadService."""
    
    def __init__(self) -> None:
        """Initialize FFmpeg service stub."""
        self.available = True
        self.supported_platforms = ["windows", "darwin"]  # Exclude linux by default for testing
        self.ffmpeg_path_exists = True
        self.conversion_history: list[dict[str, Any]] = []
        self.should_fail_conversion = False
        self.conversion_error_message = "FFmpeg conversion failed"
        
        # Progress callback tracking
        self.progress_calls: list[tuple[str, str]] = []
        
    def get_ffmpeg_path(self, platform_override: str = None) -> Path:
        """Get FFmpeg executable path for testing.
        
        Args:
            platform_override: Override platform detection for testing
            
        Returns:
            Path to FFmpeg executable
            
        Raises:
            RuntimeError: If platform is unsupported (in production, not tests)
        """
        import platform as platform_module
        
        system = platform_override or platform_module.system().lower()
        base = Path(__file__).parent.parent.parent / "app" / "resources" / "ffmpeg"
        
        if system == "windows":
            return base / "windows" / "ffmpeg.exe"
        elif system == "darwin":  # macOS
            return base / "macos" / "ffmpeg"
        elif system == "linux":
            # For testing in CI environments only - return mock path
            return Path("/fake/ffmpeg/linux/ffmpeg")
        else:
            raise RuntimeError(f"Unsupported OS: {system}")
            
    def verify_ffmpeg_availability(self, platform_override: str = None) -> bool:
        """Verify FFmpeg availability for testing.
        
        Args:
            platform_override: Override platform detection
            
        Returns:
            True if FFmpeg is available
        """
        if not self.available:
            return False
            
        try:
            path = self.get_ffmpeg_path(platform_override)
            return self.ffmpeg_path_exists
        except RuntimeError:
            return False
            
    def convert_audio(
        self,
        input_path: str,
        output_path: str,
        target_format: str,
        bitrate_k: int = 192,
        progress_callback: Callable[[str, str], None] = None
    ) -> None:
        """Simulate audio conversion with FFmpeg.
        
        Args:
            input_path: Source file path
            output_path: Target file path
            target_format: Target audio format
            bitrate_k: Bitrate in kbps for lossy formats
            progress_callback: Progress update callback
            
        Raises:
            RuntimeError: If conversion should fail
        """
        if self.should_fail_conversion:
            raise RuntimeError(self.conversion_error_message)
            
        # Record conversion for verification
        conversion = {
            "input_path": input_path,
            "output_path": output_path,
            "target_format": target_format,
            "bitrate_k": bitrate_k
        }
        self.conversion_history.append(conversion)
        
        # Simulate progress updates
        if progress_callback:
            item_name = Path(input_path).stem
            
            # Simulate conversion progress
            progress_updates = [
                f"Converting to {target_format}... 0.00%",
                f"Converting to {target_format}... 25.50%",
                f"Converting to {target_format}... 50.00%",
                f"Converting to {target_format}... 75.25%",
                f"Converting to {target_format}... 100.00%",
                "Conversion finished!"
            ]
            
            for progress_msg in progress_updates:
                progress_callback(item_name, progress_msg)
                self.progress_calls.append((item_name, progress_msg))
                # Small delay to simulate real conversion
                time.sleep(0.001)
        else:
            # Even without callback, record that progress would have been made
            item_name = Path(input_path).stem
            progress_updates = [
                f"Converting to {target_format}... 0.00%",
                f"Converting to {target_format}... 25.50%",
                f"Converting to {target_format}... 50.00%",
                f"Converting to {target_format}... 75.25%",
                f"Converting to {target_format}... 100.00%",
                "Conversion finished!"
            ]
            
            for progress_msg in progress_updates:
                self.progress_calls.append((item_name, progress_msg))
                
    def set_availability(self, available: bool) -> None:
        """Configure FFmpeg availability for testing.
        
        Args:
            available: Whether FFmpeg should be available
        """
        self.available = available
        
    def set_path_exists(self, exists: bool) -> None:
        """Configure whether FFmpeg path exists for testing.
        
        Args:
            exists: Whether FFmpeg executable should exist
        """
        self.ffmpeg_path_exists = exists
        
    def set_conversion_failure(self, should_fail: bool, error_message: str = None) -> None:
        """Configure conversion failure for testing.
        
        Args:
            should_fail: Whether conversion should fail
            error_message: Custom error message
        """
        self.should_fail_conversion = should_fail
        if error_message:
            self.conversion_error_message = error_message
            
    def reset(self) -> None:
        """Reset stub state for new test."""
        self.conversion_history.clear()
        self.progress_calls.clear()
        self.available = True
        self.ffmpeg_path_exists = True
        self.should_fail_conversion = False
        self.conversion_error_message = "FFmpeg conversion failed"


# Global stub instance for easy access
ffmpeg_stub = StubFFmpegService()
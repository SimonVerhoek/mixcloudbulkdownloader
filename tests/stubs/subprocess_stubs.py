"""Subprocess test stubs for external process simulation."""

import time
from typing import Any, TextIO
from unittest.mock import Mock

from .ffmpeg_stubs import StubFFmpegProcess


class StubSubprocessModule:
    """Stub for the subprocess module to control external process simulation."""

    def __init__(self) -> None:
        """Initialize subprocess module stub."""
        self.popen_calls: list[dict[str, Any]] = []
        self.default_process_factory = self._create_default_process
        self.custom_process_factories: dict[str, callable] = {}

        # Global configuration
        self.should_raise_on_popen = False
        self.popen_exception = OSError("Simulated subprocess error")

    def Popen(
        self, cmd: list[str], stdout: Any = None, stderr: Any = None, text: bool = True, **kwargs
    ) -> Any:
        """Create a subprocess.Popen stub.

        Args:
            cmd: Command and arguments
            stdout: Output stream configuration
            stderr: Error stream configuration
            text: Text mode flag
            **kwargs: Additional process arguments

        Returns:
            Stub process object

        Raises:
            OSError: If configured to raise on Popen
        """
        if self.should_raise_on_popen:
            raise self.popen_exception

        # Record the call for verification
        call_info = {"cmd": cmd, "stdout": stdout, "stderr": stderr, "text": text, "kwargs": kwargs}
        self.popen_calls.append(call_info)

        # Determine which process factory to use
        if cmd and len(cmd) > 0:
            executable = cmd[0]

            # Check for custom factories first
            for pattern, factory in self.custom_process_factories.items():
                if pattern in executable:
                    return factory(cmd, stdout, stderr, text, **kwargs)

            # Check for known executables
            if "ffmpeg" in executable:
                return StubFFmpegProcess(cmd, stdout, stderr, text, **kwargs)

        # Default process
        return self.default_process_factory(cmd, stdout, stderr, text, **kwargs)

    def _create_default_process(
        self, cmd: list[str], stdout: Any = None, stderr: Any = None, text: bool = True, **kwargs
    ) -> "StubGenericProcess":
        """Create a generic stub process.

        Args:
            cmd: Command and arguments
            stdout: Output stream configuration
            stderr: Error stream configuration
            text: Text mode flag
            **kwargs: Additional process arguments

        Returns:
            Generic stub process
        """
        return StubGenericProcess(cmd, stdout, stderr, text, **kwargs)

    def register_process_factory(self, executable_pattern: str, factory: callable) -> None:
        """Register a custom process factory for specific executables.

        Args:
            executable_pattern: Pattern to match in executable name
            factory: Factory function to create process stub
        """
        self.custom_process_factories[executable_pattern] = factory

    def set_popen_exception(self, should_raise: bool, exception: Exception = None) -> None:
        """Configure Popen to raise exceptions for testing.

        Args:
            should_raise: Whether to raise exception on Popen
            exception: Custom exception to raise
        """
        self.should_raise_on_popen = should_raise
        if exception:
            self.popen_exception = exception

    def reset(self) -> None:
        """Reset stub state for new test."""
        self.popen_calls.clear()
        self.custom_process_factories.clear()
        self.should_raise_on_popen = False
        self.popen_exception = OSError("Simulated subprocess error")


class StubGenericProcess:
    """Generic stub process for non-FFmpeg executables."""

    def __init__(
        self, cmd: list[str], stdout: Any = None, stderr: Any = None, text: bool = True, **kwargs
    ) -> None:
        """Initialize generic stub process.

        Args:
            cmd: Command and arguments
            stdout: Output stream configuration
            stderr: Error stream configuration
            text: Text mode flag
            **kwargs: Additional process arguments
        """
        self.cmd = cmd
        self.returncode = 0
        self.stdout = StubTextStream()
        self.stderr = StubTextStream()

        # Configuration for testing
        self.should_fail = False
        self.failure_code = 1
        self.output_lines: list[str] = []
        self.error_lines: list[str] = []

    def wait(self) -> int:
        """Wait for process completion.

        Returns:
            Process exit code
        """
        if self.should_fail:
            self.returncode = self.failure_code
        else:
            self.returncode = 0

        return self.returncode

    def poll(self) -> int | None:
        """Check if process has terminated.

        Returns:
            Return code if terminated, None if still running
        """
        return self.returncode

    def communicate(self, input: str = None) -> tuple[str, str]:
        """Communicate with process.

        Args:
            input: Input to send to process

        Returns:
            Tuple of (stdout, stderr) content
        """
        stdout_content = "\n".join(self.output_lines)
        stderr_content = "\n".join(self.error_lines)
        return stdout_content, stderr_content

    def set_output(self, stdout_lines: list[str] = None, stderr_lines: list[str] = None) -> None:
        """Configure process output for testing.

        Args:
            stdout_lines: Lines to output to stdout
            stderr_lines: Lines to output to stderr
        """
        if stdout_lines:
            self.output_lines = stdout_lines
            self.stdout.lines = stdout_lines
        if stderr_lines:
            self.error_lines = stderr_lines
            self.stderr.lines = stderr_lines

    def set_failure(self, should_fail: bool, code: int = 1) -> None:
        """Configure process failure for testing.

        Args:
            should_fail: Whether process should fail
            code: Exit code for failure
        """
        self.should_fail = should_fail
        self.failure_code = code

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass


class StubTextStream:
    """Stub for text-based process streams."""

    def __init__(self) -> None:
        """Initialize text stream stub."""
        self.lines: list[str] = []
        self.position = 0

    def __iter__(self):
        """Iterate over lines in the stream."""
        for line in self.lines:
            yield line
            # Small delay to simulate real-time output
            time.sleep(0.001)

    def readline(self) -> str:
        """Read a single line.

        Returns:
            Next line or empty string if at end
        """
        if self.position < len(self.lines):
            line = self.lines[self.position]
            self.position += 1
            return line
        return ""

    def read(self) -> str:
        """Read all content.

        Returns:
            All lines joined
        """
        return "\n".join(self.lines)

    def close(self) -> None:
        """Close the stream."""
        pass


# Global subprocess stub instance
subprocess_stub = StubSubprocessModule()


def patch_subprocess(test_func):
    """Decorator to patch subprocess module with stub.

    Args:
        test_func: Test function to decorate

    Returns:
        Decorated test function
    """

    def wrapper(*args, **kwargs):
        import subprocess

        original_popen = subprocess.Popen

        try:
            subprocess.Popen = subprocess_stub.Popen
            result = test_func(*args, **kwargs)
        finally:
            subprocess.Popen = original_popen
            subprocess_stub.reset()

        return result

    return wrapper

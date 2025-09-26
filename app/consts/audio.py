"""Audio format constants and specifications."""

from dataclasses import dataclass


@dataclass(frozen=True)
class AudioFormat:
    """Immutable audio format specification."""

    label: str
    extension: str
    is_lossless: bool
    codec: str
    name: str


class AudioFormats:
    """Container for audio formats with dot-access and iteration support."""

    def __init__(self):
        """Initialize all audio formats."""
        self.wav = AudioFormat("WAV", ".wav", True, "pcm_s16le", "wav")
        self.flac = AudioFormat("FLAC", ".flac", True, "flac", "flac")
        self.alac = AudioFormat("ALAC", ".m4a", True, "alac", "m4a")
        self.mp3 = AudioFormat("MP3", ".mp3", False, "libmp3lame", "mp3")
        self.aac = AudioFormat("AAC", ".aac", False, "aac", "aac")
        self.m4a = AudioFormat("M4A", ".m4a", False, "aac", "m4a")
        self.mp4 = AudioFormat("MP4", ".mp4", False, "aac", "mp4")
        self.webm = AudioFormat("WEBM", ".webm", False, "libopus", "webm")
        self.ogg = AudioFormat("OGG", ".ogg", False, "libvorbis", "ogg")
        self.threegp = AudioFormat("3GP", ".3gp", False, "aac", "3gp")

    def __iter__(self):
        """Enable iteration over format name and AudioFormat pairs."""
        for name in dir(self):
            if not name.startswith("_") and isinstance(getattr(self, name), AudioFormat):
                yield name, getattr(self, name)

    def values(self):
        """Return all AudioFormat instances."""
        return [fmt for _, fmt in self]

    def get(self, key: str) -> AudioFormat:
        """Get an AudioFormat by key (format name).

        Args:
            key: Format name to retrieve (e.g., 'mp3', 'wav', 'flac')

        Returns:
            AudioFormat instance for the requested format

        Raises:
            KeyError: If the format key is not found
        """
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(f"Audio format '{key}' not found")


# Audio formats instance with all supported formats
AUDIO_FORMATS = AudioFormats()

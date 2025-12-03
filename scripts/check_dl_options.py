#!/usr/bin/env python3
"""Check available download options for a Mixcloud cloudcast URL.

This script uses yt-dlp to extract information about available download formats
and options for a given Mixcloud cloudcast without actually downloading it.

Usage:
    python scripts/check_dl_options.py <cloudcast_url>

Example:
    python scripts/check_dl_options.py https://www.mixcloud.com/user/cloudcast-name/
"""

import argparse
import sys
from pathlib import Path

import yt_dlp


def check_cloudcast_options(url: str) -> None:
    """Check and display available download options for a cloudcast URL.

    Args:
        url: Mixcloud cloudcast URL to analyze
    """
    print(f"Analyzing cloudcast: {url}")
    print("=" * 80)

    # Configure yt-dlp options for info extraction only
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
        "listformats": True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Extract info without downloading
            info = ydl.extract_info(url, download=False)

            if not info:
                print("❌ Could not extract information from the URL")
                return

            # Display basic cloudcast information
            print("\n📊 CLOUDCAST INFORMATION")
            print("-" * 40)
            print(f"Title: {info.get('title', 'Unknown')}")
            print(f"Uploader: {info.get('uploader', 'Unknown')}")
            print(f"Duration: {_format_duration(info.get('duration', 0))}")
            print(f"Upload Date: {info.get('upload_date', 'Unknown')}")

            if info.get("description"):
                description = (
                    info["description"][:200] + "..."
                    if len(info.get("description", "")) > 200
                    else info.get("description", "")
                )
                print(f"Description: {description}")

            # Display available formats
            formats = info.get("formats", [])
            if formats:
                print(f"\n🎵 AVAILABLE FORMATS ({len(formats)} total)")
                print("-" * 40)

                # Group formats by quality/type
                audio_formats = []
                video_formats = []

                for fmt in formats:
                    if fmt.get("acodec", "none") != "none" and fmt.get("vcodec", "none") == "none":
                        audio_formats.append(fmt)
                    elif fmt.get("vcodec", "none") != "none":
                        video_formats.append(fmt)
                    else:
                        audio_formats.append(fmt)  # Default to audio if unclear

                # Display audio formats
                if audio_formats:
                    print("\n🔊 Audio Formats:")
                    for fmt in audio_formats:
                        format_id = fmt.get("format_id", "unknown")
                        ext = fmt.get("ext", "unknown")
                        acodec = fmt.get("acodec", "unknown")
                        abr = fmt.get("abr", 0) or 0
                        filesize = fmt.get("filesize", 0) or 0

                        size_str = _format_filesize(filesize) if filesize > 0 else "Unknown size"
                        bitrate_str = f"{int(abr)}kbps" if abr > 0 else "Unknown bitrate"

                        print(f"  • {format_id}: {ext} ({acodec}) - {bitrate_str} - {size_str}")

                # Display video formats if any
                if video_formats:
                    print("\n📹 Video Formats:")
                    for fmt in video_formats:
                        format_id = fmt.get("format_id", "unknown")
                        ext = fmt.get("ext", "unknown")
                        vcodec = fmt.get("vcodec", "unknown")
                        acodec = fmt.get("acodec", "none")
                        resolution = fmt.get("resolution", "unknown")
                        filesize = fmt.get("filesize", 0) or 0

                        size_str = _format_filesize(filesize) if filesize > 0 else "Unknown size"
                        codec_info = f"{vcodec}"
                        if acodec != "none":
                            codec_info += f"+{acodec}"

                        print(f"  • {format_id}: {ext} ({codec_info}) - {resolution} - {size_str}")
            else:
                print("\n❌ No formats found")

            # Display best format recommendations
            print(f"\n⭐ RECOMMENDED FORMATS")
            print("-" * 40)

            # Find best audio format
            best_audio = None
            for fmt in audio_formats:
                if not best_audio or (fmt.get("abr", 0) or 0) > (best_audio.get("abr", 0) or 0):
                    best_audio = fmt

            if best_audio:
                print(
                    f"Best Audio: {best_audio.get('format_id')} ({best_audio.get('ext')}) - {best_audio.get('abr', 0) or 0}kbps"
                )

            # Show the format that would be selected by default
            print(
                f"Default Selection: {info.get('format_id', 'unknown')} ({info.get('ext', 'unknown')})"
            )

            print(f"\n✅ Analysis complete!")

    except yt_dlp.utils.DownloadError as e:
        print(f"❌ yt-dlp error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


def _format_duration(seconds: int) -> str:
    """Format duration in seconds to human-readable format.

    Args:
        seconds: Duration in seconds

    Returns:
        Formatted duration string (e.g., "1h 23m 45s")
    """
    if not seconds:
        return "Unknown"

    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"


def _format_filesize(size_bytes: int) -> str:
    """Format file size in bytes to human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "45.2 MB")
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Check available download options for a Mixcloud cloudcast",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
        Examples:
          python scripts/check_dl_options.py https://www.mixcloud.com/user/cloudcast-name/
          python scripts/check_dl_options.py "https://www.mixcloud.com/artist/mix-title/"
        """,
    )

    parser.add_argument("url", help="Mixcloud cloudcast URL to analyze")

    parser.add_argument("--version", action="version", version="%(prog)s 1.0.0")

    args = parser.parse_args()

    # Validate URL format
    if not args.url.startswith(("http://", "https://")):
        print("❌ Error: URL must start with http:// or https://")
        sys.exit(1)

    if "mixcloud.com" not in args.url.lower():
        print("⚠️  Warning: This doesn't appear to be a Mixcloud URL")
        print("   The script may not work correctly with other platforms")

    # Run the analysis
    check_cloudcast_options(args.url)


if __name__ == "__main__":
    main()

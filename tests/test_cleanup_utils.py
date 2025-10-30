"""Tests for app.utils.cleanup module."""

import os
import pytest
import time
from pathlib import Path
from unittest.mock import Mock, patch

from app.utils.cleanup import PartialFileCleanup


class TestPartialFileCleanup:
    """Test cases for PartialFileCleanup utility class."""

    def test_cleanup_partial_files_nonexistent_directory(self):
        """Test cleanup with non-existent directory returns zero counts."""
        nonexistent_dir = Path("/nonexistent/directory")
        result = PartialFileCleanup.cleanup_partial_files(directory=nonexistent_dir)
        
        assert result == {"downloading": 0, "converting": 0}

    def test_cleanup_partial_files_directory_is_file(self, tmp_path):
        """Test cleanup with file path instead of directory returns zero counts."""
        test_file = tmp_path / "testfile.txt"
        test_file.write_text("test")
        
        result = PartialFileCleanup.cleanup_partial_files(directory=test_file)
        
        assert result == {"downloading": 0, "converting": 0}

    def test_cleanup_partial_files_empty_directory(self, tmp_path):
        """Test cleanup with empty directory returns zero counts."""
        result = PartialFileCleanup.cleanup_partial_files(directory=tmp_path)
        
        assert result == {"downloading": 0, "converting": 0}

    def test_cleanup_partial_files_no_partial_files(self, tmp_path):
        """Test cleanup with directory containing no partial files."""
        # Create some regular files
        (tmp_path / "regular_file.txt").write_text("content")
        (tmp_path / "another_file.mp3").write_text("audio data")
        
        result = PartialFileCleanup.cleanup_partial_files(directory=tmp_path)
        
        assert result == {"downloading": 0, "converting": 0}

    def test_cleanup_partial_files_recent_files_not_cleaned(self, tmp_path):
        """Test that recent partial files are not cleaned up."""
        # Create recent partial files
        downloading_file = tmp_path / "recent.mp3.downloading"
        converting_file = tmp_path / "recent.mp3.converting"
        
        downloading_file.write_text("downloading")
        converting_file.write_text("converting")
        
        # Use default max_age (60 minutes) - files are very recent
        result = PartialFileCleanup.cleanup_partial_files(directory=tmp_path)
        
        assert result == {"downloading": 0, "converting": 0}
        assert downloading_file.exists()
        assert converting_file.exists()

    def test_cleanup_partial_files_old_files_cleaned(self, tmp_path):
        """Test that old partial files are cleaned up."""
        downloading_file = tmp_path / "old.mp3.downloading"
        converting_file = tmp_path / "old.mp3.converting"
        
        downloading_file.write_text("downloading")
        converting_file.write_text("converting")
        
        # Mock time to make files appear old
        current_time = time.time()
        old_time = current_time - (2 * 60 * 60)  # 2 hours ago
        
        # Use real file timestamps by setting them manually
        old_timestamp = current_time - (2 * 60 * 60)  # 2 hours ago
        
        # Set actual file timestamps
        downloading_file.touch()
        converting_file.touch()
        os.utime(downloading_file, (old_timestamp, old_timestamp))
        os.utime(converting_file, (old_timestamp, old_timestamp))
        
        with patch('app.utils.cleanup.time.time', return_value=current_time):
            result = PartialFileCleanup.cleanup_partial_files(
                directory=tmp_path, 
                max_age_minutes=60
            )
        
        assert result == {"downloading": 1, "converting": 1}
        assert not downloading_file.exists()
        assert not converting_file.exists()

    def test_cleanup_partial_files_permission_error_handling(self, tmp_path):
        """Test handling of permission errors during cleanup."""
        downloading_file = tmp_path / "protected.mp3.downloading"
        downloading_file.write_text("downloading")
        
        current_time = time.time()
        old_time = current_time - (2 * 60 * 60)  # 2 hours ago
        
        # Set actual file timestamp to be old
        old_timestamp = current_time - (2 * 60 * 60)  # 2 hours ago
        downloading_file.touch()
        os.utime(downloading_file, (old_timestamp, old_timestamp))
        
        with patch('app.utils.cleanup.time.time', return_value=current_time):
            with patch('pathlib.Path.unlink', side_effect=PermissionError):
                result = PartialFileCleanup.cleanup_partial_files(
                    directory=tmp_path,
                    max_age_minutes=60
                )
        
        # Should handle error gracefully and continue
        assert result == {"downloading": 0, "converting": 0}

    def test_cleanup_partial_files_custom_max_age(self, tmp_path):
        """Test cleanup with custom max_age_minutes parameter."""
        downloading_file = tmp_path / "test.mp3.downloading"
        downloading_file.write_text("downloading")
        
        current_time = time.time()
        # File is 30 minutes old
        file_time = current_time - (30 * 60)
        
        # Set actual file timestamp
        downloading_file.touch()
        os.utime(downloading_file, (file_time, file_time))
        
        with patch('app.utils.cleanup.time.time', return_value=current_time):
            # With max_age=60 minutes, should not be cleaned
            result1 = PartialFileCleanup.cleanup_partial_files(
                directory=tmp_path,
                max_age_minutes=60
            )
            assert result1 == {"downloading": 0, "converting": 0}
            
            # With max_age=15 minutes, should be cleaned
            result2 = PartialFileCleanup.cleanup_partial_files(
                directory=tmp_path,
                max_age_minutes=15
            )
            assert result2 == {"downloading": 1, "converting": 0}

    def test_list_partial_files_nonexistent_directory(self):
        """Test listing partial files in non-existent directory."""
        nonexistent_dir = Path("/nonexistent/directory")
        result = PartialFileCleanup.list_partial_files(directory=nonexistent_dir)
        
        assert result == {"downloading": [], "converting": []}

    def test_list_partial_files_directory_is_file(self, tmp_path):
        """Test listing partial files when path is a file."""
        test_file = tmp_path / "testfile.txt"
        test_file.write_text("test")
        
        result = PartialFileCleanup.list_partial_files(directory=test_file)
        
        assert result == {"downloading": [], "converting": []}

    def test_list_partial_files_empty_directory(self, tmp_path):
        """Test listing partial files in empty directory."""
        result = PartialFileCleanup.list_partial_files(directory=tmp_path)
        
        assert result == {"downloading": [], "converting": []}

    def test_list_partial_files_with_partial_files(self, tmp_path):
        """Test listing partial files with actual partial files present."""
        # Create partial files
        downloading_files = [
            tmp_path / "track1.mp3.downloading",
            tmp_path / "track2.flac.downloading"
        ]
        converting_files = [
            tmp_path / "track3.mp3.converting",
            tmp_path / "track4.flac.converting"
        ]
        
        for file in downloading_files + converting_files:
            file.write_text("content")
        
        # Create regular files (should not be included)
        (tmp_path / "regular.mp3").write_text("audio")
        (tmp_path / "other.txt").write_text("text")
        
        result = PartialFileCleanup.list_partial_files(directory=tmp_path)
        
        expected_downloading = [str(f) for f in downloading_files]
        expected_converting = [str(f) for f in converting_files]
        
        assert set(result["downloading"]) == set(expected_downloading)
        assert set(result["converting"]) == set(expected_converting)

    def test_cleanup_fragment_files_nonexistent_directory(self):
        """Test fragment cleanup with non-existent directory."""
        nonexistent_dir = Path("/nonexistent/directory")
        result = PartialFileCleanup.cleanup_fragment_files(directory=nonexistent_dir)
        
        assert result == 0

    def test_cleanup_fragment_files_directory_is_file(self, tmp_path):
        """Test fragment cleanup when path is a file."""
        test_file = tmp_path / "testfile.txt"
        test_file.write_text("test")
        
        result = PartialFileCleanup.cleanup_fragment_files(directory=test_file)
        
        assert result == 0

    def test_cleanup_fragment_files_empty_directory(self, tmp_path):
        """Test fragment cleanup in empty directory."""
        result = PartialFileCleanup.cleanup_fragment_files(directory=tmp_path)
        
        assert result == 0

    def test_cleanup_fragment_files_with_fragments(self, tmp_path):
        """Test fragment cleanup with actual fragment files."""
        # Create fragment files matching different patterns
        fragment_files = [
            tmp_path / "video.part",
            tmp_path / "video.part-Frag1",
            tmp_path / "video.part-Frag2",
            tmp_path / "audio.webm.part1",
            tmp_path / "movie.mp4.part-001"
        ]
        
        for file in fragment_files:
            file.write_text("fragment data")
        
        # Create regular files (should not be cleaned)
        regular_files = [
            tmp_path / "complete.mp4",
            tmp_path / "audio.mp3"
        ]
        
        for file in regular_files:
            file.write_text("complete file")
        
        result = PartialFileCleanup.cleanup_fragment_files(directory=tmp_path)
        
        assert result == len(fragment_files)
        
        # Verify fragment files are gone
        for file in fragment_files:
            assert not file.exists()
        
        # Verify regular files remain
        for file in regular_files:
            assert file.exists()

    def test_cleanup_fragment_files_permission_error(self, tmp_path):
        """Test fragment cleanup with permission errors."""
        fragment_file = tmp_path / "protected.part"
        fragment_file.write_text("data")
        
        with patch('pathlib.Path.unlink', side_effect=PermissionError):
            result = PartialFileCleanup.cleanup_fragment_files(directory=tmp_path)
        
        # Should handle error gracefully
        assert result == 0

    def test_get_partial_file_info_nonexistent_file(self):
        """Test getting info for non-existent file."""
        nonexistent_file = Path("/nonexistent/file.downloading")
        result = PartialFileCleanup.get_partial_file_info(file_path=nonexistent_file)
        
        assert result is None

    def test_get_partial_file_info_directory(self, tmp_path):
        """Test getting info for directory instead of file."""
        result = PartialFileCleanup.get_partial_file_info(file_path=tmp_path)
        
        assert result is None

    def test_get_partial_file_info_non_partial_file(self, tmp_path):
        """Test getting info for non-partial file."""
        regular_file = tmp_path / "regular.mp3"
        regular_file.write_text("audio data")
        
        result = PartialFileCleanup.get_partial_file_info(file_path=regular_file)
        
        assert result is None

    def test_get_partial_file_info_downloading_with_extension(self, tmp_path):
        """Test getting info for downloading file with extension."""
        downloading_file = tmp_path / "track.mp3.downloading"
        downloading_file.write_text("downloading")
        
        result = PartialFileCleanup.get_partial_file_info(file_path=downloading_file)
        
        expected = {
            "type": "downloading",
            "base_name": "track",
            "target_extension": "mp3",
            "final_name": "track.mp3"
        }
        assert result == expected

    def test_get_partial_file_info_downloading_without_extension(self, tmp_path):
        """Test getting info for downloading file without extension."""
        downloading_file = tmp_path / "trackname.downloading"
        downloading_file.write_text("downloading")
        
        result = PartialFileCleanup.get_partial_file_info(file_path=downloading_file)
        
        expected = {
            "type": "downloading",
            "base_name": "trackname",
            "target_extension": "",
            "final_name": "trackname"
        }
        assert result == expected

    def test_get_partial_file_info_converting_with_extension(self, tmp_path):
        """Test getting info for converting file with extension."""
        converting_file = tmp_path / "track.flac.converting"
        converting_file.write_text("converting")
        
        result = PartialFileCleanup.get_partial_file_info(file_path=converting_file)
        
        expected = {
            "type": "converting",
            "base_name": "track",
            "target_extension": "flac",
            "final_name": "track.flac"
        }
        assert result == expected

    def test_get_partial_file_info_converting_without_extension(self, tmp_path):
        """Test getting info for converting file without extension."""
        converting_file = tmp_path / "trackname.converting"
        converting_file.write_text("converting")
        
        result = PartialFileCleanup.get_partial_file_info(file_path=converting_file)
        
        expected = {
            "type": "converting",
            "base_name": "trackname",
            "target_extension": "",
            "final_name": "trackname"
        }
        assert result == expected

    def test_get_partial_file_info_complex_filename(self, tmp_path):
        """Test getting info for file with complex filename including dots."""
        converting_file = tmp_path / "Artist - Track.Name.With.Dots.mp3.converting"
        converting_file.write_text("converting")
        
        result = PartialFileCleanup.get_partial_file_info(file_path=converting_file)
        
        expected = {
            "type": "converting",
            "base_name": "Artist - Track.Name.With.Dots",
            "target_extension": "mp3",
            "final_name": "Artist - Track.Name.With.Dots.mp3"
        }
        assert result == expected


# Integration test
class TestPartialFileCleanupIntegration:
    """Integration tests for PartialFileCleanup operations."""

    def test_full_cleanup_workflow(self, tmp_path):
        """Test complete cleanup workflow with mixed file types and ages."""
        # Create a mix of files
        files_to_create = [
            # Recent files (should not be cleaned)
            ("recent.mp3.downloading", "downloading"),
            ("recent.flac.converting", "converting"),
            # Old files (should be cleaned)
            ("old.mp3.downloading", "downloading"), 
            ("old.flac.converting", "converting"),
            # Fragment files (should be cleaned)
            ("fragment.part", "fragment"),
            ("video.webm.part-Frag1", "fragment"),
            # Regular files (should not be touched)
            ("regular.mp3", "audio data"),
            ("document.txt", "text content")
        ]
        
        current_time = time.time()
        recent_time = current_time - (30 * 60)  # 30 minutes ago
        old_time = current_time - (2 * 60 * 60)  # 2 hours ago
        
        created_files = {}
        for filename, content in files_to_create:
            file_path = tmp_path / filename
            file_path.write_text(content)
            created_files[filename] = file_path
        
        # Set up file times using real timestamps
        # Set timestamps for old files
        for filename in ["old.mp3.downloading", "old.flac.converting"]:
            file_path = created_files[filename]
            file_path.touch()
            os.utime(file_path, (old_time, old_time))
        
        # Set timestamps for recent files  
        for filename in ["recent.mp3.downloading", "recent.flac.converting"]:
            file_path = created_files[filename]
            file_path.touch()
            os.utime(file_path, (recent_time, recent_time))
        
        with patch('app.utils.cleanup.time.time', return_value=current_time):
                
                # Test listing files before cleanup
                listed = PartialFileCleanup.list_partial_files(directory=tmp_path)
                assert len(listed["downloading"]) == 2
                assert len(listed["converting"]) == 2
                
                # Cleanup partial files
                partial_result = PartialFileCleanup.cleanup_partial_files(
                    directory=tmp_path,
                    max_age_minutes=60
                )
                
                # Cleanup fragment files
                fragment_result = PartialFileCleanup.cleanup_fragment_files(directory=tmp_path)
        
        # Verify results
        assert partial_result == {"downloading": 1, "converting": 1}
        assert fragment_result == 2
        
        # Verify old partial files are gone
        assert not created_files["old.mp3.downloading"].exists()
        assert not created_files["old.flac.converting"].exists()
        
        # Verify fragment files are gone
        assert not created_files["fragment.part"].exists()
        assert not created_files["video.webm.part-Frag1"].exists()
        
        # Verify recent partial files remain
        assert created_files["recent.mp3.downloading"].exists()
        assert created_files["recent.flac.converting"].exists()
        
        # Verify regular files remain
        assert created_files["regular.mp3"].exists()
        assert created_files["document.txt"].exists()
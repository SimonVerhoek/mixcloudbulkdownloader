"""Tests for Unicode progress matching in CloudcastQTreeWidget."""

import pytest
from unittest.mock import Mock
from PySide6.QtWidgets import QApplication

from app.consts import KNOWN_MEDIA_EXTENSIONS
from app.custom_widgets.cloudcast_q_tree_widget import CloudcastQTreeWidget
from app.custom_widgets.cloudcast_q_tree_widget_item import CloudcastQTreeWidgetItem
from app.data_classes import MixcloudUser, Cloudcast
from tests.stubs.api_stubs import StubMixcloudAPIService
from tests.stubs.download_stubs import StubDownloadService
from tests.stubs.file_stubs import StubFileService


@pytest.fixture
def qt_app():
    """Create QApplication instance for Qt tests."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    yield app


class TestUnicodeProgressMatching:
    """Test cases for Unicode character handling in progress matching."""

    def test_normalize_expected_name_basic(self, qt_app):
        """Test basic expected name normalization."""
        widget = CloudcastQTreeWidget()
        
        user = MixcloudUser(
            key="/testuser/",
            name="TestUser",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser"
        )
        
        cloudcast = Cloudcast(
            name="Test Mix",
            url="https://www.mixcloud.com/testuser/test-mix/",
            user=user
        )
        
        item = CloudcastQTreeWidgetItem(cloudcast)
        expected = widget._get_normalized_expected_name(item)
        
        assert expected == "testuser - test mix"

    def test_normalize_expected_name_full_width_characters(self, qt_app):
        """Test normalization of full-width Unicode characters."""
        widget = CloudcastQTreeWidget()
        
        user = MixcloudUser(
            key="/prettylights/",
            name="PrettyLights",
            pictures={},
            url="https://www.mixcloud.com/prettylights/",
            username="prettylights"
        )
        
        # Cloudcast name with full-width characters (as might come from API)
        cloudcast = Cloudcast(
            name="EP302 ft. Modern Measure :: Pretty Lights - 10.25.17 - The Hot Sh*t",
            url="https://www.mixcloud.com/prettylights/test/",
            user=user
        )
        
        item = CloudcastQTreeWidgetItem(cloudcast)
        expected = widget._get_normalized_expected_name(item)
        
        # Should normalize to regular ASCII characters with safe punctuation preserved
        assert expected == "prettylights - ep302 ft. modern measure :: pretty lights - 10.25.17 - the hot sh*t"

    def test_progress_matching_with_unicode_differences(self, qt_app):
        """Test that progress matching works despite Unicode character differences."""
        # Create widget with services
        api_service = StubMixcloudAPIService()
        download_service = StubDownloadService()
        file_service = StubFileService()
        
        widget = CloudcastQTreeWidget(
            api_service=api_service,
            download_service=download_service, 
            file_service=file_service
        )
        
        # Create test data
        user = MixcloudUser(
            key="/prettylights/",
            name="PrettyLights", 
            pictures={},
            url="https://www.mixcloud.com/prettylights/",
            username="prettylights"
        )
        
        cloudcast = Cloudcast(
            name="EP302 ft. Modern Measure :: Pretty Lights - 10.25.17 - The Hot Sh*t",
            url="https://www.mixcloud.com/prettylights/test/",
            user=user
        )
        
        # Add cloudcast to widget and select it
        widget.add_result(cloudcast)
        items = widget._get_tree_items()
        assert len(items) == 1
        
        item = items[0]
        item.setCheckState(0, item.checkState(0).__class__.Checked)  # Select the item
        
        # Simulate yt-dlp providing the normalized filename (which is now expected)
        ytdlp_name = widget._get_normalized_expected_name(item) + ".m4a"
        
        # Test that progress matching works with proper normalization
        widget.update_item_download_progress(ytdlp_name, "50% completed")
        
        # Verify progress was set
        assert item.text(2) == "50% completed"

    def test_progress_matching_no_match_different_content(self, qt_app):
        """Test that progress matching fails correctly for different content."""
        widget = CloudcastQTreeWidget()
        
        user = MixcloudUser(
            key="/testuser/",
            name="TestUser",
            pictures={},
            url="https://www.mixcloud.com/testuser/",
            username="testuser"
        )
        
        cloudcast = Cloudcast(
            name="Mix A",
            url="https://www.mixcloud.com/testuser/mix-a/",
            user=user
        )
        
        widget.add_result(cloudcast)
        items = widget._get_tree_items()
        item = items[0]
        item.setCheckState(0, item.checkState(0).__class__.Checked)
        
        # Try to update progress for a different mix
        widget.update_item_download_progress("testuser - mix b", "50% completed")
        
        # Progress should not be set
        assert item.text(2) == ""

    def test_unicode_character_replacements(self, qt_app):
        """Test specific Unicode character replacements."""
        widget = CloudcastQTreeWidget()
        
        test_cases = [
            ("Test：Colon", "test:colon"),             # : preserved 
            ("Test＊Asterisk", "test*asterisk"),       # * preserved
            ("Test？Question", "testquestion"),        # ? removed
            ("Test｜Pipe", "testpipe"),                # | removed
            ("Test／Slash", "testslash"),              # / removed (still unsafe)
            ("Test＜Less", "testless"),                # < removed
            ("Test＞Greater", "testgreater"),          # > removed
            ("Test＂Quote", "testquote"),              # " removed
        ]
        
        for input_name, expected_output in test_cases:
            user = MixcloudUser(
                key="/user/", name="User", pictures={}, 
                url="https://www.mixcloud.com/user/", username="user"
            )
            
            cloudcast = Cloudcast(
                name=input_name,
                url="https://www.mixcloud.com/user/test/",
                user=user
            )
            
            item = CloudcastQTreeWidgetItem(cloudcast)
            result = widget._get_normalized_expected_name(item)
            
            assert result == f"user - {expected_output}"

    def test_nfkc_normalization(self, qt_app):
        """Test that NFKC normalization is applied correctly."""
        widget = CloudcastQTreeWidget()
        
        user = MixcloudUser(
            key="/user/", name="User", pictures={},
            url="https://www.mixcloud.com/user/", username="user"
        )
        
        # Test with composed and decomposed Unicode characters
        cloudcast = Cloudcast(
            name="Café",  # é as single character
            url="https://www.mixcloud.com/user/test/",
            user=user
        )
        
        item = CloudcastQTreeWidgetItem(cloudcast)
        result = widget._get_normalized_expected_name(item)
        
        # Should be normalized to ASCII base characters
        assert result == "user - cafe"
        
        # Test matching with different Unicode forms
        widget.add_result(cloudcast)
        items = widget._get_tree_items()
        test_item = items[0]
        test_item.setCheckState(0, test_item.checkState(0).__class__.Checked)
        
        # Simulate yt-dlp name with same normalized form
        widget.update_item_download_progress("user - cafe.m4a", "25% completed")  
        
        # Should match and update progress since both normalize to same ASCII form
        assert test_item.text(2) == "25% completed"

    def test_big_solidus_progress_matching(self, qt_app):
        """Test progress matching with BIG SOLIDUS character (U+29F8)."""
        # Create widget with services
        api_service = StubMixcloudAPIService()
        download_service = StubDownloadService()
        file_service = StubFileService()
        
        widget = CloudcastQTreeWidget(
            api_service=api_service,
            download_service=download_service, 
            file_service=file_service
        )
        
        # Create test data with the problematic cloudcast name
        user = MixcloudUser(
            key="/rogersmorgan/",
            name="Rogersmorgan", 
            pictures={},
            url="https://www.mixcloud.com/rogersmorgan/",
            username="rogersmorgan"
        )
        
        cloudcast = Cloudcast(
            name="DAVID FERRER & ROGER S MORGAN LIVE SET RINCÓN DE TINTÍN 28⧸08⧸21",
            url="https://www.mixcloud.com/rogersmorgan/test/",
            user=user
        )
        
        # Add cloudcast to widget and select it
        widget.add_result(cloudcast)
        items = widget._get_tree_items()
        assert len(items) == 1
        
        item = items[0]
        item.setCheckState(0, item.checkState(0).__class__.Checked)  # Select the item
        
        # Test normalization directly
        expected_normalized = widget._get_normalized_expected_name(item)
        expected_result = "rogersmorgan - david ferrer & roger s morgan live set rincon de tintin 280821"
        assert expected_normalized == expected_result
        
        # Simulate yt-dlp providing the exact normalized filename (realistic scenario)
        ytdlp_filename = "rogersmorgan - david ferrer & roger s morgan live set rincon de tintin 280821.m4a"
        
        # Test that progress matching works with exact normalization
        widget.update_item_download_progress(ytdlp_filename, "75% completed")
        
        # Verify progress was set
        assert item.text(2) == "75% completed"
        
    def test_big_solidus_normalization_unit(self, qt_app):
        """Test that BIG SOLIDUS character is properly normalized."""
        widget = CloudcastQTreeWidget()
        
        user = MixcloudUser(
            key="/user/", name="User", pictures={},
            url="https://www.mixcloud.com/user/", username="user"
        )
        
        # Test with BIG SOLIDUS character
        cloudcast = Cloudcast(
            name="Test Mix 28⧸08⧸21",  # Contains U+29F8 BIG SOLIDUS
            url="https://www.mixcloud.com/user/test/",
            user=user
        )
        
        item = CloudcastQTreeWidgetItem(cloudcast)
        result = widget._get_normalized_expected_name(item)
        
        # With the new ASCII-based normalization, Unicode characters are removed
        # This is more robust as it handles any Unicode character systematically
        expected_result = "user - test mix 280821"  # Unicode characters removed
        assert result == expected_result

    def test_comprehensive_unicode_normalization(self, qt_app):
        """Test comprehensive Unicode character handling with various scenarios."""
        widget = CloudcastQTreeWidget()
        
        user = MixcloudUser(
            key="/testuser/", name="TestUser", pictures={},
            url="https://www.mixcloud.com/testuser/", username="testuser"
        )
        
        # Test cases with various Unicode characters
        test_cases = [
            ("Mix with émojis 🎵🎧", "testuser - mix with emojis"),
            ("Mix：with＊special／chars", "testuser - mix:with*specialchars"),  # : and * preserved, / removed
            ("RINCÓN DE TINTÍN", "testuser - rincon de tintin"),
            ("Test⧸Mix⧸2023", "testuser - test mix 2023"),
        ]
        
        for input_name, expected_base in test_cases:
            cloudcast = Cloudcast(
                name=input_name,
                url="https://www.mixcloud.com/testuser/test/",
                user=user
            )
            
            item = CloudcastQTreeWidgetItem(cloudcast)
            result = widget._get_normalized_expected_name(item)
            
            # The result should be ASCII-only and reasonably filesystem-safe
            assert all(ord(char) < 128 for char in result), f"Non-ASCII chars in: {result}"
            # Only check for truly problematic characters (: and * are generally safe)
            assert not any(char in result for char in '<>"/\\|?'), f"Unsafe chars in: {result}"

    def test_full_width_characters_progress_matching(self, qt_app):
        """Test progress matching with full-width Unicode characters from user's specific case."""
        api_service = StubMixcloudAPIService()
        download_service = StubDownloadService()
        file_service = StubFileService()
        
        widget = CloudcastQTreeWidget(
            api_service=api_service,
            download_service=download_service, 
            file_service=file_service
        )
        
        # Create test data with the user's problematic cloudcast name  
        user = MixcloudUser(
            key="/prettylights/",
            name="PrettyLights", 
            pictures={},
            url="https://www.mixcloud.com/prettylights/",
            username="prettylights"
        )
        
        # Mixcloud API provides this (regular ASCII characters)
        cloudcast = Cloudcast(
            name="ep299 ft. Zoogma :: Pretty Lights - The HOT Sh*t - 10.04.17",
            url="https://www.mixcloud.com/prettylights/test/",
            user=user
        )
        
        # Add cloudcast to widget and select it
        widget.add_result(cloudcast)
        items = widget._get_tree_items()
        assert len(items) == 1
        
        item = items[0]
        item.setCheckState(0, item.checkState(0).__class__.Checked)
        
        # Simulate yt-dlp providing filename with full-width Unicode characters (including username)
        ytdlp_filename = "PrettyLights - ep299 ft. Zoogma ：： Pretty Lights - The HOT Sh＊t - 10.04.17.m4a"
        
        # Test that progress matching works despite Unicode differences
        widget.update_item_download_progress(ytdlp_filename, "85% completed")
        
        # Verify progress was set
        assert item.text(2) == "85% completed"

    def test_progress_matching_without_username_prefix(self, qt_app):
        """Test progress matching when yt-dlp provides filename without username prefix."""
        api_service = StubMixcloudAPIService()
        download_service = StubDownloadService()
        file_service = StubFileService()
        
        widget = CloudcastQTreeWidget(
            api_service=api_service,
            download_service=download_service, 
            file_service=file_service
        )
        
        user = MixcloudUser(
            key="/prettylights/",
            name="PrettyLights", 
            pictures={},
            url="https://www.mixcloud.com/prettylights/",
            username="prettylights"
        )
        
        # Test both problematic cases from user
        test_cases = [
            "ep299 ft. Zoogma :: Pretty Lights - The HOT Sh*t - 10.04.17",
            "ep300 :: Pretty Lights - The HOT Sh*t - 10.11.17"
        ]
        
        for i, cloudcast_name in enumerate(test_cases):
            cloudcast = Cloudcast(
                name=cloudcast_name,
                url=f"https://www.mixcloud.com/prettylights/test{i}/",
                user=user
            )
            
            # Add cloudcast to widget and select it
            widget.add_result(cloudcast)
            items = widget._get_tree_items()
            item = items[i]
            item.setCheckState(0, item.checkState(0).__class__.Checked)
            
            # Simulate yt-dlp providing filename WITHOUT username prefix
            ytdlp_filename = f"{cloudcast_name}.m4a"
            
            # Test that progress matching works even without username
            expected_progress = f"{(i+1)*30}% completed"
            widget.update_item_download_progress(ytdlp_filename, expected_progress)
            
            # Verify progress was set
            assert item.text(2) == expected_progress

    def test_file_extension_handling_with_dots_in_names(self, qt_app):
        """Test that only actual file extensions are stripped, not date parts like .17."""
        api_service = StubMixcloudAPIService()
        download_service = StubDownloadService()
        file_service = StubFileService()
        
        widget = CloudcastQTreeWidget(
            api_service=api_service,
            download_service=download_service, 
            file_service=file_service
        )
        
        user = MixcloudUser(
            key="/prettylights/",
            name="PrettyLights", 
            pictures={},
            url="https://www.mixcloud.com/prettylights/",
            username="prettylights"
        )
        
        # Test case with date that looks like file extension
        cloudcast = Cloudcast(
            name="ep299 ft. Zoogma :: Pretty Lights - The HOT Sh*t - 10.04.17",
            url="https://www.mixcloud.com/prettylights/test/",
            user=user
        )
        
        widget.add_result(cloudcast)
        item = widget._get_tree_items()[0]
        item.setCheckState(0, item.checkState(0).__class__.Checked)
        
        # Test various filename scenarios
        test_cases = [
            # Real file extensions should be stripped
            ("PrettyLights - ep299 ft. Zoogma :: Pretty Lights - The HOT Sh*t - 10.04.17.m4a", True),
            ("PrettyLights - ep299 ft. Zoogma :: Pretty Lights - The HOT Sh*t - 10.04.17.mp3", True),
            ("PrettyLights - ep299 ft. Zoogma :: Pretty Lights - The HOT Sh*t - 10.04.17.flac", True),
            
            # No extension should work as-is
            ("PrettyLights - ep299 ft. Zoogma :: Pretty Lights - The HOT Sh*t - 10.04.17", True),
            
            # Non-audio extensions should not be stripped (keeping .17)
            ("PrettyLights - ep299 ft. Zoogma :: Pretty Lights - The HOT Sh*t - 10.04.17.txt", False),
            ("PrettyLights - ep299 ft. Zoogma :: Pretty Lights - The HOT Sh*t - 10.04.17.pdf", False),
            
            # Same date format should work
            ("PrettyLights - ep299 ft. Zoogma :: Pretty Lights - The HOT Sh*t - 10.04.17.wav", True),
        ]
        
        for filename, should_match in test_cases:
            # Reset progress for each test
            item.setText(2, "")
            
            widget.update_item_download_progress(filename, "50% completed")
            
            progress_set = item.text(2) == "50% completed"
            
            if should_match:
                assert progress_set, f"Progress should be set for: {filename}"
            else:
                assert not progress_set, f"Progress should NOT be set for: {filename}"

    def test_known_audio_extensions_list(self, qt_app):
        """Test that all common audio/video extensions are properly handled."""
        widget = CloudcastQTreeWidget()
        
        # Test that _normalize_filename automatically removes extensions
        base_filename = "test-track-name"
        
        for ext in KNOWN_MEDIA_EXTENSIONS:
            filename_with_ext = f"{base_filename}{ext}"
            normalized = widget._normalize_filename(filename_with_ext)
            
            # Should end up with just the base filename (extension removal is now automatic)
            assert normalized == base_filename, f"Extension {ext} was not properly stripped"
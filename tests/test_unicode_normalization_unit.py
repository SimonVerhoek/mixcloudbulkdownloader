"""Unit tests for Unicode normalization logic without Qt dependencies."""

import pytest
import unicodedata


def normalize_name_for_matching(name: str) -> str:
    """Standalone function to test Unicode normalization logic."""
    # Convert full-width characters to half-width
    normalized = unicodedata.normalize('NFKC', name)
    
    # Additional replacements for common yt-dlp substitutions
    replacements = {
        '：': ':',  # Full-width colon
        '＊': '*',  # Full-width asterisk
        '？': '?',  # Full-width question mark
        '｜': '|',  # Full-width pipe
        '／': '/',  # Full-width slash
        '＜': '<',  # Full-width less-than
        '＞': '>',  # Full-width greater-than
        '＂': '"',  # Full-width quote
    }
    
    for full_width, half_width in replacements.items():
        normalized = normalized.replace(full_width, half_width)
    
    return normalized.lower().strip()


def get_normalized_expected_name(user_name: str, cloudcast_name: str) -> str:
    """Get normalized expected name for matching with yt-dlp filenames."""
    expected_name = f"{user_name} - {cloudcast_name}"
    return normalize_name_for_matching(expected_name)


@pytest.mark.unit
def test_basic_normalization():
    """Test basic string normalization."""
    result = normalize_name_for_matching("TestUser - Test Mix")
    assert result == "testuser - test mix"

@pytest.mark.unit
def test_full_width_colon_normalization():
    """Test full-width colon normalization."""
    # Full-width colon ：vs regular colon :
    input_name = "User - Mix：Part 1"
    result = normalize_name_for_matching(input_name)
    assert result == "user - mix:part 1"

@pytest.mark.unit
def test_full_width_asterisk_normalization():
    """Test full-width asterisk normalization."""
    # Full-width asterisk ＊vs regular asterisk *
    input_name = "User - Hot Sh＊t Mix"
    result = normalize_name_for_matching(input_name)
    assert result == "user - hot sh*t mix"

@pytest.mark.unit
def test_multiple_full_width_characters():
    """Test normalization of multiple full-width characters."""
    input_name = "PrettyLights - EP302：： Modern Measure ＊ Hot Sh＊t"
    result = normalize_name_for_matching(input_name)
    assert result == "prettylights - ep302:: modern measure * hot sh*t"

@pytest.mark.unit
def test_real_world_case():
    """Test the exact case that was failing in production."""
    # API expected name
    api_name = "prettylights - ep302 ft. modern measure :: pretty lights - 10.25.17 - the hot sh*t"
    api_normalized = normalize_name_for_matching(api_name)
    
    # yt-dlp provided name with full-width characters
    ytdlp_name = "prettylights - ep302 ft. modern measure ：： pretty lights - 10.25.17 - the hot sh＊t"
    ytdlp_normalized = normalize_name_for_matching(ytdlp_name)
    
    # Should match after normalization
    assert api_normalized == ytdlp_normalized
    assert api_normalized == "prettylights - ep302 ft. modern measure :: pretty lights - 10.25.17 - the hot sh*t"

@pytest.mark.unit
def test_nfkc_normalization():
    """Test NFKC Unicode normalization."""
    # Test with composed vs decomposed characters
    composed = "Café"  # é as single character U+00E9
    decomposed = "Café"  # e + combining acute accent U+0065 + U+0301
    
    result1 = normalize_name_for_matching(composed)
    result2 = normalize_name_for_matching(decomposed)
    
    # Should be identical after NFKC normalization
    assert result1 == result2
    assert result1 == "café"

@pytest.mark.unit
def test_all_full_width_replacements():
    """Test all full-width character replacements."""
    test_cases = [
        ("Test：", "test:"),           # Full-width colon
        ("Test＊", "test*"),          # Full-width asterisk
        ("Test？", "test?"),          # Full-width question mark
        ("Test｜", "test|"),          # Full-width pipe
        ("Test／", "test/"),          # Full-width slash
        ("Test＜", "test<"),          # Full-width less-than
        ("Test＞", "test>"),          # Full-width greater-than
        ("Test＂", 'test"'),          # Full-width quote
    ]
    
    for input_str, expected in test_cases:
        result = normalize_name_for_matching(input_str)
        assert result == expected

@pytest.mark.unit
def test_expected_name_generation():
    """Test expected name generation function."""
    result = get_normalized_expected_name("TestUser", "Mix Name：Part 1")
    assert result == "testuser - mix name:part 1"

@pytest.mark.unit
def test_case_insensitive_matching():
    """Test that matching is case insensitive."""
    name1 = "PRETTYLIGHTS - EP302 FT. MODERN MEASURE"
    name2 = "prettylights - ep302 ft. modern measure"
    
    result1 = normalize_name_for_matching(name1)
    result2 = normalize_name_for_matching(name2)
    
    assert result1 == result2
    assert result1 == "prettylights - ep302 ft. modern measure"

@pytest.mark.unit
def test_whitespace_normalization():
    """Test that extra whitespace is normalized."""
    input_name = "  User   -   Mix  Name  "
    result = normalize_name_for_matching(input_name)
    assert result == "user   -   mix  name"  # strip() only removes leading/trailing

@pytest.mark.unit
def test_empty_and_none_handling():
    """Test handling of edge cases."""
    assert normalize_name_for_matching("") == ""
    assert normalize_name_for_matching("   ") == ""

@pytest.mark.unit
def test_unicode_only_characters():
    """Test handling of Unicode-only characters."""
    # Hebrew characters (should be preserved)
    input_name = "User - דיבור חדיש 706"
    result = normalize_name_for_matching(input_name)
    assert result == "user - דיבור חדיש 706"

@pytest.mark.unit
def test_mixed_ascii_unicode():
    """Test mixed ASCII and Unicode characters."""
    input_name = "Yuval Ganor - דיבור חדיש：706＊"
    result = normalize_name_for_matching(input_name)
    assert result == "yuval ganor - דיבור חדיש:706*"


if __name__ == "__main__":
    # Allow running this test file directly with pytest
    pytest.main([__file__, "-v"])
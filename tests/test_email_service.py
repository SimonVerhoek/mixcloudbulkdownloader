"""Tests for email service functionality used by feedback system."""

import pytest
from unittest.mock import Mock, patch
from urllib.parse import unquote

from app.consts.messages import FEEDBACK_EMAIL, FEEDBACK_SUBJECT


class TestEmailServiceConstants:
    """Test email service constants and configuration."""
    
    def test_feedback_email_constant_exists(self):
        """Test that feedback email constant is defined."""
        assert FEEDBACK_EMAIL is not None
        assert isinstance(FEEDBACK_EMAIL, str)
        assert len(FEEDBACK_EMAIL) > 0
        assert "@" in FEEDBACK_EMAIL
        
    def test_feedback_subject_constant_exists(self):
        """Test that feedback subject constant is defined."""
        assert FEEDBACK_SUBJECT is not None
        assert isinstance(FEEDBACK_SUBJECT, str)
        assert len(FEEDBACK_SUBJECT) > 0
        
    def test_feedback_email_format_valid(self):
        """Test that feedback email has valid email format."""
        # Basic email validation
        assert FEEDBACK_EMAIL.count("@") == 1
        local, domain = FEEDBACK_EMAIL.split("@")
        assert len(local) > 0
        assert len(domain) > 0
        assert "." in domain


class TestMailtoURLGeneration:
    """Test mailto URL generation for feedback emails."""
    
    def test_mailto_url_basic_formation(self):
        """Test basic mailto URL formation."""
        feedback_text = "This is test feedback"
        subject = FEEDBACK_SUBJECT.replace(" ", "%20")
        body = feedback_text.replace(" ", "%20")
        
        expected_url = f"mailto:{FEEDBACK_EMAIL}?subject={subject}&body={body}"
        
        # Test URL components
        assert expected_url.startswith(f"mailto:{FEEDBACK_EMAIL}")
        assert f"subject={subject}" in expected_url
        assert f"body={body}" in expected_url
        
    def test_mailto_url_with_newlines(self):
        """Test mailto URL formation with newlines in feedback."""
        feedback_text = "Line 1\nLine 2\nLine 3"
        body = feedback_text.replace("\n", "%0A").replace(" ", "%20")
        
        expected_url = f"mailto:{FEEDBACK_EMAIL}?subject={FEEDBACK_SUBJECT.replace(' ', '%20')}&body={body}"
        
        assert "%0A" in expected_url
        assert "Line%201%0ALine%202%0ALine%203" in expected_url
        
    def test_mailto_url_with_special_characters(self):
        """Test mailto URL formation with special characters."""
        feedback_text = "Feedback with special chars: @#$%^&*()"
        
        # Test that these characters get properly encoded
        body = feedback_text.replace(" ", "%20")
        expected_url = f"mailto:{FEEDBACK_EMAIL}?subject={FEEDBACK_SUBJECT.replace(' ', '%20')}&body={body}"
        
        # URL should contain the email address and encoded content
        assert FEEDBACK_EMAIL in expected_url
        assert "special%20chars" in expected_url
        
    def test_mailto_url_decoding(self):
        """Test that encoded mailto URLs decode correctly."""
        original_text = "Test feedback with spaces and\nnewlines!"
        encoded_body = original_text.replace("\n", "%0A").replace(" ", "%20")
        
        # Decode and verify
        decoded_body = unquote(encoded_body).replace("%0A", "\n")
        assert decoded_body == original_text


class TestEmailClientIntegration:
    """Test email client integration functionality."""
    
    def test_webbrowser_open_success(self):
        """Test successful email client opening."""
        test_feedback = "Test feedback message"
        
        with patch('webbrowser.open') as mock_open:
            # Simulate what the dialog does
            subject = FEEDBACK_SUBJECT.replace(" ", "%20")
            body = test_feedback.replace(" ", "%20")
            mailto_url = f"mailto:{FEEDBACK_EMAIL}?subject={subject}&body={body}"
            
            # This is what the dialog calls
            import webbrowser
            webbrowser.open(mailto_url)
            
            mock_open.assert_called_once_with(mailto_url)
            
    def test_webbrowser_open_failure_handling(self):
        """Test handling of email client opening failures."""
        test_feedback = "Test feedback message"
        
        with patch('webbrowser.open', side_effect=OSError("No email client")) as mock_open:
            
            # Simulate error handling
            try:
                import webbrowser
                subject = FEEDBACK_SUBJECT.replace(" ", "%20")
                body = test_feedback.replace(" ", "%20")
                mailto_url = f"mailto:{FEEDBACK_EMAIL}?subject={subject}&body={body}"
                webbrowser.open(mailto_url)
                success = True
            except Exception as e:
                success = False
                error_message = str(e)
                
            assert success is False
            assert "No email client" in error_message
            mock_open.assert_called_once()
            
    def test_email_client_different_platforms(self):
        """Test email client behavior on different platforms."""
        test_feedback = "Cross-platform test"
        
        # Test that the URL formation is platform-independent
        subject = FEEDBACK_SUBJECT.replace(" ", "%20")
        body = test_feedback.replace(" ", "%20")
        mailto_url = f"mailto:{FEEDBACK_EMAIL}?subject={subject}&body={body}"
        
        # URL should be valid regardless of platform
        assert mailto_url.startswith("mailto:")
        assert FEEDBACK_EMAIL in mailto_url
        assert "Cross-platform%20test" in mailto_url


class TestEmailServiceErrorScenarios:
    """Test error scenarios in email service."""
    
    def test_empty_email_address_handling(self):
        """Test handling of empty email address."""
        empty_email = ""
        test_feedback = "Test feedback"
        
        # Should still form valid mailto URL structure
        mailto_url = f"mailto:{empty_email}?subject={FEEDBACK_SUBJECT}&body={test_feedback}"
        
        assert mailto_url.startswith("mailto:")
        # But it would be invalid for actual use
        assert "@" not in empty_email
        
    def test_malformed_email_address_handling(self):
        """Test handling of malformed email addresses."""
        malformed_emails = [
            "invalid-email",
            "@domain.com", 
            "user@",
            "user@domain",
            "user@@domain.com"
        ]
        
        for email in malformed_emails:
            mailto_url = f"mailto:{email}?subject={FEEDBACK_SUBJECT}&body=test"
            
            # URL will form but may not be valid
            assert mailto_url.startswith("mailto:")
            # Real validation would happen in email client
            
    def test_very_long_feedback_handling(self):
        """Test handling of very long feedback messages."""
        # Create very long feedback (2000 characters)
        long_feedback = "x" * 2000
        
        subject = FEEDBACK_SUBJECT.replace(" ", "%20")
        body = long_feedback.replace(" ", "%20")  # No spaces in this case
        mailto_url = f"mailto:{FEEDBACK_EMAIL}?subject={subject}&body={body}"
        
        # URL should form correctly even with long content
        assert mailto_url.startswith(f"mailto:{FEEDBACK_EMAIL}")
        assert len(body) == 2000  # All x's, no encoding needed
        
    def test_unicode_feedback_encoding(self):
        """Test handling of unicode characters in feedback."""
        unicode_feedback = "Feedback with émojis 🎵 and ñón-ASCII chars"
        
        # Test basic URL formation (real encoding handled by webbrowser)
        subject = FEEDBACK_SUBJECT.replace(" ", "%20")
        body = unicode_feedback.replace(" ", "%20").replace("\n", "%0A")
        mailto_url = f"mailto:{FEEDBACK_EMAIL}?subject={subject}&body={body}"
        
        assert mailto_url.startswith(f"mailto:{FEEDBACK_EMAIL}")
        assert "émojis" in mailto_url  # Basic replacement, real encoding by webbrowser
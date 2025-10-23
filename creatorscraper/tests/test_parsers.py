"""
Tests for parser utilities.
"""

import pytest
from creatorscraper.utils.parsers import (
    parse_human_number, normalize_url, extract_email_from_text,
    extract_phone_from_text, clean_text, extract_hashtags, extract_mentions,
    parse_engagement_rate, parse_instagram_handle, parse_linkedin_handle
)


class TestParsers:
    """Test parser utility functions."""
    
    def test_parse_human_number(self):
        """Test human number parsing."""
        # Test various formats
        assert parse_human_number("1.2M") == 1200000
        assert parse_human_number("5.4K") == 5400
        assert parse_human_number("1,234") == 1234
        assert parse_human_number("500") == 500
        assert parse_human_number("1.5B") == 1500000000
        
        # Test edge cases
        assert parse_human_number("") is None
        assert parse_human_number(None) is None
        assert parse_human_number("abc") is None
        assert parse_human_number("1.2K followers") == 1200
    
    def test_normalize_url(self):
        """Test URL normalization."""
        # Test absolute URLs
        assert normalize_url("https://example.com") == "https://example.com"
        assert normalize_url("http://example.com") == "http://example.com"
        
        # Test relative URLs
        assert normalize_url("/path", "https://example.com") == "https://example.com/path"
        assert normalize_url("path", "https://example.com/") == "https://example.com/path"
        
        # Test edge cases
        assert normalize_url("") is None
        assert normalize_url(None) is None
        assert normalize_url("invalid") is None
    
    def test_extract_email_from_text(self):
        """Test email extraction."""
        # Test valid emails
        assert extract_email_from_text("Contact me at john@example.com") == "john@example.com"
        assert extract_email_from_text("Email: test@domain.co.uk") == "test@domain.co.uk"
        
        # Test multiple emails (should return first)
        text = "Email1: first@example.com, Email2: second@example.com"
        assert extract_email_from_text(text) == "first@example.com"
        
        # Test edge cases
        assert extract_email_from_text("") is None
        assert extract_email_from_text("No email here") is None
        assert extract_email_from_text(None) is None
    
    def test_extract_phone_from_text(self):
        """Test phone number extraction."""
        # Test US format
        assert extract_phone_from_text("Call me at (555) 123-4567") == "5551234567"
        assert extract_phone_from_text("Phone: 555-123-4567") == "5551234567"
        
        # Test edge cases
        assert extract_phone_from_text("") is None
        assert extract_phone_from_text("No phone here") is None
        assert extract_phone_from_text(None) is None
    
    def test_clean_text(self):
        """Test text cleaning."""
        # Test whitespace normalization
        assert clean_text("  multiple   spaces  ") == "multiple spaces"
        assert clean_text("line1\nline2\tline3") == "line1 line2 line3"
        
        # Test special character removal
        assert clean_text("Text with @#$% symbols") == "Text with  symbols"
        
        # Test edge cases
        assert clean_text("") == ""
        assert clean_text(None) == ""
    
    def test_extract_hashtags(self):
        """Test hashtag extraction."""
        # Test valid hashtags
        assert extract_hashtags("#fitness #gym #workout") == ["fitness", "gym", "workout"]
        assert extract_hashtags("Check out #fitness and #health") == ["fitness", "health"]
        
        # Test edge cases
        assert extract_hashtags("") == []
        assert extract_hashtags("No hashtags here") == []
        assert extract_hashtags(None) == []
    
    def test_extract_mentions(self):
        """Test mention extraction."""
        # Test valid mentions
        assert extract_mentions("@john @jane @company") == ["john", "jane", "company"]
        assert extract_mentions("Follow @user1 and @user2") == ["user1", "user2"]
        
        # Test edge cases
        assert extract_mentions("") == []
        assert extract_mentions("No mentions here") == []
        assert extract_mentions(None) == []
    
    def test_parse_engagement_rate(self):
        """Test engagement rate calculation."""
        # Test valid calculation
        assert parse_engagement_rate(100, 50, 1000) == 0.15  # (100+50)/1000
        assert parse_engagement_rate(0, 0, 1000) == 0.0
        
        # Test edge cases
        assert parse_engagement_rate(100, 50, 0) is None
        assert parse_engagement_rate(100, 50, None) is None
        assert parse_engagement_rate(None, 50, 1000) is None
    
    def test_parse_instagram_handle(self):
        """Test Instagram handle parsing."""
        # Test various URL formats
        assert parse_instagram_handle("https://www.instagram.com/username/") == "username"
        assert parse_instagram_handle("https://instagram.com/username") == "username"
        assert parse_instagram_handle("@username") == "username"
        assert parse_instagram_handle("username") == "username"
        
        # Test edge cases
        assert parse_instagram_handle("") is None
        assert parse_instagram_handle("invalid-url") is None
        assert parse_instagram_handle(None) is None
    
    def test_parse_linkedin_handle(self):
        """Test LinkedIn handle parsing."""
        # Test various URL formats
        assert parse_linkedin_handle("https://www.linkedin.com/in/username/") == "username"
        assert parse_linkedin_handle("https://linkedin.com/in/username") == "username"
        assert parse_linkedin_handle("username") == "username"
        
        # Test edge cases
        assert parse_linkedin_handle("") is None
        assert parse_linkedin_handle("invalid-url") is None
        assert parse_linkedin_handle(None) is None

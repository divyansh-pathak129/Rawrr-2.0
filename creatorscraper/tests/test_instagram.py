"""
Tests for Instagram scraper functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from creatorscraper.sources.instagram import InstagramScraper
from creatorscraper.models.schemas import ScrapingResult


class TestInstagramScraper:
    """Test Instagram scraper functionality."""
    
    def setup_method(self):
        """Setup test instance."""
        with patch.dict('os.environ', {'INSTAGRAM_ACCESS_TOKEN': 'test_token'}):
            self.scraper = InstagramScraper()
    
    def test_extract_handle_valid_urls(self):
        """Test handle extraction from valid URLs."""
        # Test various URL formats
        assert self.scraper._extract_handle("https://www.instagram.com/username/") == "username"
        assert self.scraper._extract_handle("https://instagram.com/username") == "username"
        assert self.scraper._extract_handle("https://www.instagram.com/username/?hl=en") == "username"
        
        # Test with @ symbol
        assert self.scraper._extract_handle("https://www.instagram.com/@username/") == "username"
    
    def test_extract_handle_invalid_urls(self):
        """Test handle extraction from invalid URLs."""
        # Test invalid URLs
        assert self.scraper._extract_handle("") is None
        assert self.scraper._extract_handle("not-a-url") is None
        assert self.scraper._extract_handle("https://example.com") is None
        assert self.scraper._extract_handle(None) is None
    
    @pytest.mark.asyncio
    async def test_scrape_profile_api_success(self):
        """Test successful API scraping."""
        # Mock API responses
        mock_user_id = "12345"
        mock_profile_data = {
            'id': '12345',
            'username': 'testuser',
            'biography': 'Test bio',
            'followers_count': 1000,
            'follows_count': 500,
            'media_count': 50,
            'profile_picture_url': 'https://example.com/pic.jpg',
            'website': 'https://example.com'
        }
        mock_media_data = [
            {
                'id': '1',
                'permalink': 'https://instagram.com/p/1',
                'timestamp': '2023-01-01T00:00:00Z',
                'caption': 'Test post',
                'like_count': 100,
                'comments_count': 10
            }
        ]
        
        # Mock the API methods
        with patch.object(self.scraper, '_get_user_id', return_value=mock_user_id), \
             patch.object(self.scraper, '_get_user_profile', return_value=mock_profile_data), \
             patch.object(self.scraper, '_get_user_media', return_value=mock_media_data):
            
            result = await self.scraper._scrape_via_api('testuser')
            
            assert result.success is True
            assert result.profile is not None
            assert result.profile.handle == 'testuser'
            assert result.profile.follower_count == 1000
            assert result.method_used == 'api'
    
    @pytest.mark.asyncio
    async def test_scrape_profile_api_failure(self):
        """Test API scraping failure."""
        # Mock API failure
        with patch.object(self.scraper, '_get_user_id', return_value=None):
            result = await self.scraper._scrape_via_api('testuser')
            
            assert result.success is False
            assert result.error == "Could not get user ID from API"
            assert result.method_used == 'api'
    
    @pytest.mark.asyncio
    async def test_scrape_profile_playwright_success(self):
        """Test successful Playwright scraping."""
        # Mock browser and page
        mock_page = AsyncMock()
        mock_browser = AsyncMock()
        mock_browser.new_page.return_value = mock_page
        
        # Mock profile data extraction
        mock_profile_data = {
            'username': 'testuser',
            'biography': 'Test bio',
            'followers_count': 1000,
            'follows_count': 500,
            'media_count': 50,
            'profile_picture_url': 'https://example.com/pic.jpg'
        }
        
        with patch.object(self.scraper, 'browser', mock_browser), \
             patch.object(self.scraper, '_extract_profile_data', return_value=mock_profile_data):
            
            result = await self.scraper._scrape_via_playwright('https://www.instagram.com/testuser/')
            
            assert result.success is True
            assert result.profile is not None
            assert result.profile.handle == 'testuser'
            assert result.method_used == 'scraping'
    
    @pytest.mark.asyncio
    async def test_scrape_profile_playwright_failure(self):
        """Test Playwright scraping failure."""
        # Mock browser failure
        mock_browser = AsyncMock()
        mock_browser.new_page.side_effect = Exception("Browser error")
        
        with patch.object(self.scraper, 'browser', mock_browser):
            result = await self.scraper._scrape_via_playwright('https://www.instagram.com/testuser/')
            
            assert result.success is False
            assert "Browser error" in result.error
            assert result.method_used == 'scraping'
    
    def test_create_profile_from_api(self):
        """Test profile creation from API data."""
        # Mock API data
        profile_data = {
            'username': 'testuser',
            'biography': 'Test bio',
            'followers_count': 1000,
            'follows_count': 500,
            'media_count': 50,
            'profile_picture_url': 'https://example.com/pic.jpg'
        }
        media_data = [
            {
                'id': '1',
                'permalink': 'https://instagram.com/p/1',
                'timestamp': '2023-01-01T00:00:00Z',
                'caption': 'Test post',
                'like_count': 100,
                'comments_count': 10
            }
        ]
        
        profile = self.scraper._create_profile_from_api(profile_data, media_data, 'testuser')
        
        assert profile.source == 'instagram'
        assert profile.handle == 'testuser'
        assert profile.follower_count == 1000
        assert profile.following_count == 500
        assert profile.post_count == 50
        assert len(profile.top_posts) == 1
        assert profile.top_posts[0].url == 'https://instagram.com/p/1'
    
    def test_create_profile_from_scraping(self):
        """Test profile creation from scraped data."""
        # Mock scraped data
        profile_data = {
            'username': 'testuser',
            'biography': 'Test bio',
            'followers_count': 1000,
            'follows_count': 500,
            'media_count': 50,
            'profile_picture_url': 'https://example.com/pic.jpg'
        }
        
        profile = self.scraper._create_profile_from_scraping(profile_data, 'https://www.instagram.com/testuser/')
        
        assert profile.source == 'instagram'
        assert profile.handle == 'testuser'
        assert profile.follower_count == 1000
        assert profile.following_count == 500
        assert profile.post_count == 50
    
    @pytest.mark.asyncio
    async def test_scrape_profile_invalid_url(self):
        """Test scraping with invalid URL."""
        result = await self.scraper.scrape_profile('invalid-url')
        
        assert result.success is False
        assert result.error == "Invalid Instagram profile URL"
        assert result.method_used == "none"
    
    @pytest.mark.asyncio
    async def test_scrape_profile_exception(self):
        """Test scraping with exception."""
        with patch.object(self.scraper, '_extract_handle', side_effect=Exception("Test error")):
            result = await self.scraper.scrape_profile('https://www.instagram.com/test/')
            
            assert result.success is False
            assert "Test error" in result.error
            assert result.method_used == "none"
    
    @pytest.mark.asyncio
    async def test_close(self):
        """Test scraper close method."""
        # Mock browser
        mock_browser = AsyncMock()
        self.scraper.browser = mock_browser
        
        await self.scraper.close()
        
        mock_browser.close.assert_called_once()
        assert self.scraper.browser is None

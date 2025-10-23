"""
Tests for LinkedIn scraper functionality.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from creatorscraper.sources.linkedin import LinkedInScraper
from creatorscraper.models.schemas import ScrapingResult


class TestLinkedInScraper:
    """Test LinkedIn scraper functionality."""
    
    def setup_method(self):
        """Setup test instance."""
        with patch.dict('os.environ', {'LINKEDIN_ACCESS_TOKEN': 'test_token'}):
            self.scraper = LinkedInScraper()
    
    def test_extract_handle_valid_urls(self):
        """Test handle extraction from valid URLs."""
        # Test various URL formats
        assert self.scraper._extract_handle("https://www.linkedin.com/in/username/") == "username"
        assert self.scraper._extract_handle("https://linkedin.com/in/username") == "username"
        assert self.scraper._extract_handle("https://www.linkedin.com/in/username/?trk=profile") == "username"
        
        # Test with additional path
        assert self.scraper._extract_handle("https://www.linkedin.com/in/username/details/") == "username"
    
    def test_extract_handle_invalid_urls(self):
        """Test handle extraction from invalid URLs."""
        # Test invalid URLs
        assert self.scraper._extract_handle("") is None
        assert self.scraper._extract_handle("not-a-url") is None
        assert self.scraper._extract_handle("https://example.com") is None
        assert self.scraper._extract_handle("https://instagram.com/username") is None
        assert self.scraper._extract_handle(None) is None
    
    @pytest.mark.asyncio
    async def test_scrape_profile_api_success(self):
        """Test successful API scraping."""
        # Mock API responses
        mock_profile_data = {
            'id': '12345',
            'firstName': {'localized': {'en_US': 'John'}},
            'lastName': {'localized': {'en_US': 'Doe'}},
            'headline': {'localized': {'en_US': 'Software Engineer'}},
            'summary': {'localized': {'en_US': 'Experienced developer'}},
            'location': {'name': 'San Francisco, 'CA'},
            'industry': 'Technology',
            'numConnections': 500
        }
        mock_activity_data = [
            {
                'activityType': 'ARTICLE',
                'permalink': 'https://linkedin.com/posts/1',
                'created': '2023-01-01T00:00:00Z',
                'title': 'Test Article',
                'numLikes': 50,
                'numComments': 10
            }
        ]
        
        # Mock the API methods
        with patch.object(self.scraper, '_get_profile_data', return_value=mock_profile_data), \
             patch.object(self.scraper, '_get_activity_data', return_value=mock_activity_data):
            
            result = await self.scraper._scrape_via_api('testuser')
            
            assert result.success is True
            assert result.profile is not None
            assert result.profile.handle == 'testuser'
            assert result.profile.display_name == 'John Doe'
            assert result.profile.follower_count == 500
            assert result.method_used == 'api'
    
    @pytest.mark.asyncio
    async def test_scrape_profile_api_failure(self):
        """Test API scraping failure."""
        # Mock API failure
        with patch.object(self.scraper, '_get_profile_data', return_value=None):
            result = await self.scraper._scrape_via_api('testuser')
            
            assert result.success is False
            assert result.error == "Could not get profile data from API"
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
            'display_name': 'John Doe',
            'headline': 'Software Engineer',
            'summary': 'Experienced developer',
            'location': 'San Francisco, CA',
            'connections': 500,
            'experience': ['Software Engineer at Company A', 'Developer at Company B']
        }
        
        with patch.object(self.scraper, 'browser', mock_browser), \
             patch.object(self.scraper, '_extract_profile_data', return_value=mock_profile_data):
            
            result = await self.scraper._scrape_via_playwright('https://www.linkedin.com/in/testuser/')
            
            assert result.success is True
            assert result.profile is not None
            assert result.profile.handle == 'testuser'
            assert result.profile.display_name == 'John Doe'
            assert result.method_used == 'scraping'
    
    @pytest.mark.asyncio
    async def test_scrape_profile_playwright_failure(self):
        """Test Playwright scraping failure."""
        # Mock browser failure
        mock_browser = AsyncMock()
        mock_browser.new_page.side_effect = Exception("Browser error")
        
        with patch.object(self.scraper, 'browser', mock_browser):
            result = await self.scraper._scrape_via_playwright('https://www.linkedin.com/in/testuser/')
            
            assert result.success is False
            assert "Browser error" in result.error
            assert result.method_used == 'scraping'
    
    def test_create_profile_from_api(self):
        """Test profile creation from API data."""
        # Mock API data
        profile_data = {
            'id': '12345',
            'firstName': {'localized': {'en_US': 'John'}},
            'lastName': {'localized': {'en_US': 'Doe'}},
            'headline': {'localized': {'en_US': 'Software Engineer'}},
            'summary': {'localized': {'en_US': 'Experienced developer'}},
            'location': {'name': 'San Francisco, CA'},
            'industry': 'Technology',
            'numConnections': 500
        }
        activity_data = [
            {
                'activityType': 'ARTICLE',
                'permalink': 'https://linkedin.com/posts/1',
                'created': '2023-01-01T00:00:00Z',
                'title': 'Test Article',
                'numLikes': 50,
                'numComments': 10
            }
        ]
        
        profile = self.scraper._create_profile_from_api(profile_data, activity_data, 'testuser')
        
        assert profile.source == 'linkedin'
        assert profile.handle == 'testuser'
        assert profile.display_name == 'John Doe'
        assert profile.follower_count == 500
        assert profile.location == 'San Francisco, CA'
        assert len(profile.top_posts) == 1
        assert profile.top_posts[0].url == 'https://linkedin.com/posts/1'
    
    def test_create_profile_from_scraping(self):
        """Test profile creation from scraped data."""
        # Mock scraped data
        profile_data = {
            'display_name': 'John Doe',
            'headline': 'Software Engineer',
            'summary': 'Experienced developer',
            'location': 'San Francisco, CA',
            'connections': 500,
            'experience': ['Software Engineer at Company A']
        }
        
        profile = self.scraper._create_profile_from_scraping(profile_data, 'https://www.linkedin.com/in/testuser/')
        
        assert profile.source == 'linkedin'
        assert profile.handle == 'testuser'
        assert profile.display_name == 'John Doe'
        assert profile.follower_count == 500
        assert profile.location == 'San Francisco, CA'
    
    @pytest.mark.asyncio
    async def test_scrape_profile_invalid_url(self):
        """Test scraping with invalid URL."""
        result = await self.scraper.scrape_profile('invalid-url')
        
        assert result.success is False
        assert result.error == "Invalid LinkedIn profile URL"
        assert result.method_used == "none"
    
    @pytest.mark.asyncio
    async def test_scrape_profile_exception(self):
        """Test scraping with exception."""
        with patch.object(self.scraper, '_extract_handle', side_effect=Exception("Test error")):
            result = await self.scraper.scrape_profile('https://www.linkedin.com/in/test/')
            
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

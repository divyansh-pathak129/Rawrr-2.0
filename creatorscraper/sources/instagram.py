"""
Instagram scraper with Graph API primary and Playwright fallback.
"""

import os
import json
import asyncio
import re
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from playwright.async_api import async_playwright, Browser, Page
from loguru import logger

from ..models.schemas import CreatorProfile, Post, ScrapingResult
from ..utils.rate_limiter import platform_rate_limiter
from ..utils.ua_rotation import ua_rotator
from ..utils.proxy_manager import proxy_manager
from ..utils.parsers import parse_human_number, normalize_url, extract_email_from_text, parse_engagement_rate
from .niche_detector import NicheDetector


class InstagramScraper:
    """Instagram scraper with API and Playwright fallback."""
    
    def __init__(self, access_token: Optional[str] = None, app_id: Optional[str] = None):
        """
        Initialize Instagram scraper.
        
        Args:
            access_token: Instagram Graph API access token
            app_id: Instagram App ID
        """
        self.access_token = access_token or os.getenv('INSTAGRAM_ACCESS_TOKEN')
        self.app_id = app_id or os.getenv('INSTAGRAM_APP_ID')
        self.niche_detector = NicheDetector()
        self.browser: Optional[Browser] = None
        
        logger.info("Instagram scraper initialized")
    
    async def scrape_profile(self, profile_url: str, use_api: bool = True) -> ScrapingResult:
        """
        Scrape Instagram profile.
        
        Args:
            profile_url: Instagram profile URL
            use_api: Whether to try API first
            
        Returns:
            ScrapingResult with profile data
        """
        try:
            # Extract handle from URL
            handle = self._extract_handle(profile_url)
            if not handle:
                return ScrapingResult(
                    success=False,
                    error="Invalid Instagram profile URL",
                    method_used="none"
                )
            
            # Try API first if available
            if use_api and self.access_token:
                logger.info(f"Attempting API scrape for {handle}")
                result = await self._scrape_via_api(handle)
                if result.success:
                    return result
            
            # Fallback to Playwright scraping
            logger.info(f"Attempting Playwright scrape for {handle}")
            result = await self._scrape_via_playwright(profile_url)
            return result
            
        except Exception as e:
            logger.error(f"Error scraping Instagram profile {profile_url}: {e}")
            return ScrapingResult(
                success=False,
                error=str(e),
                method_used="none"
            )
    
    async def _scrape_via_api(self, handle: str) -> ScrapingResult:
        """Scrape profile using Instagram Graph API."""
        try:
            # Wait for rate limit
            await platform_rate_limiter.wait_for_platform('instagram', 'api')
            
            # Get user ID first
            user_id = await self._get_user_id(handle)
            if not user_id:
                return ScrapingResult(
                    success=False,
                    error="Could not get user ID from API",
                    method_used="api"
                )
            
            # Get user profile data
            profile_data = await self._get_user_profile(user_id)
            if not profile_data:
                return ScrapingResult(
                    success=False,
                    error="Could not get profile data from API",
                    method_used="api"
                )
            
            # Get media data
            media_data = await self._get_user_media(user_id)
            
            # Create profile object
            profile = self._create_profile_from_api(profile_data, media_data, handle)
            
            return ScrapingResult(
                success=True,
                profile=profile,
                method_used="api"
            )
            
        except Exception as e:
            logger.error(f"API scraping failed for {handle}: {e}")
            return ScrapingResult(
                success=False,
                error=str(e),
                method_used="api"
            )
    
    async def _get_user_id(self, handle: str) -> Optional[str]:
        """Get user ID from handle."""
        try:
            url = f"https://graph.instagram.com/v18.0/{handle}"
            params = {
                'fields': 'id',
                'access_token': self.access_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                return data.get('id')
                
        except Exception as e:
            logger.error(f"Error getting user ID for {handle}: {e}")
            return None
    
    async def _get_user_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user profile data from API."""
        try:
            url = f"https://graph.instagram.com/v18.0/{user_id}"
            params = {
                'fields': 'id,username,biography,followers_count,follows_count,media_count,profile_picture_url,website',
                'access_token': self.access_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            logger.error(f"Error getting profile data for {user_id}: {e}")
            return None
    
    async def _get_user_media(self, user_id: str, limit: int = 25) -> List[Dict[str, Any]]:
        """Get user media data from API."""
        try:
            url = f"https://graph.instagram.com/v18.0/{user_id}/media"
            params = {
                'fields': 'id,media_type,media_url,permalink,timestamp,caption,like_count,comments_count',
                'limit': limit,
                'access_token': self.access_token
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                return data.get('data', [])
                
        except Exception as e:
            logger.error(f"Error getting media data for {user_id}: {e}")
            return []
    
    def _create_profile_from_api(self, profile_data: Dict[str, Any], media_data: List[Dict[str, Any]], handle: str) -> CreatorProfile:
        """Create CreatorProfile from API data."""
        # Extract basic profile info
        bio = profile_data.get('biography', '')
        follower_count = profile_data.get('followers_count', 0)
        following_count = profile_data.get('follows_count', 0)
        post_count = profile_data.get('media_count', 0)
        avatar_url = profile_data.get('profile_picture_url', '')
        website = profile_data.get('website', '')
        
        # Extract email from bio or website
        public_email = None
        if bio:
            public_email = extract_email_from_text(bio)
        if not public_email and website:
            # TODO: Scrape website for email (would need additional request)
            pass
        
        # Process media data
        posts = []
        for media in media_data:
            post = Post(
                url=media.get('permalink', ''),
                timestamp=datetime.fromisoformat(media.get('timestamp', '').replace('Z', '+00:00')) if media.get('timestamp') else None,
                likes=media.get('like_count', 0),
                comments=media.get('comments_count', 0),
                caption=media.get('caption', '')[:500] if media.get('caption') else None,
                engagement_rate=parse_engagement_rate(
                    media.get('like_count', 0),
                    media.get('comments_count', 0),
                    follower_count
                )
            )
            posts.append(post)
        
        # Sort posts by engagement rate
        posts.sort(key=lambda x: x.engagement_rate or 0, reverse=True)
        
        # Get top 3 posts
        top_posts = posts[:3]
        
        # Get recent posts sample (5 most recent)
        recent_posts = sorted(posts, key=lambda x: x.timestamp or datetime.min, reverse=True)[:5]
        
        # Detect niche
        captions = [post.caption for post in posts if post.caption]
        niche, _ = self.niche_detector.detect_niche(bio, captions)
        
        # Calculate overall engagement rate
        if posts and follower_count > 0:
            total_engagement = sum((post.likes or 0) + (post.comments or 0) for post in posts)
            engagement_rate = min(1.0, total_engagement / (follower_count * len(posts)))
        else:
            engagement_rate = None
        
        return CreatorProfile(
            source='instagram',
            profile_url=f"https://www.instagram.com/{handle}/",
            handle=handle,
            display_name=handle,  # API doesn't provide display name
            bio=bio,
            niche=niche,
            public_contact_email=public_email,
            follower_count=follower_count,
            following_count=following_count,
            post_count=post_count,
            engagement_rate=engagement_rate,
            top_posts=top_posts,
            recent_posts_sample=recent_posts,
            avatar_url=avatar_url
        )
    
    async def _scrape_via_playwright(self, profile_url: str) -> ScrapingResult:
        """Scrape profile using Playwright."""
        try:
            # Wait for rate limit
            await platform_rate_limiter.wait_for_platform('instagram', 'scraping')
            
            # Initialize browser if needed
            if not self.browser:
                playwright = await async_playwright().start()
                self.browser = await playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
            
            # Create new page
            page = await self.browser.new_page()
            
            # Set user agent
            user_agent = ua_rotator.get_agent_for_platform('instagram')
            await page.set_extra_http_headers({'User-Agent': user_agent})
            
            # Set viewport
            await page.set_viewport_size({'width': 1920, 'height': 1080})
            
            # Navigate to profile
            await page.goto(profile_url, wait_until='networkidle')
            
            # Wait for content to load
            await page.wait_for_timeout(3000)
            
            # Extract profile data
            profile_data = await self._extract_profile_data(page)
            
            if not profile_data:
                return ScrapingResult(
                    success=False,
                    error="Could not extract profile data",
                    method_used="scraping"
                )
            
            # Create profile object
            profile = self._create_profile_from_scraping(profile_data, profile_url)
            
            return ScrapingResult(
                success=True,
                profile=profile,
                method_used="scraping"
            )
            
        except Exception as e:
            logger.error(f"Playwright scraping failed for {profile_url}: {e}")
            return ScrapingResult(
                success=False,
                error=str(e),
                method_used="scraping"
            )
        finally:
            if 'page' in locals():
                await page.close()
    
    async def _extract_profile_data(self, page: Page) -> Optional[Dict[str, Any]]:
        """Extract profile data from page."""
        try:
            # Try to get data from window._sharedData
            shared_data = await page.evaluate("""
                () => {
                    if (window._sharedData) {
                        return window._sharedData;
                    }
                    return null;
                }
            """)
            
            if shared_data and 'entry_data' in shared_data:
                profile_data = shared_data['entry_data'].get('ProfilePage', [{}])[0]
                return profile_data.get('graphql', {}).get('user', {})
            
            # Fallback: extract from page elements
            return await self._extract_from_elements(page)
            
        except Exception as e:
            logger.error(f"Error extracting profile data: {e}")
            return None
    
    async def _extract_from_elements(self, page: Page) -> Dict[str, Any]:
        """Extract profile data from page elements."""
        try:
            # Extract basic info
            username = await page.evaluate("""
                () => {
                    const meta = document.querySelector('meta[property="og:title"]');
                    return meta ? meta.content.split(' (@')[0] : null;
                }
            """)
            
            bio = await page.evaluate("""
                () => {
                    const bioEl = document.querySelector('meta[property="og:description"]');
                    return bioEl ? bioEl.content : '';
                }
            """)
            
            # Extract follower count
            follower_count = await page.evaluate("""
                () => {
                    const followersEl = document.querySelector('a[href*="/followers/"] span');
                    if (followersEl) {
                        const text = followersEl.textContent;
                        return text.replace(/[^\d.,KMB]/g, '');
                    }
                    return null;
                }
            """)
            
            # Extract following count
            following_count = await page.evaluate("""
                () => {
                    const followingEl = document.querySelector('a[href*="/following/"] span');
                    if (followingEl) {
                        const text = followingEl.textContent;
                        return text.replace(/[^\d.,KMB]/g, '');
                    }
                    return null;
                }
            """)
            
            # Extract post count
            post_count = await page.evaluate("""
                () => {
                    const postsEl = document.querySelector('div[class*="posts"] span');
                    if (postsEl) {
                        const text = postsEl.textContent;
                        return text.replace(/[^\d.,KMB]/g, '');
                    }
                    return null;
                }
            """)
            
            return {
                'username': username,
                'biography': bio,
                'followers_count': parse_human_number(follower_count) if follower_count else 0,
                'follows_count': parse_human_number(following_count) if following_count else 0,
                'media_count': parse_human_number(post_count) if post_count else 0,
                'profile_picture_url': '',
                'website': ''
            }
            
        except Exception as e:
            logger.error(f"Error extracting from elements: {e}")
            return {}
    
    def _create_profile_from_scraping(self, profile_data: Dict[str, Any], profile_url: str) -> CreatorProfile:
        """Create CreatorProfile from scraped data."""
        handle = self._extract_handle(profile_url)
        bio = profile_data.get('biography', '')
        follower_count = profile_data.get('followers_count', 0)
        following_count = profile_data.get('follows_count', 0)
        post_count = profile_data.get('media_count', 0)
        
        # Extract email from bio
        public_email = extract_email_from_text(bio) if bio else None
        
        # Detect niche
        niche, _ = self.niche_detector.detect_niche(bio)
        
        return CreatorProfile(
            source='instagram',
            profile_url=profile_url,
            handle=handle,
            display_name=profile_data.get('full_name', handle),
            bio=bio,
            niche=niche,
            public_contact_email=public_email,
            follower_count=follower_count,
            following_count=following_count,
            post_count=post_count,
            avatar_url=profile_data.get('profile_picture_url', '')
        )
    
    def _extract_handle(self, profile_url: str) -> Optional[str]:
        """Extract handle from Instagram URL."""
        try:
            # Handle different URL formats
            if 'instagram.com/' in profile_url:
                match = re.search(r'instagram\.com/([^/?]+)', profile_url)
                if match:
                    return match.group(1).strip('/')
            return None
        except Exception:
            return None
    
    async def close(self):
        """Close browser if open."""
        if self.browser:
            await self.browser.close()
            self.browser = None

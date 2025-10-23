"""
LinkedIn scraper with API primary and Playwright fallback.
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


class LinkedInScraper:
    """LinkedIn scraper with API and Playwright fallback."""
    
    def __init__(self, access_token: Optional[str] = None):
        """
        Initialize LinkedIn scraper.
        
        Args:
            access_token: LinkedIn API access token
        """
        self.access_token = access_token or os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.niche_detector = NicheDetector()
        self.browser: Optional[Browser] = None
        
        logger.info("LinkedIn scraper initialized")
    
    async def scrape_profile(self, profile_url: str, use_api: bool = True) -> ScrapingResult:
        """
        Scrape LinkedIn profile.
        
        Args:
            profile_url: LinkedIn profile URL
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
                    error="Invalid LinkedIn profile URL",
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
            logger.error(f"Error scraping LinkedIn profile {profile_url}: {e}")
            return ScrapingResult(
                success=False,
                error=str(e),
                method_used="none"
            )
    
    async def _scrape_via_api(self, handle: str) -> ScrapingResult:
        """Scrape profile using LinkedIn API."""
        try:
            # Wait for rate limit
            await platform_rate_limiter.wait_for_platform('linkedin', 'api')
            
            # Get profile data
            profile_data = await self._get_profile_data(handle)
            if not profile_data:
                return ScrapingResult(
                    success=False,
                    error="Could not get profile data from API",
                    method_used="api"
                )
            
            # Get activity data
            activity_data = await self._get_activity_data(handle)
            
            # Create profile object
            profile = self._create_profile_from_api(profile_data, activity_data, handle)
            
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
    
    async def _get_profile_data(self, handle: str) -> Optional[Dict[str, Any]]:
        """Get profile data from LinkedIn API."""
        try:
            # LinkedIn People API endpoint
            url = f"https://api.linkedin.com/v2/people/(id:{handle})"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            params = {
                'projection': '(id,firstName,lastName,headline,summary,location,industry,numConnections,profilePicture(displayImage~:playableStreams))'
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                return response.json()
                
        except Exception as e:
            logger.error(f"Error getting profile data for {handle}: {e}")
            return None
    
    async def _get_activity_data(self, handle: str) -> List[Dict[str, Any]]:
        """Get activity data from LinkedIn API."""
        try:
            # LinkedIn Activity API endpoint
            url = f"https://api.linkedin.com/v2/people/(id:{handle})/activities"
            headers = {
                'Authorization': f'Bearer {self.access_token}',
                'Content-Type': 'application/json'
            }
            params = {
                'count': 25
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, params=params)
                response.raise_for_status()
                
                data = response.json()
                return data.get('elements', [])
                
        except Exception as e:
            logger.error(f"Error getting activity data for {handle}: {e}")
            return []
    
    def _create_profile_from_api(self, profile_data: Dict[str, Any], activity_data: List[Dict[str, Any]], handle: str) -> CreatorProfile:
        """Create CreatorProfile from API data."""
        # Extract basic profile info
        first_name = profile_data.get('firstName', {}).get('localized', {}).get('en_US', '')
        last_name = profile_data.get('lastName', {}).get('localized', {}).get('en_US', '')
        display_name = f"{first_name} {last_name}".strip()
        
        headline = profile_data.get('headline', {}).get('localized', {}).get('en_US', '')
        summary = profile_data.get('summary', {}).get('localized', {}).get('en_US', '')
        bio = f"{headline}\n{summary}".strip()
        
        location = profile_data.get('location', {}).get('name', '')
        industry = profile_data.get('industry', '')
        num_connections = profile_data.get('numConnections', 0)
        
        # Extract avatar URL
        avatar_url = ''
        if 'profilePicture' in profile_data:
            picture_data = profile_data['profilePicture'].get('displayImage~', {})
            elements = picture_data.get('elements', [])
            if elements:
                avatar_url = elements[0].get('identifiers', [{}])[0].get('identifier', '')
        
        # Extract email from bio
        public_email = extract_email_from_text(bio) if bio else None
        
        # Process activity data
        posts = []
        for activity in activity_data:
            if activity.get('activityType') == 'ARTICLE':
                post = Post(
                    url=activity.get('permalink', ''),
                    timestamp=datetime.fromisoformat(activity.get('created', '').replace('Z', '+00:00')) if activity.get('created') else None,
                    caption=activity.get('title', '')[:500] if activity.get('title') else None,
                    likes=activity.get('numLikes', 0),
                    comments=activity.get('numComments', 0)
                )
                posts.append(post)
        
        # Sort posts by engagement
        posts.sort(key=lambda x: (x.likes or 0) + (x.comments or 0), reverse=True)
        
        # Get top 3 posts
        top_posts = posts[:3]
        
        # Get recent posts sample (5 most recent)
        recent_posts = sorted(posts, key=lambda x: x.timestamp or datetime.min, reverse=True)[:5]
        
        # Detect niche
        niche, _ = self.niche_detector.detect_niche(bio)
        
        return CreatorProfile(
            source='linkedin',
            profile_url=f"https://www.linkedin.com/in/{handle}/",
            handle=handle,
            display_name=display_name,
            bio=bio,
            niche=niche,
            public_contact_email=public_email,
            location=location,
            follower_count=num_connections,
            following_count=0,  # LinkedIn doesn't provide this
            post_count=len(posts),
            top_posts=top_posts,
            recent_posts_sample=recent_posts,
            avatar_url=avatar_url
        )
    
    async def _scrape_via_playwright(self, profile_url: str) -> ScrapingResult:
        """Scrape profile using Playwright."""
        try:
            # Wait for rate limit
            await platform_rate_limiter.wait_for_platform('linkedin', 'scraping')
            
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
            user_agent = ua_rotator.get_agent_for_platform('linkedin')
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
            # Extract basic info
            display_name = await page.evaluate("""
                () => {
                    const nameEl = document.querySelector('h1.text-heading-xlarge');
                    return nameEl ? nameEl.textContent.trim() : null;
                }
            """)
            
            headline = await page.evaluate("""
                () => {
                    const headlineEl = document.querySelector('.text-body-medium.break-words');
                    return headlineEl ? headlineEl.textContent.trim() : '';
                }
            """)
            
            summary = await page.evaluate("""
                () => {
                    const summaryEl = document.querySelector('.pv-about-section .pv-about__summary-text');
                    return summaryEl ? summaryEl.textContent.trim() : '';
                }
            """)
            
            location = await page.evaluate("""
                () => {
                    const locationEl = document.querySelector('.text-body-small.inline.t-black--light.break-words');
                    return locationEl ? locationEl.textContent.trim() : '';
                }
            """)
            
            # Extract connection count
            connections = await page.evaluate("""
                () => {
                    const connectionsEl = document.querySelector('.pv-top-card--list-bullet li:first-child span');
                    if (connectionsEl) {
                        const text = connectionsEl.textContent;
                        return text.replace(/[^\d.,KMB]/g, '');
                    }
                    return null;
                }
            """)
            
            # Extract experience/activity
            experience = await page.evaluate("""
                () => {
                    const expEls = document.querySelectorAll('.pv-entity__summary-info h3');
                    return Array.from(expEls).map(el => el.textContent.trim());
                }
            """)
            
            return {
                'display_name': display_name,
                'headline': headline,
                'summary': summary,
                'location': location,
                'connections': parse_human_number(connections) if connections else 0,
                'experience': experience
            }
            
        except Exception as e:
            logger.error(f"Error extracting profile data: {e}")
            return None
    
    def _create_profile_from_scraping(self, profile_data: Dict[str, Any], profile_url: str) -> CreatorProfile:
        """Create CreatorProfile from scraped data."""
        handle = self._extract_handle(profile_url)
        display_name = profile_data.get('display_name', '')
        headline = profile_data.get('headline', '')
        summary = profile_data.get('summary', '')
        bio = f"{headline}\n{summary}".strip()
        location = profile_data.get('location', '')
        connections = profile_data.get('connections', 0)
        
        # Extract email from bio
        public_email = extract_email_from_text(bio) if bio else None
        
        # Detect niche
        niche, _ = self.niche_detector.detect_niche(bio)
        
        return CreatorProfile(
            source='linkedin',
            profile_url=profile_url,
            handle=handle,
            display_name=display_name,
            bio=bio,
            niche=niche,
            public_contact_email=public_email,
            location=location,
            follower_count=connections,
            following_count=0,  # LinkedIn doesn't provide this
            post_count=0  # Would need additional scraping for posts
        )
    
    def _extract_handle(self, profile_url: str) -> Optional[str]:
        """Extract handle from LinkedIn URL."""
        try:
            # Handle different URL formats
            if 'linkedin.com/in/' in profile_url:
                match = re.search(r'linkedin\.com/in/([^/?]+)', profile_url)
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

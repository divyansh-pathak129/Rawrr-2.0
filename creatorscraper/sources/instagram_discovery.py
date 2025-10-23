"""
Instagram Reels discovery module for finding creators automatically.
"""

import asyncio
import json
import re
import random
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse

from playwright.async_api import async_playwright, Browser, Page
from loguru import logger

from ..utils.rate_limiter import platform_rate_limiter
from ..utils.ua_rotation import ua_rotator
from ..utils.proxy_manager import proxy_manager
from ..utils.parsers import parse_human_number, normalize_url
from .niche_detector import NicheDetector


class InstagramReelsDiscovery:
    """Discovers Instagram creators by browsing Reels."""
    
    def __init__(self):
        """Initialize Instagram Reels discovery."""
        self.browser: Optional[Browser] = None
        self.niche_detector = NicheDetector()
        self.discovered_creators: Set[str] = set()
        
        logger.info("Instagram Reels discovery initialized")
    
    async def discover_creators(
        self, 
        max_creators: int = 100,
        niches: Optional[List[str]] = None,
        min_followers: int = 1000,
        max_followers: int = 1000000,
        scroll_duration: int = 300  # seconds
    ) -> List[Dict[str, Any]]:
        """
        Discover creators by browsing Instagram Reels.
        
        Args:
            max_creators: Maximum number of creators to discover
            niches: List of niches to focus on (None for all)
            min_followers: Minimum follower count filter
            max_followers: Maximum follower count filter
            scroll_duration: How long to scroll (seconds)
            
        Returns:
            List of discovered creator profiles
        """
        try:
            # Initialize browser
            if not self.browser:
                playwright = await async_playwright().start()
                self.browser = await playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
                )
            
            # Create new page
            page = await self.browser.new_page()
            
            # Set user agent and viewport
            user_agent = ua_rotator.get_agent_for_platform('instagram')
            await page.set_extra_http_headers({'User-Agent': user_agent})
            await page.set_viewport_size({'width': 375, 'height': 812})  # Mobile viewport for Reels
            
            # Navigate to Instagram Reels
            await page.goto('https://www.instagram.com/reels/', wait_until='networkidle')
            await page.wait_for_timeout(3000)
            
            # Start discovery process
            creators = await self._discover_from_reels(
                page, max_creators, niches, min_followers, max_followers, scroll_duration
            )
            
            await page.close()
            return creators
            
        except Exception as e:
            logger.error(f"Error in creator discovery: {e}")
            return []
    
    async def _discover_from_reels(
        self, 
        page: Page, 
        max_creators: int,
        niches: Optional[List[str]],
        min_followers: int,
        max_followers: int,
        scroll_duration: int
    ) -> List[Dict[str, Any]]:
        """Discover creators by scrolling through Reels."""
        creators = []
        start_time = datetime.now()
        last_scroll_time = start_time
        
        logger.info(f"Starting Reels discovery for {scroll_duration} seconds")
        
        while len(creators) < max_creators and (datetime.now() - start_time).seconds < scroll_duration:
            try:
                # Wait for rate limit
                await platform_rate_limiter.wait_for_platform('instagram', 'scraping')
                
                # Scroll down to load more Reels
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(random.uniform(2, 4))
                
                # Extract creator info from visible Reels
                new_creators = await self._extract_creators_from_reels(page)
                
                for creator in new_creators:
                    if len(creators) >= max_creators:
                        break
                    
                    # Check if we've already seen this creator
                    if creator['handle'] in self.discovered_creators:
                        continue
                    
                    # Apply filters
                    if not self._passes_filters(creator, niches, min_followers, max_followers):
                        continue
                    
                    # Add to discovered list
                    self.discovered_creators.add(creator['handle'])
                    creators.append(creator)
                    
                    logger.info(f"Discovered creator: {creator['handle']} ({creator.get('follower_count', 0)} followers)")
                
                # Check if we're stuck (no new content)
                if (datetime.now() - last_scroll_time).seconds > 30:
                    logger.warning("No new content detected, trying to refresh")
                    await page.reload()
                    await page.wait_for_timeout(5000)
                    last_scroll_time = datetime.now()
                else:
                    last_scroll_time = datetime.now()
                
            except Exception as e:
                logger.error(f"Error during discovery scroll: {e}")
                await page.wait_for_timeout(5000)
        
        logger.info(f"Discovery completed: {len(creators)} creators found")
        return creators
    
    async def _extract_creators_from_reels(self, page: Page) -> List[Dict[str, Any]]:
        """Extract creator information from visible Reels."""
        try:
            # Extract creator data from Reels
            creators_data = await page.evaluate("""
                () => {
                    const creators = [];
                    const reels = document.querySelectorAll('a[href*="/reel/"]');
                    
                    reels.forEach(reel => {
                        try {
                            // Get creator handle from href
                            const href = reel.getAttribute('href');
                            if (href && href.includes('/reel/')) {
                                // Extract handle from the reel URL structure
                                const handleMatch = href.match(/\/reel\/[^\/]+\//);
                                if (handleMatch) {
                                    // Look for creator info in the reel container
                                    const reelContainer = reel.closest('[data-testid="reel-item"]') || reel.closest('article');
                                    if (reelContainer) {
                                        const handleEl = reelContainer.querySelector('a[href*="/"]');
                                        if (handleEl) {
                                            const handleHref = handleEl.getAttribute('href');
                                            if (handleHref && !handleHref.includes('/reel/')) {
                                                const handle = handleHref.replace('/', '').replace('@', '');
                                                if (handle && !handle.includes('/') && !handle.includes('?')) {
                                                    creators.push({
                                                        handle: handle,
                                                        profile_url: `https://www.instagram.com/${handle}/`,
                                                        source: 'instagram'
                                                    });
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        } catch (e) {
                            console.error('Error extracting creator:', e);
                        }
                    });
                    
                    return creators;
                }
            """)
            
            # Get additional profile data for each creator
            detailed_creators = []
            for creator in creators_data:
                try:
                    # Get basic profile info
                    profile_info = await self._get_creator_basic_info(page, creator['handle'])
                    if profile_info:
                        creator.update(profile_info)
                        detailed_creators.append(creator)
                except Exception as e:
                    logger.warning(f"Error getting profile info for {creator['handle']}: {e}")
                    detailed_creators.append(creator)
            
            return detailed_creators
            
        except Exception as e:
            logger.error(f"Error extracting creators from Reels: {e}")
            return []
    
    async def _get_creator_basic_info(self, page: Page, handle: str) -> Optional[Dict[str, Any]]:
        """Get basic profile information for a creator."""
        try:
            # Navigate to profile
            profile_url = f"https://www.instagram.com/{handle}/"
            await page.goto(profile_url, wait_until='networkidle')
            await page.wait_for_timeout(2000)
            
            # Extract profile data
            profile_data = await page.evaluate(f"""
                () => {{
                    try {{
                        // Get follower count
                        const followersEl = document.querySelector('a[href*="/followers/"] span');
                        const followers = followersEl ? followersEl.textContent : '0';
                        
                        // Get following count
                        const followingEl = document.querySelector('a[href*="/following/"] span');
                        const following = followingEl ? followingEl.textContent : '0';
                        
                        // Get post count
                        const postsEl = document.querySelector('div[class*="posts"] span');
                        const posts = postsEl ? postsEl.textContent : '0';
                        
                        // Get bio
                        const bioEl = document.querySelector('meta[property="og:description"]');
                        const bio = bioEl ? bioEl.content : '';
                        
                        // Get display name
                        const nameEl = document.querySelector('meta[property="og:title"]');
                        const displayName = nameEl ? nameEl.content.split(' (@')[0] : '{handle}';
                        
                        return {{
                            display_name: displayName,
                            bio: bio,
                            follower_count: followers,
                            following_count: following,
                            post_count: posts
                        }};
                    }} catch (e) {{
                        return null;
                    }}
                }}
            """)
            
            if profile_data:
                # Parse follower count
                follower_count = parse_human_number(profile_data.get('follower_count', '0'))
                following_count = parse_human_number(profile_data.get('following_count', '0'))
                post_count = parse_human_number(profile_data.get('post_count', '0'))
                
                # Detect niche
                bio = profile_data.get('bio', '')
                niche, _ = self.niche_detector.detect_niche(bio)
                
                return {
                    'display_name': profile_data.get('display_name', handle),
                    'bio': bio,
                    'follower_count': follower_count or 0,
                    'following_count': following_count or 0,
                    'post_count': post_count or 0,
                    'niche': niche
                }
            
            return None
            
        except Exception as e:
            logger.warning(f"Error getting basic info for {handle}: {e}")
            return None
    
    def _passes_filters(
        self, 
        creator: Dict[str, Any], 
        niches: Optional[List[str]], 
        min_followers: int, 
        max_followers: int
    ) -> bool:
        """Check if creator passes the specified filters."""
        try:
            # Check follower count
            follower_count = creator.get('follower_count', 0)
            if follower_count < min_followers or follower_count > max_followers:
                return False
            
            # Check niche filter
            if niches and creator.get('niche') not in niches:
                return False
            
            return True
            
        except Exception as e:
            logger.warning(f"Error checking filters for creator {creator.get('handle')}: {e}")
            return False
    
    async def discover_by_hashtag(
        self, 
        hashtags: List[str], 
        max_creators_per_hashtag: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Discover creators by browsing specific hashtags.
        
        Args:
            hashtags: List of hashtags to browse
            max_creators_per_hashtag: Maximum creators per hashtag
            
        Returns:
            List of discovered creators
        """
        creators = []
        
        try:
            if not self.browser:
                playwright = await async_playwright().start()
                self.browser = await playwright.chromium.launch(
                    headless=True,
                    args=['--no-sandbox', '--disable-dev-shm-usage']
                )
            
            page = await self.browser.new_page()
            user_agent = ua_rotator.get_agent_for_platform('instagram')
            await page.set_extra_http_headers({'User-Agent': user_agent})
            await page.set_viewport_size({'width': 375, 'height': 812})
            
            for hashtag in hashtags:
                try:
                    # Navigate to hashtag page
                    hashtag_url = f"https://www.instagram.com/explore/tags/{hashtag.replace('#', '')}/"
                    await page.goto(hashtag_url, wait_until='networkidle')
                    await page.wait_for_timeout(3000)
                    
                    # Scroll and extract creators
                    hashtag_creators = await self._extract_creators_from_hashtag(page, max_creators_per_hashtag)
                    creators.extend(hashtag_creators)
                    
                    logger.info(f"Found {len(hashtag_creators)} creators for hashtag #{hashtag}")
                    
                except Exception as e:
                    logger.error(f"Error browsing hashtag {hashtag}: {e}")
                    continue
            
            await page.close()
            return creators
            
        except Exception as e:
            logger.error(f"Error in hashtag discovery: {e}")
            return creators
    
    async def _extract_creators_from_hashtag(self, page: Page, max_creators: int) -> List[Dict[str, Any]]:
        """Extract creators from hashtag page."""
        creators = []
        
        try:
            # Scroll to load more posts
            for _ in range(5):  # Scroll 5 times
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(2000)
            
            # Extract creator handles from posts
            creator_handles = await page.evaluate("""
                () => {
                    const creators = [];
                    const posts = document.querySelectorAll('article a[href*="/p/"]');
                    
                    posts.forEach(post => {
                        try {
                            const postLink = post.getAttribute('href');
                            if (postLink) {
                                // Look for creator handle in the post container
                                const postContainer = post.closest('article');
                                if (postContainer) {
                                    const creatorLink = postContainer.querySelector('a[href*="/"]');
                                    if (creatorLink) {
                                        const href = creatorLink.getAttribute('href');
                                        if (href && !href.includes('/p/') && !href.includes('/reel/')) {
                                            const handle = href.replace('/', '').replace('@', '');
                                            if (handle && !handle.includes('/') && !handle.includes('?')) {
                                                creators.push(handle);
                                            }
                                        }
                                    }
                                }
                            }
                        } catch (e) {
                            console.error('Error extracting creator from post:', e);
                        }
                    });
                    
                    return [...new Set(creators)]; // Remove duplicates
                }
            """)
            
            # Get detailed info for each creator
            for handle in creator_handles[:max_creators]:
                if handle not in self.discovered_creators:
                    try:
                        profile_info = await self._get_creator_basic_info(page, handle)
                        if profile_info:
                            creator = {
                                'handle': handle,
                                'profile_url': f"https://www.instagram.com/{handle}/",
                                'source': 'instagram'
                            }
                            creator.update(profile_info)
                            creators.append(creator)
                            self.discovered_creators.add(handle)
                    except Exception as e:
                        logger.warning(f"Error getting info for {handle}: {e}")
            
            return creators
            
        except Exception as e:
            logger.error(f"Error extracting creators from hashtag: {e}")
            return creators
    
    async def close(self):
        """Close browser if open."""
        if self.browser:
            await self.browser.close()
            self.browser = None

"""
Rate limiter implementation using token bucket algorithm.
"""

import asyncio
import time
from typing import Dict, Optional
from loguru import logger


class RateLimiter:
    """Token bucket rate limiter for API and scraping requests."""
    
    def __init__(self, rate: float, capacity: int, platform: str = "default"):
        """
        Initialize rate limiter.
        
        Args:
            rate: Tokens per second
            capacity: Maximum tokens in bucket
            platform: Platform name for logging
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.time()
        self.platform = platform
        self._lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            
        Returns:
            True if tokens were acquired, False if rate limited
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # Add tokens based on elapsed time
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                logger.debug(f"Rate limiter {self.platform}: acquired {tokens} tokens, {self.tokens:.2f} remaining")
                return True
            else:
                logger.warning(f"Rate limiter {self.platform}: insufficient tokens, {self.tokens:.2f} available, {tokens} requested")
                return False
    
    async def wait_for_tokens(self, tokens: int = 1) -> None:
        """
        Wait until tokens are available.
        
        Args:
            tokens: Number of tokens needed
        """
        while not await self.acquire(tokens):
            wait_time = (tokens - self.tokens) / self.rate
            logger.info(f"Rate limiter {self.platform}: waiting {wait_time:.2f}s for {tokens} tokens")
            await asyncio.sleep(wait_time)


class PlatformRateLimiter:
    """Rate limiter for different platforms with specific limits."""
    
    def __init__(self):
        self.limiters: Dict[str, RateLimiter] = {}
        self._setup_default_limits()
    
    def _setup_default_limits(self):
        """Setup default rate limits for different platforms."""
        # Instagram API: 200 requests per hour
        self.limiters['instagram_api'] = RateLimiter(
            rate=200/3600,  # 200 per hour
            capacity=200,
            platform='instagram_api'
        )
        
        # Instagram scraping: 20 requests per hour with jitter
        self.limiters['instagram_scraping'] = RateLimiter(
            rate=20/3600,  # 20 per hour
            capacity=20,
            platform='instagram_scraping'
        )
        
        # LinkedIn API: 500 requests per day
        self.limiters['linkedin_api'] = RateLimiter(
            rate=500/86400,  # 500 per day
            capacity=500,
            platform='linkedin_api'
        )
        
        # LinkedIn scraping: 10 requests per hour
        self.limiters['linkedin_scraping'] = RateLimiter(
            rate=10/3600,  # 10 per hour
            capacity=10,
            platform='linkedin_scraping'
        )
    
    def get_limiter(self, platform: str, method: str = "api") -> RateLimiter:
        """
        Get rate limiter for specific platform and method.
        
        Args:
            platform: Platform name (instagram, linkedin)
            method: Method type (api, scraping)
            
        Returns:
            RateLimiter instance
        """
        key = f"{platform}_{method}"
        if key not in self.limiters:
            # Default limiter for unknown platforms
            self.limiters[key] = RateLimiter(
                rate=10/3600,  # 10 per hour
                capacity=10,
                platform=key
            )
        return self.limiters[key]
    
    async def wait_for_platform(self, platform: str, method: str = "api", tokens: int = 1) -> None:
        """
        Wait for rate limit on specific platform.
        
        Args:
            platform: Platform name
            method: Method type
            tokens: Number of tokens needed
        """
        limiter = self.get_limiter(platform, method)
        await limiter.wait_for_tokens(tokens)


# Global rate limiter instance
platform_rate_limiter = PlatformRateLimiter()

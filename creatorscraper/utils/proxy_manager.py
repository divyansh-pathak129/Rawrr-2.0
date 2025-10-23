"""
Proxy management utility for rotating proxies.
"""

import random
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
import httpx
from loguru import logger


class ProxyManager:
    """Manages proxy rotation for scraping requests."""
    
    def __init__(self, proxy_list: Optional[List[str]] = None):
        """
        Initialize proxy manager.
        
        Args:
            proxy_list: List of proxy URLs (http://user:pass@host:port or socks5://user:pass@host:port)
        """
        self.proxies = proxy_list or []
        self.current_index = 0
        self.failed_proxies = set()
        logger.info(f"Initialized ProxyManager with {len(self.proxies)} proxies")
    
    def add_proxy(self, proxy_url: str) -> None:
        """
        Add a proxy to the list.
        
        Args:
            proxy_url: Proxy URL in format http://user:pass@host:port or socks5://user:pass@host:port
        """
        if self._validate_proxy_url(proxy_url):
            self.proxies.append(proxy_url)
            logger.info(f"Added proxy: {self._mask_proxy_url(proxy_url)}")
        else:
            logger.error(f"Invalid proxy URL format: {proxy_url}")
    
    def _validate_proxy_url(self, proxy_url: str) -> bool:
        """Validate proxy URL format."""
        try:
            parsed = urlparse(proxy_url)
            return parsed.scheme in ['http', 'https', 'socks5'] and parsed.hostname
        except Exception:
            return False
    
    def _mask_proxy_url(self, proxy_url: str) -> str:
        """Mask sensitive information in proxy URL for logging."""
        try:
            parsed = urlparse(proxy_url)
            if parsed.username:
                return f"{parsed.scheme}://***:***@{parsed.hostname}:{parsed.port}"
            return proxy_url
        except Exception:
            return "***"
    
    def get_random_proxy(self) -> Optional[str]:
        """Get a random working proxy."""
        working_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        if not working_proxies:
            logger.warning("No working proxies available")
            return None
        
        proxy = random.choice(working_proxies)
        logger.debug(f"Selected random proxy: {self._mask_proxy_url(proxy)}")
        return proxy
    
    def get_next_proxy(self) -> Optional[str]:
        """Get the next proxy in sequence."""
        working_proxies = [p for p in self.proxies if p not in self.failed_proxies]
        if not working_proxies:
            logger.warning("No working proxies available")
            return None
        
        proxy = working_proxies[self.current_index % len(working_proxies)]
        self.current_index += 1
        logger.debug(f"Selected next proxy: {self._mask_proxy_url(proxy)}")
        return proxy
    
    def mark_proxy_failed(self, proxy_url: str) -> None:
        """Mark a proxy as failed."""
        self.failed_proxies.add(proxy_url)
        logger.warning(f"Marked proxy as failed: {self._mask_proxy_url(proxy_url)}")
    
    def reset_failed_proxies(self) -> None:
        """Reset failed proxies list."""
        self.failed_proxies.clear()
        logger.info("Reset failed proxies list")
    
    def get_proxy_config(self, proxy_url: str) -> Dict[str, Any]:
        """
        Get proxy configuration for httpx/requests.
        
        Args:
            proxy_url: Proxy URL
            
        Returns:
            Proxy configuration dict
        """
        try:
            parsed = urlparse(proxy_url)
            
            if parsed.scheme in ['http', 'https']:
                return {
                    'http://': proxy_url,
                    'https://': proxy_url
                }
            elif parsed.scheme == 'socks5':
                # For SOCKS5, we need to use httpx-socks
                return {
                    'http://': f'socks5://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}',
                    'https://': f'socks5://{parsed.username}:{parsed.password}@{parsed.hostname}:{parsed.port}'
                }
            else:
                logger.error(f"Unsupported proxy scheme: {parsed.scheme}")
                return {}
        except Exception as e:
            logger.error(f"Error parsing proxy URL {proxy_url}: {e}")
            return {}
    
    def test_proxy(self, proxy_url: str, test_url: str = "https://httpbin.org/ip", timeout: int = 10) -> bool:
        """
        Test if a proxy is working.
        
        Args:
            proxy_url: Proxy URL to test
            test_url: URL to test with
            timeout: Request timeout
            
        Returns:
            True if proxy is working, False otherwise
        """
        try:
            proxy_config = self.get_proxy_config(proxy_url)
            if not proxy_config:
                return False
            
            with httpx.Client(proxies=proxy_config, timeout=timeout) as client:
                response = client.get(test_url)
                if response.status_code == 200:
                    logger.debug(f"Proxy test successful: {self._mask_proxy_url(proxy_url)}")
                    return True
                else:
                    logger.warning(f"Proxy test failed with status {response.status_code}: {self._mask_proxy_url(proxy_url)}")
                    return False
        except Exception as e:
            logger.warning(f"Proxy test failed: {self._mask_proxy_url(proxy_url)} - {e}")
            return False
    
    def test_all_proxies(self, test_url: str = "https://httpbin.org/ip") -> List[str]:
        """
        Test all proxies and return working ones.
        
        Args:
            test_url: URL to test with
            
        Returns:
            List of working proxy URLs
        """
        working_proxies = []
        for proxy in self.proxies:
            if self.test_proxy(proxy, test_url):
                working_proxies.append(proxy)
            else:
                self.mark_proxy_failed(proxy)
        
        logger.info(f"Proxy test completed: {len(working_proxies)}/{len(self.proxies)} proxies working")
        return working_proxies
    
    def get_proxy_count(self) -> int:
        """Get total number of proxies."""
        return len(self.proxies)
    
    def get_working_proxy_count(self) -> int:
        """Get number of working proxies."""
        return len([p for p in self.proxies if p not in self.failed_proxies])


# Global proxy manager instance
proxy_manager = ProxyManager()

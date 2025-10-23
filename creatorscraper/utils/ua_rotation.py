"""
User agent rotation utility for avoiding detection.
"""

import random
from typing import List, Optional
from loguru import logger


class UserAgentRotator:
    """Rotates user agents to avoid detection."""
    
    def __init__(self, custom_agents: Optional[List[str]] = None):
        """
        Initialize user agent rotator.
        
        Args:
            custom_agents: Custom list of user agents to use
        """
        self.agents = custom_agents or self._get_default_agents()
        self.current_index = 0
        logger.info(f"Initialized UserAgentRotator with {len(self.agents)} agents")
    
    def _get_default_agents(self) -> List[str]:
        """Get default list of realistic user agents."""
        return [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
            
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/120.0",
            
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
            
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
            
            # Chrome on Linux
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            
            # Firefox on Linux
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/120.0",
            
            # Mobile Chrome
            "Mozilla/5.0 (Linux; Android 10; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            "Mozilla/5.0 (Linux; Android 11; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
            
            # Mobile Safari
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        ]
    
    def get_random_agent(self) -> str:
        """Get a random user agent."""
        agent = random.choice(self.agents)
        logger.debug(f"Selected random user agent: {agent[:50]}...")
        return agent
    
    def get_next_agent(self) -> str:
        """Get the next user agent in sequence."""
        agent = self.agents[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.agents)
        logger.debug(f"Selected next user agent: {agent[:50]}...")
        return agent
    
    def get_agent_for_platform(self, platform: str) -> str:
        """
        Get user agent optimized for specific platform.
        
        Args:
            platform: Platform name (instagram, linkedin)
            
        Returns:
            User agent string
        """
        if platform.lower() == "instagram":
            # Instagram works best with Chrome
            chrome_agents = [agent for agent in self.agents if "Chrome" in agent and "Edg" not in agent]
            return random.choice(chrome_agents) if chrome_agents else self.get_random_agent()
        elif platform.lower() == "linkedin":
            # LinkedIn works well with Firefox
            firefox_agents = [agent for agent in self.agents if "Firefox" in agent]
            return random.choice(firefox_agents) if firefox_agents else self.get_random_agent()
        else:
            return self.get_random_agent()
    
    def add_agent(self, agent: str) -> None:
        """Add a custom user agent."""
        if agent not in self.agents:
            self.agents.append(agent)
            logger.info(f"Added custom user agent: {agent[:50]}...")
    
    def remove_agent(self, agent: str) -> None:
        """Remove a user agent."""
        if agent in self.agents:
            self.agents.remove(agent)
            logger.info(f"Removed user agent: {agent[:50]}...")
    
    def get_agent_count(self) -> int:
        """Get total number of user agents."""
        return len(self.agents)


# Global user agent rotator instance
ua_rotator = UserAgentRotator()

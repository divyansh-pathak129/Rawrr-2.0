"""Source modules for scraping different platforms."""

from .instagram import InstagramScraper
from .linkedin import LinkedInScraper
from .instagram_discovery import InstagramReelsDiscovery
from .niche_detector import NicheDetector

__all__ = ["InstagramScraper", "LinkedInScraper", "InstagramReelsDiscovery", "NicheDetector"]
"""
Creator Scraper - A production-ready Python package for scraping Instagram and LinkedIn creator profiles.

This package provides tools to extract structured creator data from social media platforms
and store it in Supabase with proper rate limiting, anti-detection measures, and legal compliance.
"""

__version__ = "1.0.0"
__author__ = "Creator Scraper Team"

from .models.schemas import CreatorProfile, Post
from .storage.supabase_client import SupabaseClient
from .sources.instagram import InstagramScraper
from .sources.linkedin import LinkedInScraper

__all__ = [
    "CreatorProfile",
    "Post", 
    "SupabaseClient",
    "InstagramScraper",
    "LinkedInScraper"
]

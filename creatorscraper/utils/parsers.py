"""
Data parsing and normalization utilities.
"""

import re
from typing import Optional, List, Dict, Any
from urllib.parse import urlparse, urljoin
from loguru import logger


def parse_human_number(text: str) -> Optional[int]:
    """
    Parse human-readable numbers (1.2M, 5.4K, etc.) to integers.
    
    Args:
        text: String containing human-readable number
        
    Returns:
        Parsed integer or None if parsing fails
        
    Examples:
        "1.2M" -> 1200000
        "5.4K" -> 5400
        "1,234" -> 1234
        "500" -> 500
    """
    if not text or not isinstance(text, str):
        return None
    
    # Remove commas and whitespace
    text = text.replace(',', '').strip()
    
    # Handle empty string
    if not text:
        return None
    
    # Regular expression to match numbers with suffixes
    pattern = r'^([\d.]+)\s*([KMB]?)$'
    match = re.match(pattern, text, re.IGNORECASE)
    
    if not match:
        # Try to extract just the number part
        number_match = re.search(r'[\d.]+', text)
        if number_match:
            try:
                return int(float(number_match.group()))
            except ValueError:
                pass
        return None
    
    number_str, suffix = match.groups()
    
    try:
        number = float(number_str)
    except ValueError:
        return None
    
    # Apply suffix multiplier
    suffix = suffix.upper()
    if suffix == 'K':
        number *= 1000
    elif suffix == 'M':
        number *= 1000000
    elif suffix == 'B':
        number *= 1000000000
    
    return int(number)


def normalize_url(url: str, base_url: Optional[str] = None) -> Optional[str]:
    """
    Normalize and validate URL.
    
    Args:
        url: URL to normalize
        base_url: Base URL for relative URLs
        
    Returns:
        Normalized URL or None if invalid
    """
    if not url or not isinstance(url, str):
        return None
    
    # Remove whitespace
    url = url.strip()
    
    # Handle relative URLs
    if base_url and not url.startswith(('http://', 'https://')):
        try:
            url = urljoin(base_url, url)
        except Exception as e:
            logger.warning(f"Error joining URLs {base_url} + {url}: {e}")
            return None
    
    # Validate URL format
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            return None
        return url
    except Exception:
        return None


def extract_email_from_text(text: str) -> Optional[str]:
    """
    Extract email address from text.
    
    Args:
        text: Text to search for email
        
    Returns:
        First valid email found or None
    """
    if not text or not isinstance(text, str):
        return None
    
    # Email regex pattern
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    
    if matches:
        # Return first valid email
        return matches[0]
    
    return None


def extract_phone_from_text(text: str) -> Optional[str]:
    """
    Extract phone number from text.
    
    Args:
        text: Text to search for phone number
        
    Returns:
        First valid phone number found or None
    """
    if not text or not isinstance(text, str):
        return None
    
    # Phone number patterns
    phone_patterns = [
        r'\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})',  # US format
        r'\+?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}',  # International
    ]
    
    for pattern in phone_patterns:
        matches = re.findall(pattern, text)
        if matches:
            # Return first valid phone number
            return matches[0] if isinstance(matches[0], str) else ''.join(matches[0])
    
    return None


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Text to clean
        
    Returns:
        Cleaned text
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove special characters that might cause issues
    text = re.sub(r'[^\w\s@.,!?\-()]', '', text)
    
    return text.strip()


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text.
    
    Args:
        text: Text to search for hashtags
        
    Returns:
        List of hashtags (without #)
    """
    if not text or not isinstance(text, str):
        return []
    
    hashtag_pattern = r'#(\w+)'
    matches = re.findall(hashtag_pattern, text)
    
    return matches


def extract_mentions(text: str) -> List[str]:
    """
    Extract mentions from text.
    
    Args:
        text: Text to search for mentions
        
    Returns:
        List of mentions (without @)
    """
    if not text or not isinstance(text, str):
        return []
    
    mention_pattern = r'@(\w+)'
    matches = re.findall(mention_pattern, text)
    
    return matches


def parse_engagement_rate(likes: int, comments: int, followers: int) -> Optional[float]:
    """
    Calculate engagement rate.
    
    Args:
        likes: Number of likes
        comments: Number of comments
        followers: Number of followers
        
    Returns:
        Engagement rate (0-1) or None if invalid
    """
    if not followers or followers <= 0:
        return None
    
    total_engagement = (likes or 0) + (comments or 0)
    return min(1.0, total_engagement / followers)


def parse_instagram_handle(url_or_handle: str) -> Optional[str]:
    """
    Extract Instagram handle from URL or handle.
    
    Args:
        url_or_handle: Instagram URL or handle
        
    Returns:
        Clean handle without @ or None if invalid
    """
    if not url_or_handle:
        return None
    
    # Remove @ if present
    handle = url_or_handle.lstrip('@')
    
    # Extract from URL
    if 'instagram.com' in handle:
        match = re.search(r'instagram\.com/([^/?]+)', handle)
        if match:
            handle = match.group(1)
    
    # Validate handle format
    if re.match(r'^[a-zA-Z0-9._]+$', handle):
        return handle
    
    return None


def parse_linkedin_handle(url_or_handle: str) -> Optional[str]:
    """
    Extract LinkedIn handle from URL or handle.
    
    Args:
        url_or_handle: LinkedIn URL or handle
        
    Returns:
        Clean handle or None if invalid
    """
    if not url_or_handle:
        return None
    
    # Extract from URL
    if 'linkedin.com/in/' in url_or_handle:
        match = re.search(r'linkedin\.com/in/([^/?]+)', url_or_handle)
        if match:
            return match.group(1)
    
    # Return as-is if it looks like a handle
    if re.match(r'^[a-zA-Z0-9\-]+$', url_or_handle):
        return url_or_handle
    
    return None

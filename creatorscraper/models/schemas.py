"""
Pydantic models for creator profile data validation and serialization.
"""

import re
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from urllib.parse import urlparse

from pydantic import BaseModel, Field, validator, root_validator
import json


class Post(BaseModel):
    """Individual post data structure."""
    
    url: str
    timestamp: Optional[datetime] = None
    views: Optional[int] = None
    likes: Optional[int] = None
    comments: Optional[int] = None
    caption: Optional[str] = None
    engagement_rate: Optional[float] = None
    
    @validator('url')
    def validate_url(cls, v):
        """Validate URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v
    
    @validator('engagement_rate')
    def validate_engagement_rate(cls, v):
        """Validate engagement rate is between 0 and 1."""
        if v is not None and not 0 <= v <= 1:
            raise ValueError('Engagement rate must be between 0 and 1')
        return v


class CreatorProfile(BaseModel):
    """Main creator profile data structure."""
    
    source: str = Field(..., description="Platform source: 'instagram' or 'linkedin'")
    profile_url: str = Field(..., description="Full profile URL")
    handle: Optional[str] = None
    display_name: Optional[str] = None
    bio: Optional[str] = None
    niche: Optional[str] = None
    public_contact_email: Optional[str] = None
    location: Optional[str] = None
    follower_count: Optional[int] = None
    following_count: Optional[int] = None
    post_count: Optional[int] = None
    engagement_rate: Optional[float] = None
    top_posts: Optional[List[Post]] = None
    recent_posts_sample: Optional[List[Post]] = None
    avatar_url: Optional[str] = None
    raw: Optional[Dict[str, Any]] = None
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('source')
    def validate_source(cls, v):
        """Validate source is either instagram or linkedin."""
        if v.lower() not in ['instagram', 'linkedin']:
            raise ValueError('Source must be either "instagram" or "linkedin"')
        return v.lower()
    
    @validator('profile_url')
    def validate_profile_url(cls, v):
        """Validate profile URL format."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError('Profile URL must start with http:// or https://')
        return v
    
    @validator('public_contact_email')
    def validate_email(cls, v):
        """Validate email format if provided."""
        if v is not None:
            email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_regex, v):
                raise ValueError('Invalid email format')
        return v
    
    @validator('engagement_rate')
    def validate_engagement_rate(cls, v):
        """Validate engagement rate is between 0 and 1."""
        if v is not None and not 0 <= v <= 1:
            raise ValueError('Engagement rate must be between 0 and 1')
        return v
    
    @validator('top_posts', 'recent_posts_sample')
    def validate_posts(cls, v):
        """Validate posts list length."""
        if v is not None and len(v) > 10:
            raise ValueError('Posts list cannot exceed 10 items')
        return v
    
    @root_validator
    def calculate_engagement_rate(cls, values):
        """Calculate engagement rate from posts if not provided."""
        if values.get('engagement_rate') is None:
            posts = values.get('top_posts', []) or []
            if posts:
                total_engagement = sum(
                    (post.get('likes', 0) or 0) + (post.get('comments', 0) or 0)
                    for post in posts
                )
                follower_count = values.get('follower_count', 0) or 0
                if follower_count > 0:
                    values['engagement_rate'] = total_engagement / follower_count
        return values
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for database storage."""
        data = self.dict()
        
        # Convert datetime objects to ISO strings
        if data.get('scraped_at'):
            data['scraped_at'] = data['scraped_at'].isoformat()
        
        # Convert Post objects to dictionaries
        if data.get('top_posts'):
            data['top_posts'] = [post.dict() if hasattr(post, 'dict') else post for post in data['top_posts']]
        
        if data.get('recent_posts_sample'):
            data['recent_posts_sample'] = [post.dict() if hasattr(post, 'dict') else post for post in data['recent_posts_sample']]
        
        return data


class ScrapingResult(BaseModel):
    """Result of a scraping operation."""
    
    success: bool
    profile: Optional[CreatorProfile] = None
    error: Optional[str] = None
    method_used: Optional[str] = None  # 'api' or 'scraping'
    retry_count: int = 0
    
    class Config:
        """Pydantic configuration."""
        arbitrary_types_allowed = True


class ScrapingConfig(BaseModel):
    """Configuration for scraping operations."""
    
    use_api: bool = True
    max_retries: int = 3
    delay_between_requests: float = 2.0
    max_concurrent: int = 4
    store_raw_data: bool = False
    store_personal_contacts: bool = False
    proxy_url: Optional[str] = None
    user_agent: Optional[str] = None
    
    @validator('delay_between_requests')
    def validate_delay(cls, v):
        """Validate delay is positive."""
        if v < 0:
            raise ValueError('Delay must be positive')
        return v
    
    @validator('max_concurrent')
    def validate_max_concurrent(cls, v):
        """Validate max concurrent is positive."""
        if v <= 0:
            raise ValueError('Max concurrent must be positive')
        return v

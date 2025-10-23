"""
Supabase client for database operations.
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime
from supabase import create_client, Client
from loguru import logger

from ..models.schemas import CreatorProfile


class SupabaseClient:
    """Client for Supabase database operations."""
    
    def __init__(self, url: Optional[str] = None, key: Optional[str] = None):
        """
        Initialize Supabase client.
        
        Args:
            url: Supabase URL (defaults to env var)
            key: Supabase service key (defaults to env var)
        """
        self.url = url or os.getenv('SUPABASE_URL')
        self.key = key or os.getenv('SUPABASE_SERVICE_KEY')
        
        if not self.url or not self.key:
            raise ValueError("Supabase URL and service key must be provided")
        
        try:
            self.client: Client = create_client(self.url, self.key)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise
    
    def upsert_creator(self, profile: CreatorProfile) -> bool:
        """
        Upsert creator profile to database.
        
        Args:
            profile: Creator profile to upsert
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert profile to dict for database
            profile_data = profile.to_dict()
            
            # Prepare data for upsert
            upsert_data = {
                'source': profile_data['source'],
                'profile_url': profile_data['profile_url'],
                'handle': profile_data.get('handle'),
                'display_name': profile_data.get('display_name'),
                'bio': profile_data.get('bio'),
                'niche': profile_data.get('niche'),
                'public_contact_email': profile_data.get('public_contact_email'),
                'location': profile_data.get('location'),
                'follower_count': profile_data.get('follower_count'),
                'following_count': profile_data.get('following_count'),
                'post_count': profile_data.get('post_count'),
                'engagement_rate': profile_data.get('engagement_rate'),
                'top_posts': profile_data.get('top_posts'),
                'recent_posts_sample': profile_data.get('recent_posts_sample'),
                'avatar_url': profile_data.get('avatar_url'),
                'raw': profile_data.get('raw'),
                'scraped_at': profile_data.get('scraped_at'),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            # Remove None values
            upsert_data = {k: v for k, v in upsert_data.items() if v is not None}
            
            # Perform upsert
            result = self.client.table('creators').upsert(upsert_data).execute()
            
            if result.data:
                logger.info(f"Successfully upserted creator: {profile.handle or profile.profile_url}")
                return True
            else:
                logger.error(f"Failed to upsert creator: {profile.handle or profile.profile_url}")
                return False
                
        except Exception as e:
            logger.error(f"Error upserting creator {profile.handle or profile.profile_url}: {e}")
            return False
    
    def get_creator(self, profile_url: str) -> Optional[Dict[str, Any]]:
        """
        Get creator by profile URL.
        
        Args:
            profile_url: Profile URL to search for
            
        Returns:
            Creator data or None if not found
        """
        try:
            result = self.client.table('creators').select('*').eq('profile_url', profile_url).execute()
            
            if result.data:
                return result.data[0]
            return None
            
        except Exception as e:
            logger.error(f"Error getting creator {profile_url}: {e}")
            return None
    
    def get_creators_by_source(self, source: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get creators by source.
        
        Args:
            source: Source platform (instagram, linkedin)
            limit: Maximum number of results
            
        Returns:
            List of creator data
        """
        try:
            result = self.client.table('creators').select('*').eq('source', source).limit(limit).execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting creators by source {source}: {e}")
            return []
    
    def get_creators_by_niche(self, niche: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get creators by niche.
        
        Args:
            niche: Niche category
            limit: Maximum number of results
            
        Returns:
            List of creator data
        """
        try:
            result = self.client.table('creators').select('*').eq('niche', niche).limit(limit).execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting creators by niche {niche}: {e}")
            return []
    
    def get_top_creators(self, source: str = None, niche: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get top creators by follower count.
        
        Args:
            source: Filter by source platform
            niche: Filter by niche
            limit: Maximum number of results
            
        Returns:
            List of creator data sorted by follower count
        """
        try:
            query = self.client.table('creators').select('*').not_.is_('follower_count', 'null')
            
            if source:
                query = query.eq('source', source)
            
            if niche:
                query = query.eq('niche', niche)
            
            result = query.order('follower_count', desc=True).limit(limit).execute()
            return result.data or []
            
        except Exception as e:
            logger.error(f"Error getting top creators: {e}")
            return []
    
    def get_creators_stats(self) -> Dict[str, Any]:
        """
        Get statistics about creators in database.
        
        Returns:
            Dictionary with statistics
        """
        try:
            # Get total count
            total_result = self.client.table('creators').select('id', count='exact').execute()
            total_count = total_result.count or 0
            
            # Get count by source
            instagram_result = self.client.table('creators').select('id', count='exact').eq('source', 'instagram').execute()
            instagram_count = instagram_result.count or 0
            
            linkedin_result = self.client.table('creators').select('id', count='exact').eq('source', 'linkedin').execute()
            linkedin_count = linkedin_result.count or 0
            
            # Get count by niche
            niche_result = self.client.table('creators').select('niche', count='exact').not_.is_('niche', 'null').execute()
            niche_counts = {}
            for row in niche_result.data or []:
                niche = row.get('niche')
                if niche:
                    niche_counts[niche] = niche_counts.get(niche, 0) + 1
            
            return {
                'total_creators': total_count,
                'by_source': {
                    'instagram': instagram_count,
                    'linkedin': linkedin_count
                },
                'by_niche': niche_counts
            }
            
        except Exception as e:
            logger.error(f"Error getting creators stats: {e}")
            return {}
    
    def delete_creator(self, profile_url: str) -> bool:
        """
        Delete creator by profile URL.
        
        Args:
            profile_url: Profile URL to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            result = self.client.table('creators').delete().eq('profile_url', profile_url).execute()
            
            if result.data:
                logger.info(f"Successfully deleted creator: {profile_url}")
                return True
            else:
                logger.warning(f"Creator not found for deletion: {profile_url}")
                return False
                
        except Exception as e:
            logger.error(f"Error deleting creator {profile_url}: {e}")
            return False
    
    def health_check(self) -> bool:
        """
        Check if database connection is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            # Simple query to test connection
            result = self.client.table('creators').select('id').limit(1).execute()
            logger.info("Database health check passed")
            return True
            
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

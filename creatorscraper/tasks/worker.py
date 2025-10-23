"""
RQ worker tasks for async scraping operations.
"""

import os
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from rq import get_current_job
from loguru import logger

from ..sources.instagram import InstagramScraper
from ..sources.linkedin import LinkedInScraper
from ..storage.supabase_client import SupabaseClient
from ..models.schemas import ScrapingResult


def scrape_creator_profile(source: str, profile_url: str, use_api: bool = True, store_raw: bool = False) -> Dict[str, Any]:
    """
    RQ task to scrape a single creator profile.
    
    Args:
        source: Platform source (instagram, linkedin)
        profile_url: Profile URL to scrape
        use_api: Whether to try API first
        store_raw: Whether to store raw data
        
    Returns:
        Dictionary with scraping results
    """
    job = get_current_job()
    job_id = job.id if job else "unknown"
    
    logger.info(f"Starting scraping task {job_id} for {source}: {profile_url}")
    
    try:
        # Initialize scrapers
        instagram_scraper = InstagramScraper()
        linkedin_scraper = LinkedInScraper()
        
        # Initialize database client
        db_client = SupabaseClient()
        
        # Run async scraping
        result = asyncio.run(_scrape_profile_async(
            source, profile_url, use_api, store_raw, instagram_scraper, linkedin_scraper, db_client
        ))
        
        # Clean up scrapers
        asyncio.run(instagram_scraper.close())
        asyncio.run(linkedin_scraper.close())
        
        logger.info(f"Completed scraping task {job_id} for {source}: {profile_url}")
        return result
        
    except Exception as e:
        logger.error(f"Error in scraping task {job_id} for {source}: {profile_url} - {e}")
        return {
            'success': False,
            'error': str(e),
            'source': source,
            'profile_url': profile_url,
            'timestamp': datetime.utcnow().isoformat()
        }


async def _scrape_profile_async(
    source: str, 
    profile_url: str, 
    use_api: bool, 
    store_raw: bool,
    instagram_scraper: InstagramScraper,
    linkedin_scraper: LinkedInScraper,
    db_client: SupabaseClient
) -> Dict[str, Any]:
    """Async helper for scraping profile."""
    try:
        # Select appropriate scraper
        if source.lower() == 'instagram':
            scraper = instagram_scraper
        elif source.lower() == 'linkedin':
            scraper = linkedin_scraper
        else:
            raise ValueError(f"Unsupported source: {source}")
        
        # Scrape profile
        result: ScrapingResult = await scraper.scrape_profile(profile_url, use_api)
        
        if result.success and result.profile:
            # Store raw data if requested
            if store_raw and result.profile.raw is None:
                result.profile.raw = {
                    'scraping_method': result.method_used,
                    'scraped_at': result.profile.scraped_at.isoformat(),
                    'job_metadata': {
                        'source': source,
                        'profile_url': profile_url,
                        'use_api': use_api
                    }
                }
            
            # Save to database
            db_success = db_client.upsert_creator(result.profile)
            
            return {
                'success': True,
                'profile': result.profile.to_dict(),
                'method_used': result.method_used,
                'db_saved': db_success,
                'source': source,
                'profile_url': profile_url,
                'timestamp': datetime.utcnow().isoformat()
            }
        else:
            return {
                'success': False,
                'error': result.error,
                'method_used': result.method_used,
                'source': source,
                'profile_url': profile_url,
                'timestamp': datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error(f"Error in async scraping for {source}: {profile_url} - {e}")
        return {
            'success': False,
            'error': str(e),
            'source': source,
            'profile_url': profile_url,
            'timestamp': datetime.utcnow().isoformat()
        }


def process_creator_batch(creators: List[Dict[str, str]], use_api: bool = True, store_raw: bool = False) -> Dict[str, Any]:
    """
    RQ task to process a batch of creators.
    
    Args:
        creators: List of creator dictionaries with 'source' and 'profile_url'
        use_api: Whether to try API first
        store_raw: Whether to store raw data
        
    Returns:
        Dictionary with batch processing results
    """
    job = get_current_job()
    job_id = job.id if job else "unknown"
    
    logger.info(f"Starting batch processing task {job_id} for {len(creators)} creators")
    
    results = {
        'success': True,
        'total_creators': len(creators),
        'successful': 0,
        'failed': 0,
        'results': [],
        'timestamp': datetime.utcnow().isoformat()
    }
    
    for creator in creators:
        try:
            source = creator.get('source', '').lower()
            profile_url = creator.get('profile_url', '')
            
            if not source or not profile_url:
                logger.warning(f"Skipping invalid creator: {creator}")
                results['results'].append({
                    'success': False,
                    'error': 'Missing source or profile_url',
                    'creator': creator
                })
                results['failed'] += 1
                continue
            
            # Process individual creator
            result = scrape_creator_profile(source, profile_url, use_api, store_raw)
            results['results'].append(result)
            
            if result.get('success'):
                results['successful'] += 1
            else:
                results['failed'] += 1
                
        except Exception as e:
            logger.error(f"Error processing creator {creator}: {e}")
            results['results'].append({
                'success': False,
                'error': str(e),
                'creator': creator
            })
            results['failed'] += 1
    
    # Update overall success status
    results['success'] = results['failed'] == 0
    
    logger.info(f"Completed batch processing task {job_id}: {results['successful']} successful, {results['failed']} failed")
    return results


def health_check() -> Dict[str, Any]:
    """
    Health check task for worker.
    
    Returns:
        Dictionary with health status
    """
    try:
        # Test database connection
        db_client = SupabaseClient()
        db_healthy = db_client.health_check()
        
        return {
            'success': True,
            'database_healthy': db_healthy,
            'timestamp': datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }

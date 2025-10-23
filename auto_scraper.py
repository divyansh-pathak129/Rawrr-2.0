#!/usr/bin/env python3
"""
Automated Creator Discovery and Scraping System

This script automatically:
1. Discovers Instagram creators by browsing Reels
2. Saves them to creators.csv
3. Runs the scraper to collect detailed data
4. Repeats the process in a loop
"""

import asyncio
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from creatorscraper.sources.instagram_discovery import InstagramReelsDiscovery
from creatorscraper.sources.instagram import InstagramScraper
from creatorscraper.sources.linkedin import LinkedInScraper
from creatorscraper.storage.supabase_client import SupabaseClient
from creatorscraper.tasks.worker import scrape_creator_profile
from rq import Queue, Connection
from redis import Redis
from loguru import logger


class AutoScraperSystem:
    """Automated system for discovering and scraping creators."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the auto scraper system.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.discovery = InstagramReelsDiscovery()
        self.instagram_scraper = InstagramScraper()
        self.linkedin_scraper = LinkedInScraper()
        self.db_client = SupabaseClient()
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        # Setup logging
        logger.remove()
        logger.add(
            sys.stderr,
            level=config.get('log_level', 'INFO'),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
        logger.info("Auto scraper system initialized")
    
    async def discover_creators(self) -> List[Dict[str, Any]]:
        """Discover new Instagram creators."""
        logger.info("🔍 Starting creator discovery...")
        
        try:
            # Discover creators from Reels
            creators = await self.discovery.discover_creators(
                max_creators=self.config.get('max_creators_per_cycle', 20),
                niches=self.config.get('target_niches', ['Fitness', 'Tech', 'Fashion']),
                min_followers=self.config.get('min_followers', 1000),
                max_followers=self.config.get('max_followers', 100000),
                scroll_duration=self.config.get('scroll_duration', 120)  # 2 minutes
            )
            
            # Also discover from hashtags if specified
            if self.config.get('hashtags'):
                hashtag_creators = await self.discovery.discover_by_hashtag(
                    self.config['hashtags'],
                    max_creators_per_hashtag=self.config.get('max_creators_per_hashtag', 10)
                )
                creators.extend(hashtag_creators)
            
            # Remove duplicates
            unique_creators = []
            seen_handles = set()
            for creator in creators:
                if creator['handle'] not in seen_handles:
                    unique_creators.append(creator)
                    seen_handles.add(creator['handle'])
            
            logger.info(f"✅ Discovered {len(unique_creators)} unique creators")
            return unique_creators
            
        except Exception as e:
            logger.error(f"❌ Error during discovery: {e}")
            return []
    
    def save_creators_to_csv(self, creators: List[Dict[str, Any]], filename: str = "creators.csv"):
        """Save discovered creators to CSV file."""
        try:
            # Check if file exists and load existing creators
            existing_creators = []
            if os.path.exists(filename):
                with open(filename, 'r', encoding='utf-8') as file:
                    reader = csv.DictReader(file)
                    existing_creators = list(reader)
            
            # Get existing handles
            existing_handles = {creator.get('handle', '') for creator in existing_creators}
            
            # Filter out creators that already exist
            new_creators = []
            for creator in creators:
                if creator['handle'] not in existing_handles:
                    new_creators.append({
                        'source': 'instagram',
                        'profile_url': creator['profile_url'],
                        'handle': creator['handle'],
                        'display_name': creator.get('display_name', ''),
                        'bio': creator.get('bio', ''),
                        'niche': creator.get('niche', ''),
                        'follower_count': creator.get('follower_count', 0),
                        'discovered_at': datetime.now().isoformat()
                    })
            
            if new_creators:
                # Append new creators to existing file
                with open(filename, 'a', newline='', encoding='utf-8') as file:
                    fieldnames = ['source', 'profile_url', 'handle', 'display_name', 'bio', 'niche', 'follower_count', 'discovered_at']
                    writer = csv.DictWriter(file, fieldnames=fieldnames)
                    
                    # Write header if file is empty
                    if not existing_creators:
                        writer.writeheader()
                    
                    writer.writerows(new_creators)
                
                logger.info(f"💾 Saved {len(new_creators)} new creators to {filename}")
            else:
                logger.info("ℹ️ No new creators to save")
            
            return len(new_creators)
            
        except Exception as e:
            logger.error(f"❌ Error saving creators to CSV: {e}")
            return 0
    
    def enqueue_scraping_jobs(self, creators: List[Dict[str, Any]]) -> List[str]:
        """Enqueue scraping jobs for discovered creators."""
        try:
            redis_conn = Redis.from_url(self.redis_url)
            queue = Queue(connection=redis_conn)
            
            job_ids = []
            for creator in creators:
                job = queue.enqueue(
                    scrape_creator_profile,
                    'instagram',  # All discovered creators are Instagram
                    creator['profile_url'],
                    self.config.get('use_api', True),
                    self.config.get('store_raw', False),
                    timeout=300,  # 5 minutes timeout
                    job_timeout=300
                )
                job_ids.append(job.id)
                logger.info(f"📤 Enqueued job {job.id} for @{creator['handle']}")
            
            logger.info(f"📤 Enqueued {len(job_ids)} scraping jobs")
            return job_ids
            
        except Exception as e:
            logger.error(f"❌ Error enqueueing jobs: {e}")
            return []
    
    def check_job_status(self, job_ids: List[str]) -> Dict[str, int]:
        """Check the status of scraping jobs."""
        try:
            redis_conn = Redis.from_url(self.redis_url)
            queue = Queue(connection=redis_conn)
            
            completed = 0
            failed = 0
            pending = 0
            
            for job_id in job_ids:
                job = queue.fetch_job(job_id)
                if job:
                    if job.is_finished:
                        if job.result and job.result.get('success'):
                            completed += 1
                        else:
                            failed += 1
                    elif job.is_failed:
                        failed += 1
                    else:
                        pending += 1
                else:
                    pending += 1
            
            return {
                'completed': completed,
                'failed': failed,
                'pending': pending,
                'total': len(job_ids)
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking job status: {e}")
            return {'completed': 0, 'failed': 0, 'pending': 0, 'total': 0}
    
    def get_database_stats(self) -> Dict[str, Any]:
        """Get statistics from the database."""
        try:
            return self.db_client.get_creators_stats()
        except Exception as e:
            logger.error(f"❌ Error getting database stats: {e}")
            return {}
    
    async def run_cycle(self, cycle_number: int) -> Dict[str, Any]:
        """Run a single discovery and scraping cycle."""
        logger.info(f"🔄 Starting cycle {cycle_number}")
        
        cycle_start = datetime.now()
        results = {
            'cycle_number': cycle_number,
            'start_time': cycle_start.isoformat(),
            'creators_discovered': 0,
            'creators_saved': 0,
            'jobs_enqueued': 0,
            'jobs_completed': 0,
            'jobs_failed': 0,
            'duration': 0
        }
        
        try:
            # Step 1: Discover creators
            creators = await self.discover_creators()
            results['creators_discovered'] = len(creators)
            
            if creators:
                # Step 2: Save to CSV
                saved_count = self.save_creators_to_csv(creators)
                results['creators_saved'] = saved_count
                
                if saved_count > 0:
                    # Step 3: Enqueue scraping jobs
                    job_ids = self.enqueue_scraping_jobs(creators[:saved_count])
                    results['jobs_enqueued'] = len(job_ids)
                    
                    # Step 4: Wait for jobs to complete (with timeout)
                    if job_ids:
                        logger.info(f"⏳ Waiting for {len(job_ids)} jobs to complete...")
                        max_wait_time = self.config.get('max_wait_time', 1800)  # 30 minutes
                        wait_start = time.time()
                        
                        while time.time() - wait_start < max_wait_time:
                            status = self.check_job_status(job_ids)
                            results['jobs_completed'] = status['completed']
                            results['jobs_failed'] = status['failed']
                            
                            if status['pending'] == 0:
                                break
                            
                            logger.info(f"📊 Jobs status: {status['completed']} completed, {status['failed']} failed, {status['pending']} pending")
                            await asyncio.sleep(30)  # Check every 30 seconds
                        
                        # Final status check
                        final_status = self.check_job_status(job_ids)
                        results['jobs_completed'] = final_status['completed']
                        results['jobs_failed'] = final_status['failed']
                
                # Step 5: Get database stats
                db_stats = self.get_database_stats()
                results['database_stats'] = db_stats
                
                logger.info(f"✅ Cycle {cycle_number} completed: {results['creators_discovered']} discovered, {results['creators_saved']} saved, {results['jobs_completed']} scraped")
            else:
                logger.info(f"ℹ️ Cycle {cycle_number}: No new creators discovered")
            
        except Exception as e:
            logger.error(f"❌ Error in cycle {cycle_number}: {e}")
            results['error'] = str(e)
        
        finally:
            cycle_end = datetime.now()
            results['end_time'] = cycle_end.isoformat()
            results['duration'] = (cycle_end - cycle_start).total_seconds()
            
            await self.discovery.close()
        
        return results
    
    async def run_continuous(self):
        """Run the system continuously in a loop."""
        logger.info("🚀 Starting continuous auto scraper system")
        logger.info(f"📋 Configuration: {self.config}")
        
        cycle_number = 1
        
        try:
            while True:
                # Run a single cycle
                results = await self.run_cycle(cycle_number)
                
                # Log cycle results
                logger.info(f"📊 Cycle {cycle_number} Results:")
                logger.info(f"   - Creators discovered: {results['creators_discovered']}")
                logger.info(f"   - Creators saved: {results['creators_saved']}")
                logger.info(f"   - Jobs enqueued: {results['jobs_enqueued']}")
                logger.info(f"   - Jobs completed: {results['jobs_completed']}")
                logger.info(f"   - Jobs failed: {results['jobs_failed']}")
                logger.info(f"   - Duration: {results['duration']:.2f} seconds")
                
                # Wait before next cycle
                wait_time = self.config.get('cycle_interval', 3600)  # 1 hour default
                logger.info(f"⏰ Waiting {wait_time} seconds before next cycle...")
                await asyncio.sleep(wait_time)
                
                cycle_number += 1
                
        except KeyboardInterrupt:
            logger.info("🛑 Auto scraper stopped by user")
        except Exception as e:
            logger.error(f"❌ Fatal error in auto scraper: {e}")
        finally:
            await self.discovery.close()
            logger.info("👋 Auto scraper system shutdown complete")


async def main():
    """Main entry point."""
    # Configuration
    config = {
        'max_creators_per_cycle': 20,  # Discover 20 creators per cycle
        'target_niches': ['Fitness', 'Tech', 'Fashion', 'Gaming', 'Food'],  # Target niches
        'hashtags': ['fitness', 'tech', 'fashion', 'gaming', 'food'],  # Hashtags to browse
        'max_creators_per_hashtag': 5,  # Max creators per hashtag
        'min_followers': 1000,  # Minimum follower count
        'max_followers': 100000,  # Maximum follower count
        'scroll_duration': 120,  # Scroll for 2 minutes
        'use_api': True,  # Try API first
        'store_raw': False,  # Don't store raw data
        'max_wait_time': 1800,  # Wait max 30 minutes for jobs
        'cycle_interval': 3600,  # Wait 1 hour between cycles
        'log_level': 'INFO'
    }
    
    # Create and run the auto scraper system
    system = AutoScraperSystem(config)
    await system.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())

#!/usr/bin/env python3
"""
Simplified Auto Scraper System (No Redis Required)

This script automatically:
1. Discovers Instagram creators by browsing Reels
2. Saves them to creators.csv
3. Scrapes detailed profile data directly
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
from loguru import logger


class SimpleAutoScraper:
    """Simplified auto scraper system without Redis."""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the simple auto scraper system.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        self.discovery = InstagramReelsDiscovery()
        self.instagram_scraper = InstagramScraper()
        self.linkedin_scraper = LinkedInScraper()
        self.db_client = SupabaseClient()
        
        # Setup logging
        logger.remove()
        logger.add(
            sys.stderr,
            level=config.get('log_level', 'INFO'),
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
        )
        
        logger.info("Simple auto scraper system initialized")
    
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
    
    async def scrape_creators_directly(self, creators: List[Dict[str, Any]]) -> Dict[str, int]:
        """Scrape creators directly without Redis queue."""
        logger.info(f"🔄 Starting direct scraping for {len(creators)} creators...")
        
        results = {
            'successful': 0,
            'failed': 0,
            'skipped': 0
        }
        
        # Process creators with concurrency control
        semaphore = asyncio.Semaphore(self.config.get('max_concurrent', 3))
        
        async def scrape_single_creator(creator: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    # Check if creator already exists in database
                    existing = self.db_client.get_creator(creator['profile_url'])
                    if existing:
                        logger.info(f"⏭️ Skipping @{creator['handle']} - already in database")
                        return {'status': 'skipped', 'creator': creator}
                    
                    # Scrape the creator
                    logger.info(f"🔍 Scraping @{creator['handle']}...")
                    result = await self.instagram_scraper.scrape_profile(
                        creator['profile_url'],
                        use_api=self.config.get('use_api', True)
                    )
                    
                    if result.success and result.profile:
                        # Save to database
                        db_success = self.db_client.upsert_creator(result.profile)
                        if db_success:
                            logger.info(f"✅ Successfully scraped and saved @{creator['handle']}")
                            return {'status': 'success', 'creator': creator, 'profile': result.profile}
                        else:
                            logger.error(f"❌ Failed to save @{creator['handle']} to database")
                            return {'status': 'failed', 'creator': creator, 'error': 'Database save failed'}
                    else:
                        logger.error(f"❌ Failed to scrape @{creator['handle']}: {result.error}")
                        return {'status': 'failed', 'creator': creator, 'error': result.error}
                        
                except Exception as e:
                    logger.error(f"❌ Error scraping @{creator['handle']}: {e}")
                    return {'status': 'failed', 'creator': creator, 'error': str(e)}
        
        # Process all creators
        tasks = [scrape_single_creator(creator) for creator in creators]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Count results
        for result in results_list:
            if isinstance(result, Exception):
                results['failed'] += 1
            elif result.get('status') == 'success':
                results['successful'] += 1
            elif result.get('status') == 'failed':
                results['failed'] += 1
            elif result.get('status') == 'skipped':
                results['skipped'] += 1
        
        logger.info(f"📊 Scraping completed: {results['successful']} successful, {results['failed']} failed, {results['skipped']} skipped")
        return results
    
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
            'scraping_successful': 0,
            'scraping_failed': 0,
            'scraping_skipped': 0,
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
                    # Step 3: Scrape creators directly
                    scraping_results = await self.scrape_creators_directly(creators[:saved_count])
                    results['scraping_successful'] = scraping_results['successful']
                    results['scraping_failed'] = scraping_results['failed']
                    results['scraping_skipped'] = scraping_results['skipped']
                
                # Step 4: Get database stats
                db_stats = self.get_database_stats()
                results['database_stats'] = db_stats
                
                logger.info(f"✅ Cycle {cycle_number} completed: {results['creators_discovered']} discovered, {results['creators_saved']} saved, {results['scraping_successful']} scraped")
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
        logger.info("🚀 Starting continuous simple auto scraper system")
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
                logger.info(f"   - Scraping successful: {results['scraping_successful']}")
                logger.info(f"   - Scraping failed: {results['scraping_failed']}")
                logger.info(f"   - Scraping skipped: {results['scraping_skipped']}")
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
        'max_creators_per_cycle': 15,  # Discover 15 creators per cycle
        'target_niches': ['Fitness', 'Tech', 'Fashion', 'Gaming', 'Food'],  # Target niches
        'hashtags': ['fitness', 'tech', 'fashion', 'gaming', 'food'],  # Hashtags to browse
        'max_creators_per_hashtag': 3,  # Max creators per hashtag
        'min_followers': 1000,  # Minimum follower count
        'max_followers': 100000,  # Maximum follower count
        'scroll_duration': 120,  # Scroll for 2 minutes
        'use_api': True,  # Try API first
        'max_concurrent': 3,  # Max 3 concurrent scraping operations
        'cycle_interval': 3600,  # Wait 1 hour between cycles
        'log_level': 'INFO'
    }
    
    # Create and run the simple auto scraper system
    system = SimpleAutoScraper(config)
    await system.run_continuous()


if __name__ == "__main__":
    asyncio.run(main())

"""
Main orchestrator for the creator scraper system.
"""

import asyncio
import os
import sys
from typing import List, Dict, Any, Optional
from pathlib import Path

from loguru import logger

from .sources.instagram import InstagramScraper
from .sources.linkedin import LinkedInScraper
from .storage.supabase_client import SupabaseClient
from .models.schemas import ScrapingResult, ScrapingConfig


class CreatorScraperOrchestrator:
    """Main orchestrator for scraping creator profiles."""
    
    def __init__(self, config: Optional[ScrapingConfig] = None):
        """
        Initialize orchestrator.
        
        Args:
            config: Scraping configuration
        """
        self.config = config or ScrapingConfig()
        self.instagram_scraper = InstagramScraper()
        self.linkedin_scraper = LinkedInScraper()
        self.db_client = SupabaseClient()
        
        logger.info("Creator scraper orchestrator initialized")
    
    async def scrape_creator(self, source: str, profile_url: str) -> ScrapingResult:
        """
        Scrape a single creator profile.
        
        Args:
            source: Platform source (instagram, linkedin)
            profile_url: Profile URL to scrape
            
        Returns:
            ScrapingResult with profile data
        """
        try:
            # Select appropriate scraper
            if source.lower() == 'instagram':
                scraper = self.instagram_scraper
            elif source.lower() == 'linkedin':
                scraper = self.linkedin_scraper
            else:
                return ScrapingResult(
                    success=False,
                    error=f"Unsupported source: {source}",
                    method_used="none"
                )
            
            # Scrape profile
            result = await scraper.scrape_profile(profile_url, self.config.use_api)
            
            # Store in database if successful
            if result.success and result.profile:
                db_success = self.db_client.upsert_creator(result.profile)
                if not db_success:
                    logger.warning(f"Failed to save profile to database: {profile_url}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error scraping creator {source}: {profile_url} - {e}")
            return ScrapingResult(
                success=False,
                error=str(e),
                method_used="none"
            )
    
    async def scrape_creators_batch(self, creators: List[Dict[str, str]]) -> List[ScrapingResult]:
        """
        Scrape multiple creators with concurrency control.
        
        Args:
            creators: List of creator dictionaries with 'source' and 'profile_url'
            
        Returns:
            List of ScrapingResult objects
        """
        semaphore = asyncio.Semaphore(self.config.max_concurrent)
        
        async def scrape_with_semaphore(creator: Dict[str, str]) -> ScrapingResult:
            async with semaphore:
                return await self.scrape_creator(creator['source'], creator['profile_url'])
        
        # Create tasks for all creators
        tasks = [scrape_with_semaphore(creator) for creator in creators]
        
        # Execute with concurrency control
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle exceptions
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(ScrapingResult(
                    success=False,
                    error=str(result),
                    method_used="none"
                ))
            else:
                processed_results.append(result)
        
        return processed_results
    
    async def scrape_creators_from_csv(self, csv_path: str, sources: Optional[List[str]] = None) -> List[ScrapingResult]:
        """
        Scrape creators from CSV file.
        
        Args:
            csv_path: Path to CSV file
            sources: Optional list of sources to filter by
            
        Returns:
            List of ScrapingResult objects
        """
        # Load creators from CSV
        creators = self._load_creators_from_csv(csv_path)
        
        if not creators:
            logger.error("No valid creators found in CSV file")
            return []
        
        # Filter by sources if specified
        if sources:
            creators = [c for c in creators if c['source'].lower() in [s.lower() for s in sources]]
            logger.info(f"Filtered to {len(creators)} creators for sources: {sources}")
        
        # Scrape creators
        return await self.scrape_creators_batch(creators)
    
    def _load_creators_from_csv(self, csv_path: str) -> List[Dict[str, str]]:
        """Load creators from CSV file."""
        import csv
        
        creators = []
        
        try:
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    if 'source' in row and 'profile_url' in row:
                        creators.append({
                            'source': row['source'].strip(),
                            'profile_url': row['profile_url'].strip()
                        })
                    else:
                        logger.warning(f"Skipping invalid row: {row}")
            
            logger.info(f"Loaded {len(creators)} creators from {csv_path}")
            return creators
            
        except Exception as e:
            logger.error(f"Error loading CSV file {csv_path}: {e}")
            return []
    
    def get_scraping_stats(self) -> Dict[str, Any]:
        """Get statistics about scraped creators."""
        try:
            return self.db_client.get_creators_stats()
        except Exception as e:
            logger.error(f"Error getting scraping stats: {e}")
            return {}
    
    async def close(self):
        """Close scrapers and connections."""
        await self.instagram_scraper.close()
        await self.linkedin_scraper.close()
        logger.info("Creator scraper orchestrator closed")


async def main():
    """Main entry point for direct execution."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Creator Profile Scraper")
    parser.add_argument('--input', required=True, help='Path to CSV file with creators')
    parser.add_argument('--source', nargs='+', choices=['instagram', 'linkedin'], help='Filter by source')
    parser.add_argument('--concurrency', type=int, default=4, help='Max concurrent jobs')
    parser.add_argument('--use-api', action='store_true', help='Try API first')
    parser.add_argument('--store-raw', action='store_true', help='Store raw data')
    
    args = parser.parse_args()
    
    # Create configuration
    config = ScrapingConfig(
        use_api=args.use_api,
        max_concurrent=args.concurrency,
        store_raw_data=args.store_raw
    )
    
    # Initialize orchestrator
    orchestrator = CreatorScraperOrchestrator(config)
    
    try:
        # Scrape creators
        results = await orchestrator.scrape_creators_from_csv(args.input, args.source)
        
        # Print results
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        
        logger.info(f"Scraping completed: {successful} successful, {failed} failed")
        
        # Print stats
        stats = orchestrator.get_scraping_stats()
        if stats:
            logger.info(f"Database stats: {stats}")
        
    finally:
        await orchestrator.close()


if __name__ == '__main__':
    asyncio.run(main())

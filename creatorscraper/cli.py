"""
Command-line interface for the creator scraper.
"""

import argparse
import csv
import os
import sys
from typing import List, Dict, Any
from pathlib import Path

from rq import Queue, Connection
from redis import Redis
from loguru import logger

from .tasks.worker import scrape_creator_profile, process_creator_batch
from .storage.supabase_client import SupabaseClient
from .sources.instagram_discovery import InstagramReelsDiscovery


def setup_logging(log_level: str = "INFO"):
    """Setup logging configuration."""
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )


def load_creators_from_csv(csv_path: str) -> List[Dict[str, str]]:
    """
    Load creators from CSV file.
    
    Args:
        csv_path: Path to CSV file
        
    Returns:
        List of creator dictionaries
    """
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


def filter_creators_by_source(creators: List[Dict[str, str]], sources: List[str]) -> List[Dict[str, str]]:
    """
    Filter creators by source.
    
    Args:
        creators: List of creators
        sources: List of sources to include
        
    Returns:
        Filtered list of creators
    """
    if not sources:
        return creators
    
    filtered = []
    for creator in creators:
        if creator['source'].lower() in [s.lower() for s in sources]:
            filtered.append(creator)
    
    logger.info(f"Filtered to {len(filtered)} creators from sources: {sources}")
    return filtered


def enqueue_creators(creators: List[Dict[str, str]], use_api: bool, store_raw: bool, concurrency: int) -> List[str]:
    """
    Enqueue creators for processing.
    
    Args:
        creators: List of creators to process
        use_api: Whether to use API first
        store_raw: Whether to store raw data
        concurrency: Maximum concurrent jobs
        
    Returns:
        List of job IDs
    """
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    try:
        redis_conn = Redis.from_url(redis_url)
        queue = Queue(connection=redis_conn)
        
        job_ids = []
        
        # Enqueue individual jobs
        for creator in creators:
            job = queue.enqueue(
                scrape_creator_profile,
                creator['source'],
                creator['profile_url'],
                use_api,
                store_raw,
                timeout=300,  # 5 minutes timeout
                job_timeout=300
            )
            job_ids.append(job.id)
            logger.info(f"Enqueued job {job.id} for {creator['source']}: {creator['profile_url']}")
        
        logger.info(f"Enqueued {len(job_ids)} jobs")
        return job_ids
        
    except Exception as e:
        logger.error(f"Error enqueueing jobs: {e}")
        return []


def enqueue_batch(creators: List[Dict[str, str]], use_api: bool, store_raw: bool) -> str:
    """
    Enqueue creators as a batch job.
    
    Args:
        creators: List of creators to process
        use_api: Whether to use API first
        store_raw: Whether to store raw data
        
    Returns:
        Job ID
    """
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    try:
        redis_conn = Redis.from_url(redis_url)
        queue = Queue(connection=redis_conn)
        
        job = queue.enqueue(
            process_creator_batch,
            creators,
            use_api,
            store_raw,
            timeout=1800,  # 30 minutes timeout
            job_timeout=1800
        )
        
        logger.info(f"Enqueued batch job {job.id} for {len(creators)} creators")
        return job.id
        
    except Exception as e:
        logger.error(f"Error enqueueing batch job: {e}")
        return ""


def check_database_connection() -> bool:
    """Check if database connection is working."""
    try:
        db_client = SupabaseClient()
        return db_client.health_check()
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return False


async def discover_instagram_creators(
    max_creators: int = 100,
    niches: List[str] = None,
    min_followers: int = 1000,
    max_followers: int = 1000000,
    scroll_duration: int = 300,
    hashtags: List[str] = None
) -> List[Dict[str, Any]]:
    """
    Discover Instagram creators automatically.
    
    Args:
        max_creators: Maximum number of creators to discover
        niches: List of niches to focus on
        min_followers: Minimum follower count
        max_followers: Maximum follower count
        scroll_duration: How long to scroll (seconds)
        hashtags: List of hashtags to browse
        
    Returns:
        List of discovered creators
    """
    discovery = InstagramReelsDiscovery()
    
    try:
        creators = []
        
        # Discover from Reels
        if not hashtags:
            logger.info("Starting Reels discovery...")
            reels_creators = await discovery.discover_creators(
                max_creators=max_creators,
                niches=niches,
                min_followers=min_followers,
                max_followers=max_followers,
                scroll_duration=scroll_duration
            )
            creators.extend(reels_creators)
        
        # Discover from hashtags
        if hashtags:
            logger.info(f"Starting hashtag discovery for hashtags: {hashtags}")
            hashtag_creators = await discovery.discover_by_hashtag(hashtags, max_creators // len(hashtags) if hashtags else 20)
            creators.extend(hashtag_creators)
        
        # Remove duplicates
        unique_creators = []
        seen_handles = set()
        for creator in creators:
            if creator['handle'] not in seen_handles:
                unique_creators.append(creator)
                seen_handles.add(creator['handle'])
        
        logger.info(f"Discovered {len(unique_creators)} unique creators")
        return unique_creators
        
    finally:
        await discovery.close()


def save_discovered_creators(creators: List[Dict[str, Any]], output_file: str):
    """Save discovered creators to CSV file."""
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as file:
            if creators:
                fieldnames = ['source', 'profile_url', 'handle', 'display_name', 'bio', 'niche', 'follower_count']
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                
                for creator in creators:
                    writer.writerow({
                        'source': creator.get('source', 'instagram'),
                        'profile_url': creator.get('profile_url', ''),
                        'handle': creator.get('handle', ''),
                        'display_name': creator.get('display_name', ''),
                        'bio': creator.get('bio', ''),
                        'niche': creator.get('niche', ''),
                        'follower_count': creator.get('follower_count', 0)
                    })
        
        logger.info(f"Saved {len(creators)} discovered creators to {output_file}")
        
    except Exception as e:
        logger.error(f"Error saving discovered creators: {e}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Creator Profile Scraper - Scrape Instagram and LinkedIn creator profiles",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scrape all creators from CSV
  python cli.py --input creators.csv
  
  # Discover Instagram creators automatically
  python cli.py --discover-instagram --max-creators 50
  
  # Discover creators from specific hashtags
  python cli.py --discover-instagram --hashtags fitness tech --max-creators 30
  
  # Discover creators with niche filter
  python cli.py --discover-instagram --niches fitness fashion --min-followers 5000
  
  # Scrape only Instagram profiles with API
  python cli.py --input creators.csv --source instagram --use-api
  
  # Scrape with custom concurrency and store raw data
  python cli.py --input creators.csv --concurrency 8 --store-raw
        """
    )
    
    # Discovery arguments
    parser.add_argument(
        '--discover-instagram',
        action='store_true',
        help='Discover Instagram creators automatically by browsing Reels'
    )
    
    parser.add_argument(
        '--max-creators',
        type=int,
        default=100,
        help='Maximum number of creators to discover (default: 100)'
    )
    
    parser.add_argument(
        '--niches',
        nargs='+',
        choices=['Fitness', 'Fashion', 'Tech', 'Gaming', 'Food', 'Travel', 'Business', 'Education', 'Entertainment', 'Lifestyle', 'Beauty', 'Health', 'Finance', 'Sports', 'Art', 'Music', 'Parenting', 'DIY', 'Photography'],
        help='Filter by specific niches'
    )
    
    parser.add_argument(
        '--hashtags',
        nargs='+',
        help='Browse specific hashtags for discovery'
    )
    
    parser.add_argument(
        '--min-followers',
        type=int,
        default=1000,
        help='Minimum follower count filter (default: 1000)'
    )
    
    parser.add_argument(
        '--max-followers',
        type=int,
        default=1000000,
        help='Maximum follower count filter (default: 1000000)'
    )
    
    parser.add_argument(
        '--scroll-duration',
        type=int,
        default=300,
        help='How long to scroll for discovery in seconds (default: 300)'
    )
    
    parser.add_argument(
        '--output',
        help='Output file for discovered creators (default: discovered_creators.csv)'
    )
    
    # Existing arguments
    parser.add_argument(
        '--input',
        help='Path to CSV file with creators (columns: source, profile_url)'
    )
    
    parser.add_argument(
        '--source',
        nargs='+',
        choices=['instagram', 'linkedin'],
        help='Filter by source platform (default: all)'
    )
    
    parser.add_argument(
        '--concurrency',
        type=int,
        default=4,
        help='Maximum concurrent jobs (default: 4)'
    )
    
    parser.add_argument(
        '--use-api',
        action='store_true',
        help='Try API first before falling back to scraping'
    )
    
    parser.add_argument(
        '--no-api',
        action='store_true',
        help='Skip API and use scraping only'
    )
    
    parser.add_argument(
        '--store-raw',
        action='store_true',
        help='Store raw HTML/JSON data'
    )
    
    parser.add_argument(
        '--batch',
        action='store_true',
        help='Process creators as a single batch job'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--check-db',
        action='store_true',
        help='Check database connection and exit'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Check database connection if requested
    if args.check_db:
        logger.info("Checking database connection...")
        if check_database_connection():
            logger.info("Database connection successful")
            sys.exit(0)
        else:
            logger.error("Database connection failed")
            sys.exit(1)
    
    # Handle Instagram discovery
    if args.discover_instagram:
        import asyncio
        
        logger.info("Starting Instagram creator discovery...")
        
        # Set output file
        output_file = args.output or "discovered_creators.csv"
        
        # Run discovery
        try:
            creators = asyncio.run(discover_instagram_creators(
                max_creators=args.max_creators,
                niches=args.niches,
                min_followers=args.min_followers,
                max_followers=args.max_followers,
                scroll_duration=args.scroll_duration,
                hashtags=args.hashtags
            ))
            
            if creators:
                # Save discovered creators
                save_discovered_creators(creators, output_file)
                
                # Optionally scrape the discovered creators
                if args.input is None:  # Only if no input file provided
                    logger.info(f"Discovered {len(creators)} creators. Use --input {output_file} to scrape them.")
                else:
                    # Process discovered creators
                    use_api = args.use_api and not args.no_api
                    if args.batch:
                        job_id = enqueue_batch(creators, use_api, args.store_raw)
                        if job_id:
                            logger.info(f"Batch job enqueued: {job_id}")
                        else:
                            logger.error("Failed to enqueue batch job")
                            sys.exit(1)
                    else:
                        job_ids = enqueue_creators(creators, use_api, args.store_raw, args.concurrency)
                        if job_ids:
                            logger.info(f"Enqueued {len(job_ids)} individual jobs")
                        else:
                            logger.error("Failed to enqueue jobs")
                            sys.exit(1)
            else:
                logger.warning("No creators discovered")
                sys.exit(1)
                
        except Exception as e:
            logger.error(f"Error during discovery: {e}")
            sys.exit(1)
    
    # Handle CSV input
    elif args.input:
        # Validate input file
        if not os.path.exists(args.input):
            logger.error(f"Input file not found: {args.input}")
            sys.exit(1)
        
        # Load creators from CSV
        creators = load_creators_from_csv(args.input)
        if not creators:
            logger.error("No valid creators found in CSV file")
            sys.exit(1)
        
        # Filter by source if specified
        if args.source:
            creators = filter_creators_by_source(creators, args.source)
            if not creators:
                logger.error("No creators found for specified sources")
                sys.exit(1)
        
        # Determine API usage
        use_api = args.use_api and not args.no_api
        
        # Check database connection
        if not check_database_connection():
            logger.error("Database connection failed. Please check your Supabase credentials.")
            sys.exit(1)
        
        # Enqueue jobs
        if args.batch:
            job_id = enqueue_batch(creators, use_api, args.store_raw)
            if job_id:
                logger.info(f"Batch job enqueued: {job_id}")
            else:
                logger.error("Failed to enqueue batch job")
                sys.exit(1)
        else:
            job_ids = enqueue_creators(creators, use_api, args.store_raw, args.concurrency)
            if job_ids:
                logger.info(f"Enqueued {len(job_ids)} individual jobs")
            else:
                logger.error("Failed to enqueue jobs")
                sys.exit(1)
    
    else:
        logger.error("Either --input or --discover-instagram must be specified")
        sys.exit(1)
    
    logger.info("Jobs enqueued successfully. Start RQ workers to process them.")


if __name__ == '__main__':
    main()
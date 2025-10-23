#!/usr/bin/env python3
"""
Simple script to run the auto scraper system.
"""

import asyncio
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from auto_scraper import AutoScraperSystem


async def main():
    """Run the auto scraper with custom configuration."""
    
    # Custom configuration - modify these values as needed
    config = {
        # Discovery settings
        'max_creators_per_cycle': 30,  # Discover 30 creators per cycle
        'target_niches': ['Fitness', 'Tech', 'Fashion', 'Gaming', 'Food', 'Travel'],  # Target niches
        'hashtags': ['fitness', 'tech', 'fashion', 'gaming', 'food', 'travel'],  # Hashtags to browse
        'max_creators_per_hashtag': 5,  # Max creators per hashtag
        'min_followers': 2000,  # Minimum follower count
        'max_followers': 50000,  # Maximum follower count
        'scroll_duration': 180,  # Scroll for 3 minutes
        
        # Scraping settings
        'use_api': True,  # Try API first
        'store_raw': False,  # Don't store raw data
        'max_wait_time': 1800,  # Wait max 30 minutes for jobs
        
        # Loop settings
        'cycle_interval': 7200,  # Wait 2 hours between cycles
        
        # Logging
        'log_level': 'INFO'
    }
    
    print("🚀 Starting Auto Scraper System")
    print("=" * 50)
    print(f"📊 Configuration:")
    print(f"   - Max creators per cycle: {config['max_creators_per_cycle']}")
    print(f"   - Target niches: {config['target_niches']}")
    print(f"   - Min followers: {config['min_followers']:,}")
    print(f"   - Max followers: {config['max_followers']:,}")
    print(f"   - Cycle interval: {config['cycle_interval']} seconds ({config['cycle_interval']//3600} hours)")
    print("=" * 50)
    
    # Create and run the auto scraper system
    system = AutoScraperSystem(config)
    await system.run_continuous()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Auto scraper stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)

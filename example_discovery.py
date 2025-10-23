#!/usr/bin/env python3
"""
Example script demonstrating Instagram creator discovery.
"""

import asyncio
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from creatorscraper.sources.instagram_discovery import InstagramReelsDiscovery
from creatorscraper.sources.instagram import InstagramScraper
from creatorscraper.storage.supabase_client import SupabaseClient


async def main():
    """Example of discovering and scraping Instagram creators."""
    print("🚀 Starting Instagram Creator Discovery...")
    
    # Initialize discovery
    discovery = InstagramReelsDiscovery()
    
    try:
        # Discover creators from Reels
        print("📱 Browsing Instagram Reels for creators...")
        creators = await discovery.discover_creators(
            max_creators=20,  # Discover 20 creators
            niches=['Fitness', 'Tech', 'Fashion'],  # Focus on these niches
            min_followers=1000,  # Minimum 1K followers
            max_followers=100000,  # Maximum 100K followers
            scroll_duration=60  # Scroll for 1 minute
        )
        
        print(f"✅ Discovered {len(creators)} creators!")
        
        # Display discovered creators
        for i, creator in enumerate(creators, 1):
            print(f"\n{i}. @{creator['handle']}")
            print(f"   Name: {creator.get('display_name', 'N/A')}")
            print(f"   Followers: {creator.get('follower_count', 0):,}")
            print(f"   Niche: {creator.get('niche', 'N/A')}")
            print(f"   Bio: {creator.get('bio', 'N/A')[:100]}...")
        
        # Optionally scrape detailed profiles
        if creators:
            print(f"\n🔍 Scraping detailed profiles for {len(creators)} creators...")
            
            scraper = InstagramScraper()
            db_client = SupabaseClient()
            
            successful_scrapes = 0
            for creator in creators:
                try:
                    print(f"   Scraping @{creator['handle']}...")
                    result = await scraper.scrape_profile(creator['profile_url'])
                    
                    if result.success:
                        # Save to database
                        db_success = db_client.upsert_creator(result.profile)
                        if db_success:
                            successful_scrapes += 1
                            print(f"   ✅ Saved @{creator['handle']} to database")
                        else:
                            print(f"   ❌ Failed to save @{creator['handle']} to database")
                    else:
                        print(f"   ❌ Failed to scrape @{creator['handle']}: {result.error}")
                        
                except Exception as e:
                    print(f"   ❌ Error scraping @{creator['handle']}: {e}")
            
            print(f"\n🎉 Successfully scraped and saved {successful_scrapes}/{len(creators)} creators!")
        
    except Exception as e:
        print(f"❌ Error during discovery: {e}")
    
    finally:
        await discovery.close()
        print("\n✨ Discovery completed!")


if __name__ == "__main__":
    asyncio.run(main())

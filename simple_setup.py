#!/usr/bin/env python3
"""
Simple setup script for the auto scraper system (No Redis Required).
"""

import os
import sys
import subprocess
from pathlib import Path


def check_requirements():
    """Check if all requirements are installed."""
    print("🔍 Checking requirements...")
    
    try:
        import playwright
        import supabase
        print("✅ All Python packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing package: {e}")
        print("📦 Installing requirements...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        return True


def check_supabase():
    """Check if Supabase credentials are configured."""
    print("🔍 Checking Supabase configuration...")
    
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
    
    if not supabase_url or supabase_url == 'your_supabase_url_here':
        print("❌ SUPABASE_URL not configured")
        return False
    
    if not supabase_key or supabase_key == 'your_supabase_service_key_here':
        print("❌ SUPABASE_SERVICE_KEY not configured")
        return False
    
    print("✅ Supabase credentials configured")
    return True


def setup_database():
    """Setup the database schema."""
    print("🗄️ Setting up database schema...")
    
    try:
        from creatorscraper.storage.supabase_client import SupabaseClient
        db_client = SupabaseClient()
        
        if db_client.health_check():
            print("✅ Database connection successful")
            print("💡 Make sure to run the SQL schema in your Supabase project:")
            print("   psql $SUPABASE_URL -f sql/create_tables.sql")
            return True
        else:
            print("❌ Database connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Database setup error: {e}")
        return False


def install_playwright():
    """Install Playwright browsers."""
    print("🎭 Installing Playwright browsers...")
    
    try:
        subprocess.run(["playwright", "install", "chromium"], check=True)
        print("✅ Playwright browsers installed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Playwright installation failed: {e}")
        return False


def create_env_file():
    """Create .env file if it doesn't exist."""
    if not os.path.exists('.env'):
        print("📝 Creating .env file...")
        
        with open('.env.example', 'r') as f:
            content = f.read()
        
        with open('.env', 'w') as f:
            f.write(content)
        
        print("✅ Created .env file")
        print("⚠️  Please edit .env file with your credentials")
        return False
    else:
        print("✅ .env file exists")
        return True


def main():
    """Main setup function."""
    print("🚀 Simple Auto Scraper System Setup (No Redis Required)")
    print("=" * 60)
    
    # Check requirements
    if not check_requirements():
        print("❌ Requirements check failed")
        return
    
    # Create .env file
    env_ready = create_env_file()
    if not env_ready:
        print("\n⚠️  Please configure your .env file with the following credentials:")
        print("   - SUPABASE_URL: Your Supabase project URL")
        print("   - SUPABASE_SERVICE_KEY: Your Supabase service key")
        print("   - Optional: INSTAGRAM_ACCESS_TOKEN, LINKEDIN_ACCESS_TOKEN")
        print("\nThen run this setup script again.")
        return
    
    # Check Supabase
    if not check_supabase():
        print("\n💡 To get Supabase credentials:")
        print("   1. Go to https://supabase.com")
        print("   2. Create a new project")
        print("   3. Go to Settings > API")
        print("   4. Copy the URL and service_role key")
        print("   5. Update your .env file")
        return
    
    # Setup database
    if not setup_database():
        print("\n💡 To setup the database:")
        print("   1. Run: psql $SUPABASE_URL -f sql/create_tables.sql")
        print("   2. Or copy the SQL from sql/create_tables.sql to your Supabase SQL editor")
        return
    
    # Install Playwright
    if not install_playwright():
        print("❌ Playwright installation failed")
        return
    
    print("\n🎉 Setup complete!")
    print("\n📋 Next steps:")
    print("   1. Run simple auto scraper: python simple_auto_scraper.py")
    print("\n🔧 Configuration options in simple_auto_scraper.py:")
    print("   - max_creators_per_cycle: Number of creators to discover per cycle")
    print("   - target_niches: Niches to focus on")
    print("   - cycle_interval: Time between cycles (seconds)")
    print("   - min_followers/max_followers: Follower count filters")
    print("\n✨ No Redis required - everything runs in a single process!")


if __name__ == "__main__":
    main()

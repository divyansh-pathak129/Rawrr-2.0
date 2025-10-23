# 🤖 Auto Scraper System - Complete Setup Guide

This guide will help you set up the automated creator discovery and scraping system that runs continuously in a loop.

## 🎯 What This System Does

1. **Automatically discovers Instagram creators** by browsing Reels and hashtags
2. **Saves discovered creators** to `creators.csv`
3. **Scrapes detailed profile data** for each creator
4. **Stores data in Supabase** database
5. **Runs continuously** in a loop (configurable intervals)

## 📋 Prerequisites

- Python 3.11+
- Redis server
- Supabase account
- Instagram account (for discovery)

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Install Python packages
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
```

### 2. Setup Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env file with your credentials (see below)
```

### 3. Configure Credentials

Edit your `.env` file with these **REQUIRED** credentials:

```env
# REQUIRED: Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=your_service_role_key_here

# REQUIRED: Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Optional: Instagram API (for better scraping)
INSTAGRAM_ACCESS_TOKEN=your_instagram_token_here
INSTAGRAM_APP_ID=your_instagram_app_id_here

# Optional: LinkedIn API
LINKEDIN_ACCESS_TOKEN=your_linkedin_token_here
```

### 4. Setup Database

```bash
# Run the SQL schema in your Supabase project
psql $SUPABASE_URL -f sql/create_tables.sql

# Or copy the SQL from sql/create_tables.sql to your Supabase SQL editor
```

### 5. Start Redis Server

```bash
# On Windows: Download Redis from https://github.com/microsoftarchive/redis/releases
# On macOS: brew install redis && redis-server
# On Linux: sudo apt-get install redis-server && redis-server

redis-server
```

### 6. Start the System

```bash
# Terminal 1: Start RQ workers
python start_workers.py --workers 2

# Terminal 2: Start auto scraper
python run_auto_scraper.py
```

## 🔧 Configuration

Edit `run_auto_scraper.py` to customize the system:

```python
config = {
    # Discovery settings
    'max_creators_per_cycle': 30,  # Discover 30 creators per cycle
    'target_niches': ['Fitness', 'Tech', 'Fashion'],  # Target niches
    'hashtags': ['fitness', 'tech', 'fashion'],  # Hashtags to browse
    'min_followers': 2000,  # Minimum follower count
    'max_followers': 50000,  # Maximum follower count
    'scroll_duration': 180,  # Scroll for 3 minutes

    # Loop settings
    'cycle_interval': 7200,  # Wait 2 hours between cycles
}
```

## 📊 How It Works

### Discovery Process

1. **Reels Browsing**: Opens Instagram Reels in headless browser
2. **Scrolling**: Scrolls through content for specified duration
3. **Extraction**: Extracts creator handles and basic info
4. **Filtering**: Applies follower count and niche filters
5. **Deduplication**: Removes creators already in database

### Scraping Process

1. **Job Queue**: Enqueues scraping jobs for discovered creators
2. **Parallel Processing**: Multiple workers process jobs simultaneously
3. **Data Collection**: Collects detailed profile data (posts, engagement, etc.)
4. **Database Storage**: Saves data to Supabase

### Loop Process

1. **Discovery**: Find new creators
2. **Scraping**: Process discovered creators
3. **Wait**: Wait for specified interval
4. **Repeat**: Start next cycle

## 📈 Monitoring

### Check Job Status

```bash
# Check Redis queue status
redis-cli
> LLEN rq:queue:default
> LLEN rq:queue:failed
```

### Check Database

```sql
-- Check total creators
SELECT COUNT(*) FROM creators;

-- Check by niche
SELECT niche, COUNT(*) FROM creators GROUP BY niche;

-- Check by source
SELECT source, COUNT(*) FROM creators GROUP BY source;
```

### View Logs

The system logs all activities:

- Discovery progress
- Scraping results
- Error messages
- Database operations

## 🛠️ Troubleshooting

### Common Issues

1. **Redis Connection Failed**

   ```bash
   # Check if Redis is running
   redis-cli ping
   # Should return PONG
   ```

2. **Database Connection Failed**

   ```bash
   # Check Supabase credentials
   python -c "from creatorscraper.storage.supabase_client import SupabaseClient; print(SupabaseClient().health_check())"
   ```

3. **No Creators Discovered**

   - Check if Instagram is accessible
   - Try different niches or hashtags
   - Increase scroll duration

4. **Jobs Not Processing**
   - Check if workers are running
   - Check Redis connection
   - Check job queue: `redis-cli LLEN rq:queue:default`

### Debug Mode

```bash
# Run with debug logging
LOG_LEVEL=DEBUG python run_auto_scraper.py
```

## 📁 Output Files

- `creators.csv`: Discovered creators list
- `logs/`: System logs (if configured)
- Database: Supabase `creators` table

## 🔒 Security & Legal

- **Rate Limiting**: Built-in rate limiting to avoid blocks
- **Respectful Scraping**: Only public data, no private content
- **Terms of Service**: Respects Instagram's ToS
- **Data Privacy**: No personal information stored

## 📊 Performance Tips

1. **Increase Workers**: More workers = faster processing
2. **Optimize Discovery**: Focus on specific niches
3. **Database Indexing**: Ensure proper database indexes
4. **Proxy Rotation**: Use proxies for large-scale scraping

## 🎯 Use Cases

- **Influencer Research**: Find creators in specific niches
- **Market Analysis**: Analyze creator landscape
- **Lead Generation**: Find potential collaboration partners
- **Trend Analysis**: Discover emerging creators

## 📞 Support

If you encounter issues:

1. Check the logs for error messages
2. Verify all credentials are correct
3. Ensure Redis and Supabase are accessible
4. Check network connectivity

## 🚀 Advanced Usage

### Custom Discovery

```python
# Custom discovery with specific hashtags
creators = await discovery.discover_by_hashtag(['fitness', 'tech'], max_creators_per_hashtag=10)
```

### Batch Processing

```python
# Process existing CSV file
python cli.py --input creators.csv --concurrency 4
```

### API Integration

```python
# Use Instagram Graph API for better data
config['use_api'] = True
```

---

**🎉 You're all set! The auto scraper system will now continuously discover and scrape Instagram creators automatically.**

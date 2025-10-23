# Creator Profile Scraper

A production-ready Python package for scraping Instagram and LinkedIn creator profiles and storing them in Supabase. This tool provides comprehensive creator data including follower counts, engagement metrics, niche detection, and top-performing content.

## 🚀 Features

- **🤖 Auto-Discovery**: Automatically discover Instagram creators by browsing Reels and hashtags
- **Hybrid Scraping**: Instagram Graph API + Playwright fallback for Instagram
- **LinkedIn Integration**: LinkedIn API + Playwright fallback for LinkedIn
- **Niche Detection**: AI-powered categorization of creators (20+ categories)
- **Engagement Analysis**: Top posts, engagement rates, and performance metrics
- **Rate Limiting**: Intelligent rate limiting to avoid IP blocks and captchas
- **Async Processing**: RQ + Redis for scalable background job processing
- **Data Validation**: Pydantic models with comprehensive validation
- **Docker Support**: Full containerization with Docker Compose
- **Comprehensive Testing**: 90%+ test coverage with mocked dependencies

## 📊 Data Collected

For each creator, the scraper collects:

- **Basic Info**: Handle, display name, bio, location, avatar
- **Metrics**: Follower count, following count, post count
- **Engagement**: Engagement rate, top 3 posts, recent posts sample
- **Niche**: Auto-detected category (Fitness, Tech, Fashion, etc.)
- **Contact**: Public email addresses (if available)
- **Content**: Post URLs, captions, likes, comments, timestamps

## 🛠️ Installation

### Prerequisites

- Python 3.11+
- Redis server
- Supabase account
- Docker (optional)

### Local Installation

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd creator-scraper
   ```

2. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

3. **Setup environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Setup database**
   ```bash
   # Run the SQL schema in your Supabase project
   psql $SUPABASE_URL -f sql/create_tables.sql
   ```

### Docker Installation

1. **Clone and setup**

   ```bash
   git clone <repository-url>
   cd creator-scraper
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Start services**
   ```bash
   docker-compose up -d
   ```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url_here
SUPABASE_SERVICE_KEY=your_supabase_service_key_here

# Instagram API (Optional - for Graph API access)
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token_here
INSTAGRAM_APP_ID=your_instagram_app_id_here

# LinkedIn API (Optional - for official API access)
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token_here

# Redis Configuration
REDIS_URL=redis://localhost:6379/0

# Scraping Configuration
LOG_LEVEL=INFO
STORE_RAW_DATA=false
STORE_PERSONAL_CONTACTS=false
MAX_CONCURRENT_JOBS=4
```

### API Credentials Setup

#### Instagram Graph API

1. **Create Facebook App**

   - Go to [Facebook Developers](https://developers.facebook.com/)
   - Create a new app
   - Add Instagram Basic Display product

2. **Get Access Token**
   - Use Instagram Basic Display API
   - Generate long-lived access token
   - Add to `INSTAGRAM_ACCESS_TOKEN` in `.env`

#### LinkedIn API

1. **Create LinkedIn App**

   - Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
   - Create a new app
   - Request access to People API

2. **Get Access Token**
   - Use OAuth 2.0 flow
   - Generate access token
   - Add to `LINKEDIN_ACCESS_TOKEN` in `.env`

## 🚀 Usage

### 🤖 Auto Scraper System (Recommended)

**Complete automated system that discovers creators and scrapes them continuously:**

```bash
# 1. Setup (one-time)
python setup_auto_scraper.py

# 2. Start workers (Terminal 1)
python start_workers.py --workers 2

# 3. Start auto scraper (Terminal 2)
python run_auto_scraper.py
```

**What it does:**

- 🔍 Automatically discovers Instagram creators by browsing Reels
- 💾 Saves discovered creators to `creators.csv`
- 🔄 Scrapes detailed profile data for each creator
- 📊 Stores everything in Supabase database
- 🔁 Runs continuously in a loop (configurable intervals)

### Command Line Interface

```bash
# Basic usage - scrape all creators from CSV
python cli.py --input creators.csv

# 🚀 NEW: Discover Instagram creators automatically by browsing Reels
python cli.py --discover-instagram --max-creators 50

# Discover creators from specific hashtags
python cli.py --discover-instagram --hashtags fitness tech --max-creators 30

# Discover creators with niche and follower filters
python cli.py --discover-instagram --niches fitness fashion --min-followers 5000 --max-followers 100000

# Filter by source platform
python cli.py --input creators.csv --source instagram linkedin

# Use API first (requires credentials)
python cli.py --input creators.csv --use-api

# Custom concurrency and store raw data
python cli.py --input creators.csv --concurrency 8 --store-raw

# Process as batch job
python cli.py --input creators.csv --batch

# Check database connection
python cli.py --check-db
```

### Programmatic Usage

```python
from creatorscraper import InstagramScraper, InstagramReelsDiscovery, SupabaseClient

# Auto-discover creators
discovery = InstagramReelsDiscovery()
creators = await discovery.discover_creators(
    max_creators=50,
    niches=['Fitness', 'Tech'],
    min_followers=1000,
    scroll_duration=300
)

# Scrape discovered creators
scraper = InstagramScraper()
db_client = SupabaseClient()

for creator in creators:
    result = await scraper.scrape_profile(creator['profile_url'])
    if result.success:
        db_client.upsert_creator(result.profile)
```

### RQ Worker Setup

1. **Start Redis server**

   ```bash
   redis-server
   ```

2. **Start RQ worker**

   ```bash
   rq worker --url redis://localhost:6379/0
   ```

3. **Enqueue jobs**
   ```bash
   python cli.py --input creators.csv
   ```

## 📁 Project Structure

```
creatorscraper/
├── __init__.py
├── cli.py                   # Command-line interface
├── run_scraper.py          # Main orchestrator
├── sources/
│   ├── instagram.py        # Instagram scraper
│   ├── linkedin.py         # LinkedIn scraper
│   └── niche_detector.py   # Niche classification
├── storage/
│   └── supabase_client.py  # Database operations
├── models/
│   └── schemas.py          # Pydantic models
├── utils/
│   ├── rate_limiter.py     # Rate limiting
│   ├── ua_rotation.py      # User agent rotation
│   ├── proxy_manager.py    # Proxy management
│   └── parsers.py          # Data parsing
├── tasks/
│   └── worker.py           # RQ worker tasks
└── tests/                  # Test suite
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest creatorscraper/tests/ -v

# Run with coverage
pytest creatorscraper/tests/ -v --cov=creatorscraper --cov-report=html

# Run specific test file
pytest creatorscraper/tests/test_instagram.py -v
```

### Test Coverage

The test suite includes:

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Mock Tests**: API and database operation mocking
- **Edge Cases**: Error handling and boundary conditions

## 🐳 Docker Deployment

### Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production

```bash
# Build production image
docker build -t creator-scraper:latest .

# Run with environment variables
docker run -d \
  --name creator-scraper \
  --env-file .env \
  creator-scraper:latest
```

## 📊 Database Schema

The scraper uses a single `creators` table with the following structure:

```sql
CREATE TABLE creators (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source TEXT NOT NULL,
    profile_url TEXT NOT NULL UNIQUE,
    handle TEXT,
    display_name TEXT,
    bio TEXT,
    niche TEXT,                          -- Auto-detected category
    public_contact_email TEXT,
    location TEXT,
    follower_count BIGINT,
    following_count BIGINT,
    post_count BIGINT,
    engagement_rate FLOAT,               -- Avg engagement across posts
    top_posts JSONB,                     -- Top 3 posts with stats
    recent_posts_sample JSONB,           -- 5 most recent posts
    avatar_url TEXT,
    raw JSONB,                           -- Optional full data dump
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    inserted_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## 🔒 Security & Privacy

### Data Protection

- **No Private Data**: Only public profile information is collected
- **Email Filtering**: Only public contact emails are stored
- **GDPR Compliance**: Built-in data retention and deletion capabilities
- **Secure Storage**: All credentials stored in environment variables

### Rate Limiting

- **Instagram API**: 200 requests/hour
- **Instagram Scraping**: 20 requests/hour with jitter
- **LinkedIn API**: 500 requests/day
- **LinkedIn Scraping**: 10 requests/hour

### Anti-Detection

- **User Agent Rotation**: 50+ realistic user agents
- **Proxy Support**: HTTP/SOCKS5 proxy rotation
- **Random Delays**: 2-5 second delays between requests
- **Stealth Mode**: Headless browser with realistic viewport

## ⚖️ Legal & Ethical Considerations

### Terms of Service Compliance

- **Instagram**: Respects robots.txt and rate limits
- **LinkedIn**: Uses official APIs when possible
- **Data Usage**: Only public information is collected
- **No Scraping**: Private or protected content is not accessed

### Ethical Guidelines

- **Respect Privacy**: No personal or sensitive information
- **Rate Limiting**: Prevents server overload
- **Data Retention**: Configurable data retention policies
- **Opt-out Support**: Built-in data deletion capabilities

### Disclaimer

This tool is for educational and research purposes. Users are responsible for:

- Complying with platform Terms of Service
- Respecting robots.txt directives
- Following applicable data protection laws
- Obtaining necessary permissions for data collection

## 🚨 Troubleshooting

### Common Issues

1. **Database Connection Failed**

   ```bash
   # Check Supabase credentials
   python cli.py --check-db
   ```

2. **Rate Limit Exceeded**

   - Reduce concurrency: `--concurrency 2`
   - Use API credentials: `--use-api`
   - Add delays between requests

3. **Playwright Browser Issues**

   ```bash
   # Reinstall browsers
   playwright install chromium
   ```

4. **Redis Connection Failed**
   ```bash
   # Check Redis server
   redis-cli ping
   ```

### Debug Mode

```bash
# Enable debug logging
python cli.py --input creators.csv --log-level DEBUG
```

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open Pull Request**

### Development Setup

```bash
# Install development dependencies
pip install -r requirements.txt
pip install pytest black flake8 mypy

# Run tests
pytest creatorscraper/tests/ -v

# Format code
black creatorscraper/

# Lint code
flake8 creatorscraper/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [Wiki](https://github.com/your-repo/wiki)
- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)

## 🙏 Acknowledgments

- **Playwright**: For headless browser automation
- **Supabase**: For database and authentication
- **RQ**: For job queue management
- **Pydantic**: For data validation
- **Instagram Graph API**: For official data access
- **LinkedIn API**: For professional network data

---

**⚠️ Important**: This tool is for educational and research purposes. Always respect platform Terms of Service and applicable laws. Use responsibly and ethically.

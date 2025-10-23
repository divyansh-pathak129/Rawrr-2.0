#!/usr/bin/env python3
"""
Script to start RQ workers for processing scraping jobs.
"""

import os
import subprocess
import sys
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))


def start_worker():
    """Start a single RQ worker."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    print(f"🚀 Starting RQ worker with Redis: {redis_url}")
    print("💡 Press Ctrl+C to stop the worker")
    
    try:
        subprocess.run([
            sys.executable, "-m", "rq", "worker",
            "--url", redis_url,
            "--name", "creator-scraper-worker"
        ])
    except KeyboardInterrupt:
        print("\n🛑 Worker stopped by user")
    except Exception as e:
        print(f"❌ Error starting worker: {e}")


def start_multiple_workers(num_workers=2):
    """Start multiple RQ workers."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    print(f"🚀 Starting {num_workers} RQ workers with Redis: {redis_url}")
    print("💡 Press Ctrl+C to stop all workers")
    
    try:
        subprocess.run([
            sys.executable, "-m", "rq", "worker",
            "--url", redis_url,
            "--name", "creator-scraper-worker",
            "--workers", str(num_workers)
        ])
    except KeyboardInterrupt:
        print("\n🛑 Workers stopped by user")
    except Exception as e:
        print(f"❌ Error starting workers: {e}")


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Start RQ workers for creator scraping")
    parser.add_argument(
        '--workers',
        type=int,
        default=2,
        help='Number of workers to start (default: 2)'
    )
    
    args = parser.parse_args()
    
    if args.workers == 1:
        start_worker()
    else:
        start_multiple_workers(args.workers)


if __name__ == "__main__":
    main()

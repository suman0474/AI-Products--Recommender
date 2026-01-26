#!/usr/bin/env python3
"""
Production Server Startup Script

This script starts the AI Product Recommender API using Gunicorn WSGI server
with production-ready configuration.

Usage:
    python start_production.py

    # With custom configuration:
    export GUNICORN_WORKERS=8
    export GUNICORN_BIND=0.0.0.0:8080
    python start_production.py

    # Quick start options:
    python start_production.py --workers 8
    python start_production.py --bind 0.0.0.0:8080
    python start_production.py --reload  # Development mode with auto-reload
"""

import sys
import os
import subprocess
import argparse
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_requirements():
    """Check if required dependencies are installed."""
    try:
        import gunicorn
        logger.info(f"✓ Gunicorn {gunicorn.__version__} found")
    except ImportError:
        logger.error("✗ Gunicorn not installed!")
        logger.error("  Install it with: pip install gunicorn")
        sys.exit(1)

    try:
        import flask
        logger.info(f"✓ Flask {flask.__version__} found")
    except ImportError:
        logger.error("✗ Flask not installed!")
        logger.error("  Install it with: pip install -r requirements.txt")
        sys.exit(1)


def check_environment():
    """Check and display environment configuration."""
    logger.info("="*70)
    logger.info("Environment Configuration:")
    logger.info("-"*70)

    # Check critical environment variables
    env_vars = [
        ("AZURE_STORAGE_CONNECTION_STRING", "Azure Blob Storage", False),
        ("GOOGLE_API_KEY", "Google Gemini API", True),
        ("OPENAI_API_KEY", "OpenAI API (Fallback)", False),
        ("SERPAPI_API_KEY", "SerpAPI (Search)", False),
        ("GOOGLE_CSE_ID", "Google Custom Search", False),
        ("SECRET_KEY", "Flask Secret Key", True),
    ]

    for var, description, required in env_vars:
        value = os.getenv(var)
        if value:
            # Mask sensitive values
            if "KEY" in var or "SECRET" in var or "CONNECTION" in var:
                display_value = value[:10] + "..." if len(value) > 10 else "***"
            else:
                display_value = value
            logger.info(f"  ✓ {description:30s}: {display_value}")
        else:
            status = "✗ MISSING (REQUIRED)" if required else "⚠ Not set (optional)"
            logger.info(f"  {status:30s}: {description}")

    logger.info("="*70)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Start AI Product Recommender API in production mode'
    )

    parser.add_argument(
        '--workers', '-w',
        type=int,
        default=None,
        help='Number of worker processes (default: CPU*2+1)'
    )

    parser.add_argument(
        '--threads', '-t',
        type=int,
        default=None,
        help='Number of threads per worker (default: 4)'
    )

    parser.add_argument(
        '--bind', '-b',
        type=str,
        default=None,
        help='Server bind address (default: 0.0.0.0:5000)'
    )

    parser.add_argument(
        '--timeout',
        type=int,
        default=None,
        help='Worker timeout in seconds (default: 3600)'
    )

    parser.add_argument(
        '--reload',
        action='store_true',
        help='Enable auto-reload on code changes (DEVELOPMENT ONLY!)'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['debug', 'info', 'warning', 'error', 'critical'],
        default=None,
        help='Log level (default: info)'
    )

    parser.add_argument(
        '--access-log',
        action='store_true',
        help='Enable access logging'
    )

    parser.add_argument(
        '--no-preload',
        action='store_true',
        help='Disable app preloading (use for development)'
    )

    return parser.parse_args()


def build_gunicorn_command(args):
    """Build Gunicorn command with configuration."""
    cmd = ['gunicorn']

    # Use configuration file
    cmd.extend(['-c', 'gunicorn.conf.py'])

    # Override config with command-line args if provided
    if args.workers:
        os.environ['GUNICORN_WORKERS'] = str(args.workers)
        logger.info(f"Override: Workers = {args.workers}")

    if args.threads:
        os.environ['GUNICORN_THREADS'] = str(args.threads)
        logger.info(f"Override: Threads = {args.threads}")

    if args.bind:
        os.environ['GUNICORN_BIND'] = args.bind
        logger.info(f"Override: Bind = {args.bind}")

    if args.timeout:
        os.environ['GUNICORN_TIMEOUT'] = str(args.timeout)
        logger.info(f"Override: Timeout = {args.timeout}s")

    if args.reload:
        os.environ['GUNICORN_RELOAD'] = 'true'
        os.environ['GUNICORN_PRELOAD'] = 'false'
        logger.warning("⚠ Auto-reload enabled - DEVELOPMENT MODE ONLY!")

    if args.log_level:
        os.environ['GUNICORN_LOG_LEVEL'] = args.log_level
        logger.info(f"Override: Log level = {args.log_level}")

    if args.access_log:
        os.environ['GUNICORN_ACCESS_LOG_ENABLED'] = 'true'
        logger.info("Override: Access log enabled")

    if args.no_preload:
        os.environ['GUNICORN_PRELOAD'] = 'false'
        logger.info("Override: Preload disabled")

    # WSGI application
    cmd.append('main:app')

    return cmd


def main():
    """Main entry point."""
    # Print banner
    print("""
    ╔═══════════════════════════════════════════════════════════╗
    ║   AI Product Recommender API - Production Server          ║
    ║   Powered by Gunicorn WSGI Server                         ║
    ╚═══════════════════════════════════════════════════════════╝
    """)

    # Parse arguments
    args = parse_args()

    # Check requirements
    logger.info("Checking dependencies...")
    check_requirements()

    # Check environment
    logger.info("Checking environment configuration...")
    check_environment()

    # Build command
    logger.info("Building Gunicorn command...")
    cmd = build_gunicorn_command(args)

    # Display final configuration
    logger.info("="*70)
    logger.info("Starting Production Server:")
    logger.info(f"  Command: {' '.join(cmd)}")
    logger.info("="*70)
    logger.info("")
    logger.info("Press Ctrl+C to stop the server")
    logger.info("")

    # Start Gunicorn
    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        logger.info("\n\nShutting down gracefully...")
        sys.exit(0)
    except subprocess.CalledProcessError as e:
        logger.error(f"\n\nGunicorn exited with error code {e.returncode}")
        sys.exit(e.returncode)
    except Exception as e:
        logger.error(f"\n\nError starting server: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()

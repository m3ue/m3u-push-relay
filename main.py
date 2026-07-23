#!/usr/bin/env python3
"""
m3u-push-relay - Main Entry Point
Stateless APNs/FCM push relay for self-hosted m3u-editor instances.
"""

import logging
import os
import sys

import uvicorn

# Add the src directory to Python path so local modules in `src/` can be imported
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from config import settings, VERSION  # noqa: E402


def main():
    logging.basicConfig(
        level=settings.LOG_LEVEL.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info(f"Starting m3u-push-relay v{VERSION} on {settings.HOST}:{settings.PORT}")
    logger.info("=" * 60)
    logger.info(f"APNs configured: {settings.apns_configured}")
    logger.info(f"FCM configured: {settings.fcm_configured}")
    if not settings.RELAY_SHARED_SECRET:
        logger.warning("RELAY_SHARED_SECRET is not set — /push is unauthenticated!")

    uvicorn.run(
        "api:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()

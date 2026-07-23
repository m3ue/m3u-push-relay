#!/usr/bin/env python3
"""
m3u-push-relay - Main Entry Point
Stateless FCM (Firebase) push relay for self-hosted m3u-editor instances.
Handles both Android and iOS mobile push; Apple delivery is bridged by
Firebase using the APNs auth key uploaded in the Firebase console.
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
    logger.info(f"FCM configured: {settings.fcm_configured}")
    logger.info(
        f"Rate limits: {settings.RATE_LIMIT_PER_IP_PER_MINUTE}/min per IP, "
        f"{settings.RATE_LIMIT_PER_TOKEN_PER_HOUR}/hour per token"
    )

    uvicorn.run(
        "api:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
    )


if __name__ == "__main__":
    main()

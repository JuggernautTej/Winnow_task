"""
The entry point for the manifest service.

This module initializes the application, configures logging, and starts the manifest polling process.

Environment Variables:
- LOG_LEVEL : The Python logging level name (default: INFO)
- MANIFEST_URL: The URL to poll for the manifest (default: http://localhost:8000/manifest)
- DEVICE_TOKEN: The device token to use for authentication (default: test-token)
- POLL_INTERVAL: The interval in seconds between manifest polls (default: 60)
- DOWNLOAD_DIR: The directory to download files to (default: /tmp/winnow)
- STATE_FILE: The file where to persis the download state (default: /tmp/winnow/.state.json)
- REMOVE_STALE_FILES: Set to "true" to delete files removed from manifest (default: false)
"""

import logging
import os
import sys
from fetcher import Downloader
from poller import ManifestPoller
from state import StateStore

def _configure_logging(level_name: str) -> None:
    """Application configuration for logging."""
    level = getattr(logging, level_name.upper(), logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )

def main() -> None:
    """The main entry point for the manifest service."""

    log_level = os.getenv("LOG_LEVEL", "INFO")
    _configure_logging(log_level)

    logger = logging.getLogger(__name__)

    manifest_url = os.getenv(
        "MANIFEST_URL", "http://localhost:8080/v2/manifest")
    device_token = os.getenv("DEVICE_TOKEN", "test-token")
    poll_interval = int(os.getenv("POLL_INTERVAL", "60"))
    download_dir = os.environ.get("DOWNLOAD_DIR", "/tmp/winnow")
    state_file = os.environ.get("STATE_FILE", "/tmp/winnow/state.json")
    remove_stale_files = os.getenv(
        "REMOVE_STALE_FILES", "false").lower() == "true"

    logger.info("Starting manifest service...")
    logger.info("Manifest URL : %s", manifest_url)
    logger.info("Download directory : %s", download_dir)
    logger.info("Poll interval : %s", poll_interval)
    logger.info("Remove stale files : %s", remove_stale_files)

    state = StateStore(state_file=state_file)
    downloader = Downloader(download_dir=download_dir)
    poller = ManifestPoller(
        manifest_url=manifest_url,
        device_token=device_token,
        poll_interval_seconds=poll_interval,
        downloader=downloader,
        state=state,
        remove_stale_content=remove_stale_files,
    )

    poller.persistent_runner()

if __name__ == "__main__":
    main()

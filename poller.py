""" This module defines the poller functionality by
- periodically polling the manifest endpoint (HTTP GET)
- uses ETag / If-None-Match headers to avoid unnecessary processing
 unchanged manifests saving bandwidth.
- compares what is in the new manifest with what is in the local state 
to determine what content new or gone.
- Triggers downloads for new/updated items.
- Optionally removes files that have been removed from the manifest.
- Publishes MQTT notices for every change.
"""

import logging
import time
from typing import Optional

import requests

from fetcher import Downloader
from publisher import publish
from state import StateStore

logger = logging.getLogger(__name__)

class ManifestPoller:
    """
    This is a class that acts as the poller which periodically fetches
    the manifest from a remote endpoint and synchronizes with the
    local content.

    Args:
    - manifest_url: The URL of the manifest to poll.
    - poll_interval_seconds: The interval in seconds between each poll.
    - downloader: An instance of the Downloader class to handle download
      and saving files.
    - state: An instance of the StateStore class to manage the state of
    downloaded items.
    - device_token: The device authentication token sent as 
    X-Authorization-Device header when fetching the manifest.
    - remove_stale_content: If True, content items that are present in 
    the local state but not in the latest manifest will be removed and 
    a "REMOVED" message will be published for each. If False, stale 
    content will be left untouched.
    """
    def __init__(
            self,
            manifest_url: str,
            downloader: Downloader,
            state: StateStore,
            device_token: str,
            remove_stale_content: bool = False,
            poll_interval_seconds: int = 60
    ) -> None:
        self._url = manifest_url
        self._poll_interval_seconds = poll_interval_seconds
        self._downloader = downloader
        self._state = state
        self._device_token = device_token
        self._remove_stale_content = remove_stale_content
        self._manifest_etag: Optional[str] = None  
        # ETag of the last successfully fetched manifest. Starts with None.

    # Public API

    def persistent_runner(self) -> None:
        """
        Poll loop that runs indefinitely until the process is 
        terminated. It handles exceptions in the loop to ensure that a
        temporary network blip or a bad manifest doesn't crash the 
        entire service, allowing it to recover and continue polling in
        the next cycle.
        """
        logger.info("Starting manifest poller. Polling %s every %ds.",
                     self._url, self._poll_interval_seconds)
        while True:
            try:
                self._poll_once()
            except Exception as exc:
                # Log the exception but continue the loop to keep the 
                # service running. "Stale content is preferable to no 
                # content" applies here.
                logger.error("Unexpected error during manifest polling: %s", exc, exc_info=True)
            time.sleep(self._poll_interval_seconds)
    
    def poll_once(self) -> None:
        """
        Publice wrapper for the _poll_once method to allow for easier testing and manual triggering of the poller logic without having to wait for the next cycle of the persistent runner.
        """
        self._poll_once()
    
    # Private methods
    def _poll_once(self) -> None:
        """
        
        """
        manifest = self._fetch_manifest()
        if manifest is None:
            logger.info("Manifest has not changed since the last poll. Skipping processing.")
            return
        self._process_manifest(manifest)
    
    def _fetch_manifest(self) -> Optional[dict]:
        """
        Fetches the manifest from the remote endpoint.

        Returns:
            Parsed JSON dict on success (HTTP 200).
            None if the manifest hasn't changed (HTTP 304) or on error.
        """
        headers = {"X-Authorization-Device": self._device_token}
        if self._manifest_etag:
            headers["If-None-Match"] = self._manifest_etag
        try:
            response = requests.get(self._url, headers=headers, timeout=15)
        except requests.RequestException as exc:
            logger.warning("Could not reach manifest server: %s", exc)
            return None
        if response.status_code == 304:
            logger.debug("Manifest not modified (HTTP 304). Nothing to do.")
            return None
        if response.status_code == 401:
            logger.error("Device token rejected (401). Check X-Authorization-Device.")
            return None
        if response.status_code >= 500:
            logger.warning("Manifest server error (%d). Will retry later.", response.status_code)
            return None
        if response.status_code != 200:
            logger.warning("Unexpected status code %d from manifest server.", response.status_code)
            return None
        
        # Store the new ETag, to send it on to the next request.
        self._manifest_etag = response.headers.get("ETag")
        logger.debug("Received new manifest (ETag: %s).", self._manifest_etag)
        return response.json()
    
    def _process_manifest(self, manifest: dict) -> None:
        """
        Process the fetched manifest and update the local state accordingly.

        Args:
            manifest (dict): The manifest data parsed from JSON.
        """
        manifest_names: set = set()

        for content_type, section in manifest.items():
            # Skip content types that are structured unexpectedly (not a dict with "items" key)
            if not isinstance(section, dict):
                continue

            # If the whole category is temporarily unavailable, it is
            #  skipped but the exisiting files are not deleted, as the 
            # challenge manifests states "do not expire unavailable 
            # content".
            if section.get("unavailable", False):
                logger.info(
                    "Content type '%s' is marked as unavailable. Skipping.", content_type)
                # Names are still addeded to manifest_names to avoid 
                # deleting existing content that is not in the manifest 
                # but belongs to an unavailable category.
                for item in section.get("items", []):
                    if item.get('name'):
                        manifest_names.add(item['name'])
                continue

            for item in section.get("items", []):
                name = item.get("name")
                if not name:
                    continue

                manifest_names.add(name)

                # Items that are individually unavailable are skipped
                if item.get("unavailable", False):
                    logger.debug("Item '%s is marked unavailable. Skipping.", name)
                    continue
                uri = item.get("uri")
                etag = item.get("ETag", "")

                if not uri:
                    logger.warning("Item '%s' has no URI. Skipping.", name)
                    continue

                # Only download if the exact version doesn't exist.
                if self._state.has(name, etag):
                    logger.debug("Item '%s' is up to date. Skipping download.", name)
                    continue
                self._download_item(name, uri, etag)

        # Handle removals - items in the local state that are no longer in the manifest
        stale_names = self._state.all_names() - manifest_names
        for name in stale_names:
            logger.info("Item '%s' removed from manifest.", name)
            if self._remove_stale_content:
                try:
                    self._downloader.remove(name)
                except OSError as exc:
                    logger.warning("Failed to remove stale item '%s': %s", name, exc)
            self._state.remove(name)
            publish("REMOVED", name)
    
    def _download_item(self, name: str, uri: str, etag: str) -> None:
        """
        Downloads a single content item, updates the state and publishes.

        Args:
            name (str): The name of the content item.
            uri (str): The URI to download the content item from.
            etag (str): The ETag of the content item, used for caching and state management.
        """
        try:
            self._downloader.download(name, uri)
            self._state.add(name, etag)
            publish("ADDED", name)
            logger.info("Successfully processed item '%s'.", name)
        except requests.HTTPError as exc:
            logger.error("HTTP error downloading '%s': %s", name, exc)
        except requests.RequestException as exc:
            logger.error("Network error downloading '%s': %s", name, exc)
        except OSError as exc:
            logger.error("Filesytem error saving '%s': %s", name, exc)

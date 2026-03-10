"""
This module keeps track of the content downloaded to the device.

The StateStore class provides a simple interface to check if a content item with a specific name and ETag has already been downloaded, add new items to the state, and remove items from the state. The state is persisted to a local JSON file, allowing the application to maintain knowledge of previously downloaded content across restarts. This is crucial for the manifest poller to efficiently determine which content items have changed and need to be re-downloaded, thus optimizing bandwidth usage and ensuring that the device stays up-to-date with the latest content from the manifest.
"""

import json
import logging
import os
from typing import Dict

logger = logging.getLogger(__name__)

# Default path to the state file where the manifest state is stored locally.
DEFAULT_STATE_FILE_PATH = "/tmp/winnow/manifest_state.json"

class StateStore:
    """
    A simple state store that persists the downloaded items across restarts by saving the state to a local JSON file in the following format:
        {
            "icon-1.png": "zyx987etag",
            "menu-en.json": "abc123etag"
        }
    Keys are content names and values are their corresponding ETags from the manifest. This allows the poller to determine if a content item has changed since the last download by comparing ETags and avoiding unnecessary downloads.
    """

    def __init__(self, state_file: str = DEFAULT_STATE_FILE_PATH) -> None:
        self._state_file = state_file
        self._items: Dict[str, str] = {}
        self._load_state()

    # Public API

    def has(self, name: str, etag: str) -> bool:
        """
        Check if the state store has a content item with the given name and ETag.

        Args:
            name (str): The name of the content item.
            etag (str): The ETag of the content item.
        Returns:
            bool: True if the content item exists with the given ETag, False otherwise.
        """
        return self._items.get(name) == etag
    
    def add(self, name: str, etag: str) -> None:
        """
        Add a content item to the state store with the given name and ETag.

        Args:
            name (str): The name of the content item.
            etag (str): The ETag of the content item.
        """
        self._items[name] = etag
        self._save_state()

    def remove(self, name: str) -> None:
        """
        Remove a content item from the state store by name.

        Args:
            name (str): The name of the content item to remove.
        """
        if name in self._items:
            del self._items[name]
            self._save_state()
    
    def all_names(self) -> set:
        """
        Retrieves all items that are currently being tracked.
        
        Returns:            
        set: A set of all content item names currently tracked in the state store.        
        """
        return set(self._items.keys())
    
    # Private methods

    def _load_state(self) -> None:
        """
        Load the state from the JSON file. If the file does not exist, start fresh.
        """
        if not os.path.exists(self._state_file):
            logger.debug("State file %s not found, starting fresh.", self._state_file)
            return
        try:
            with open(self._state_file, "r") as f:
                self._items = json.load(f)
            logger.info("Loaded %d items from state file.", len(self._items))
        except (json.JSONDecodeError, OSError) as exc:
            # If the file is corrupted or cannot be read, log an error.
            # Worst case is to re-download.
            logger.warning("Could not read state file: %s. Starting fresh.", exc)

    def _save_state(self) -> None:
        """
        Save the current state to the JSON file.
        """
        tmp_path = self._state_file + ".tmp"
        os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
        try:
            with open(tmp_path, "w") as f:
                json.dump(self._items, f, indent=2)
            os.replace(tmp_path, self._state_file)
            logger.debug("Saved state with %d items to file.", len(self._items))
        except OSError as exc:
            logger.error("Failed to save state to file: %s", exc)

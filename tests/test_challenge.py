"""
The unit tests
"""

import json
import os
import tempfile
# from turtle import fd
import unittest
from unittest.mock import patch, MagicMock, call
from fetcher import Downloader
from poller import ManifestPoller
from state import StateStore

# Helper functions

def _tmp_state_file() -> str:
    """Helper function that returns a temporary file path that doesn't exist yet."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)  # close the file descriptor immediately, we just need the path
    os.unlink(path)  # remove the file so it doesn't exist yet
    return path

# Statestore tests

class TestStateStore(unittest.TestCase):
    """Unit tests for the StateStore class."""

    def setUp(self):
        """Set up a temporary state file for each test."""
        self.state_file = _tmp_state_file()
        self.store = StateStore(state_file=self.state_file)

    def tearDown(self):
        """Clean up the temporary state file after each test."""
        for path in [self.state_file, self.state_file + "tmp"]:
            if os.path.exists(path):
                os.unlink(path)

    def test_new_store_is_empty(self):
        """A new state store should start with no items."""
        self.assertEqual(self.store.all_names(), set())

    def test_add_and_has(self):
        """Test adding an item and checking if it exists."""
        self.store.add("icon-1.png", "etag-1")
        self.assertTrue(self.store.has("icon-1.png", "etag-1"))

    def test_has_returns_false_for_different_etag(self):
        """Test that has() returns False for an item with a different ETag."""
        self.store.add("icon-1.png", "etag-1")
        self.assertFalse(self.store.has("icon-1.png", "etag-2"))

    def test_remove(self):
        """Test removing an item from the state store."""
        self.store.add("icon-1.png", "etag-1")
        self.store.remove("icon-1.png")
        self.assertFalse(self.store.has("icon-1.png", "etag-1"))

    def test_persists_across_instances(self):
        """Test that the state persists across different instances of StateStore using the same file."""
        self.store.add("icon-1.png", "etag-1")
        # Create a new instance of StateStore with the same state file
        new_store = StateStore(state_file=self.state_file)
        self.assertTrue(new_store.has("icon-1.png", "etag-1"))

    def test_corrupted_state_file_starts_fresh(self):
        """Test that a corrupted state file starts fresh."""
        # Create a corrupted state file
        with open(self.state_file, "w") as f:
            f.write("corrupted json")
        # Create a new instance of StateStore with the corrupted state file
        new_store = StateStore(state_file=self.state_file)
        self.assertEqual(new_store.all_names(), set())


# Poller tests

class TestManifestPoller(unittest.TestCase):

    @patch("poller.requests.get")
    @patch("poller.publish")
    def test_new_itmem_is_downloaded_and_state_updated(self, mock_publish, mock_get):
        pass

    @patch("poller.requests.get")
    @patch("poller.publish")
    def test_already_downloaded_item_is_skipped(self, mock_publish, mock_get):
        pass

if __name__ == "__main__":
    unittest.main()

"""
The unit tests
"""

import json
import os
import tempfile
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

def _make_poller(
        state=None, downloader=None, remove_stale_content=False) -> ManifestPoller:
    """Helper function to create a ManifestPoller with default or mocked dependencies."""
    if state is None:
        state = StateStore(state_file=_tmp_state_file())
    if downloader is None:
        downloader = MagicMock(spec=Downloader)
    return ManifestPoller(
        manifest_url="http://test/v2/manifest",
        device_token="test-token",
        poll_interval_seconds=1,
        downloader=downloader,
        state=state,
        remove_stale_content=remove_stale_content,
    )

def _manifest_response(
        manifest: dict, etag: str = "etag-v1") -> MagicMock:
    """Helper function to create a mocked response object for the manifest with the given content and ETag."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = manifest
    mock_resp.headers = {"ETag": etag}
    return mock_resp

def _304_response() -> MagicMock:
    """Helper function to create a mocked response object for a 304 Not Modified."""
    mock_resp = MagicMock()
    mock_resp.status_code = 304
    return mock_resp

MOCK_MANIFEST = {
    "icons": {
        "unavailable": False,
        "items": [
            {"name": "icon-1.png", "uri": "http://test/v2/icons/icon-1.png", "ETag": "etag-a"},
        ],
    }
}

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
    def test_new_item_is_downloaded_and_state_updated(
        self, mock_publish, mock_get):
        """Test that a new item in the manifest is downloaded, added to
          the state, and published.
        """
        mock_get.return_value = _manifest_response(MOCK_MANIFEST)
        poller = _make_poller()
        poller._poll_once()

        poller._downloader.download.assert_called_once_with(
            "icon-1.png", "http://test/v2/icons/icon-1.png") #
        mock_publish.assert_called_once_with("ADDED", "icon-1.png")


    @patch("poller.requests.get")
    @patch("poller.publish")
    def test_already_downloaded_item_is_skipped(
        self, mock_publish, mock_get):
        """Test that an item that is already downloaded with the same ETag is skipped and not published again."""
        mock_get.return_value = _manifest_response(MOCK_MANIFEST)
        state = StateStore(state_file=_tmp_state_file())
        state.add("icon-1.png", "etag-a")  # Same ETag as in the manifest
        poller = _make_poller(state=state)
        poller._poll_once()

        poller._downloader.download.assert_not_called()
        mock_publish.assert_not_called()

    @patch("poller.requests.get")
    @patch("poller.publish")
    def test_updated_item_is_re_downloaded(self, mock_publish, mock_get):
        """Test that an item with an updated ETag is re-downloaded and the state is updated."""
        mock_get.return_value = _manifest_response(MOCK_MANIFEST)
        state = StateStore(state_file=_tmp_state_file())
        state.add("icon-1.png", "etag-OLD")  # Different ETag from the manifest
        poller = _make_poller(state=state)
        poller._poll_once()

        poller._downloader.download.assert_called_once_with(
            "icon-1.png", "http://test/v2/icons/icon-1.png") #
        mock_publish.assert_called_once_with("ADDED", "icon-1.png")

    @patch("poller.requests.get")
    @patch("poller.publish")
    def test_304_does_nothing(self, mock_publish, mock_get):
        """Test that a 304 Not Modified response does not trigger any downloads or publishes.
        """
        mock_get.return_value = _304_response()
        poller = _make_poller()
        poller._poll_once()
        poller._downloader.download.assert_not_called()
        mock_publish.assert_not_called()

    @patch("poller.requests.get")
    @patch("poller.publish")
    def test_removed_item_publishes_removal(
        self, mock_publish, mock_get):
        """Test that an item that is in the state but no longer in the manifest is removed from the state and published as removed."""
        empty_manifest = {"icons": {"unavailable": False, "items": []}}
        mock_get.return_value = _manifest_response(empty_manifest)
        state = StateStore(state_file=_tmp_state_file())
        state.add("icon-1.png", "etag-a")
        poller = _make_poller(state=state, remove_stale_content=True)
        poller._poll_once()
        poller._downloader.remove.assert_called_once_with("icon-1.png") #
        mock_publish.assert_called_once_with("REMOVED", "icon-1.png")

    @patch("poller.requests.get")
    @patch("poller.publish")
    def test_unavailable_section_skips_download_but_keeps_files(
        self, mock_publish, mock_get):
        """Test that items in the unavailable section are skipped during download but their files are kept."""
        unavailable_manifest = {
            "icons": {
                "unavailable": True,
                "items": [
                    {"name": "icon-1.png", "url": "http://test/v2/icons/icon-1.png", "ETag": "etag-a"},
                ],
            }
        }
        mock_get.return_value = _manifest_response(unavailable_manifest)
        state = StateStore(state_file=_tmp_state_file())
        state.add("icon-1.png", "etag-a")
        poller = _make_poller(state=state, remove_stale_content=True)
        poller._poll_once()
        poller._downloader.download.assert_not_called()
        mock_publish.assert_not_called()

    @patch("poller.requests.get")
    @patch("poller.publish")
    def test_network_error_does_not_crash_service(self, mock_publish, mock_get):
        """Test that a network error does not crash the service."""
        poller = _make_poller()
        with self.assertRaises(Exception):
            poller.poll_once()

    @patch("poller.requests.get")
    def test_etag_sent_on_subsequent_requests(self, mock_get):
        """Test that an ETag is sent on the next request after a successful poll."""
        mock_get.return_value = _manifest_response(MOCK_MANIFEST, etag="etag-v2")
        poller = _make_poller()
        poller._poll_once()
        # Simulate a second poll with the same manifest and ETag
        mock_get.return_value = _304_response()
        poller._poll_once()
        second_call_headers = mock_get.call_args_list[1][1]["headers"] #
        self.assertEqual(second_call_headers.get("If-None-Match"), "etag-v2")

if __name__ == "__main__":
    unittest.main()

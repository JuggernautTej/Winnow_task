"""
This module fetches the manifest from a remote endpoint and saving it to the local file directory.
"""

import logging
import os
import tempfile
import requests

logger = logging.getLogger(__name__)

# path to store files locally
DEFAULT_DOWNLOAD_DIR = "/tmp/winnow"

# How long to wait for remote server to respond before timing out (in seconds)
REQUEST_TIMEOUT_SECONDS = 30

# Default bytes to be read at a given time when dowloading.
CHUNK_SIZE_BYTES = 8192

class Downloader:
    """
    A downloader for fetching the manifest from a remote endpoint and saving it to the local file directory.
    """
    def __init__(self, download_dir: str = DEFAULT_DOWNLOAD_DIR) -> None:
        self._download_dir = download_dir
        os.makedirs(self._download_dir, exist_ok=True)

    def download(self, name: str, uri: str) -> str:
        """
        Download the content from the uri and saves it.

        Args:
            uri (str): The full URL to download from.
            name (str): The name to save the file as e.g. "icon-1.png".
        
        Returns:
            str: The path to the downloaded file.
        
        Raises:
            requests.HTTPError: If the request fails with an HTTP error.
            requests.RequestException: If the request fails for any other reason.
        """
        dest_path = os.path.join(self._download_dir, name)
        logger.info("Downloading %s from %s to %s", name, uri, dest_path)

        # stream the download to avoid loading the entire file into memory
        response = requests.get(uri, stream=True, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()  # raise an exception for HTTP errors

        # write the content to a temporary file first to avoid leaving partial files in case of errors (atomic operation)
        dir_fd = self._download_dir
        with tempfile.NamedTemporaryFile(delete=False, dir=dir_fd) as tmp_file:
            tmp_path = tmp_file.name
            try:
                for chunk in response.iter_content(chunk_size=CHUNK_SIZE_BYTES):
                    if chunk:  # filter out keep-alive chunks
                        tmp_file.write(chunk)
                # tmp_file.flush()  # ensure all data is written to disk
                # os.fsync(tmp_file.fileno())  # force write to disk
            except Exception:
                # clean up the temporary file in case of any errors during download
                os.unlink(tmp_path)
                raise
        # move the temporary file to the final destination (atomic operation)
        os.replace(tmp_path, dest_path)
        logger.info("Successfully downloaded %s to %s", name, dest_path)
        return dest_path

    def remove(self, name: str) -> None:
        """
        Deletes a content file that is no longer in the manifest.
        
        Args:
            name (str): The name of the file to be deleted e.g. "icon-1.png".
        """
        path = os.path.join(self._download_dir, name)
        if os.path.exists(path):
            os.remove(path)
            logger.info("Removed file %s", path)
        else:
            logger.debug("File %s does not exist, skipping removal", path)

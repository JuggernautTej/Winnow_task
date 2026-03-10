""" This module defines the poller functionality by
- periodically polling the manifest endpoint
- uses ETag / If-None-Match headers to avoid unnecessary processing unchanged manifests saving bandwidth.
"""

import logging
import time
from typing import Optional

import requests

from fetcher import Downloader
from publisher import Publisher
from state import StateStore

logger = logging.getLogger(__name__)

class ManifestPoller:
    """
    A poller for periodically fetching the manifest from a remote endpoint and synchronising with local content.
    """
    pass

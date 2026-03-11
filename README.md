
# Winnow Challenge Data Sync Service

  

A lightweight service that runs on Winnow IoT kitchen devices to keep locally cached content in sync with the cloud manifest.

---
  ## What it does


1.  **Polls** the manifest endpoint every N seconds (default is set at 60 seconds).

2.  **Downloads** any new or updated content files to `/tmp/winnow`.

3.  **Publishes** dummy MQTT events to `stdout` for every change:

```

Publishing {"action": "ADDED", "key": "icon-1.png"}

Publishing {"action": "REMOVED", "key": "old-icon.png"}

```

4.  **Persists** its download state across restarts so it never re-downloads

unchanged content.

  

---

  

## Project structure

  

```

Winnow-Task/

├── main.py # Entry point + configuration via env variables

├── poller.py # Core polling and diffing logic

├── fetcher.py # HTTP file downloader (atomic writes)

├── state.py # Persistent state (JSON file on disk)

├── publisher.py # Dummy MQTT publisher (stdout)

├── stub_server.py # Fake manifest server for local development

├── tests/

│ └── test_challenge.py

├── requirements.txt

└── TODO.md

```

  

---

  

## Running locally

  

### 1. Install dependencies

  

```bash

python3  -m  venv  venv

source  venv/bin/activate  # Windows: venv\Scripts\activate

pip  install  -r  requirements.txt

```

  

### 2. Start the stub manifest server (in one terminal)

  

```bash

python  stub_server.py

# → Stub manifest server running at http://localhost:8080

```

  

### 3. Start the sync service (in another terminal)

  

```bash

source  venv/bin/activate

python  main.py

```

  

You should see output like:

  

```

2024-01-01T12:00:00 INFO __main__ Starting manifest service...

2024-01-01T12:00:00 INFO __main__ Manifest URL : http://localhost:8080/v2/manifest

...

Publishing {"action": "ADDED", "key": "menu-en.json"}

Publishing {"action": "ADDED", "key": "menu-fr.json"}

Publishing {"action": "ADDED", "key": "icon-1.png"}

Publishing {"action": "ADDED", "key": "icon-2.png"}

```

  

Downloaded files appear in `/tmp/winnow/`.

  

---

  



  

## Running the tests

  

```bash

source  venv/bin/activate

python  -m  pytest  tests/  -v

```

  

---

  

## Configuration

  

All settings are read from environment variables:

  

| Variable | Default | Description |

|-----------------|----------------------------------------|--------------------------------------------------|

| `MANIFEST_URL` | `http://localhost:8080/v2/manifest` | URL of the manifest endpoint |

| `DEVICE_TOKEN` | `test-token` | Device auth token (`X-Authorization-Device`) |

| `POLL_INTERVAL` | `60` | Seconds between manifest polls |

| `DOWNLOAD_DIR` | `/tmp/winnow` | Directory for downloaded files |

| `STATE_FILE` | `/tmp/winnow/state.json` | Path for persisted download state |

| `REMOVE_STALE` | `false` | Delete files removed from manifest (`true/false`)|

| `LOG_LEVEL` | `INFO` | Python log level (`DEBUG`, `INFO`, `WARNING`, …) |

  

Example:

  

```bash

POLL_INTERVAL=10  DEVICE_TOKEN=my-device-xyz  python  main.py

```

  

---

  

## Design decisions

  

### Why ETags?

Sending `If-None-Match` with every poll means the server can reply `304 Not 
Modified` instead of sending the full manifest body. For thousands of devices polling frequently, this drastically reduces bandwidth.

  

### Why atomic writes?

Both the downloader and the state store write to a temporary file and then rename it into place. Rename is atomic on POSIX systems, so other services always see either the old complete file or the new complete file — never a half-written one, even if the device loses power mid-write.

  

### Why not delete stale content by default?

The spec says "stale content is preferable to no content". If the manifest server has a bad deployment and temporarily removes an item, we don't want to delete the local copy immediately. `REMOVE_STALE=true` is opt-in.

  

### Why catch all exceptions in `run_forever`?

Devices are in kitchens worldwide, often behind unreliable networks. A transient DNS failure, a cloud hiccup, or a malformed manifest response should never crash the service permanently.
    

## Author

**Jimi Tej**  
Milton Keynes, UK  
Passionate about backend development, sustainability, and football
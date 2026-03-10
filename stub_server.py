"""
A miniature Flask web server that assumes to be the cloud manifest service. It serves a static manifest and files for testing the manifest poller and downloader logic in the main application.

Usage:
    python stub_server.py

The server listens pn http://localhost:8080 by default. 
It serves a manifest with two content types (menus, icons).
It also hosts the actual "content files" so the downloader can fetch them.

"""

import hashlib
import io
import time

from flask import Flask, Response, jsonify, request, send_file

app = Flask(__name__)

# Configurable manifest data for testing purposes
MANIFEST = {
    "menus": {
        "unavailable": False,
        "items": [
            {
                "name": "menu-en.json",
                "uri": "http://localhost:8080/content/menu-en.json",
                "expiresAt": "2099-12-31T23:59:59Z",
                "ETag": "etag-menu-en-v1",
                "unavailable": False,
            },
            {
                "name": "menu-fr.json",
                "uri": "http://localhost:8080/content/menu-fr.json",
                "expiresAt": "2099-12-31T23:59:59Z",
                "ETag": "etag-menu-fr-v1",
                "unavailable": False,
            },
        ],
    },
    "icons": {
        "unavailable": False,
        "items": [
            {
                "name": "icon-1.png",
                "uri": "http://localhost:8080/content/icon-1.png",
                "expiresAt": "2099-12-31T23:59:59Z",
                "ETag": "etag-icon-1-v1",
                "unavailable": False,
            },
            {
                "name": "icon-2.png",
                "uri": "http://localhost:8080/content/icon-2.png",
                "expiresAt": "2099-12-31T23:59:59Z",
                "ETag": "etag-icon-2-v1",
                "unavailable": False,
            }
        ],
    },
}

def _compute_manifest_etag() -> str:
    import json
    raw = json.dumps(MANIFEST, sort_keys=True).encode("utf-8")
    return hashlib.md5(raw).hexdigest()

MANIFEST_ETAG = _compute_manifest_etag()

# Dummy file contents served when the downloader requests a file
CONTENT_FILES = {
    "menu-en.json": b'{"items": ["Salad", "Soup", "Pasta"]}',
    "menu-fr.json": b'{"items": ["Salade", "Soupe", "P\xc3\xa2tes"]}',
    "icon-1.png": b"\x89PNG\r\n\x1a\n" + b"\x00" * 20,  # Not a real PNG, just placeholder bytes
    "icon-2.png": b"\x89PNG\r\n\x1a\n" * 20,
}

# Routes

@app.get("/v2/manifest")
def get_manifest():
    """
    Returns the manifest, respecting If-None-Match for cache validation.
    Also checks X-Authorization-Device for a non-empty token.
    """
    token = request.headers.get("X-Authorization-Device", "")
    if not token:
        return jsonify({"errors": [{"key": "auth", "message": "Missing token", "source": "stub"}]}), 401
    
    client_etag = request.headers.get("If-None-Match", "")
    if client_etag == MANIFEST_ETAG:
        return Response(status=304)
    
    response = jsonify(MANIFEST)
    response.headers["ETag"] = MANIFEST_ETAG
    return response

@app.get("/content/<filename>")
def get_content(filename: str):
    """Serve a content file by name."""
    data = CONTENT_FILES.get(filename)
    if data is None:
        return jsonify({"errors": [{"key": "file", "message": "File not found", "source": "stub"}]}), 404

    # 
    content_type = "application/json" if filename.endswith(".json") else "image/png"
    return Response(data, content_type=content_type)

# Entry point

if __name__ == "__main__":
    print("Stub manifest server running at http://localhost:8080")
    print("Manifest Etag:", MANIFEST_ETAG)
    print("Edit MANIFEST in this file to simulate changes.")
    app.run(host="0.0.0.0", port=8080, debug=True)

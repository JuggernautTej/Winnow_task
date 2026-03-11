# TODO - Future Improvements

### 1. Implement Real MQTT Publisher
Replace `publisher.py`'s `print()` call with a proper MQTT client
The topic structure could be `winnow/content/<action>/<name>` so
subscribers can filter by content type.

### 2. Per-item Etag
When re-downloading a known item we could send the stored ETag as
`If-None-Match` to the content CDN so it can also return 304 and save
bandwidth.

### 3. Exponential back-off on errors
Currently the poller sleeps a fixed `POLL_INTERVAL` after every failure.
Under a cloud outage this means thousands of devices hammer the server the moment it recovers. Addressing this will be essential to reduce this swamping effect.


"""
This module is the dummy MQTT publisher.
"""
import json

def publish(action: str, key: str) -> None:
    """
    Publish a message notifying that a content item has been added or removed.

    Args:
        action (str): The action performed on the content item, either "ADDED" or "REMOVED".
        key (str): The filename or identifier of the content item. e.g. "icon-1.png".
    Sample Output:
        Publishing {"action": "ADDED", "key": "icon-1.png"}
    """
    payload = json.dumps({"action": action, "key": key})
    print(f"Publishing {payload}")


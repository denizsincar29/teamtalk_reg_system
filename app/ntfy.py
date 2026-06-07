"""ntfy push notification helper.

Uses only stdlib urllib so it works both in the main FastAPI process
and in the teamtalk worker subprocess without extra dependencies.

Configure via .env:
    NTFY_URL=https://ntfy.sh/mytopic          # full URL (takes precedence)
  OR
    NTFY_SERVER=https://ntfy.sh
    NTFY_TOPIC=mytopic

If NTFY_URL is empty, all calls are silent no-ops.
"""

import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger("teamtalk.ntfy")


def notify(title: str, message: str, ntfy_url: str, tags: list[str] | None = None, priority: int = 3) -> None:
    """Send a push notification via ntfy (blocking, fire-and-forget).

    Args:
        title:    Notification title.
        message:  Notification body.
        ntfy_url: Full ntfy topic URL, e.g. https://ntfy.sh/mytopic.
        tags:     Optional list of emoji tag names (e.g. ["bell", "tada"]).
        priority: ntfy priority 1-5 (default 3 = default).
    """
    if not ntfy_url:
        return

    payload = {
        "title": title,
        "message": message,
        "priority": priority,
    }
    if tags:
        payload["tags"] = tags

    try:
        data = json.dumps(payload).encode()
        req = Request(
            ntfy_url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(req, timeout=5):
            pass
    except URLError as e:
        logger.warning("ntfy notification failed: %s", e)
    except Exception as e:
        logger.warning("ntfy notification error: %s", e)

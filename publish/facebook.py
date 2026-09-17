import os
import requests

META_ACCESS_TOKEN  = os.getenv("META_ACCESS_TOKEN")
META_PAGE_ID       = os.getenv("META_PAGE_ID")
META_GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v26.0")
GRAPH_BASE    = f"https://graph.facebook.com/{META_GRAPH_VERSION}"


def publish_to_facebook(message, target_id=None, link=None):
    if not META_ACCESS_TOKEN:
        raise RuntimeError("META_ACCESS_TOKEN is not configured")

    target_id = target_id or META_PAGE_ID
    if not target_id:
        raise RuntimeError("META_PAGE_ID is not configured and no target_id was passed")

    url = f"{GRAPH_BASE}/{target_id}/feed"

    payload = {
        "message": message,
        "access_token": META_ACCESS_TOKEN,
    }
    if link:
        payload["link"] = link

    response = requests.post(url, data=payload, timeout=15)

    if not response.ok:
        err = _extract_error(response)
        raise RuntimeError(f"Facebook publish failed: {err}")

    result = response.json()
    if "id" not in result:
        raise RuntimeError(f"Facebook publish succeeded without post ID: {result}")

    return {
        "success": True,
        "platform": "facebook",
        "target_id": target_id,
        "post_id": result["id"],
        "response": result,
    }


def _extract_error(response):
    """Pull Meta's actual error message out of a failed response."""
    try:
        body = response.json()
        err = body.get("error", {})
        return (
            f"[{response.status_code}] "
            f"{err.get('type', 'Unknown')} "
            f"(code {err.get('code', '?')}): "
            f"{err.get('message', response.text)}"
        )
    except ValueError:
        return f"[{response.status_code}] {response.text}"
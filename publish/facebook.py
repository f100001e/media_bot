import os
import requests

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v26.0")


def publish_to_facebook(message, target_id, link=None):
    if not ACCESS_TOKEN:
        raise RuntimeError("META_ACCESS_TOKEN is not configured")

    if not target_id:
        raise ValueError("Facebook target_id is required")

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/{target_id}/feed"
    )

    payload = {
        "message": message,
        "access_token": ACCESS_TOKEN
    }

    if link:
        payload["link"] = link

    try:
        response = requests.post(
            url,
            data=payload,
            timeout=15
        )

        response.raise_for_status()
        result = response.json()

        if "id" not in result:
            raise RuntimeError(
                f"Facebook publish succeeded without post ID: {result}"
            )

        return {
            "success": True,
            "platform": "facebook",
            "target_id": target_id,
            "post_id": result["id"],
            "response": result
        }

    except requests.RequestException as exc:
        raise RuntimeError(
            f"Facebook publish request failed: {exc}"
        ) from exc
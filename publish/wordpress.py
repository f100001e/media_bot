import os
import requests


WP_IG_ENDPOINT = os.getenv(
    "WP_IG_ENDPOINT",
    "https://www.presspassla.com/wp-json/media-bot/v1/instagram-item",
)

WP_SHARED_SECRET = os.getenv(
    "WP_SHARED_SECRET"
)


def push_instagram_item(
    title,
    article_url,
    image_url,
    caption,
    instagram_url,
    published_at=None,
):
    """
    Push a successfully published Instagram article
    to the PressPassLA WordPress landing-page endpoint.
    """

    if not WP_IG_ENDPOINT:
        raise RuntimeError(
            "WP_IG_ENDPOINT is not configured"
        )

    payload = {
        "title": title,
        "article_url": article_url,
        "image_url": image_url,
        "caption": caption,
        "instagram_url": instagram_url,
        "published_at": published_at,
    }

    headers = {
        "Content-Type": "application/json",
    }

    if WP_SHARED_SECRET:
        headers[
            "X-Media-Bot-Secret"
        ] = WP_SHARED_SECRET

    response = requests.post(
        WP_IG_ENDPOINT,
        json=payload,
        headers=headers,
        timeout=20,
    )

    if not response.ok:
        raise RuntimeError(
            "WordPress push failed: "
            f"[{response.status_code}] "
            f"{response.text}"
        )

    try:
        return response.json()

    except ValueError:
        return {
            "success": True,
            "response": response.text,
        }
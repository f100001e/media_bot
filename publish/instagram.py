import os
import requests


IG_ACCESS_TOKEN = os.getenv("IG_ACCESS_TOKEN")
IG_USER_ID = os.getenv("IG_USER_ID")
IG_GRAPH_VERSION = os.getenv(
    "IG_GRAPH_VERSION",
    "v26.0",
)

IG_GRAPH_BASE = (
    f"https://graph.instagram.com/{IG_GRAPH_VERSION}"
)

IG_LANDING_URL = os.getenv(
    "IG_LANDING_URL",
    "https://presspassla.com/ig/",
)


def publish_to_instagram(
    image_url,
    caption,
    landing_url=None,
    ig_user_id=None,
):
    """
    Publish an image post to Instagram.

    image_url must be publicly accessible by Meta.
    """

    if not IG_ACCESS_TOKEN:
        raise RuntimeError(
            "IG_ACCESS_TOKEN is not configured"
        )

    ig_user_id = ig_user_id or IG_USER_ID

    if not ig_user_id:
        raise RuntimeError(
            "IG_USER_ID is not configured"
        )

    if not image_url:
        raise ValueError(
            "image_url is required for Instagram publishing"
        )

    if not caption:
        raise ValueError(
            "caption is required for Instagram publishing"
        )

    landing_url = landing_url or IG_LANDING_URL

    full_caption = (
        f"{caption}\n\n{landing_url}"
        if landing_url
        else caption
    )

    # -------------------------------------------------
    # Step 1: create media container
    # -------------------------------------------------

    create_response = requests.post(
        f"{IG_GRAPH_BASE}/{ig_user_id}/media",
        data={
            "image_url": image_url,
            "caption": full_caption,
            "access_token": IG_ACCESS_TOKEN,
        },
        timeout=30,
    )

    if not create_response.ok:
        raise RuntimeError(
            "IG media container failed: "
            f"{_extract_error(create_response)}"
        )

    creation_id = create_response.json().get("id")

    if not creation_id:
        raise RuntimeError(
            "Instagram did not return a creation ID: "
            f"{create_response.json()}"
        )

    # -------------------------------------------------
    # Step 2: publish media container
    # -------------------------------------------------

    publish_response = requests.post(
        f"{IG_GRAPH_BASE}/{ig_user_id}/media_publish",
        data={
            "creation_id": creation_id,
            "access_token": IG_ACCESS_TOKEN,
        },
        timeout=30,
    )

    if not publish_response.ok:
        raise RuntimeError(
            "IG publish failed: "
            f"{_extract_error(publish_response)}"
        )

    post_id = publish_response.json().get("id")

    if not post_id:
        raise RuntimeError(
            "Instagram did not return a post ID: "
            f"{publish_response.json()}"
        )

    # -------------------------------------------------
    # Step 3: fetch published permalink
    # -------------------------------------------------

    post_url = None

    permalink_response = requests.get(
        f"{IG_GRAPH_BASE}/{post_id}",
        params={
            "fields": "id,permalink",
            "access_token": IG_ACCESS_TOKEN,
        },
        timeout=15,
    )

    if permalink_response.ok:
        post_url = (
            permalink_response
            .json()
            .get("permalink")
        )

    # -------------------------------------------------
    # Return normalized result
    # -------------------------------------------------

    return {
        "success": True,
        "platform": "instagram",
        "action": "publish_post",
        "account_id": ig_user_id,
        "creation_id": creation_id,
        "post_id": post_id,
        "post_url": post_url,
        "image_url": image_url,
        "landing_url": landing_url,
    }


def reply_to_instagram_comment(
    comment_id,
    message,
):
    """Reply to an existing Instagram comment."""

    if not IG_ACCESS_TOKEN:
        raise RuntimeError(
            "IG_ACCESS_TOKEN is not configured"
        )

    if not comment_id:
        raise ValueError(
            "comment_id is required"
        )

    if not message:
        raise ValueError(
            "message is required"
        )

    response = requests.post(
        f"{IG_GRAPH_BASE}/{comment_id}/replies",
        data={
            "message": message,
            "access_token": IG_ACCESS_TOKEN,
        },
        timeout=15,
    )

    if not response.ok:
        raise RuntimeError(
            "IG comment reply failed: "
            f"{_extract_error(response)}"
        )

    result = response.json()

    return {
        "success": True,
        "platform": "instagram",
        "action": "reply_comment",
        "comment_id": comment_id,
        "post_id": result.get("id"),
        "response": result,
    }


def _extract_error(response):
    """Pull Meta's actual error message from a failed response."""

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
        return (
            f"[{response.status_code}] "
            f"{response.text}"
        )
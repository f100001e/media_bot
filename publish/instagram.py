import os
import requests

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
IG_USER_ID = os.getenv("INSTAGRAM_USER_ID")
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v26.0")
IG_LANDING_URL = "https://presspassla.com/ig/"


def publish_to_instagram(
    image_url,
    caption,
    landing_url=None,
    ig_user_id=None
):
    """
    Publish an image post to Instagram.

    image_url must be publicly accessible by Meta.
    """

    if not ACCESS_TOKEN:
        raise RuntimeError("META_ACCESS_TOKEN is not configured")

    ig_user_id = ig_user_id or IG_USER_ID

    if not ig_user_id:
        raise RuntimeError("INSTAGRAM_USER_ID is not configured")

    landing_url = landing_url or IG_LANDING_URL

    # Add the article/landing destination to the caption
    full_caption = f"{caption}\n\n{landing_url}"

    # Step 1: Create media container
    create_url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/{ig_user_id}/media"
    )

    create_response = requests.post(
        create_url,
        data={
            "image_url": image_url,
            "caption": full_caption,
            "access_token": ACCESS_TOKEN
        },
        timeout=30
    )

    create_response.raise_for_status()
    create_result = create_response.json()

    creation_id = create_result.get("id")

    if not creation_id:
        raise RuntimeError(
            f"Instagram did not return a creation ID: "
            f"{create_result}"
        )

    # Step 2: Publish media container
    publish_url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/{ig_user_id}/media_publish"
    )

    publish_response = requests.post(
        publish_url,
        data={
            "creation_id": creation_id,
            "access_token": ACCESS_TOKEN
        },
        timeout=30
    )

    publish_response.raise_for_status()
    publish_result = publish_response.json()

    post_id = publish_result.get("id")

    if not post_id:
        raise RuntimeError(
            f"Instagram did not return a post ID: "
            f"{publish_result}"
        )

    return {
        "success": True,
        "platform": "instagram",
        "action": "publish_post",
        "account_id": ig_user_id,
        "creation_id": creation_id,
        "post_id": post_id,
        "image_url": image_url,
        "landing_url": landing_url
    }


def reply_to_instagram_comment(comment_id, message):
    """
    Reply to an existing Instagram comment.
    """

    if not ACCESS_TOKEN:
        raise RuntimeError("META_ACCESS_TOKEN is not configured")

    url = (
        f"https://graph.facebook.com/"
        f"{GRAPH_VERSION}/{comment_id}/replies"
    )

    response = requests.post(
        url,
        data={
            "message": message,
            "access_token": ACCESS_TOKEN
        },
        timeout=15
    )

    response.raise_for_status()
    result = response.json()

    return {
        "success": True,
        "platform": "instagram",
        "action": "reply_comment",
        "comment_id": comment_id,
        "response": result
    }
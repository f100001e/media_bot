import os

from redis import Redis
from rq import Queue, Retry

from models.db import SessionLocal, Draft, Published

from publish.facebook import publish_to_facebook
from publish.instagram import (
    publish_to_instagram,
    reply_to_instagram_comment
)
from publish.reddit import publish_to_reddit


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

REDDIT_ENABLED = os.getenv(
    "REDDIT_ENABLED",
    "false"
).lower() == "true"

redis_conn = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT
)

queue = Queue(
    "publisher",
    connection=redis_conn
)


def publish_job(draft_id, platform, params):
    db = SessionLocal()

    try:
        draft = (
            db.query(Draft)
            .filter(Draft.id == draft_id)
            .first()
        )

        if not draft:
            raise ValueError(
                f"Draft {draft_id} not found"
            )

        draft.status = "publishing"
        db.commit()

        action = params.get(
            "action",
            "publish_post"
        )

        # Facebook
        if platform == "facebook":

            result = publish_to_facebook(
                message=params.get("message"),
                target_id=params.get("target_id"),
                link=params.get("link")
            )

        # Reddit
        elif platform == "reddit":

            if not REDDIT_ENABLED:
                raise RuntimeError(
                    "Reddit publishing is disabled"
                )

            result = publish_to_reddit(
                title=params.get("title"),
                selftext=params.get("selftext"),
                subreddit=params.get("subreddit")
            )

        # Instagram
        elif platform == "instagram":

            if action == "publish_post":

                result = publish_to_instagram(
                    image_url=params.get("image_url"),
                    caption=params.get("caption"),
                    ig_user_id=params.get("ig_user_id")
                )

            elif action == "reply_comment":

                result = reply_to_instagram_comment(
                    comment_id=params.get("comment_id"),
                    message=params.get("message")
                )

            else:
                raise ValueError(
                    f"Unknown Instagram action: {action}"
                )

        else:
            raise ValueError(
                f"Unknown platform: {platform}"
            )

        # Successful publish
        post_id = None

        if isinstance(result, dict):
            post_id = (
                result.get("post_id")
                or result.get("id")
            )

        published = Published(
            draft_id=draft.id,
            platform=platform,
            target=draft.target,
            post_id=post_id
        )

        db.add(published)

        draft.status = "published"

        db.commit()

        return result

    except Exception:
        db.rollback()

        draft = (
            db.query(Draft)
            .filter(Draft.id == draft_id)
            .first()
        )

        if draft:
            draft.status = "failed"
            db.commit()

        # IMPORTANT:
        # re-raise so RQ knows the job failed
        # and Retry(max=3...) can actually work.
        raise

    finally:
        db.close()


def enqueue_publish(
    draft_id,
    platform,
    params
):
    job = queue.enqueue(
        publish_job,
        draft_id,
        platform,
        params,
        retry=Retry(
            max=3,
            interval=60
        )
    )

    print(
        f"Enqueued job {job.id} "
        f"for draft {draft_id} "
        f"on {platform}"
    )

    return job.id
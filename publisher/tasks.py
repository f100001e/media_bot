import os

from redis import Redis
from rq import Queue, Retry

from models.db import SessionLocal, Draft, Published

from publish.facebook import publish_to_facebook
from publish.instagram import (
    publish_to_instagram,
    reply_to_instagram_comment,
)
from publish.reddit import publish_to_reddit


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

REDDIT_ENABLED = (
    os.getenv("REDDIT_ENABLED", "false").lower() == "true"
)

redis_conn = Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
)

queue = Queue(
    "publisher",
    connection=redis_conn,
)


def publish_job(draft_id, platform, params):
    db = SessionLocal()
    draft = None

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

        # Determine action.
        #
        # Instagram comment replies can be inferred from comment_id,
        # which also keeps older queued jobs from exploding if they
        # don't explicitly contain action="reply_comment".
        if platform == "instagram":
            if params.get("action"):
                action = params["action"]
            elif params.get("comment_id"):
                action = "reply_comment"
            else:
                action = "publish_post"
        else:
            action = params.get(
                "action",
                "publish_post",
            )

        # -------------------------------------------------
        # Facebook
        # -------------------------------------------------

        if platform == "facebook":
            result = publish_to_facebook(
                message=params.get("message"),
                target_id=params.get("target_id"),
                link=params.get("link"),
            )

        # -------------------------------------------------
        # Reddit
        # -------------------------------------------------

        elif platform == "reddit":
            if not REDDIT_ENABLED:
                raise RuntimeError(
                    "Reddit publishing is disabled"
                )

            result = publish_to_reddit(
                title=params.get("title"),
                selftext=params.get("selftext"),
                subreddit=params.get("subreddit"),
            )

        # -------------------------------------------------
        # Instagram
        # -------------------------------------------------

        elif platform == "instagram":

            if action == "publish_post":
                result = publish_to_instagram(
                    image_url=params.get("image_url"),
                    caption=params.get("caption"),
                    landing_url=params.get("landing_url"),
                    ig_user_id=params.get("ig_user_id"),
                )

            elif action == "reply_comment":
                result = reply_to_instagram_comment(
                    comment_id=params.get("comment_id"),
                    message=params.get("message"),
                )

            else:
                raise ValueError(
                    f"Unknown Instagram action: {action}"
                )

        else:
            raise ValueError(
                f"Unknown platform: {platform}"
            )

        # -------------------------------------------------
        # Normalize publish result
        # -------------------------------------------------

        post_id = None
        post_url = None
        result_action = action
        target = None

        if isinstance(result, dict):
            post_id = (
                result.get("post_id")
                or result.get("id")
            )

            post_url = (
                result.get("post_url")
                or result.get("permalink")
            )

            result_action = result.get(
                "action",
                action,
            )

            target = (
                result.get("account_id")
                or result.get("target_id")
                or result.get("comment_id")
            )

        # Fall back to original parameters if publisher
        # did not return a useful target.
        if not target:

            if platform == "facebook":
                target = params.get("target_id")

            elif platform == "instagram":

                if action == "reply_comment":
                    target = params.get("comment_id")
                else:
                    target = params.get("ig_user_id")

            elif platform == "reddit":
                target = params.get("subreddit")

        # Final fallback to whatever was stored on Draft.
        if not target:
            target = getattr(
                draft,
                "target",
                None,
            )

        # -------------------------------------------------
        # Record successful publication
        # -------------------------------------------------

        published = Published(
            draft_id=draft.id,
            platform=platform,
            action=result_action,
            target=target,
            post_id=post_id,
            post_url=post_url,
        )

        db.add(published)

        draft.status = "published"

        db.commit()

        return result

    except Exception:
        db.rollback()

        # If we found the draft, mark it failed.
        # Re-query so we're working with fresh DB state.
        failed_draft = (
            db.query(Draft)
            .filter(Draft.id == draft_id)
            .first()
        )

        if failed_draft:
            failed_draft.status = "failed"
            db.commit()

        # Re-raise so RQ registers the failure and
        # Retry(max=3, interval=60) actually works.
        raise

    finally:
        db.close()


def enqueue_publish(
    draft_id,
    platform,
    params,
):
    job = queue.enqueue(
        publish_job,
        draft_id,
        platform,
        params,
        retry=Retry(
            max=3,
            interval=60,
        ),
    )

    print(
        f"Enqueued job {job.id} "
        f"for draft {draft_id} "
        f"on {platform}"
    )

    return job.id
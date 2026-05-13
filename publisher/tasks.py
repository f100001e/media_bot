from rq import Queue, Retry          # ← add Retry import
from redis import Redis
from publish.facebook import publish_to_facebook
from publish.reddit import publish_to_reddit
from publish.instagram import publish_to_instagram
import os

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

redis_conn = Redis(host=REDIS_HOST, port=REDIS_PORT)
queue = Queue('publisher', connection=redis_conn)

def publish_job(draft_id, platform, params):
    if platform == "facebook":
        return publish_to_facebook(
            message=params.get("message"),
            target_id=params.get("target_id")
        )
    elif platform == "reddit":
        return publish_to_reddit(
            title=params.get("title"),
            selftext=params.get("selftext"),
            subreddit=params.get("subreddit")
        )
    elif platform == "instagram":
        return publish_to_instagram(
            comment_id=params.get("comment_id"),
            message=params.get("message")
        )
    else:
        raise ValueError(f"Unknown platform: {platform}")

def enqueue_publish(draft_id, platform, params):
    # Single enqueue call with retry
    job = queue.enqueue(
        publish_job, draft_id, platform, params,
        retry=Retry(max=3, interval=60)   # retry up to 3 times with 60s delay
    )
    print(f"Enqueued job {job.id} for draft {draft_id} on {platform}")
    return job.id

if __name__ == "__main__":
    enqueue_publish(1, "facebook", {"message": "Hello Facebook!", "target_id": "12345"})
    enqueue_publish(2, "reddit", {"title": "Hello Reddit!", "selftext": "This is a test post.", "subreddit": "test"})
    enqueue_publish(3, "instagram", {"comment_id": "67890", "message": "Hello Instagram!"})
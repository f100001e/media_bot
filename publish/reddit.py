import praw
import os

reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    username=os.getenv("REDDIT_USERNAME"),
    password=os.getenv("REDDIT_PASSWORD"),
    user_agent=os.getenv("REDDIT_USER_AGENT")
)

def publish_to_reddit(title, selftext, subreddit_name):
    subreddit = reddit.subreddit(subreddit_name)
    submission = subreddit.submit(title, selftext=selftext)
    return {"id": submission.id, "url": submission.url}
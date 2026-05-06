import feedparser
import praw
import requests
from models.db import SessionLocal, RawContent
from opengraph import OpenGraph

def fetch_rss(feed_urls):
    for url in feed_urls:
        feed = feedparser.parse(url)
        for entry in feed.entries[:5]:
            yield {
                "source": url,
                "url": entry.link,
                "title": entry.title,
                "body": entry.summary
            }

def fetch_reddit(subreddits, limit=10):
    reddit = praw.Reddit(
        client_id="YOUR_CLIENT_ID",  # move to env later
        client_secret="YOUR_SECRET",
        user_agent="polibot"
    )
    for sub in subreddits:
        for post in reddit.subreddit(sub).hot(limit=limit):
            yield {
                "source": f"reddit.com/r/{sub}",
                "url": f"https://reddit.com{post.permalink}",
                "title": post.title,
                "body": post.selftext or post.title
            }

def fetch_opengraph_metadata(url, timeout=5):
    """Return dict of OG tags or empty dict if fails."""
    try:
        og = OpenGraph(url=url, timeout=timeout)
        return {
            "og_title": og.get('title'),
            "og_description": og.get('description'),
            "og_image": og.get('image'),
            "og_site_name": og.get('site_name')
        }
    except Exception as e:
        print(f"OG fetch failed for {url}: {e}")
        return {}
  
def save_raw_items():
    db = SessionLocal()
    rss_sources = ["https://www.politico.com/rss/politics.xml"]
    for item in fetch_rss(rss_sources):
        og = fetch_opengraph_metadata(item["url"])
        raw = RawContent(**item, **og, processed=0)
        db.add(raw)
    
    for item in fetch_reddit(["politics", "PoliticalDiscussion"]):
        og = fetch_opengraph_metadata(item["url"])
        raw = RawContent(**item, **og, processed=0)
        db.add(raw)
    
    db.commit()
    db.close()
    
if __name__ == "__main__":
    save_raw_items()
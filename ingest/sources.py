import requests
import xml.etree.ElementTree as ET
from importlib import import_module
from models.db import SessionLocal, RawContent
from opengraph_py3 import OpenGraph

def fetch_rss(feed_urls):
    for url in feed_urls:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        entries = root.findall("./channel/item")
        if not entries:
            entries = root.findall(".//{http://www.w3.org/2005/Atom}entry")

        for entry in entries[:5]:
            def get_text(tag):
                element = entry.find(tag)
                if element is None:
                    element = entry.find(
                        f"{{http://www.w3.org/2005/Atom}}{tag}"
                    )
                return element.text if element is not None else ""

            link = get_text("link")
            if not link:
                link_element = entry.find(
                    "{http://www.w3.org/2005/Atom}link"
                )
                link = link_element.get("href", "") if link_element is not None else ""
            yield {
                "source": url,
                "url": link,
                "title": get_text("title"),
                "body": get_text("description") or get_text("summary")
            }

def fetch_reddit(subreddits, limit=10):
    try:
        praw = import_module("praw")
    except ImportError as exc:
        raise RuntimeError(
            "Reddit support requires PRAW. Install it with: pip install praw"
        ) from exc

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
    rss_sources = [
    "https://feeds.npr.org/1014/rss.xml",
    "https://kff.org/feed/",                          # Kaiser Family Foundation - health policy
    "https://www.healthaffairs.org/rss/current.xml",  # Health Affairs
    "https://insurancenewsnet.com/rss",               # Insurance News Net
    "https://www.insurance.com/rss.xml",              # Insurance.com
]
    for item in fetch_rss(rss_sources):
        og = fetch_opengraph_metadata(item["url"])
        raw = RawContent(**item, **og, processed=0)
        db.add(raw)
    
    # for item in fetch_reddit(["politics", "PoliticalDiscussion"]):
    #     og = fetch_opengraph_metadata(item["url"])
    #     raw = RawContent(**item, **og, processed=0)
    #     db.add(raw)
    
    db.commit()
    db.close()
    
if __name__ == "__main__":
    save_raw_items()
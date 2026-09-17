import os
import requests
import xml.etree.ElementTree as ET

from importlib import import_module
from models.db import SessionLocal, RawContent
from opengraph_py3 import OpenGraph
import re

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 "
        "(Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 "
        "(KHTML, like Gecko) "
        "Chrome/151.0.0.0 Safari/537.36"
    )
}

def extract_feed_image(entry):
    """
    Extract an image URL directly from an RSS/Atom entry.
    Works with xml.etree.ElementTree elements.
    """

    # media:content
    media_content = entry.find(
        "{http://search.yahoo.com/mrss/}content"
    )

    if media_content is not None:
        url = media_content.get("url")
        medium = media_content.get("medium", "")

        if url and (not medium or medium == "image"):
            return url

    # media:thumbnail
    media_thumbnail = entry.find(
        "{http://search.yahoo.com/mrss/}thumbnail"
    )

    if media_thumbnail is not None:
        url = media_thumbnail.get("url")

        if url:
            return url

    # RSS enclosure
    enclosure = entry.find("enclosure")

    if enclosure is not None:
        enclosure_type = enclosure.get("type", "")
        url = enclosure.get("url")

        if (
            url
            and enclosure_type.startswith("image/")
        ):
            return url

    # Atom enclosure/link
    atom_links = entry.findall(
        "{http://www.w3.org/2005/Atom}link"
    )

    for link in atom_links:
        link_type = link.get("type", "")
        href = link.get("href", "")

        if (
            href
            and link_type.startswith("image/")
        ):
            return href

    # WordPress content:encoded
    encoded = entry.find(
        "{http://purl.org/rss/1.0/modules/content/}encoded"
    )

    if (
        encoded is not None
        and encoded.text
    ):
        match = re.search(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            encoded.text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

    # Description fallback
    description = entry.find("description")

    if (
        description is not None
        and description.text
    ):
        match = re.search(
            r'<img[^>]+src=["\']([^"\']+)["\']',
            description.text,
            re.IGNORECASE,
        )

        if match:
            return match.group(1)

    return None

def fetch_rss(feed_urls):
    """
    Fetch RSS/Atom feeds.

    Bad or blocked feeds are skipped instead of terminating
    the entire ingest process.
    """

    for url in feed_urls:
        print(f"Fetching RSS: {url}")

        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=15,
            )

            response.raise_for_status()

        except requests.RequestException as exc:
            print(
                f"Skipping RSS source {url}: {exc}"
            )
            continue

        try:
            root = ET.fromstring(
                response.content
            )

        except ET.ParseError as exc:
            print(
                f"Skipping malformed RSS source "
                f"{url}: {exc}"
            )
            continue

        # Standard RSS
        entries = root.findall(
            "./channel/item"
        )

        # Atom fallback
        if not entries:
            entries = root.findall(
                ".//{http://www.w3.org/2005/Atom}entry"
            )

        if not entries:
            print(
                f"No entries found in feed: {url}"
            )
            continue

        for entry in entries[:5]:

            def get_text(tag):
                element = entry.find(tag)

                if element is None:
                    element = entry.find(
                        "{http://www.w3.org/"
                        f"2005/Atom}}{tag}"
                    )

                if (
                    element is not None
                    and element.text
                ):
                    return element.text.strip()

                return ""

            link = get_text("link")

            if not link:
                link_element = entry.find(
                    "{http://www.w3.org/"
                    "2005/Atom}link"
                )

                if link_element is not None:
                    link = link_element.get(
                        "href",
                        "",
                    )

            title = get_text("title")

            body = (
                get_text("description")
                or get_text("summary")
            )

            if not link:
                print(
                    f"Skipping entry without URL "
                    f"from {url}"
                )
                continue

            feed_image = extract_feed_image(entry)

            yield {
                "source": url,
                "url": link,
                "title": title,
                "body": body,
                "feed_image": feed_image,
            }


def fetch_reddit(
    subreddits,
    limit=10,
):
    try:
        praw = import_module("praw")

    except ImportError as exc:
        raise RuntimeError(
            "Reddit support requires PRAW. "
            "Install it with: pip install praw"
        ) from exc

    client_id = os.getenv(
        "REDDIT_CLIENT_ID"
    )

    client_secret = os.getenv(
        "REDDIT_CLIENT_SECRET"
    )

    user_agent = os.getenv(
        "REDDIT_USER_AGENT",
        "media_bot",
    )

    if not client_id or not client_secret:
        raise RuntimeError(
            "Reddit credentials are not configured"
        )

    reddit = praw.Reddit(
        client_id=client_id,
        client_secret=client_secret,
        user_agent=user_agent,
    )

    for sub in subreddits:
        for post in reddit.subreddit(
            sub
        ).hot(limit=limit):

            yield {
                "source": (
                    f"reddit.com/r/{sub}"
                ),
                "url": (
                    "https://reddit.com"
                    f"{post.permalink}"
                ),
                "title": post.title,
                "body": (
                    post.selftext
                    or post.title
                ),
            }


def fetch_opengraph_metadata(
    url,
    timeout=5,
):
    """
    Return OpenGraph metadata.

    Failures are non-fatal because many sites block
    metadata scraping or omit OG tags entirely.
    """

    try:
        og = OpenGraph(
            url=url,
            timeout=timeout,
        )

        return {
            "og_title": og.get(
                "title"
            ),
            "og_description": og.get(
                "description"
            ),
            "og_image": og.get(
                "image"
            ),
            "og_site_name": og.get(
                "site_name"
            ),
        }

    except Exception as exc:
        print(
            f"OG fetch failed for "
            f"{url}: {exc}"
        )

        return {}


def save_raw_items():
    db = SessionLocal()

    rss_sources = [
        "https://www.presspassla.com/feed/",
        "https://variety.com/feed/",
        "https://www.tmz.com/rss.xml",
        "https://www.hollywoodreporter.com/feed/",
    ]

    saved_count = 0
    skipped_duplicates = 0
    try:
        for item in fetch_rss(rss_sources):
            existing = (
                db.query(RawContent)
                .filter(
                    RawContent.url == item["url"]
                )
                .first()
            )

            feed_image = item.get("feed_image")

            # If this article already exists, use the RSS image
            # to repair a missing og_image instead of blindly skipping it.
            if existing:
                if not existing.og_image and feed_image:
                    existing.og_image = feed_image

                    print(
                        f"Updated missing image: "
                        f"{item['title']}"
                    )
                else:
                    skipped_duplicates += 1

                continue

            if "presspassla.com" in item["url"]:
                og = {}
            else:
                og = fetch_opengraph_metadata(
                    item["url"]
                )

            # RSS image is the fallback when OpenGraph
            # does not provide one.
            if not og.get("og_image") and feed_image:
                og["og_image"] = feed_image

            raw = RawContent(
                source=item["source"],
                url=item["url"],
                title=item["title"],
                body=item["body"],
                processed=0,
                **og,
            )

            db.add(raw)
            saved_count += 1

        db.commit()

        print(
            f"Saved {saved_count} "
            f"new raw items"
        )

        if skipped_duplicates:
            print(
                f"Skipped "
                f"{skipped_duplicates} "
                f"duplicate items"
            )

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    save_raw_items()
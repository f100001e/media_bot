import requests
import os

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

def publish_to_instagram(comment_id, message):
    url = f"https://graph.facebook.com/v18.0/{comment_id}/replies"
    params = {
        "message": message,
        "access_token": ACCESS_TOKEN
    }
    resp = requests.post(url, params=params)
    return resp.json()
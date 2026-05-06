import requests
import os

ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")

def publish_to_facebook(message, target_id):
    url = f"https://graph.facebook.com/v18.0/{target_id}/feed"
    payload = {
        "message": message,
        "access_token": ACCESS_TOKEN
    }
    resp = requests.post(url, data=payload)
    return resp.json()  # will contain 'id' of post
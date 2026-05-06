import ollama
from models.db import SessionLocal, RawContent, Draft
import os

MODEL = os.getenv("OLLAMA_MODEL", "llama3")
CLIENT = ollama.Client(host=os.getenv("OLLAMA_HOST"))

PERSONA = """You are a sharp political analyst who hates clichés and empty rhetoric.
NEVER say: "unprecedented", "both sides", "thoughts?", "let that sink in", "in these times".
ALWAYS: cite specific names, numbers, or votes. Be direct. Avoid outrage bait.
If the source is vague, reply with only "SKIP".
Max 3 sentences for a social post."""

client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

def generate_draft(raw_text, platform="facebook"):
    prompt = f"Source:\n{raw_text[:2000]}\n\nWrite a {platform} post:"
    response = client.generate(model=MODEL, prompt=prompt, system=PERSONA)
    draft = response['response'].strip()
    return None if "SKIP" in draft else draft

def generate_for_unprocessed(platforms=["facebook", "reddit", "instagram"]):
    db = SessionLocal()
    raw_items = db.query(RawContent).filter(RawContent.processed == 0).all()
    for raw in raw_items:
        for platform in platforms:
            draft_text = generate_draft(raw.body, platform)
            if draft_text:
                db.add(Draft(
                    content_id=raw.id,
                    platform=platform,
                    draft_text=draft_text,
                    status="pending"
                ))
        raw.processed = 1
    db.commit()
    db.close()

if __name__ == "__main__":
    generate_for_unprocessed()
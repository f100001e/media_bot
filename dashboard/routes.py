from fastapi import FastAPI, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from models.db import SessionLocal, Draft, Published, RawContent
from publisher.tasks import enqueue_publish
from datetime import datetime                
from pathlib import Path

app = FastAPI()
templates = Jinja2Templates(directory="dashboard/templates")
app.mount("/static", StaticFiles(directory="dashboard/static"), name="static")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/meta/callback")
async def meta_callback(request: Request, code: str = None, error: str = None):
    if error:
        return {"error": error}
    return {"code": code}

@app.get("/queue")
def approval_queue(request: Request, db: Session = Depends(get_db)):
    # Query drafts with their raw content
    results = db.query(Draft, RawContent).join(
        RawContent, Draft.content_id == RawContent.id
    ).filter(Draft.status == "pending").all()
    
    # Transform into list of dicts for easier template access
    drafts_with_preview = []
    for draft, raw in results:
        drafts_with_preview.append({
            "draft": draft,
            "url": raw.url,
            "og_title": raw.og_title,
            "og_description": raw.og_description,
            "og_image": raw.og_image,
            "og_site_name": raw.og_site_name
        })
    
    return templates.TemplateResponse("queue.html", {
        "request": request,
        "items": drafts_with_preview
    })

@app.post("/approve")
async def approve_draft(
    request: Request,
    db: Session = Depends(get_db)
):
    form = await request.form()
    draft_ids = form.getlist("draft_id")
    platform = form.get("platform")
    target = form.get("target")

    for draft_id in draft_ids:
        draft_id = int(draft_id)
        edited_text = form.get(f"edit_text_{draft_id}")
        link = form.get(f"link_{draft_id}")
        
        draft = db.query(Draft).filter(Draft.id == draft_id).first()
        if not draft:
            continue
        
        final_text = edited_text if edited_text else draft.draft_text
        draft.status = "approved"
        draft.approved_at = datetime.utcnow()
        db.commit()
        
        if platform == "facebook":
            params = {"message": final_text, "target_id": target, "link": link if link else None}
        elif platform == "reddit":
            title = final_text[:100] if len(final_text) > 100 else final_text
            params = {"title": title, "selftext": final_text, "subreddit": target}
        elif platform == "instagram":
            params = {"comment_id": target, "message": final_text}
        
        enqueue_publish(draft_id, platform, params)

    return {"status": "queued", "count": len(draft_ids)}
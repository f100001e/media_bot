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

@app.get("/engagement")
def engagement(request: Request):
    return templates.TemplateResponse(
        "engagement.html",
        {
            "request": request,
            "items": []
        }
    )

@app.get("/published")
def published(
    request: Request,
    db: Session = Depends(get_db),
):
    results = (
        db.query(Published)
        .order_by(Published.published_at.desc())
        .all()
    )

    published_items = []

    for item in results:
        published_items.append({
            "draft_id": item.draft_id,
            "platform": item.platform or "unknown",
            "target": item.target,
            "post_id": item.post_id,
            "post_url": item.post_url,
            "published_at": item.published_at,
        })

    return templates.TemplateResponse(
        "published.html",
        {
            "request": request,
            "items": published_items,
        },
    )

@app.get("/failed")
def failed(
    request: Request,
    db: Session = Depends(get_db)
):
    items = (
        db.query(Draft)
        .filter(Draft.status == "failed")
        .order_by(Draft.created_at.desc())
        .all()
    )

    return templates.TemplateResponse(
        "failed.html",
        {
            "request": request,
            "items": items
        }
    )

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
    db: Session = Depends(get_db),
):
    form = await request.form()

    draft_ids = form.getlist("draft_id")

    selected_platform = form.get("platform")
    selected_target = form.get("target")

    queued_count = 0

    for draft_id in draft_ids:
        draft_id = int(draft_id)

        draft = (
            db.query(Draft)
            .filter(Draft.id == draft_id)
            .first()
        )

        if not draft:
            continue

        platform = selected_platform or draft.platform
        target = selected_target or draft.target

        if not platform:
            raise ValueError(
                f"Draft {draft_id} has no platform configured"
            )

        edited_text = form.get(f"edit_text_{draft_id}")
        link = form.get(f"link_{draft_id}")

        raw = (
            db.query(RawContent)
            .filter(RawContent.id == draft.content_id)
            .first()
        )

        image_url = (
            form.get(f"image_url_{draft_id}")
            or (raw.og_image if raw else None)
        )

        final_text = (
            edited_text
            if edited_text
            else draft.draft_text
        )

        # ---------------------------------------------
        # Build platform-specific publish parameters
        # ---------------------------------------------

        if platform == "facebook":
            params = {
                "message": final_text,
                "target_id": target,
                "link": link or None,
            }

        elif platform == "reddit":
            title = (
                final_text[:100]
                if len(final_text) > 100
                else final_text
            )

            params = {
                "title": title,
                "selftext": final_text,
                "subreddit": target,
            }

        elif platform == "instagram":
            if not image_url:
                raise ValueError(
                    f"Draft {draft_id} has no image URL "
                    "and cannot be published to Instagram"
                )

            params = {
                "action": "publish_post",
                "image_url": image_url,
                "caption": final_text,
                "ig_user_id": target or None,
            }

        else:
            raise ValueError(
                f"Unsupported platform: {platform}"
            )

        draft.status = "approved"
        draft.approved_at = datetime.utcnow()

        db.commit()

        enqueue_publish(
            draft_id,
            platform,
            params,
        )

        queued_count += 1

    return {
        "status": "queued",
        "count": queued_count,
    }
            
@app.post("/delete-drafts")
async def delete_drafts(
    request: Request,
    db: Session = Depends(get_db),
):
    form = await request.form()
    draft_ids = form.getlist("draft_id")

    deleted_count = 0

    for draft_id in draft_ids:
        draft = (
            db.query(Draft)
            .filter(Draft.id == int(draft_id))
            .first()
        )

        if not draft:
            continue

        db.delete(draft)
        deleted_count += 1

    db.commit()

    return {
        "status": "deleted",
        "count": deleted_count,
    }

from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DB_PATH = (BASE_DIR / os.getenv("DB_PATH", "bot.db")).resolve()

engine = create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

class RawContent(Base):
    __tablename__ = "raw_content"
    id = Column(Integer, primary_key=True)
    source = Column(String)
    url = Column(String)
    title = Column(String)
    body = Column(Text)
    fetched_at = Column(DateTime, default=datetime.utcnow)
    processed = Column(Integer, default=0)
    og_title = Column(String, nullable=True)
    og_description = Column(Text, nullable=True)
    og_image = Column(String, nullable=True)
    og_site_name = Column(String, nullable=True)

class Draft(Base):
    __tablename__ = "drafts"
    id = Column(Integer, primary_key=True)
    content_id = Column(Integer)
    platform = Column(String)          # facebook / reddit / instagram
    draft_text = Column(Text)
    status = Column(String, default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=datetime.utcnow)
    approved_at = Column(DateTime)
    platform_params = Column(JSON)     # store subreddit, flair, etc.

class Published(Base):
    __tablename__ = "published"
    id = Column(Integer, primary_key=True)
    draft_id = Column(Integer)
    platform = Column(String)
    target = Column(String)             # group_id, subreddit name, etc.
    post_id = Column(String)
    published_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)
print(f"DB ready: {DB_PATH}")
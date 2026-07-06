"""
MangaFlow AI — SQLAlchemy ORM Models
Complete database schema: users, projects, jobs, pages, glossaries, api_keys, audit_logs, payments
"""
import uuid
from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import (
    Boolean, Column, DateTime, Enum, Float, ForeignKey,
    Integer, JSON, String, Text, BigInteger, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)

def new_uuid():
    return str(uuid.uuid4())


class UserRole(str, PyEnum):
    GUEST = "guest"
    FREE = "free"
    PREMIUM = "premium"
    ADMIN = "admin"


class JobStatus(str, PyEnum):
    QUEUED = "queued"
    EXTRACTING = "extracting"
    OCR = "ocr"
    TRANSLATING = "translating"
    INPAINTING = "inpainting"
    TYPESETTING = "typesetting"
    EXPORTING = "exporting"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"
    CANCELLED = "cancelled"


class FileFormat(str, PyEnum):
    PDF = "pdf"
    EPUB = "epub"
    ZIP = "zip"


class OAuthProvider(str, PyEnum):
    GOOGLE = "google"
    GITHUB = "github"
    EMAIL = "email"
    GUEST = "guest"


class User(Base):
    __tablename__ = "users"
    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    email = Column(String(255), unique=True, nullable=True, index=True)
    username = Column(String(100), unique=True, nullable=True)
    display_name = Column(String(200), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    role = Column(Enum(UserRole), default=UserRole.FREE, nullable=False)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    oauth_provider = Column(Enum(OAuthProvider), nullable=True)
    oauth_id = Column(String(255), nullable=True)
    pages_used_today = Column(Integer, default=0)
    pages_used_total = Column(Integer, default=0)
    last_usage_reset = Column(DateTime(timezone=True), default=utcnow)
    stripe_customer_id = Column(String(255), nullable=True)
    stripe_subscription_id = Column(String(255), nullable=True)
    subscription_expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    glossaries = relationship("Glossary", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    __table_args__ = (
        UniqueConstraint("oauth_provider", "oauth_id", name="uq_oauth"),
    )


class Project(Base):
    __tablename__ = "projects"
    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_format = Column(Enum(FileFormat), nullable=False)
    file_size_bytes = Column(BigInteger, default=0)
    total_pages = Column(Integer, default=0)
    source_file_key = Column(String(1000), nullable=True)
    output_pdf_key = Column(String(1000), nullable=True)
    output_epub_key = Column(String(1000), nullable=True)
    output_zip_key = Column(String(1000), nullable=True)
    source_language = Column(String(20), default="auto")
    target_language = Column(String(20), default="en")
    ai_provider = Column(String(20), default="openai")
    preserve_honorifics = Column(Boolean, default=True)
    translate_sfx = Column(Boolean, default=False)
    glossary_id = Column(UUID(as_uuid=False), ForeignKey("glossaries.id"), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    tags = Column(JSON, default=list)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    user = relationship("User", back_populates="projects")
    jobs = relationship("TranslationJob", back_populates="project", cascade="all, delete-orphan")
    pages = relationship("Page", back_populates="project", cascade="all, delete-orphan")
    glossary = relationship("Glossary", foreign_keys=[glossary_id])


class TranslationJob(Base):
    __tablename__ = "translation_jobs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    celery_task_id = Column(String(255), nullable=True, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.QUEUED, nullable=False, index=True)
    current_page = Column(Integer, default=0)
    total_pages = Column(Integer, default=0)
    pages_per_second = Column(Float, default=0.0)
    estimated_seconds_remaining = Column(Integer, nullable=True)
    queued_at = Column(DateTime(timezone=True), default=utcnow)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    error_traceback = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    logs = Column(JSON, default=list)
    checkpoint_data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    project = relationship("Project", back_populates="jobs")


class Page(Base):
    __tablename__ = "pages"
    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    original_image_key = Column(String(1000), nullable=True)
    cleaned_image_key = Column(String(1000), nullable=True)
    final_image_key = Column(String(1000), nullable=True)
    ocr_done = Column(Boolean, default=False)
    translation_done = Column(Boolean, default=False)
    inpainting_done = Column(Boolean, default=False)
    typesetting_done = Column(Boolean, default=False)
    bubbles = Column(JSON, default=list)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    detected_language = Column(String(20), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    project = relationship("Project", back_populates="pages")
    __table_args__ = (
        UniqueConstraint("project_id", "page_number", name="uq_project_page"),
    )


class Glossary(Base):
    __tablename__ = "glossaries"
    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    source_language = Column(String(20), default="ja")
    target_language = Column(String(20), default="en")
    terms = Column(JSON, default=list)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    user = relationship("User", back_populates="glossaries")


class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=False)
    key_hash = Column(String(255), nullable=False, unique=True)
    key_prefix = Column(String(10), nullable=False)
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    scopes = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    user = relationship("User", back_populates="api_keys")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=True)
    resource_id = Column(String(255), nullable=True)
    details = Column(JSON, default=dict)
    ip_address = Column(String(45), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, index=True)


class Payment(Base):
    __tablename__ = "payments"
    id = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id = Column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    stripe_payment_intent_id = Column(String(255), unique=True, nullable=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String(3), default="usd")
    status = Column(String(50), nullable=False)
    plan = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)

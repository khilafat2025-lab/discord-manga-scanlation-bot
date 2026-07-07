"""
MangaFlow AI - Database Models (8 Tables)
users, projects, translation_jobs, pages, glossaries, api_keys, audit_logs, payments
"""
import uuid
from datetime import datetime, timezone
from typing import Optional
from enum import Enum as PyEnum

from sqlalchemy import (
    String, Text, Integer, Float, Boolean, DateTime,
    ForeignKey, JSON, Enum, BigInteger, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


def utcnow():
    return datetime.now(timezone.utc)


class UserRole(str, PyEnum):
    GUEST = "guest"
    FREE = "free"
    PREMIUM = "premium"
    ADMIN = "admin"


class AuthProvider(str, PyEnum):
    EMAIL = "email"
    GOOGLE = "google"
    GITHUB = "github"
    GUEST = "guest"


class ProjectStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


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
    CANCELLED = "cancelled"


class ExportFormat(str, PyEnum):
    PDF = "pdf"
    EPUB = "epub"
    ZIP = "zip"


class PageStatus(str, PyEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# Table 1: Users
class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(100), unique=True, nullable=True)
    full_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    auth_provider: Mapped[AuthProvider] = mapped_column(Enum(AuthProvider), default=AuthProvider.EMAIL)
    provider_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.FREE)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    pages_used_today: Mapped[int] = mapped_column(Integer, default=0)
    pages_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    total_pages_processed: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    projects: Mapped[list["Project"]] = relationship("Project", back_populates="user", cascade="all, delete-orphan")
    api_keys: Mapped[list["ApiKey"]] = relationship("ApiKey", back_populates="user", cascade="all, delete-orphan")
    payments: Mapped[list["Payment"]] = relationship("Payment", back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship("AuditLog", back_populates="user")


# Table 2: Projects
class Project(Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(500))
    original_filename: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(10))
    file_size: Mapped[int] = mapped_column(BigInteger)
    file_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    processed_pages: Mapped[int] = mapped_column(Integer, default=0)
    source_language: Mapped[str] = mapped_column(String(10), default="ja")
    target_language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[ProjectStatus] = mapped_column(Enum(ProjectStatus), default=ProjectStatus.PENDING)
    settings: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    output_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    output_format: Mapped[Optional[ExportFormat]] = mapped_column(Enum(ExportFormat), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="projects")
    translation_jobs: Mapped[list["TranslationJob"]] = relationship("TranslationJob", back_populates="project", cascade="all, delete-orphan")
    pages: Mapped[list["Page"]] = relationship("Page", back_populates="project", cascade="all, delete-orphan")
    glossaries: Mapped[list["Glossary"]] = relationship("Glossary", back_populates="project", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_projects_user_status", "user_id", "status"),)


# Table 3: Translation Jobs
class TranslationJob(Base):
    __tablename__ = "translation_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    celery_task_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.QUEUED)
    current_step: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    current_page: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    pages_per_second: Mapped[float] = mapped_column(Float, default=0.0)
    estimated_seconds_remaining: Mapped[int] = mapped_column(Integer, default=0)
    logs: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="translation_jobs")


# Table 4: Pages
class Page(Base):
    __tablename__ = "pages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    page_number: Mapped[int] = mapped_column(Integer)
    original_image_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    processed_image_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    status: Mapped[PageStatus] = mapped_column(Enum(PageStatus), default=PageStatus.PENDING)
    bubbles: Mapped[Optional[list]] = mapped_column(JSON, nullable=True, default=list)
    ocr_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    processing_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="pages")
    __table_args__ = (Index("ix_pages_project_number", "project_id", "page_number"),)


# Table 5: Glossaries
class Glossary(Base):
    __tablename__ = "glossaries"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_term: Mapped[str] = mapped_column(String(500))
    translated_term: Mapped[str] = mapped_column(String(500))
    term_type: Mapped[str] = mapped_column(String(50), default="general")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    auto_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship("Project", back_populates="glossaries")


# Table 6: API Keys
class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    key_prefix: Mapped[str] = mapped_column(String(10))
    hashed_key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    usage_count: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")


# Table 7: Audit Logs
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100))
    resource_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)

    user: Mapped[Optional["User"]] = relationship("User", back_populates="audit_logs")


# Table 8: Payments
class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    stripe_payment_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, unique=True)
    stripe_subscription_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    plan: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50))
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    metadata: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    user: Mapped["User"] = relationship("User", back_populates="payments")

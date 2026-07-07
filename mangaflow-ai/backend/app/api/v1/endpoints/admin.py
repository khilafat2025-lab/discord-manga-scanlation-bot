"""
MangaFlow AI - Admin Panel Endpoints
User management, queue monitoring, revenue analytics
"""
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc

from app.core.security import decode_token
from app.db.base import get_db
from app.models.models import User, Project, TranslationJob, Payment, AuditLog, UserRole, ProjectStatus, JobStatus

router = APIRouter()


async def require_admin(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(auth.split(" ")[1])
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == payload["sub"]))
    user = result.scalar_one_or_none()
    if not user or user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


@router.get("/stats")
async def get_stats(request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request, db)
    total_users = (await db.execute(select(func.count()).select_from(User))).scalar()
    total_projects = (await db.execute(select(func.count()).select_from(Project))).scalar()
    active_jobs = (await db.execute(
        select(func.count()).select_from(TranslationJob).where(
            TranslationJob.status.in_([JobStatus.QUEUED, JobStatus.OCR, JobStatus.TRANSLATING])
        )
    )).scalar()
    total_revenue = (await db.execute(
        select(func.sum(Payment.amount_cents)).where(Payment.status == "succeeded")
    )).scalar() or 0
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)
    new_users = (await db.execute(
        select(func.count()).select_from(User).where(User.created_at >= week_ago)
    )).scalar()
    return {
        "total_users": total_users, "new_users_7d": new_users,
        "total_projects": total_projects, "active_jobs": active_jobs,
        "total_revenue_cents": total_revenue, "total_revenue_usd": total_revenue / 100,
    }


@router.get("/users")
async def list_users(request: Request, page: int = 1, per_page: int = 50, search: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    await require_admin(request, db)
    query = select(User).order_by(desc(User.created_at))
    if search:
        query = query.where(User.email.ilike(f"%{search}%"))
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    users = result.scalars().all()
    return {"users": [{"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": u.role.value, "is_active": u.is_active, "total_pages_processed": u.total_pages_processed, "created_at": u.created_at.isoformat()} for u in users]}


@router.patch("/users/{user_id}/role")
async def update_user_role(user_id: str, role: str, request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request, db)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.role = UserRole(role)
    return {"success": True, "user_id": user_id, "new_role": role}


@router.patch("/users/{user_id}/toggle")
async def toggle_user(user_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request, db)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.is_active = not user.is_active
    return {"success": True, "is_active": user.is_active}


@router.get("/jobs")
async def list_jobs(request: Request, status: Optional[str] = None, page: int = 1, per_page: int = 50, db: AsyncSession = Depends(get_db)):
    await require_admin(request, db)
    query = select(TranslationJob).order_by(desc(TranslationJob.created_at))
    if status:
        query = query.where(TranslationJob.status == status)
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    jobs = result.scalars().all()
    return {"jobs": [{"id": str(j.id), "project_id": str(j.project_id), "status": j.status.value, "current_step": j.current_step, "current_page": j.current_page, "total_pages": j.total_pages, "retry_count": j.retry_count, "created_at": j.created_at.isoformat()} for j in jobs]}


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, request: Request, db: AsyncSession = Depends(get_db)):
    await require_admin(request, db)
    result = await db.execute(select(TranslationJob).where(TranslationJob.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.celery_task_id:
        try:
            from app.tasks.translation_tasks import celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)
        except Exception:
            pass
    job.status = JobStatus.CANCELLED
    return {"success": True}

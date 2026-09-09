from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List
from datetime import datetime
from app.database import get_db
from app.models.submission_window import SubmissionWindow
from app.models.teacher import Teacher
from app.auth import get_current_teacher, get_current_admin
from pydantic import BaseModel
from zoneinfo import ZoneInfo

class SubmissionWindowCreate(BaseModel):
    title: str
    start_date: datetime
    end_date: datetime
    is_active: bool = True

class SubmissionWindowResponse(BaseModel):
    id: int
    title: str
    start_date: datetime
    end_date: datetime
    is_active: bool

    class Config:
        from_attributes = True

router = APIRouter(prefix="/submission-windows", tags=["submission-windows"])

@router.get("/", response_model=List[SubmissionWindowResponse])
async def list_windows(
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher)
):
    result = await db.execute(select(SubmissionWindow).order_by(SubmissionWindow.start_date.desc()))
    return result.scalars().all()

@router.get("/active", response_model=SubmissionWindowResponse | None)
async def get_active_window(
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher)
):
    """בודק אם יש חלון הגשה פעיל כרגע"""
    now = datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None)
    result = await db.execute(
        select(SubmissionWindow).where(
            SubmissionWindow.is_active == True,
            SubmissionWindow.start_date <= now,
            SubmissionWindow.end_date >= now
        )
    )
    return result.scalar_one_or_none()

@router.post("/", response_model=SubmissionWindowResponse)
async def create_window(
    data: SubmissionWindowCreate,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin)
):
    dump = data.model_dump()
    dump['start_date'] = dump['start_date'].replace(tzinfo=None)
    dump['end_date'] = dump['end_date'].replace(tzinfo=None)
    window = SubmissionWindow(**dump)
    db.add(window)
    await db.commit()
    await db.refresh(window)
    return window

@router.delete("/{window_id}")
async def delete_window(
    window_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin)
):
    result = await db.execute(select(SubmissionWindow).where(SubmissionWindow.id == window_id))
    window = result.scalar_one_or_none()
    if not window:
        raise HTTPException(status_code=404, detail="Window not found")
    await db.delete(window)
    await db.commit()
    return {"message": "Deleted"}

class SubmissionStatusResponse(BaseModel):
    submitted: bool
    submitted_at: datetime | None = None


@router.get("/active/my-status", response_model=SubmissionStatusResponse)
async def get_my_submission_status(
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    now = datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None)
    window_result = await db.execute(
        select(SubmissionWindow).where(
            SubmissionWindow.is_active == True,
            SubmissionWindow.start_date <= now,
            SubmissionWindow.end_date >= now
        )
    )
    window = window_result.scalar_one_or_none()
    if not window:
        return SubmissionStatusResponse(submitted=False)

    sub_result = await db.execute(
        text("SELECT submitted_at FROM teacher_submissions WHERE teacher_id=:tid AND submission_window_id=:wid"),
        {"tid": current_teacher.id, "wid": window.id}
    )
    row = sub_result.mappings().one_or_none()
    if row:
        return SubmissionStatusResponse(submitted=True, submitted_at=row["submitted_at"])
    return SubmissionStatusResponse(submitted=False)


@router.post("/active/submit", response_model=SubmissionStatusResponse)
async def submit_my_preferences(
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    now = datetime.now(ZoneInfo("Asia/Jerusalem")).replace(tzinfo=None)
    window_result = await db.execute(
        select(SubmissionWindow).where(
            SubmissionWindow.is_active == True,
            SubmissionWindow.start_date <= now,
            SubmissionWindow.end_date >= now
        )
    )
    window = window_result.scalar_one_or_none()
    if not window:
        raise HTTPException(status_code=400, detail="אין חלון הגשה פעיל כרגע")

    existing = await db.execute(
        text("SELECT submitted_at FROM teacher_submissions WHERE teacher_id=:tid AND submission_window_id=:wid"),
        {"tid": current_teacher.id, "wid": window.id}
    )
    row = existing.mappings().one_or_none()
    if row:
        return SubmissionStatusResponse(submitted=True, submitted_at=row["submitted_at"])

    insert_result = await db.execute(
        text("INSERT INTO teacher_submissions (teacher_id, submission_window_id) VALUES (:tid, :wid) RETURNING submitted_at"),
        {"tid": current_teacher.id, "wid": window.id}
    )
    submitted_at = insert_result.scalar()

    # Notify every admin — sendNotification's endpoint only targets
    # non-admins, so we create the notification rows directly here.
    notif_result = await db.execute(
        text("INSERT INTO notifications (title, body, created_by) VALUES (:title, :body, :created_by) RETURNING id"),
        {
            "title": "מורה הגיש/ה את טופס ההעדפות",
            "body": f"{current_teacher.first_name} {current_teacher.last_name} הגיש/ה את טופס ההעדפות עבור \"{window.title}\".",
            "created_by": current_teacher.id,
        }
    )
    notification_id = notif_result.scalar()

    admins_result = await db.execute(text("SELECT id FROM teachers WHERE is_admin = true"))
    admin_ids = [r[0] for r in admins_result.all()]
    for admin_id in admin_ids:
        await db.execute(
            text("INSERT INTO teacher_notifications (notification_id, teacher_id) VALUES (:nid, :tid)"),
            {"nid": notification_id, "tid": admin_id}
        )

    await db.commit()
    return SubmissionStatusResponse(submitted=True, submitted_at=submitted_at)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from pydantic import BaseModel

from app.database import get_db
from app.models.schedule_run import ScheduleRun
from app.models.teacher import Teacher
from app.schemas.schedule_run import ScheduleRunCreate, ScheduleRunResponse
from app.auth import get_current_teacher, get_current_admin

router = APIRouter(prefix="/schedule-runs", tags=["schedule-runs"])


@router.get("/", response_model=List[ScheduleRunResponse])
async def list_runs(
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher),
):
    result = await db.execute(select(ScheduleRun).order_by(ScheduleRun.run_at.desc()))
    return result.scalars().all()


@router.get("/{run_id}", response_model=ScheduleRunResponse)
async def get_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher),
):
    return await _get_or_404(db, run_id)


@router.post("/", response_model=ScheduleRunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(
    data: ScheduleRunCreate,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    run = ScheduleRun(algorithm=data.algorithm)
    db.add(run)
    await db.commit()
    await db.refresh(run)
    return run


@router.patch("/{run_id}/select", response_model=ScheduleRunResponse)
async def select_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    await _get_or_404(db, run_id)

    await db.execute(update(ScheduleRun).values(is_selected=False))
    await db.execute(update(ScheduleRun).where(ScheduleRun.id == run_id).values(is_selected=True))
    await db.commit()

    result = await db.execute(select(ScheduleRun).where(ScheduleRun.id == run_id))
    return result.scalar_one()


@router.delete("/{run_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    run = await _get_or_404(db, run_id)
    if run.is_selected or run.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the currently selected or published schedule.",
        )
    await db.delete(run)
    await db.commit()


async def _get_or_404(db: AsyncSession, run_id: int) -> ScheduleRun:
    result = await db.execute(select(ScheduleRun).where(ScheduleRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule run not found")
    return run


class NoteUpdate(BaseModel):
    admin_note: Optional[str] = None


@router.patch("/{run_id}/note", response_model=ScheduleRunResponse)
async def update_run_note(
    run_id: int,
    data: NoteUpdate,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    run = await _get_or_404(db, run_id)
    note = (data.admin_note or "").strip()
    run.admin_note = note[:255] if note else None
    await db.commit()
    await db.refresh(run)
    return run

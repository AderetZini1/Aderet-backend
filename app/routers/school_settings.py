from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict
from app.database import get_db
from app.models.teacher import Teacher
from app.auth import get_current_admin
from pydantic import BaseModel
import json

class BreakTime(BaseModel):
    after_lesson: int
    duration_minutes: int

class SchoolSettingsSchema(BaseModel):
    active_days: List[int]
    start_time: str
    breaks: List[BreakTime]
    grade_end_times: Optional[Dict[str, str]] = {}

class GradeLimitSchema(BaseModel):
    grade_level: int
    max_lessons_per_day: int

class PedagogicalConstraintSchema(BaseModel):
    constraint_type: str
    subject_a_id: Optional[int] = None
    subject_b_id: Optional[int] = None
    numeric_value: Optional[int] = None
    weight: Optional[int] = 1
    raw_text: Optional[str] = None

router = APIRouter(prefix="/school-settings", tags=["school-settings"])

@router.get("/")
async def get_settings(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM system_requirements LIMIT 1"))
    row = result.mappings().one_or_none()
    if not row:
        return {"active_days": [1,2,3,4,5,6], "start_time": "08:00", "breaks": [], "grade_end_times": {}}
    d = dict(row)
    d['breaks'] = d['breaks'] if d['breaks'] else []
    d['grade_end_times'] = d.get('grade_end_times') or {}
    return d

@router.post("/")
async def save_settings(
    data: SchoolSettingsSchema,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin)
):
    existing = await db.execute(text("SELECT id FROM system_requirements LIMIT 1"))
    row = existing.scalar_one_or_none()
    breaks_json = json.dumps([b.model_dump() for b in data.breaks])
    grade_end_json = json.dumps(data.grade_end_times)
    if row:
        await db.execute(
            text("UPDATE system_requirements SET active_days=:days, start_time=:start, breaks=:breaks, grade_end_times=:get, updated_at=NOW() WHERE id=:id"),
            {"days": data.active_days, "start": data.start_time, "breaks": breaks_json, "get": grade_end_json, "id": row}
        )
    else:
        await db.execute(
            text("INSERT INTO system_requirements (active_days, start_time, breaks, grade_end_times) VALUES (:days, :start, :breaks, :get)"),
            {"days": data.active_days, "start": data.start_time, "breaks": breaks_json, "get": grade_end_json}
        )
    await db.commit()
    return {"message": "נשמר"}

@router.get("/grade-limits")
async def get_grade_limits(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM grade_schedule_limits ORDER BY grade_level"))
    return [dict(r) for r in result.mappings().all()]

@router.post("/grade-limits")
async def save_grade_limit(
    data: GradeLimitSchema,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin)
):
    await db.execute(
        text("INSERT INTO grade_schedule_limits (grade_level, max_lessons_per_day) VALUES (:g, :m) ON CONFLICT (grade_level) DO UPDATE SET max_lessons_per_day=:m"),
        {"g": data.grade_level, "m": data.max_lessons_per_day}
    )
    await db.commit()
    return {"message": "נשמר"}

@router.get("/pedagogical")
async def get_pedagogical(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("SELECT * FROM school_constraints WHERE is_active=true ORDER BY created_at DESC"))
    return [dict(r) for r in result.mappings().all()]

@router.post("/pedagogical")
async def add_pedagogical(
    data: PedagogicalConstraintSchema,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin)
):
    await db.execute(
        text("""INSERT INTO school_constraints 
            (constraint_type, subject_a_id, subject_b_id, numeric_value, weight, raw_text, is_active, source)
            VALUES (:ct, :sa, :sb, :nv, :w, :rt, true, 'manual')"""),
        {"ct": data.constraint_type, "sa": data.subject_a_id, "sb": data.subject_b_id,
         "nv": data.numeric_value, "w": data.weight, "rt": data.raw_text}
    )
    await db.commit()
    return {"message": "נוסף"}

@router.delete("/pedagogical/{constraint_id}")
async def delete_pedagogical(
    constraint_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin)
):
    await db.execute(
        text("UPDATE school_constraints SET is_active=false WHERE id=:id"),
        {"id": constraint_id}
    )
    await db.commit()
    return {"message": "נמחק"}

from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from app.database import get_db
from app.services.claude_service import parse_teacher_preferences
from app.auth import get_current_teacher
from app.models.teacher import Teacher

router = APIRouter(prefix="/ai", tags=["AI"])


class ParsePreferencesRequest(BaseModel):
    text: str


@router.post("/parse-preferences")
async def parse_preferences(
    request: ParsePreferencesRequest,
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    slots_result = await db.execute(text("SELECT day_of_week, hour_of_day FROM timeslots"))
    valid_slots = [dict(r) for r in slots_result.mappings().all()]

    subjects_result = await db.execute(text("SELECT subject_name FROM subjects"))
    subject_names = [r[0] for r in subjects_result.all()]

    groups_result = await db.execute(text("SELECT group_name FROM student_groups"))
    group_names = [r[0] for r in groups_result.all()]

    try:
        result = parse_teacher_preferences(request.text, valid_slots, subject_names, group_names)
        return {"status": "ok", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI parsing failed: {str(e)}")
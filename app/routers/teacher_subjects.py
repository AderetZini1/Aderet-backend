from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from app.database import get_db
from app.models.teacher import Teacher
from app.auth import get_current_teacher, get_current_admin
from pydantic import BaseModel
from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base

class TeacherSubject(Base):
    __tablename__ = "teacher_subjects"
    id = Column(Integer, primary_key=True, index=True)
    teacher_id = Column(Integer, ForeignKey("teachers.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)

class TeacherSubjectResponse(BaseModel):
    id: int
    teacher_id: int
    subject_id: int

    class Config:
        from_attributes = True

router = APIRouter(prefix="/teacher-subjects", tags=["teacher-subjects"])

@router.get("/me", response_model=List[TeacherSubjectResponse])
async def get_my_subjects(
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    from sqlalchemy import text
    result = await db.execute(
        text("SELECT * FROM teacher_subjects WHERE teacher_id = :tid"),
        {"tid": current_teacher.id}
    )
    rows = result.mappings().all()
    return [dict(r) for r in rows]

@router.get("/for-teacher/{teacher_id}", response_model=List[TeacherSubjectResponse])
async def get_subjects_for_teacher(
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Teacher = Depends(get_current_admin)
):
    from sqlalchemy import text
    result = await db.execute(
        text("SELECT * FROM teacher_subjects WHERE teacher_id = :tid"),
        {"tid": teacher_id}
    )
    return [dict(r) for r in result.mappings().all()]

@router.post("/me/{subject_id}", response_model=TeacherSubjectResponse)
async def add_my_subject(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    from sqlalchemy import text
    try:
        result = await db.execute(
            text("INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (:tid, :sid) RETURNING *"),
            {"tid": current_teacher.id, "sid": subject_id}
        )
        await db.commit()
        return dict(result.mappings().one())
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Already exists")

@router.delete("/me/{subject_id}")
async def remove_my_subject(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    from sqlalchemy import text
    await db.execute(
        text("DELETE FROM teacher_subjects WHERE teacher_id = :tid AND subject_id = :sid"),
        {"tid": current_teacher.id, "sid": subject_id}
    )
    await db.commit()
    return {"message": "Deleted"}

@router.post("/for-teacher/{teacher_id}/{subject_id}", response_model=TeacherSubjectResponse)
async def add_subject_for_teacher(
    teacher_id: int,
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Teacher = Depends(get_current_admin)
):
    from sqlalchemy import text
    try:
        result = await db.execute(
            text("INSERT INTO teacher_subjects (teacher_id, subject_id) VALUES (:tid, :sid) RETURNING *"),
            {"tid": teacher_id, "sid": subject_id}
        )
        await db.commit()
        return dict(result.mappings().one())
    except Exception:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Already exists")

@router.delete("/for-teacher/{teacher_id}/{subject_id}")
async def remove_subject_for_teacher(
    teacher_id: int,
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: Teacher = Depends(get_current_admin)
):
    from sqlalchemy import text
    await db.execute(
        text("DELETE FROM teacher_subjects WHERE teacher_id = :tid AND subject_id = :sid"),
        {"tid": teacher_id, "sid": subject_id}
    )
    await db.commit()
    return {"message": "Deleted"}

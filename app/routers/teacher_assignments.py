from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List

from app.database import get_db
from app.models.teacher_assignment import TeacherAssignment
from app.models.curriculum_requirement import CurriculumRequirement
from app.models.teacher import Teacher
from app.schemas.teacher_assignment import TeacherAssignmentCreate, TeacherAssignmentResponse
from app.auth import get_current_teacher, get_current_admin

router = APIRouter(prefix="/teacher-assignments", tags=["teacher-assignments"])


@router.get("/", response_model=List[TeacherAssignmentResponse])
async def list_assignments(
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher),
):
    result = await db.execute(select(TeacherAssignment))
    return result.scalars().all()

@router.get("/teacher-loads")
async def get_teacher_loads(
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    # לכל מורה: מכסה, סכום שעות שכבר משויכות אליו, וכמה נותר.
    # assigned_hours = סכום weekly_hours של כל הדרישות המשויכות למורה.
    # המכסה נגזרת מ-max_hours (התקרה); min_hours נשמר לתצוגה עתידית.
    result = await db.execute(
        select(
            Teacher.id,
            Teacher.first_name,
            Teacher.last_name,
            Teacher.min_hours,
            Teacher.max_hours,
            func.coalesce(func.sum(CurriculumRequirement.weekly_hours), 0).label("assigned_hours"),
        )
        .outerjoin(TeacherAssignment, TeacherAssignment.teacher_id == Teacher.id)
        .outerjoin(
            CurriculumRequirement,
            CurriculumRequirement.id == TeacherAssignment.cur_requirement_id,
        )
        .group_by(
            Teacher.id,
            Teacher.first_name,
            Teacher.last_name,
            Teacher.min_hours,
            Teacher.max_hours,
        )
    )
    rows = result.all()

    loads = []
    for r in rows:
        quota = r.max_hours  # המכסה = התקרה; יכול להיות None
        assigned = r.assigned_hours or 0
        loads.append({
            "teacher_id": r.id,
            "first_name": r.first_name,
            "last_name": r.last_name,
            "min_hours": r.min_hours,
            "max_hours": r.max_hours,
            "quota": quota,                         # None = לא הוגדרה מכסה
            "assigned_hours": assigned,
            "remaining": (quota - assigned) if quota is not None else None,
            "has_quota": quota is not None,
        })
    return loads


@router.get("/{assignment_id}", response_model=TeacherAssignmentResponse)
async def get_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher),
):
    return await _get_or_404(db, assignment_id)


@router.post("/", response_model=TeacherAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    data: TeacherAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    assignment = TeacherAssignment(
        teacher_id=data.teacher_id,
        cur_requirement_id=data.cur_requirement_id,
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    return assignment

@router.put("/{assignment_id}", response_model=TeacherAssignmentResponse)
async def update_assignment(
    assignment_id: int,
    data: TeacherAssignmentCreate,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    assignment = await _get_or_404(db, assignment_id)
    assignment.teacher_id = data.teacher_id
    assignment.cur_requirement_id = data.cur_requirement_id
    await db.commit()
    await db.refresh(assignment)
    return assignment

@router.delete("/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_assignment(
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    assignment = await _get_or_404(db, assignment_id)
    await db.delete(assignment)
    await db.commit()


async def _get_or_404(db: AsyncSession, assignment_id: int) -> TeacherAssignment:
    result = await db.execute(
        select(TeacherAssignment).where(TeacherAssignment.id == assignment_id)
    )
    assignment = result.scalar_one_or_none()
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Teacher assignment not found"
        )
    return assignment

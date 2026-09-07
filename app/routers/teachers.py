from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.teacher import Teacher
from app.schemas.teacher import TeacherCreate, TeacherUpdate, TeacherResponse
from app.auth import hash_password, get_current_teacher, get_current_admin

router = APIRouter(prefix="/teachers", tags=["teachers"])


@router.get("/", response_model=List[TeacherResponse])
async def list_teachers(
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher),
):
    result = await db.execute(select(Teacher))
    return result.scalars().all()


@router.get("/{teacher_id}", response_model=TeacherResponse)
async def get_teacher(
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher),
):
    teacher = await _get_or_404(db, teacher_id)
    return teacher


@router.post("/", response_model=TeacherResponse, status_code=status.HTTP_201_CREATED)
async def create_teacher(
    data: TeacherCreate,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    teacher = Teacher(
        teacher_identity=data.teacher_identity,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email,
        phone_number=data.phone_number,
        weekly_hours_quota=data.weekly_hours_quota,
        teacher_color=data.teacher_color,
        password_hash=hash_password(data.password),
        is_admin=False,
    )
    db.add(teacher)
    await db.commit()
    await db.refresh(teacher)
    return teacher


@router.patch("/{teacher_id}", response_model=TeacherResponse)
async def update_teacher(
    teacher_id: int,
    data: TeacherUpdate,
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher),
):
    if not current_teacher.is_admin and current_teacher.id != teacher_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own profile",
        )

    teacher = await _get_or_404(db, teacher_id)
    update_data = data.model_dump(exclude_unset=True)
    if "password" in update_data:
        pwd = update_data.pop("password")
        print(f"[DEBUG] password branch hit, pwd={pwd!r}")   # <-- add this
        if pwd:  # only reset if a non-empty password was sent
            teacher.password_hash = hash_password(pwd)
    for field, value in update_data.items():
        setattr(teacher, field, value)

    await db.commit()
    await db.refresh(teacher)
    return teacher


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_teacher(
    teacher_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    teacher = await _get_or_404(db, teacher_id)
    await db.delete(teacher)
    await db.commit()


async def _get_or_404(db: AsyncSession, teacher_id: int) -> Teacher:
    result = await db.execute(select(Teacher).where(Teacher.id == teacher_id))
    teacher = result.scalar_one_or_none()
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Teacher not found")
    return teacher

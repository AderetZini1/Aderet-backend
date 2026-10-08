from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.subject import Subject
from app.models.teacher import Teacher
from app.schemas.subject import SubjectCreate, SubjectUpdate, SubjectResponse
from app.auth import get_current_teacher, get_current_admin

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("/", response_model=List[SubjectResponse])
async def list_subjects(
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher),
):
    result = await db.execute(select(Subject).order_by(Subject.subject_name))
    return result.scalars().all()


@router.get("/{subject_id}", response_model=SubjectResponse)
async def get_subject(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher),
):
    return await _get_or_404(db, subject_id)


@router.post("/", response_model=SubjectResponse, status_code=status.HTTP_201_CREATED)
async def create_subject(
    data: SubjectCreate,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):

    dup = await db.execute(select(Subject.id).where(Subject.subject_name == data.subject_name))
    if dup.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"field_errors": {"subject_name": "קיים מקצוע בעל אותו שם"}},
        )
    
    subject = Subject(subject_name=data.subject_name, required_room_id=data.required_room_id)
    db.add(subject)
    await db.commit()
    await db.refresh(subject)
    return subject


@router.patch("/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: int,
    data: SubjectUpdate,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    subject = await _get_or_404(db, subject_id)
    update_data = data.model_dump(exclude_unset=True)
    new_name = update_data.get("subject_name")
    if new_name is not None and new_name != subject.subject_name:
        dup = await db.execute(
            select(Subject.id).where(Subject.subject_name == new_name, Subject.id != subject_id)
        )
        if dup.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"field_errors": {"subject_name": "קיים מקצוע בעל אותו שם"}},
            )
    for field, value in update_data.items():
        setattr(subject, field, value)
    await db.commit()
    await db.refresh(subject)
    return subject


@router.delete("/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_subject(
    subject_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    subject = await _get_or_404(db, subject_id)
    await db.delete(subject)
    await db.commit()


async def _get_or_404(db: AsyncSession, subject_id: int) -> Subject:
    result = await db.execute(select(Subject).where(Subject.id == subject_id))
    subject = result.scalar_one_or_none()
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found")
    return subject

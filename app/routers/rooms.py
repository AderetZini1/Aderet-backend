from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from app.database import get_db
from app.models.room import Room
from app.models.teacher import Teacher
from app.schemas.room import RoomCreate, RoomUpdate, RoomResponse
from app.auth import get_current_teacher, get_current_admin

router = APIRouter(prefix="/rooms", tags=["rooms"])


@router.get("/", response_model=List[RoomResponse])
async def list_rooms(
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher),
):
    result = await db.execute(select(Room))
    return result.scalars().all()


@router.get("/{room_id}", response_model=RoomResponse)
async def get_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_teacher),
):
    return await _get_or_404(db, room_id)


@router.post("/", response_model=RoomResponse, status_code=status.HTTP_201_CREATED)
async def create_room(
    data: RoomCreate,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):

    dup = await db.execute(select(Room.id).where(Room.room_name == data.room_name))
    if dup.first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"field_errors": {"room_name": "קיים חדר בעל אותו שם"}},
        )

    room = Room(room_name=data.room_name, capacity=data.capacity)
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


@router.patch("/{room_id}", response_model=RoomResponse)
async def update_room(
    room_id: int,
    data: RoomUpdate,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    room = await _get_or_404(db, room_id)
    update_data = data.model_dump(exclude_unset=True)
    new_name = update_data.get("room_name")
    if new_name is not None and new_name != room.room_name:
        dup = await db.execute(
            select(Room.id).where(Room.room_name == new_name, Room.id != room_id)
        )
        if dup.first() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={"field_errors": {"room_name": "קיים חדר בעל אותו שם"}},
            )
    for field, value in update_data.items():
        setattr(room, field, value)
    await db.commit()
    await db.refresh(room)
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: int,
    db: AsyncSession = Depends(get_db),
    _: Teacher = Depends(get_current_admin),
):
    room = await _get_or_404(db, room_id)
    await db.delete(room)
    await db.commit()


async def _get_or_404(db: AsyncSession, room_id: int) -> Room:
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room

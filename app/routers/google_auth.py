from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.auth import create_access_token
from pydantic import BaseModel
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

GOOGLE_CLIENT_ID = "119668439307-1cqr1eppvomer7c1en4sj70snc1igt7c.apps.googleusercontent.com"

router = APIRouter(prefix="/auth/google-oauth", tags=["auth-google"])


class GoogleTokenRequest(BaseModel):
    credential: str


@router.post("/")
async def google_login(payload: GoogleTokenRequest, db: AsyncSession = Depends(get_db)):
    try:
        id_info = id_token.verify_oauth2_token(
            payload.credential,
            google_requests.Request(),
            GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(status_code=401, detail="טוקן גוגל לא תקין")

    email = id_info.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="לא נמצא אימייל בחשבון גוגל")

    result = await db.execute(
        text("SELECT id, first_name, last_name, is_admin FROM teachers WHERE email = :email"),
        {"email": email},
    )
    teacher = result.mappings().first()

    if not teacher:
        raise HTTPException(
            status_code=404,
            detail="לא נמצא חשבון מורה עם האימייל הזה. פנה/י למנהל המערכת."
        )

    access_token = create_access_token(data={"sub": str(teacher["id"])})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "id": teacher["id"],
        "is_admin": teacher["is_admin"],
        "first_name": teacher["first_name"],
        "last_name": teacher["last_name"],
    }
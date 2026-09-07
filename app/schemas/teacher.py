from pydantic import BaseModel, EmailStr
from typing import Optional

# בסיס - שדות משותפים
class TeacherBase(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone_number: Optional[str] = None
    weekly_hours_quota: Optional[int] = None
    teacher_color: Optional[str] = None

# ליצירת מורה חדש - מה מגיע מהFrontend
class TeacherCreate(TeacherBase):
    teacher_identity: str
    password: str  # סיסמה גלויה - תוצפן בשרת לפני שמירה

# לעדכון פרטים - כל השדות אופציונליים
class TeacherUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone_number: Optional[str] = None
    weekly_hours_quota: Optional[int] = None
    teacher_color: Optional[str] = None
    password: Optional[str] = None

# מה שחוזר מהשרת לFrontend
class TeacherResponse(TeacherBase):
    id: int
    teacher_identity: str
    is_admin: bool

    class Config:
        from_attributes = True  # מאפשר המרה מאובייקט SQLAlchemy

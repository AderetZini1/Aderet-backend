from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# בסיס - שדות משותפים
class ScheduleRunBase(BaseModel):
    algorithm: str  # CSP / HILL_CLIMBING / GENETIC
    score: Optional[float] = None  # ציון פונקציית המטרה
    is_selected: bool = False  # המערכת הנבחרת
    is_published: bool = False  # פורסם לצוות
    published_at: Optional[datetime] = None  # מתי פורסם
    admin_note: Optional[str] = None  # הערת מנהל

# ליצירת הרצה חדשה
class ScheduleRunCreate(BaseModel):
    algorithm: str  # רק האלגוריתם נשלח - השאר ממולא אוטומטית

# מה שחוזר מהשרת
class ScheduleRunResponse(ScheduleRunBase):
    id: int
    run_at: datetime  # זמן ההרצה

    class Config:
        from_attributes = True

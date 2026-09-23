from pydantic import BaseModel
from typing import Optional

# בסיס - שדות משותפים
class CurriculumRequirementBase(BaseModel):
    subject_id: int
    student_group_id: int
    weekly_hours: int  # שעות שבועיות נדרשות
    sync_block_identity: Optional[int] = None  # לשיעורים מסונכרנים, NULL לשיעור רגיל

# ליצירת דרישה חדשה
class CurriculumRequirementCreate(CurriculumRequirementBase):
    pass

# לעדכון דרישה
class CurriculumRequirementUpdate(BaseModel):
    weekly_hours: Optional[int] = None
    sync_block_identity: Optional[int] = None

# מה שחוזר מהשרת
class CurriculumRequirementResponse(CurriculumRequirementBase):
    id: int

    class Config:
        from_attributes = True

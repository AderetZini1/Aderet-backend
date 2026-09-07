from typing import Literal, Optional
from pydantic import BaseModel, Field


class AIConstraint(BaseModel):
    day: int = Field(ge=1, le=6)
    hour: int
    type: Literal["unavailable", "preferred_not"]


class AIPreferences(BaseModel):
    priority_early_finish: Optional[int] = None
    priority_no_gaps: Optional[int] = None
    priority_free_day: Optional[int] = None
    priority_consecutive: Optional[int] = None


class AIHomeroom(BaseModel):
    wants_homeroom: Optional[bool] = None
    preferred_group_name: Optional[str] = None  # matched exactly against real group names


class AIParseResult(BaseModel):
    constraints: list[AIConstraint]
    preferences: AIPreferences
    subjects: list[str] = []       # matched exactly against real subject names
    grade_levels: list[int] = []   # 1-6
    homeroom: AIHomeroom = AIHomeroom()
    unmapped: list[str] = []
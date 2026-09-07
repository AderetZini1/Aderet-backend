from typing import Literal, Optional
from pydantic import BaseModel, Field


class AIConstraint(BaseModel):
    day: int = Field(ge=1, le=6)
    hour: int = Field(ge=1, le=8)
    type: Literal["unavailable", "preferred_not"]


class AIPreferences(BaseModel):
    priority_early_finish: Optional[int] = None
    priority_no_gaps: Optional[int] = None
    priority_free_day: Optional[int] = None
    priority_consecutive: Optional[int] = None


class AIParseResult(BaseModel):
    constraints: list[AIConstraint]
    preferences: AIPreferences
    unmapped: list[str]
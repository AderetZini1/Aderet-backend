from typing import Literal, Optional
from pydantic import BaseModel


class AIConstraint(BaseModel):
    day: int
    hour: int
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
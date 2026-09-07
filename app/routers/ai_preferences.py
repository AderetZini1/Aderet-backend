from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.claude_service import parse_teacher_preferences


router = APIRouter(
    prefix="/ai",
    tags=["AI"]
)


class ParsePreferencesRequest(BaseModel):
    text: str


@router.post("/parse-preferences")
async def parse_preferences(request: ParsePreferencesRequest):
    try:
        result = parse_teacher_preferences(request.text)

        return {
            "status": "ok",
            "result": result
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"AI parsing failed: {str(e)}"
        )
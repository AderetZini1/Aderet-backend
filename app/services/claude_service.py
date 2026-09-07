import os
import json
from anthropic import Anthropic
from app.schemas.ai_preferences import AIParseResult

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are part of a school timetable scheduling system.
Convert a teacher's natural-language preferences into structured JSON.

Return ONLY valid JSON in exactly this structure, no markdown, no extra text:

{
  "constraints": [{"day": 1, "hour": 1, "type": "unavailable"}],
  "preferences": {
    "priority_early_finish": null,
    "priority_no_gaps": null,
    "priority_free_day": null,
    "priority_consecutive": null
  },
  "unmapped": []
}

Rules:
- day: 1=Sunday ... 6=Friday
- hour: between 1 and 8
- constraint type: "unavailable" or "preferred_not"
- "cannot work" -> unavailable
- "prefer not to work" -> preferred_not
- Do not invent constraints the teacher did not mention.
- If something cannot be mapped safely, place it in "unmapped".
- null means the teacher did not mention that preference."""


def parse_teacher_preferences(text: str):
    if not text or not text.strip():
        raise ValueError("empty text")

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1000,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": text}]
    )

    raw_text = response.content[0].text.strip()
    if raw_text.startswith("```"):
        raw_text = raw_text.strip("`").removeprefix("json").strip()

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"[AI parse] invalid JSON from model: {raw_text[:500]}")
        raise

    validated = AIParseResult.model_validate(data)
    return validated.model_dump()
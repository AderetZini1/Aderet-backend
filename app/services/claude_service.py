import os
import json
from collections import defaultdict
from anthropic import Anthropic
from app.schemas.ai_preferences import AIParseResult

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DAY_NAMES = {1: "ראשון", 2: "שני", 3: "שלישי", 4: "רביעי", 5: "חמישי", 6: "שישי"}


def _build_schedule_description(valid_slots: list[dict]) -> str:
    """valid_slots: list of {"day_of_week": int, "hour_of_day": int} from the timeslots table."""
    by_day = defaultdict(list)
    for slot in valid_slots:
        by_day[slot["day_of_week"]].append(slot["hour_of_day"])

    lines = []
    for day in sorted(by_day):
        hours = sorted(by_day[day])
        lines.append(f"- Day {day} ({DAY_NAMES.get(day, day)}): valid hours are {hours}")
    return "\n".join(lines)


def _build_system_prompt(valid_slots: list[dict]) -> str:
    schedule_desc = _build_schedule_description(valid_slots)
    return f"""You are part of a school timetable scheduling system.
Convert a teacher's natural-language preferences into structured JSON.

This school's actual valid schedule (day of week -> valid hour numbers) is:
{schedule_desc}

Return ONLY valid JSON in exactly this structure, no markdown, no extra text:

{{
  "constraints": [{{"day": 1, "hour": 1, "type": "unavailable"}}],
  "preferences": {{
    "priority_early_finish": null,
    "priority_no_gaps": null,
    "priority_free_day": null,
    "priority_consecutive": null
  }},
  "unmapped": []
}}

Rules:
- day: 1=Sunday ... 6=Friday. Only use days that appear in the schedule above.
- hour: MUST be an integer. Only use hour values that are valid for that specific day, per the schedule above.
  Never use null for hour, and never invent an hour number that isn't listed for that day.
- If the teacher mentions a whole day without a specific hour (e.g. "I cannot work on Monday"),
  create one constraint object for EVERY valid hour of that day (per the schedule above), all with the same type.
- constraint type: "unavailable" or "preferred_not"
- "cannot work" -> unavailable
- "prefer not to work" -> preferred_not
- Do not invent constraints the teacher did not mention.
- If a day/hour mentioned by the teacher does not exist in this school's schedule, place that part of the text in "unmapped" instead of guessing.
- If something cannot be mapped safely, place it in "unmapped".
- null means the teacher did not mention that preference (only applies to "preferences", never to "hour")."""


def parse_teacher_preferences(text: str, valid_slots: list[dict]):
    if not text or not text.strip():
        raise ValueError("empty text")
    if not valid_slots:
        raise ValueError("no valid timeslots configured for this school")

    system_prompt = _build_system_prompt(valid_slots)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
        temperature=0,
        system=system_prompt,
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
    result = validated.model_dump()

    # Second line of defense: drop any constraint that doesn't match a real slot,
    # even if the model didn't follow the schedule correctly.
    valid_pairs = {(s["day_of_week"], s["hour_of_day"]) for s in valid_slots}
    kept, dropped = [], []
    for c in result["constraints"]:
        if (c["day"], c["hour"]) in valid_pairs:
            kept.append(c)
        else:
            dropped.append(c)
    result["constraints"] = kept
    if dropped:
        result["unmapped"].append(
            f"{len(dropped)} constraint(s) referenced a day/hour that doesn't exist in the schedule and were dropped."
        )

    return result
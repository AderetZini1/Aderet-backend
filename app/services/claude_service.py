import os
import json
from collections import defaultdict
from anthropic import Anthropic
from app.schemas.ai_preferences import AIParseResult

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

DAY_NAMES = {1: "ראשון", 2: "שני", 3: "שלישי", 4: "רביעי", 5: "חמישי", 6: "שישי"}


def _build_schedule_description(valid_slots: list[dict]) -> str:
    by_day = defaultdict(list)
    for slot in valid_slots:
        by_day[slot["day_of_week"]].append(slot["hour_of_day"])
    lines = []
    for day in sorted(by_day):
        hours = sorted(by_day[day])
        lines.append(f"- Day {day} ({DAY_NAMES.get(day, day)}): valid hours are {hours}")
    return "\n".join(lines)


def _build_system_prompt(valid_slots: list[dict], subject_names: list[str], group_names: list[str]) -> str:
    schedule_desc = _build_schedule_description(valid_slots)
    subjects_desc = ", ".join(subject_names) if subject_names else "(none configured)"
    groups_desc = ", ".join(group_names) if group_names else "(none configured)"

    return f"""You are part of a school timetable scheduling system.
Convert a teacher's natural-language preferences into structured JSON.

This school's actual valid schedule (day of week -> valid hour numbers) is:
{schedule_desc}

This school's actual subject names are:
{subjects_desc}

This school's actual class/group names (for homeroom) are:
{groups_desc}

Return ONLY valid JSON in exactly this structure, no markdown, no extra text:

{{
  "constraints": [{{"day": 1, "hour": 1, "type": "unavailable"}}],
  "preferences": {{
    "priority_early_finish": null,
    "priority_no_gaps": null,
    "priority_free_day": null,
    "priority_consecutive": null
  }},
  "subjects": ["exact subject name from the list above"],
  "grade_levels": [1],
  "homeroom": {{"wants_homeroom": null, "preferred_group_name": null}},
  "unmapped": []
}}

Rules for constraints/hours:
- day: 1=Sunday ... 6=Friday. Only use days that appear in the schedule above.
- hour: MUST be an integer. Only use hour values valid for that specific day, per the schedule above.
  Never use null for hour. If the teacher mentions a whole day without a specific hour, create one
  constraint for EVERY valid hour of that day, all with the same type.
- constraint type: "unavailable" or "preferred_not". "cannot work" -> unavailable, "prefer not to" -> preferred_not.

Rules for subjects:
- The teacher may use abbreviations, nicknames, or slightly different phrasing for a subject
  (e.g. "חנג" or "חינוך גופני" both mean the subject "חינוך גופני"; "זהב" or "זהירות בדרכים" both
  mean the subject "זהירות בדרכים"). Use your knowledge of common Hebrew school subject
  abbreviations to match what the teacher wrote to the CLOSEST subject name in the list above.
- Only include a subject in "subjects" if you are confident it matches one from the list above.
  Always use the EXACT full name as it appears in the list, never the abbreviation the teacher used.
- If the teacher mentions a subject that does not clearly match any subject in the list, do not
  guess — place that part of the text in "unmapped" instead.

Rules for grade_levels:
- Grade levels are 1 through 6 (א'-ו'). Include any grade level the teacher explicitly says they
  want or don't want to teach. If they say e.g. "לא רוצה ללמד כיתה ג'" this is a negative preference —
  still extract the grade number 3 into "unmapped" with a short note, since grade_levels here only
  represents grades the teacher WANTS to teach, not excludes.

Rules for homeroom:
- If the teacher expresses wanting or not wanting to be a homeroom teacher ("מחנך/ת"), set
  wants_homeroom to true or false accordingly.
- If they name a specific preferred class/group, match it to the EXACT group name from the list
  above and put it in preferred_group_name. Only if confident of the match; otherwise leave null
  and note it in unmapped.

General rules:
- Do not invent constraints, subjects, or groups the teacher did not mention.
- If a day/hour mentioned by the teacher does not exist in this school's schedule, or a subject/group
  cannot be confidently matched, place that part of the text in "unmapped" instead of guessing.
- null/empty means the teacher did not mention that item."""


def parse_teacher_preferences(
    text: str,
    valid_slots: list[dict],
    subject_names: list[str],
    group_names: list[str],
):
    if not text or not text.strip():
        raise ValueError("empty text")
    if not valid_slots:
        raise ValueError("no valid timeslots configured for this school")

    system_prompt = _build_system_prompt(valid_slots, subject_names, group_names)

    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1500,
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

    # Second line of defense: constraints must match real slots
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
            f"{len(dropped)} constraint(s) referenced a day/hour that doesn't exist and were dropped."
        )

    # Second line of defense: subjects must match real names exactly
    valid_subjects = set(subject_names)
    kept_subjects = [s for s in result["subjects"] if s in valid_subjects]
    dropped_subjects = [s for s in result["subjects"] if s not in valid_subjects]
    result["subjects"] = kept_subjects
    if dropped_subjects:
        result["unmapped"].append(
            f"Subject(s) {dropped_subjects} did not match a real subject and were dropped."
        )

    # Second line of defense: grade levels must be 1-6
    result["grade_levels"] = [g for g in result["grade_levels"] if 1 <= g <= 6]

    # Second line of defense: homeroom group must match real name exactly
    valid_groups = set(group_names)
    pref_group = result["homeroom"].get("preferred_group_name")
    if pref_group and pref_group not in valid_groups:
        result["unmapped"].append(f"Group '{pref_group}' did not match a real group and was dropped.")
        result["homeroom"]["preferred_group_name"] = None

    return result

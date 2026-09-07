from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import auth, teachers, rooms, timeslots, subjects, student_groups, teacher_constraints, teacher_assignments, curriculum_requirements, schedule_runs, schedule, submission_windows, teacher_requests, teacher_preferences, teacher_subjects, teacher_grade_levels, teacher_homeroom_prefs, google_auth, notifications, school_settings, ai_preferences

app = FastAPI(
    title="Smartime API",
    description="Smart Timetable Scheduling System",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(teachers.router)
app.include_router(rooms.router)
app.include_router(timeslots.router)
app.include_router(subjects.router)
app.include_router(student_groups.router)
app.include_router(teacher_constraints.router)
app.include_router(teacher_assignments.router)
app.include_router(curriculum_requirements.router)
app.include_router(schedule_runs.router)
app.include_router(schedule.router)
app.include_router(submission_windows.router)
app.include_router(teacher_requests.router)
app.include_router(teacher_preferences.router)
app.include_router(teacher_subjects.router)
app.include_router(teacher_grade_levels.router)
app.include_router(teacher_homeroom_prefs.router)
app.include_router(google_auth.router)
app.include_router(notifications.router)
app.include_router(school_settings.router)
app.include_router(ai_preferences.router)

@app.get("/")
async def root():
    return {"message": "Smartime API is running"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}
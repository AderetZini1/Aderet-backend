from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.database import get_db
from app.models.teacher import Teacher
from app.auth import get_current_teacher, get_current_admin
from pydantic import BaseModel
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
load_dotenv()

class NotificationCreate(BaseModel):
    title: str
    body: str
    teacher_ids: list[int] | None = None

router = APIRouter(prefix="/notifications", tags=["notifications"])

def send_emails_background(teachers, title, body):
    gmail_user = os.getenv("GMAIL_USER")
    gmail_password = os.getenv("GMAIL_APP_PASSWORD")
    print(f"EMAIL TASK STARTED: user={gmail_user}, teachers={len(teachers)}")
    if not gmail_user or not gmail_password:
        print("Gmail credentials not set")
        return
    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(gmail_user, gmail_password)
            for teacher in teachers:
                msg = MIMEMultipart('alternative')
                msg['Subject'] = f"הודעה חדשה: {title}"
                msg['From'] = gmail_user
                msg['To'] = teacher["email"]
                html = f"""
                <div dir="rtl" style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2 style="color: #4a3f35;">הודעה חדשה מהמנהל</h2>
                    <h3 style="color: #8a9e78;">{title}</h3>
                    <p style="color: #4a3f35;">{body}</p>
                    <hr style="border-color: #e2dacc;">
                    <p style="color: #c8baa6; font-size: 12px;">Smartime — מערכת שעות חכמה</p>
                </div>
                """
                msg.attach(MIMEText(html, 'html'))
                server.sendmail(gmail_user, teacher["email"], msg.as_string())
        print(f"Emails sent successfully to {len(teachers)} teachers")
    except Exception as e:
        print(f"Email error: {e}")

@router.post("/")
async def send_notification(
    data: NotificationCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_admin)
):
    result = await db.execute(
        text("INSERT INTO notifications (title, body, created_by) VALUES (:title, :body, :created_by) RETURNING id"),
        {"title": data.title, "body": data.body, "created_by": current_teacher.id}
    )
    notification_id = result.scalar()

    if data.teacher_ids:
        teachers_result = await db.execute(
            text("SELECT id, email, first_name FROM teachers WHERE is_admin = false AND id = ANY(:ids)"),
            {"ids": data.teacher_ids}
        )
    else:
        teachers_result = await db.execute(
            text("SELECT id, email, first_name FROM teachers WHERE is_admin = false")
        )
    teachers = teachers_result.mappings().all()

    for teacher in teachers:
        await db.execute(
            text("INSERT INTO teacher_notifications (notification_id, teacher_id) VALUES (:nid, :tid)"),
            {"nid": notification_id, "tid": teacher["id"]}
        )

    await db.commit()

    teachers_list = [dict(t) for t in teachers]
    background_tasks.add_task(send_emails_background, teachers_list, data.title, data.body)
    return {"message": f"נשלחה התראה ל-{len(teachers)} מורים"}

@router.get("/admin")
async def get_all_notifications(
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_admin)
):
    result = await db.execute(
        text("SELECT * FROM notifications ORDER BY created_at DESC")
    )
    return [dict(r) for r in result.mappings().all()]

@router.get("/me")
async def get_my_notifications(
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    result = await db.execute(
        text("""
            SELECT tn.id, tn.notification_id, n.title, n.body, tn.is_read, n.created_at
            FROM teacher_notifications tn
            JOIN notifications n ON tn.notification_id = n.id
            WHERE tn.teacher_id = :tid
            ORDER BY n.created_at DESC
        """),
        {"tid": current_teacher.id}
    )
    return [dict(r) for r in result.mappings().all()]

@router.patch("/me/{notification_id}/read")
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
    current_teacher: Teacher = Depends(get_current_teacher)
):
    await db.execute(
        text("UPDATE teacher_notifications SET is_read = true, read_at = NOW() WHERE notification_id = :nid AND teacher_id = :tid"),
        {"nid": notification_id, "tid": current_teacher.id}
    )
    await db.commit()
    return {"message": "נסומן כנקרא"}

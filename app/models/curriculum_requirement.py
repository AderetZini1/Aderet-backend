from sqlalchemy import Column, Integer, ForeignKey
from app.database import Base

class CurriculumRequirement(Base):
    __tablename__ = "curriculum_requirements"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    student_group_id = Column(Integer, ForeignKey("student_groups.id"), nullable=False)
    weekly_hours = Column(Integer, nullable=False)
    sync_block_identity = Column(Integer, nullable=True)

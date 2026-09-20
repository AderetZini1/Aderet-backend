from sqlalchemy import Column, Integer, String, Boolean
from app.database import Base

class Teacher(Base):
    __tablename__ = "teachers"  

    id = Column(Integer, primary_key=True, index=True)
    teacher_identity = Column(String, unique=True, nullable=False)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    password_hash = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone_number = Column(String, nullable=True)
    min_hours = Column(Integer, nullable=True)
    max_hours = Column(Integer, nullable=True)
    teacher_color = Column(String, nullable=True) 

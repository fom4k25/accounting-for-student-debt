from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Debt(Base):
    __tablename__ = "debts"

    id = Column(Integer, primary_key=True, index=True)
    subject = Column(String)
    student_id = Column(Integer, ForeignKey("students.id", ondelete="CASCADE"))
    status = Column(String, default="активна")
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="debts")
    schedule = relationship("Schedule", back_populates="debt", uselist=False, cascade="all, delete-orphan")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    faculty = Column(String)
    group = Column(String)
    student_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    debts = relationship("Debt", back_populates="student", cascade="all, delete-orphan")

class Schedule(Base):
    __tablename__ = "schedule"

    id = Column(Integer, primary_key=True, index=True)
    debt_id = Column(Integer, ForeignKey("debts.id", ondelete="CASCADE"))
    group = Column(String)
    teacher = Column(String)
    date = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    debt = relationship("Debt", back_populates="schedule") 
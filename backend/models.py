from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, JSON, DateTime, Float
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base

class Professor(Base):
    __tablename__ = "professors"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    office = Column(String, nullable=True)
    rank = Column(String)  # e.g., Tenured, Tenure-Track, Adjunct, Visiting
    max_sections = Column(Integer, default=3)
    active = Column(Boolean, default=True)

    sections = relationship("Section", back_populates="professor")
    preferences = relationship("Preference", back_populates="professor")
    email_logs = relationship("EmailLog", back_populates="professor")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True)  # e.g., ECON 301
    name = Column(String)
    credits = Column(Integer, default=3)
    level = Column(Integer)  # e.g., 100, 300, 400
    min_sections = Column(Integer, default=1)
    max_sections = Column(Integer, default=5)
    requires_lab = Column(Boolean, default=False)

    sections = relationship("Section", back_populates="course")


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id = Column(Integer, primary_key=True, index=True)
    days = Column(String)  # e.g., "MWF", "TTh"
    start_time = Column(String)  # e.g., "09:00"
    end_time = Column(String)  # e.g., "09:50"
    label = Column(String)  # e.g., "MWF 9:00am"
    active = Column(Boolean, default=True)

    sections = relationship("Section", back_populates="timeslot")


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    semester = Column(String)  # e.g., "Fall"
    year = Column(Integer)
    status = Column(String, default="Draft")  # Draft, Finalized
    solver_log = Column(String, nullable=True)
    finalized_at = Column(DateTime, nullable=True)
    excel_path = Column(String, nullable=True)

    sections = relationship("Section", back_populates="schedule")


class Section(Base):
    __tablename__ = "sections"

    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(Integer, ForeignKey("courses.id"))
    professor_id = Column(Integer, ForeignKey("professors.id"), nullable=True)
    timeslot_id = Column(Integer, ForeignKey("time_slots.id"), nullable=True)
    schedule_id = Column(Integer, ForeignKey("schedules.id"))
    status = Column(String, default="Pending")

    course = relationship("Course", back_populates="sections")
    professor = relationship("Professor", back_populates="sections")
    timeslot = relationship("TimeSlot", back_populates="sections")
    schedule = relationship("Schedule", back_populates="sections")


class Preference(Base):
    __tablename__ = "preferences"

    id = Column(Integer, primary_key=True, index=True)
    professor_id = Column(Integer, ForeignKey("professors.id"))
    semester = Column(String)
    year = Column(Integer)
    raw_email = Column(String, nullable=True)
    parsed_json = Column(JSON, nullable=True)
    confidence = Column(Float, nullable=True)
    admin_approved = Column(Boolean, default=False)
    received_at = Column(DateTime, default=datetime.utcnow)

    professor = relationship("Professor", back_populates="preferences")


class EmailLog(Base):
    __tablename__ = "email_log"

    id = Column(Integer, primary_key=True, index=True)
    professor_id = Column(Integer, ForeignKey("professors.id"))
    direction = Column(String)  # 'sent' or 'received'
    gmail_thread_id = Column(String, nullable=True)
    subject = Column(String)
    status = Column(String)
    sent_at = Column(DateTime, default=datetime.utcnow)

    professor = relationship("Professor", back_populates="email_logs")


class Constraint(Base):
    __tablename__ = "constraints"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)  # 'hard' or 'soft'
    name = Column(String)
    value_json = Column(JSON, nullable=True)
    description = Column(String)
    active = Column(Boolean, default=True)
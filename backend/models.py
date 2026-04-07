from datetime import datetime
from typing import Any, Optional

from sqlalchemy import ForeignKey, JSON, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Room(Base):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint('building', 'room_number', name='uix_room_building_number'),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    building: Mapped[str] = mapped_column()
    room_number: Mapped[str] = mapped_column()
    capacity: Mapped[int] = mapped_column()

    sections = relationship("Section", back_populates="room")


class Professor(Base):
    __tablename__ = "professors"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    tcu_id: Mapped[Optional[str]] = mapped_column(unique=True, index=True, default=None)
    name: Mapped[str] = mapped_column(index=True)
    email: Mapped[str] = mapped_column(unique=True, index=True)
    office: Mapped[Optional[str]] = mapped_column(default=None)
    rank: Mapped[str] = mapped_column()  # e.g., Tenured, Tenure-Track, Adjunct, Visiting
    fall_count: Mapped[int] = mapped_column(default=3)
    spring_count: Mapped[int] = mapped_column(default=3)
    active: Mapped[bool] = mapped_column(default=True)

    sections = relationship("Section", back_populates="professor")
    preferences = relationship("Preference", back_populates="professor")
    email_logs = relationship("EmailLog", back_populates="professor")


class CourseTemplate(Base):
    __tablename__ = "course_templates"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(index=True)
    name: Mapped[str] = mapped_column()
    credits: Mapped[int] = mapped_column(default=3)
    level: Mapped[int] = mapped_column()
    default_min_sections: Mapped[int] = mapped_column(default=1)
    default_max_sections: Mapped[int] = mapped_column(default=5)
    default_capacity: Mapped[int] = mapped_column(default=45)

    core_ssc: Mapped[bool] = mapped_column(default=False)
    core_ht: Mapped[bool] = mapped_column(default=False)
    core_ga: Mapped[bool] = mapped_column(default=False)
    core_wem: Mapped[bool] = mapped_column(default=False)
    
    courses = relationship("Course", back_populates="template")


class Course(Base):
    __tablename__ = "courses"
    __table_args__ = (UniqueConstraint('code', 'name', 'semester', 'year', name='uix_course_code_name_term'),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    template_id: Mapped[Optional[int]] = mapped_column(ForeignKey("course_templates.id"), default=None)
    code: Mapped[str] = mapped_column(index=True)  # e.g. ECON 10223, can have duplicates for special topics
    name: Mapped[str] = mapped_column()
    semester: Mapped[str] = mapped_column(index=True)
    year: Mapped[int] = mapped_column(index=True)
    credits: Mapped[int] = mapped_column(default=3)
    level: Mapped[int] = mapped_column()  # e.g., 10000, 30000, 40000
    min_sections: Mapped[int] = mapped_column(default=1)
    max_sections: Mapped[int] = mapped_column(default=5)
    capacity: Mapped[int] = mapped_column(default=45)

    # Core requirements satisfied by this course
    core_ssc: Mapped[bool] = mapped_column(default=False)
    core_ht: Mapped[bool] = mapped_column(default=False)
    core_ga: Mapped[bool] = mapped_column(default=False)
    core_wem: Mapped[bool] = mapped_column(default=False)

    template = relationship("CourseTemplate", back_populates="courses")
    sections = relationship("Section", back_populates="course")


class TimeSlot(Base):
    __tablename__ = "time_slots"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    days: Mapped[str] = mapped_column()  # e.g., "MWF", "TR"
    start_time: Mapped[str] = mapped_column()  # e.g., "09:00"
    end_time: Mapped[str] = mapped_column()  # e.g., "09:50"
    label: Mapped[str] = mapped_column()  # e.g., "MWF 9:00am"
    section_number: Mapped[str] = mapped_column(default="000")  # 3-digit zero-padded, e.g. "002"
    max_classes: Mapped[int] = mapped_column(default=5)  # max sections allowed in this slot
    active: Mapped[bool] = mapped_column(default=True)

    sections = relationship("Section", back_populates="timeslot")


class Schedule(Base):
    __tablename__ = "schedules"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    semester: Mapped[str] = mapped_column()  # e.g., "Fall"
    year: Mapped[int] = mapped_column()
    status: Mapped[str] = mapped_column(default="Draft")  # Draft, Finalized
    solver_log: Mapped[Optional[str]] = mapped_column(default=None)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(default=None)
    excel_path: Mapped[Optional[str]] = mapped_column(default=None)

    sections = relationship("Section", back_populates="schedule")


class Section(Base):
    __tablename__ = "sections"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"))
    professor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("professors.id"), default=None)
    timeslot_id: Mapped[Optional[int]] = mapped_column(ForeignKey("time_slots.id"), default=None)
    room_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rooms.id"), default=None)
    schedule_id: Mapped[int] = mapped_column(ForeignKey("schedules.id"))
    status: Mapped[str] = mapped_column(default="Pending")

    course = relationship("Course", back_populates="sections")
    professor = relationship("Professor", back_populates="sections")
    timeslot = relationship("TimeSlot", back_populates="sections")
    room = relationship("Room", back_populates="sections")
    schedule = relationship("Schedule", back_populates="sections")


class Preference(Base):
    __tablename__ = "preferences"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    professor_id: Mapped[int] = mapped_column(ForeignKey("professors.id"))
    semester: Mapped[str] = mapped_column()
    year: Mapped[int] = mapped_column()
    raw_email: Mapped[Optional[str]] = mapped_column(default=None)
    parsed_json: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    confidence: Mapped[Optional[float]] = mapped_column(default=None)
    admin_approved: Mapped[bool] = mapped_column(default=False)
    received_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    professor = relationship("Professor", back_populates="preferences")


class EmailLog(Base):
    __tablename__ = "email_log"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    professor_id: Mapped[Optional[int]] = mapped_column(ForeignKey("professors.id"), default=None)
    direction: Mapped[str] = mapped_column()  # 'sent' or 'received'
    gmail_thread_id: Mapped[Optional[str]] = mapped_column(default=None)
    subject: Mapped[str] = mapped_column()
    status: Mapped[str] = mapped_column()
    sent_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)

    professor = relationship("Professor", back_populates="email_logs")


class Constraint(Base):
    __tablename__ = "constraints"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    type: Mapped[str] = mapped_column()  # 'hard' or 'soft'
    name: Mapped[str] = mapped_column()
    value_json: Mapped[Optional[Any]] = mapped_column(JSON, default=None)
    description: Mapped[str] = mapped_column()
    active: Mapped[bool] = mapped_column(default=True)
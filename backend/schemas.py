from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProfessorBase(BaseModel):
    tcu_id: Optional[str] = None
    name: str
    email: EmailStr
    office: Optional[str] = None
    rank: str
    fall_count: int = 3
    spring_count: int = 3
    active: bool = True

class ProfessorCreate(ProfessorBase):
    pass

class ProfessorResponse(ProfessorBase):
    id: int

    class Config:
        from_attributes = True

class CourseTemplateBase(BaseModel):
    code: str
    name: str
    credits: int = 3
    level: int
    default_min_sections: int = 1
    default_max_sections: int = 5
    default_capacity: int = 45
    core_ssc: bool = False
    core_ht: bool = False
    core_ga: bool = False
    core_wem: bool = False

class CourseTemplateResponse(CourseTemplateBase):
    id: int

    class Config:
        from_attributes = True

class CourseBase(BaseModel):
    template_id: Optional[int] = None
    code: str
    name: str
    semester: str
    year: int
    credits: int = 3
    level: int
    min_sections: int = 1
    max_sections: int = 5
    capacity: int = 45
    core_ssc: bool = False
    core_ht: bool = False
    core_ga: bool = False
    core_wem: bool = False

class CourseResponse(CourseBase):
    id: int

    class Config:
        from_attributes = True

class TimeSlotBase(BaseModel):
    days: str
    start_time: str
    end_time: str
    label: str
    section_number: str = "000"
    max_classes: int = 5
    active: bool = True

class TimeSlotResponse(TimeSlotBase):
    id: int

    class Config:
        from_attributes = True

class RoomBase(BaseModel):
    building: str
    room_number: str
    capacity: int

class RoomResponse(RoomBase):
    id: int

    class Config:
        from_attributes = True

class ProfessorBrief(BaseModel):
    id: int
    name: str
    email: str

    class Config:
        from_attributes = True


class PreferenceResponse(BaseModel):
    id: int
    professor_id: int
    semester: str
    year: int
    raw_email: Optional[str] = None
    parsed_json: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None
    admin_approved: bool
    received_at: datetime
    professor: Optional[ProfessorBrief] = None

    class Config:
        from_attributes = True


class SectionResponse(BaseModel):
    id: int
    course_id: int
    professor_id: Optional[int] = None
    timeslot_id: Optional[int] = None
    room_id: Optional[int] = None
    status: str
    course_code: Optional[str] = None
    course_name: Optional[str] = None
    professor_name: Optional[str] = None
    timeslot_label: Optional[str] = None
    room_building: Optional[str] = None
    room_number: Optional[str] = None
    days: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    semester: Optional[str] = None
    year: Optional[int] = None

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_relations(cls, section):
        return cls(
            id=section.id,
            course_id=section.course_id,
            professor_id=section.professor_id,
            timeslot_id=section.timeslot_id,
            room_id=section.room_id,
            status=section.status,
            course_code=section.course.code if section.course else None,
            course_name=section.course.name if section.course else None,
            professor_name=section.professor.name if section.professor else None,
            timeslot_label=section.timeslot.label if section.timeslot else None,
            room_building=section.room.building if section.room else None,
            room_number=section.room.room_number if section.room else None,
            days=section.timeslot.days if section.timeslot else None,
            start_time=section.timeslot.start_time if section.timeslot else None,
            end_time=section.timeslot.end_time if section.timeslot else None,
            semester=section.schedule.semester if getattr(section, 'schedule', None) else None,
            year=section.schedule.year if getattr(section, 'schedule', None) else None,
        )


class ScheduleResponse(BaseModel):
    id: int
    semester: str
    year: int
    status: str
    finalized_at: Optional[datetime] = None
    sections: List[SectionResponse] = []

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_with_relations(cls, schedule):
        return cls(
            id=schedule.id,
            semester=schedule.semester,
            year=schedule.year,
            status=schedule.status,
            finalized_at=schedule.finalized_at,
            sections=[
                SectionResponse.from_orm_with_relations(s) for s in schedule.sections
            ],
        )
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class ProfessorBase(BaseModel):
    name: str
    email: EmailStr
    office: Optional[str] = None
    rank: str
    max_sections: int = 3
    active: bool = True

class ProfessorCreate(ProfessorBase):
    pass

class ProfessorResponse(ProfessorBase):
    id: int

    class Config:
        from_attributes = True

class CourseBase(BaseModel):
    code: str
    name: str
    credits: int = 3
    level: int
    min_sections: int = 1
    max_sections: int = 5
    requires_lab: bool = False

class CourseResponse(CourseBase):
    id: int

    class Config:
        from_attributes = True

class TimeSlotBase(BaseModel):
    days: str
    start_time: str
    end_time: str
    label: str
    active: bool = True

class TimeSlotResponse(TimeSlotBase):
    id: int

    class Config:
        from_attributes = True
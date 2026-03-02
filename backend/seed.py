from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import Professor, Course, TimeSlot

def seed_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # Check if we already have data
    if db.query(Professor).first():
        print("Database already seeded. Skipping...")
        db.close()
        return

    print("Seeding professors...")
    professors = [
        Professor(name="Dr. Smith", email="smith@university.edu", office="Econ Bldg 101", rank="Tenured", max_sections=3),
        Professor(name="Dr. Jones", email="jones@university.edu", office="Econ Bldg 102", rank="Tenured", max_sections=3),
        Professor(name="Prof. Doe", email="doe@university.edu", office="Econ Bldg 201", rank="Tenure-Track", max_sections=3),
        Professor(name="Dr. Miller", email="miller@university.edu", office="Econ Bldg 305", rank="Visiting", max_sections=4),
        Professor(name="Prof. Garcia", email="garcia@university.edu", office="Econ Bldg 110", rank="Adjunct", max_sections=3),
        Professor(name="Prof. Shah", email="sameep.shah@tcu.edu", office="Lib Giga Lab", rank="Adjunct", max_sections=2),
    ]
    db.add_all(professors)

    print("Seeding courses...")
    courses = [
        Course(code="ECON 10223", name="Intro Microeconomics", level=100, min_sections=4, max_sections=8, core_ssc=True),
        Course(code="ECON 10233", name="Intro Macroeconomics", level=100, min_sections=4, max_sections=6, core_ssc=True),
        Course(code="ECON 30223", name="Intermediate Microeconomics", level=300, min_sections=2, max_sections=3),
        Course(code="ECON 30233", name="Intermediate Macroeconomics", level=300, min_sections=2, max_sections=3),
        Course(code="ECON 30243", name="Contending Perspectives in Economics", level=300, min_sections=2, max_sections=3),
        Course(code="ECON 40313", name="Econometrics", level=400, min_sections=1, max_sections=2, requires_lab=True),
        Course(code="ECON 40123", name="Game Theory", level=400, min_sections=1, max_sections=1),
    ]
    db.add_all(courses)

    print("Seeding time slots...")
    timeslots = [
        TimeSlot(days="MWF", start_time="09:00", end_time="09:50", label="MWF 9:00-9:50"),
        TimeSlot(days="MWF", start_time="10:00", end_time="10:50", label="MWF 10:00-10:50"),
        TimeSlot(days="MWF", start_time="11:00", end_time="11:50", label="MWF 11:00-11:50"),
        TimeSlot(days="MWF", start_time="13:00", end_time="13:50", label="MWF 13:00-13:50"),
        TimeSlot(days="MWF", start_time="14:00", end_time="14:50", label="MWF 14:00-14:50"),
        TimeSlot(days="MWF", start_time="15:00", end_time="15:50", label="MWF 15:00-15:50"),
        TimeSlot(days="MW", start_time="14:00", end_time="15:20", label="MW 14:00-15:20"),
        TimeSlot(days="MW", start_time="16:00", end_time="17:20", label="MW 16:00-17:20"),
        TimeSlot(days="MW", start_time="17:30", end_time="18:50", label="MW 17:30-18:50"),
        TimeSlot(days="TR", start_time="09:30", end_time="10:50", label="TR 9:30-10:50"),
        TimeSlot(days="TR", start_time="11:00", end_time="12:20", label="TR 11:00-12:20"),
        TimeSlot(days="TR", start_time="13:00", end_time="14:20", label="TR 13:00-14:20"),
        TimeSlot(days="TR", start_time="14:30", end_time="15:50", label="TR 14:30-15:50"),
        TimeSlot(days="TR", start_time="16:00", end_time="17:20", label="TR 16:00-17:20"),
        TimeSlot(days="TR", start_time="17:30", end_time="18:50", label="TR 17:30-18:50"),
        TimeSlot(days="T", start_time="18:00", end_time="20:40", label="T 18:00-20:40"),
        TimeSlot(days="R", start_time="18:00", end_time="20:40", label="R 18:00-20:40"),
    ]
    db.add_all(timeslots)

    db.commit()
    db.close()
    print("Seed complete.")

if __name__ == "__main__":
    seed_db()
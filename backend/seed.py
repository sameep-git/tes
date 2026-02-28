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
        Professor(name="Dr. Jones", email="jones@university.edu", office="Econ Bldg 102", rank="Tenured", max_sections=2),
        Professor(name="Prof. Doe", email="doe@university.edu", office="Econ Bldg 201", rank="Tenure-Track", max_sections=3),
        Professor(name="Dr. Miller", email="miller@university.edu", office="Econ Bldg 305", rank="Visiting", max_sections=4),
        Professor(name="Prof. Garcia", email="garcia@university.edu", office="Econ Bldg 110", rank="Adjunct", max_sections=2),
        Professor(name="Prof. Shah", email="sameep.shah@tcu.edu", office="Lib Giga Lab", rank="Adjunct", max_sections=1),
    ]
    db.add_all(professors)

    print("Seeding courses...")
    courses = [
        Course(code="ECON 101", name="Principles of Microeconomics", level=100, min_sections=4, max_sections=8),
        Course(code="ECON 102", name="Principles of Macroeconomics", level=100, min_sections=4, max_sections=6),
        Course(code="ECON 301", name="Intermediate Microeconomics", level=300, min_sections=2, max_sections=3),
        Course(code="ECON 302", name="Intermediate Macroeconomics", level=300, min_sections=2, max_sections=3),
        Course(code="ECON 405", name="Econometrics", level=400, min_sections=1, max_sections=2, requires_lab=True),
        Course(code="ECON 410", name="Game Theory", level=400, min_sections=1, max_sections=1),
        Course(code="ECON 420", name="International Trade", level=400, min_sections=1, max_sections=2),
        Course(code="ECON 450", name="Public Economics", level=400, min_sections=1, max_sections=1),
    ]
    db.add_all(courses)

    print("Seeding time slots...")
    timeslots = [
        TimeSlot(days="MWF", start_time="09:00", end_time="09:50", label="MWF 9:00am"),
        TimeSlot(days="MWF", start_time="10:00", end_time="10:50", label="MWF 10:00am"),
        TimeSlot(days="MWF", start_time="11:00", end_time="11:50", label="MWF 11:00am"),
        TimeSlot(days="MWF", start_time="13:00", end_time="13:50", label="MWF 1:00pm"),
        TimeSlot(days="TTh", start_time="09:30", end_time="10:45", label="TTh 9:30am"),
        TimeSlot(days="TTh", start_time="11:00", end_time="12:15", label="TTh 11:00am"),
        TimeSlot(days="TTh", start_time="13:00", end_time="14:15", label="TTh 1:00pm"),
        TimeSlot(days="TTh", start_time="14:30", end_time="15:45", label="TTh 2:30pm"),
    ]
    db.add_all(timeslots)

    db.commit()
    db.close()
    print("Seed complete.")

if __name__ == "__main__":
    seed_db()
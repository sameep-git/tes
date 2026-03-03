from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import Professor, Course, TimeSlot, Constraint

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
        Professor(name="Rishav Bista",      email="r.bista@tcu.edu",         rank="Associate Professor",                         max_sections=3),
        Professor(name="Douglas Butler",    email="d.butler@tcu.edu",         rank="Instructor I",                                max_sections=4),
        Professor(name="Michael Butler",    email="m.butler@tcu.edu",         rank="Associate Professor",                         max_sections=3),
        Professor(name="Dawn Elliott",      email="d.elliott@tcu.edu",        rank="Associate Professor and Department Chair",     max_sections=2),
        Professor(name="Rosemarie Fike",    email="rosemarie.fike@tcu.edu",   rank="Instructor II",                               max_sections=4),
        Professor(name="Graham Gardner",    email="graham.gardner@tcu.edu",   rank="Assistant Professor",                         max_sections=3),
        Professor(name="Robert Garnett",    email="r.garnett@tcu.edu",        rank="Professor",                                   max_sections=3),
        Professor(name="Stepan Gordeev",    email="s.gordeev@tcu.edu",        rank="Assistant Professor",                         max_sections=2),
        Professor(name="John T. Harvey",    email="j.harvey@tcu.edu",         rank="Hal Wright Professor of Economics",           max_sections=3),
        Professor(name="Zackary Hawley",    email="z.hawley@tcu.edu",         rank="Professor",                                   max_sections=3),
        Professor(name="Weiwei Liu",        email="w.liu1236@tcu.edu",        rank="Associate Professor",                         max_sections=3),
        Professor(name="John Lovett",       email="j.lovett@tcu.edu",         rank="Senior Instructor",                           max_sections=4),
        Professor(name="Stephen Nicar",     email="s.nicar@tcu.edu",          rank="Instructor I",                                max_sections=4),
        Professor(name="Stephen Quinn",     email="s.quinn@tcu.edu",          rank="Professor",                                   max_sections=3),
        Professor(name="Kiril Tochkov",     email="k.tochkov@tcu.edu",        rank="Professor",                                   max_sections=3),
        Professor(name="Isabella Yerby",    email="i.yerby@tcu.edu",          rank="Instructor I",                                max_sections=4),
        Professor(name="Xiaodan Zhao",      email="xiaodan.zhao@tcu.edu",     rank="Visiting Assistant Professor",                max_sections=2),
        Professor(name="Prof. Shah",        email="sameep.shah@tcu.edu",      rank="Adjunct",                                     max_sections=2),
    ]
    db.add_all(professors)

    print("Seeding courses...")
    courses = [
        # 10000 level courses
        Course(code="ECON 10223", name="Intro Microeconomics", level=10000, min_sections=4, max_sections=8, core_ssc=True),
        Course(code="ECON 10233", name="Intro Macroeconomics", level=10000, min_sections=4, max_sections=8, core_ssc=True),

        # 30000 level courses
        Course(code="ECON 30223", name="Intermediate Microeconomics", level=30000, min_sections=2, max_sections=3),
        Course(code="ECON 31223", name="Intermediate Microeconomics: Math Approach", level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30233", name="Intermediate Macroeconomics", level=30000, min_sections=2, max_sections=3),
        Course(code="ECON 30243", name="Contending Perspectives in Economics", level=30000, min_sections=2, max_sections=3),
        Course(code="ECON 30253", name="Hist of Econ Thought", level=30000, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 30433", name="Development Studies", level=30000, min_sections=1, max_sections=2, core_ga=True),
        Course(code="ECON 30443", name="Asian Economics", level=30000, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 30483", name="Financial History", level=30000, min_sections=1, max_sections=2, core_ht=True, core_wem=True),
        
        # 40000 level courses
        Course(code="ECON 40153", name="Eco of Financial Markets", level=40000, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 40313", name="Econometrics", level=40000, min_sections=2, max_sections=3),
        Course(code="ECON 40323", name="Time Series Econometrics", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40513", name="Perspective in Internatl Econ", level=40000, min_sections=1, max_sections=2, core_ga=True),
        Course(code="ECON 40123", name="Game Theory", level=40000, min_sections=1, max_sections=1),
    ]
    db.add_all(courses)

    print("Seeding time slots...")
    timeslots = [
        # MWF timeslots
        TimeSlot(days="MWF", start_time="08:00", end_time="08:50", label="MWF 8:00-8:50", section_number="002", max_classes=8),
        TimeSlot(days="MWF", start_time="09:00", end_time="09:50", label="MWF 9:00-9:50", section_number="010", max_classes=10),
        TimeSlot(days="MWF", start_time="10:00", end_time="10:50", label="MWF 10:00-10:50", section_number="020", max_classes=10),
        TimeSlot(days="MWF", start_time="11:00", end_time="11:50", label="MWF 11:00-11:50", section_number="030", max_classes=10),
        TimeSlot(days="MWF", start_time="12:00", end_time="12:50", label="MWF 12:00-12:50", section_number="040", max_classes=10),
        TimeSlot(days="MWF", start_time="13:00", end_time="13:50", label="MWF 13:00-13:50", section_number="050", max_classes=10),
        TimeSlot(days="MWF", start_time="14:00", end_time="14:50", label="MWF 14:00-14:50", section_number="060", max_classes=10),
        TimeSlot(days="MWF", start_time="15:00", end_time="15:50", label="MWF 15:00-15:50", section_number="070", max_classes=4),

        # MW timeslots
        TimeSlot(days="MW", start_time="16:00", end_time="17:20", label="MW 16:00-17:20", section_number="074", max_classes=4),
        TimeSlot(days="MW", start_time="17:30", end_time="18:50", label="MW 17:30-18:50", section_number="080", max_classes=4),
        TimeSlot(days="MW", start_time="19:00", end_time="20:20", label="MW 19:00-20:20", section_number="080", max_classes=4),

        # M timeslots
        TimeSlot(days="M", start_time="19:00", end_time="21:40", label="M 19:00-21:40", section_number="080", max_classes=3),

        # W timeslots
        TimeSlot(days="W", start_time="19:00", end_time="21:40", label="W 19:00-21:40", section_number="080", max_classes=3),

        # TR timeslots
        TimeSlot(days="TR", start_time="08:00", end_time="09:20", label="TR 8:00-9:20", section_number="005", max_classes=10),
        TimeSlot(days="TR", start_time="09:30", end_time="10:50", label="TR 9:30-10:50", section_number="015", max_classes=20),
        TimeSlot(days="TR", start_time="11:00", end_time="12:20", label="TR 11:00-12:20", section_number="035", max_classes=10),
        TimeSlot(days="TR", start_time="12:30", end_time="13:50", label="TR 12:30-13:50", section_number="045", max_classes=10),
        TimeSlot(days="TR", start_time="14:00", end_time="15:20", label="TR 14:00-15:20", section_number="055", max_classes=10),
        TimeSlot(days="TR", start_time="15:30", end_time="16:50", label="TR 15:30-16:50", section_number="065", max_classes=10),
        TimeSlot(days="TR", start_time="17:00", end_time="18:20", label="TR 17:00-18:20", section_number="080", max_classes=5),
        TimeSlot(days="TR", start_time="18:30", end_time="19:50", label="TR 18:30-19:50", section_number="080", max_classes=5),
        TimeSlot(days="TR", start_time="20:00", end_time="21:20", label="TR 20:00-21:20", section_number="080", max_classes=5),

        # T timeslots
        TimeSlot(days="T", start_time="18:30", end_time="21:10", label="T 18:30-21:10", section_number="080", max_classes=3),

        # R timeslots
        TimeSlot(days="R", start_time="18:30", end_time="21:10", label="R 18:30-21:10", section_number="080", max_classes=3),
    ]
    db.add_all(timeslots)

    print("Seeding constraints...")
    constraints = [
        Constraint(
            type="hard",
            name="prime_time",
            value_json={"start_time": "08:45", "end_time": "14:45", "max_percentage": 65},
            description="At most 65% of sections may start during the 8:45-14:45 window",
            active=True,
        ),
        Constraint(
            type="hard",
            name="blocked_timeslots",
            value_json={"labels": ["MWF 12:00-12:50"]},
            description="Econ department policy: no classes scheduled during MWF 12:00-12:50",
            active=True,
        ),
    ]
    db.add_all(constraints)

    db.commit()
    db.close()
    print("Seed complete.")

if __name__ == "__main__":
    seed_db()
from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import Professor, Course, TimeSlot, Constraint, Schedule, Section, Preference

def seed_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    print("Clearing old data...")
    db.query(Section).delete()
    db.query(Schedule).delete()
    db.query(Constraint).delete()
    db.query(TimeSlot).delete()
    db.query(Course).delete()
    db.query(Professor).delete()
    db.commit()

    print("Seeding professors...")
    professors = [
        Professor(name="Graham Gardner", email="graham.gardner@tcu.edu", rank="Assistant Professor", max_sections=3),
        Professor(name="Stepan Gordeev", email="s.gordeev@tcu.edu", rank="Assistant Professor", max_sections=3),
        Professor(name="Maxwell Bullard", email="m.bullard@tcu.edu", rank="Assistant Professor", max_sections=3),
        Professor(name="Haley Wilbert", email="h.wilbert@tcu.edu", rank="Assistant Professor", max_sections=3),
        Professor(name="Rishav Bista", email="r.bista@tcu.edu", rank="Associate Professor", max_sections=3),
        Professor(name="Dawn Elliott", email="d.elliott@tcu.edu", rank="Associate Professor", max_sections=3),
        Professor(name="Weiwei Liu", email="w.liu1236@tcu.edu", rank="Associate Professor", max_sections=3),
        Professor(name="Rob Garnett", email="r.garnett@tcu.edu", rank="Professor", max_sections=3),
        Professor(name="John Harvey", email="j.harvey@tcu.edu", rank="Professor", max_sections=3),
        Professor(name="Zack Hawley", email="z.hawley@tcu.edu", rank="Professor", max_sections=3),
        Professor(name="Stephen Quinn", email="s.quinn@tcu.edu", rank="Professor", max_sections=3),
        Professor(name="Kiril Tochkov", email="k.tochkov@tcu.edu", rank="Professor", max_sections=3),
        Professor(name="Isabella Yerby", email="i.yerby@tcu.edu", rank="Instructor I", max_sections=4),
        Professor(name="Douglas Glenn Butler", email="d.butler@tcu.edu", rank="Instructor I", max_sections=4),
        Professor(name="Michael Butler", email="m.butler@tcu.edu", rank="Instructor I", max_sections=4),
        Professor(name="John Lovett", email="j.lovett@tcu.edu", rank="Instructor I", max_sections=4),
        Professor(name="Stephen Nicar", email="s.nicar@tcu.edu", rank="Instructor I", max_sections=4),
        Professor(name="Rosemarie Fike", email="rosemarie.fike@tcu.edu", rank="Instructor II", max_sections=4),
        Professor(name="Xiaodan Zhao", email="xiaodan.zhao@tcu.edu", rank="Adjunct", max_sections=2),
        Professor(name="Lee Bailiff", email="lee.bailiff@tcu.edu", rank="Adjunct", max_sections=2),
        Professor(name="Horacio Cocchi", email="h.cocchi@tcu.edu", rank="Adjunct", max_sections=2),
        Professor(name="John Powers", email="john.powers@tcu.edu", rank="Adjunct", max_sections=2),
        Professor(name="Julie Russell", email="julie.russell@tcu.edu", rank="Adjunct", max_sections=2),
        Professor(name="Justin Sheffield", email="j.b.sheffield@tcu.edu", rank="Adjunct", max_sections=2),
        Professor(name="Jill Trask", email="j.trask@tcu.edu", rank="Adjunct", max_sections=2),
    ]
    db.add_all(professors)

    print("Seeding courses...")
    semester = "Fall"
    year = 2026
    
    courses = [
        # 10000 level courses (Intros)
        Course(code="ECON 10223", name="Intro Microeconomics", semester=semester, year=year, level=10000, min_sections=4, max_sections=8, core_ssc=True),
        Course(code="ECON 10233", name="Intro Macroeconomics", semester=semester, year=year, level=10000, min_sections=4, max_sections=8, core_ssc=True),
        Course(code="ECON 10223", name="Intro Micro - Honors", semester=semester, year=year, level=10000, min_sections=1, max_sections=2, core_ssc=True),
        Course(code="ECON 10233", name="Intro Macro - Honors", semester=semester, year=year, level=10000, min_sections=1, max_sections=2, core_ssc=True),

        # 30000 level courses (Foundations & Electives)
        Course(code="ECON 30223", name="Intermediate Microeconomics", semester=semester, year=year, level=30000, min_sections=2, max_sections=3),
        Course(code="ECON 31223", name="Intermediate Micro: Math Approach", semester=semester, year=year, level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30233", name="Intermediate Macroeconomics", semester=semester, year=year, level=30000, min_sections=2, max_sections=3),
        Course(code="ECON 31233", name="Intermediate Macro: Math Approach", semester=semester, year=year, level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30243", name="Contending Perspectives in Economics", semester=semester, year=year, level=30000, min_sections=2, max_sections=3),
        Course(code="ECON 30213", name="Development Theory", semester=semester, year=year, level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30253", name="History of Economic Thought", semester=semester, year=year, level=30000, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 30433", name="Development Studies", semester=semester, year=year, level=30000, min_sections=1, max_sections=2, core_ga=True),
        Course(code="ECON 30443", name="Asian Economics", semester=semester, year=year, level=30000, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 30473", name="Regional and Urban Economics", semester=semester, year=year, level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30483", name="Financial History", semester=semester, year=year, level=30000, min_sections=1, max_sections=2, core_ht=True, core_wem=True),
        Course(code="ECON 30503", name="Health Economics", semester=semester, year=year, level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30523", name="Resource and Energy Economics", semester=semester, year=year, level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30543", name="Environmental Economics and Policy", semester=semester, year=year, level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30733", name="European Economic History II", semester=semester, year=year, level=30000, min_sections=1, max_sections=2, core_ht=True),
        Course(code="ECON 30773", name="Public Choice", semester=semester, year=year, level=30000, min_sections=1, max_sections=2),
        
        # 40000 level courses
        Course(code="ECON 40313", name="Econometrics", semester=semester, year=year, level=40000, min_sections=2, max_sections=3),
        Course(code="ECON 40323", name="Time Series Econometrics", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40123", name="Game Theory", semester=semester, year=year, level=40000, min_sections=1, max_sections=1),
        Course(code="ECON 40143", name="Public Finance", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40153", name="Economics of Financial Markets", semester=semester, year=year, level=40000, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 40213", name="International Trade and Payments", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40223", name="International Monetary Economics", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40333", name="Machine Learning in Economics", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40433", name="Law and Economics", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40493", name="Macro Analysis and Communication", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40513", name="Perspective in Internatl Econ", semester=semester, year=year, level=40000, min_sections=1, max_sections=2, core_ga=True),
        
        # 40970 Special Topics
        Course(code="ECON 40970", name="Real Estate Principles", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Causal Inferences", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Growth", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Agriculture (Development)", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Scientific Computation", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="International Financial Crises", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Big Data in Economics", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Global Health", semester=semester, year=year, level=40000, min_sections=1, max_sections=2),
    ]
    semester = "Spring"
    year = 2026
    spring_courses = [
        Course(code="ECON 10223", name="Intro Microeconomics", semester=semester, year=year, level=10000, credits=3, min_sections=16, max_sections=18, core_ssc=True),
        Course(code="ECON 10233", name="Intro Macroeconomics", semester=semester, year=year, level=10000, credits=3, min_sections=10, max_sections=12, core_ssc=True),
        Course(code="ECON 30003", name="Junior Honors Seminar", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=3),
        Course(code="ECON 30223", name="Intermed Microeconomics", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=3),
        Course(code="ECON 30233", name="Intermed Macroeconomics", semester=semester, year=year, level=30000, credits=3, min_sections=2, max_sections=4),
        Course(code="ECON 30243", name="Contending Perspectives in Eco", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=3),
        Course(code="ECON 30253", name="Hist of Econ Thought", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 30433", name="Development Studies", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=2, core_ga=True),
        Course(code="ECON 30443", name="Asian Economics", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=3, core_wem=True),
        Course(code="ECON 30483", name="Financial History", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=3, core_ht=True, core_wem=True),
        Course(code="ECON 30543", name="Environ Econ & Policy", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=2),
        Course(code="ECON 30733", name="European Economic History II", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=2, core_ht=True),
        Course(code="ECON 30773", name="Public Choice", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=3),
        Course(code="ECON 31223", name="Inter Micro: Math Approach", semester=semester, year=year, level=30000, credits=3, min_sections=1, max_sections=2),
        Course(code="ECON 40003", name="Senior Honors Resh Paper", semester=semester, year=year, level=40000, credits=3, min_sections=1, max_sections=3, core_wem=True),
        Course(code="ECON 40143", name="Public Finance", semester=semester, year=year, level=40000, credits=3, min_sections=1, max_sections=2),
        Course(code="ECON 40153", name="Eco Of Financial Markets", semester=semester, year=year, level=40000, credits=3, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 40213", name="International Trade/Pmts", semester=semester, year=year, level=40000, credits=3, min_sections=1, max_sections=2),
        Course(code="ECON 40313", name="Econometrics", semester=semester, year=year, level=40000, credits=3, min_sections=1, max_sections=3),
        Course(code="ECON 40323", name="Time Series Econometrics", semester=semester, year=year, level=40000, credits=3, min_sections=1, max_sections=2),
        Course(code="ECON 40513", name="Perspective in Internatl Econ", semester=semester, year=year, level=40000, credits=3, min_sections=1, max_sections=2, core_ga=True),
        Course(code="ECON 40970", name="Experimental Course - Big Data in Economics", semester=semester, year=year, level=40000, credits=3, min_sections=1, max_sections=3),
        Course(code="ECON 40990", name="Economics Internship", semester=semester, year=year, level=40000, credits=3, min_sections=1, max_sections=3),
    ]
    courses.extend(spring_courses)
    db.add_all(courses)

    print("Seeding time slots...")
    timeslots_data = [
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
        TimeSlot(days="T", start_time="18:00", end_time="20:40", label="T 18:00-20:40", section_number="080", max_classes=3),
        TimeSlot(days="T", start_time="18:30", end_time="21:10", label="T 18:30-21:10", section_number="080", max_classes=3),
        TimeSlot(days="T", start_time="19:00", end_time="21:40", label="T 19:00-21:40", section_number="080", max_classes=3),

        # R timeslots
        TimeSlot(days="R", start_time="18:30", end_time="21:10", label="R 18:30-21:10", section_number="080", max_classes=3),
        TimeSlot(days="R", start_time="19:00", end_time="21:40", label="R 19:00-21:40", section_number="080", max_classes=3),
    ]
    db.add_all(timeslots_data)

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

    print("Seeding preferences...")
    # Get professors
    graham = db.query(Professor).filter_by(name="Graham Gardner").first()
    stepan = db.query(Professor).filter_by(name="Stepan Gordeev").first()
    maxwell = db.query(Professor).filter_by(name="Maxwell Bullard").first()

    if graham and stepan and maxwell:
        # Add preferences
        preferences = [
            Preference(
                professor_id=graham.id,
                semester="Spring",
                year=2026,
                raw_email="I would like to teach Intro Microeconomics and Intermed Microeconomics. I prefer MWF mornings and avoid T R classes if possible. Please don't give me 8am.",
                parsed_json={
                    "preferred_courses": ["ECON 10223 | Intro Microeconomics", "ECON 30223 | Intermed Microeconomics"],
                    "avoid_courses": [],
                    "preferred_timeslots": ["MWF 9:00-9:50", "MWF 10:00-10:50", "MWF 11:00-11:50"],
                    "avoid_timeslots": ["MWF 8:00-8:50"],
                    "avoid_days": ["T", "R"],
                    "max_load": 3,
                    "wants_back_to_back": False,
                    "on_leave": False
                },
                confidence=0.92,
                admin_approved=True
            ),
            Preference(
                professor_id=stepan.id,
                semester="Spring",
                year=2026,
                raw_email="I'm open to teaching Macroeconomics and Econometrics. TR schedule is preferred. Thanks.",
                parsed_json={
                    "preferred_courses": ["ECON 10233 | Intro Macroeconomics", "ECON 40313 | Econometrics"],
                    "avoid_courses": [],
                    "preferred_timeslots": ["TR 9:30-10:50", "TR 11:00-12:20", "TR 12:30-13:50"],
                    "avoid_timeslots": [],
                    "avoid_days": ["M", "W", "F"],
                    "max_load": 3,
                    "wants_back_to_back": True,
                    "on_leave": False
                },
                confidence=0.88,
                admin_approved=False
            ),
            Preference(
                professor_id=maxwell.id,
                semester="Spring",
                year=2026,
                raw_email="I will be on sabbatical this spring.",
                parsed_json={
                    "preferred_courses": [],
                    "avoid_courses": [],
                    "preferred_timeslots": [],
                    "avoid_timeslots": [],
                    "avoid_days": [],
                    "max_load": 0,
                    "wants_back_to_back": None,
                    "on_leave": True,
                    "notes_for_admin": "Sabbatical"
                },
                confidence=0.95,
                admin_approved=True
            )
        ]
        db.add_all(preferences)
        db.commit()

    # No schedule seeded for now to allow for blank slate
    db.close()
    print("Seed complete.")

if __name__ == "__main__":
    seed_db()
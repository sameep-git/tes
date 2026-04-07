from sqlalchemy.orm import Session
from .database import SessionLocal
from .models import Professor, Course, TimeSlot, Constraint, Schedule, Section, Preference, Room, CourseTemplate

def seed_db():
    # NOTE: Schema is managed by Alembic (run via `alembic upgrade head` or automatically
    # on app startup). Do NOT call Base.metadata.create_all() here — it bypasses migrations.
    db = SessionLocal()
    
    print("Clearing old data...")
    # Delete child records before parent records to respect foreign keys
    db.query(Preference).delete()
    db.query(Section).delete()
    db.query(Schedule).delete()
    db.query(Course).delete()
    db.query(CourseTemplate).delete()
    db.query(Professor).delete()
    db.query(Room).delete()
    db.query(TimeSlot).delete()
    db.query(Constraint).delete()
    db.commit()

    print("Seeding rooms...")
    rooms = [
        Room(building="SAD", room_number="108", capacity=41),
        Room(building="SAD", room_number="110", capacity=23),
        Room(building="SAD", room_number="113", capacity=5),
        Room(building="SAD", room_number="114", capacity=24),
        Room(building="SAD", room_number="115", capacity=32),
        Room(building="SAD", room_number="117", capacity=24),
        Room(building="SAD", room_number="122", capacity=24),
        Room(building="SAD", room_number="123", capacity=34),
        Room(building="SAD", room_number="208", capacity=24),
        Room(building="SAD", room_number="209", capacity=32),
        Room(building="SAD", room_number="216", capacity=18),
        Room(building="SAD", room_number="217", capacity=32),
        Room(building="SAD", room_number="218", capacity=24),
        Room(building="SAD", room_number="221", capacity=22),
        Room(building="SAD", room_number="222", capacity=38),
        Room(building="SAD", room_number="223", capacity=16),
        Room(building="SAD", room_number="420", capacity=24),
        Room(building="SAD", room_number="421", capacity=32),
        Room(building="SAD", room_number="422", capacity=24),
        Room(building="SAD", room_number="442", capacity=24),
        Room(building="SCHAR", room_number="1001", capacity=52),
        Room(building="SCHAR", room_number="1007", capacity=24),
        Room(building="SCHAR", room_number="1008", capacity=64),
        Room(building="SCHAR", room_number="1010", capacity=58),
        Room(building="SCHAR", room_number="1011", capacity=24),
        Room(building="SCHAR", room_number="2003", capacity=20),
        Room(building="SCHAR", room_number="2008", capacity=32),
        Room(building="SCHAR", room_number="2010", capacity=30),
        Room(building="SCHAR", room_number="2011", capacity=15),
        Room(building="SCHAR", room_number="3003", capacity=18),
        Room(building="SCHAR", room_number="3004", capacity=24),
        Room(building="SCHAR", room_number="3019", capacity=15),
        Room(building="SCHAR", room_number="4002", capacity=18),
        Room(building="SCHAR", room_number="4009", capacity=18),
        Room(building="SCHAR", room_number="4015", capacity=22),
        Room(building="SCHAR", room_number="4022", capacity=24),
    ]
    db.add_all(rooms)

    print("Seeding professors...")
    professors = [
        Professor(name="Graham Gardner", email="graham.gardner@tcu.edu", rank="Assistant", fall_count=2, spring_count=3, tcu_id="108016560"),
        Professor(name="Stepan Gordeev", email="s.gordeev@tcu.edu", rank="Assistant", fall_count=2, spring_count=3, tcu_id="108017438"),
        Professor(name="Maxwell Bullard", email="m.bullard@tcu.edu", rank="Assistant", fall_count=2, spring_count=2, tcu_id=None),
        Professor(name="Haley Wilbert", email="h.wilbert@tcu.edu", rank="Assistant", fall_count=2, spring_count=2, tcu_id=None),
        Professor(name="Rishav Bista", email="r.bista@tcu.edu", rank="Associate", fall_count=2, spring_count=1, tcu_id="108012962"),
        Professor(name="Dawn C. Elliott", email="d.elliott@tcu.edu", rank="Associate", fall_count=1, spring_count=1, tcu_id="101072668"),
        Professor(name="Weiwei Liu", email="w.liu1236@tcu.edu", rank="Associate", fall_count=2, spring_count=3, tcu_id="108011770"),
        Professor(name="Robert F. Garnett", email="r.garnett@tcu.edu", rank="Full", fall_count=2, spring_count=3, tcu_id="101009405"),
        Professor(name="John T. Harvey", email="j.harvey@tcu.edu", rank="Full", fall_count=1, spring_count=1, tcu_id="101013266"),
        Professor(name="Zackary B. Hawley", email="z.hawley@tcu.edu", rank="Full", fall_count=1, spring_count=1, tcu_id="107416683"),
        Professor(name="Stephen Quinn", email="s.quinn@tcu.edu", rank="Full", fall_count=3, spring_count=2, tcu_id="101010932"),
        Professor(name="Kiril Tochkov", email="k.tochkov@tcu.edu", rank="Full", fall_count=2, spring_count=3, tcu_id="106697023"),
        Professor(name="Isabella Yerby", email="i.yerby@tcu.edu", rank="Instructor 1", fall_count=4, spring_count=4, tcu_id="108018153"),
        Professor(name="Douglas Glenn Butler", email="d.butler@tcu.edu", rank="Instructor 1", fall_count=4, spring_count=4, tcu_id="106553418"),
        Professor(name="Stephen Nicar", email="s.nicar@tcu.edu", rank="Instructor 1", fall_count=4, spring_count=4, tcu_id="108013472"),
        Professor(name="Rosemarie Fike", email="rosemarie.fike@tcu.edu", rank="Instructor 2", fall_count=4, spring_count=3, tcu_id="108011128"),
        Professor(name="Xiaodan Zhao", email="xiaodan.zhao@tcu.edu", rank="Adjunct", fall_count=3, spring_count=3, tcu_id="108016479"),
        Professor(name="Lee Bailiff", email="lee.bailiff@tcu.edu", rank="Adjunct", fall_count=3, spring_count=3, tcu_id="108010151"),
        Professor(name="Horacio Cocchi", email="h.cocchi@tcu.edu", rank="Adjunct", fall_count=3, spring_count=3, tcu_id="108016491"),
        Professor(name="John Powers", email="john.powers@tcu.edu", rank="Adjunct", fall_count=1, spring_count=1, tcu_id="108017411"),
        Professor(name="Julie Russell", email="julie.russell@tcu.edu", rank="Adjunct", fall_count=2, spring_count=2, tcu_id="108010120"),
        Professor(name="Justin Sheffield", email="j.b.sheffield@tcu.edu", rank="Adjunct", fall_count=2, spring_count=2, tcu_id="103201661"),
        Professor(name="Jill Trask", email="j.trask@tcu.edu", rank="Adjunct", fall_count=3, spring_count=3, tcu_id="108015288"),
    ]
    db.add_all(professors)

    print("Seeding courses templates...")
    
    courses = [
        CourseTemplate(code="ECON 10223", name="Intro Microeconomics", level=10000, credits=3, default_min_sections=4, default_max_sections=8, default_capacity=45, core_ssc=True),
        CourseTemplate(code="ECON 10233", name="Intro Macroeconomics", level=10000, credits=3, default_min_sections=4, default_max_sections=8, default_capacity=45, core_ssc=True),
        CourseTemplate(code="ECON 10223", name="Intro Micro - Honors", level=10000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=45, core_ssc=True),
        CourseTemplate(code="ECON 10233", name="Intro Macro - Honors", level=10000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=45, core_ssc=True),

        CourseTemplate(code="ECON 30223", name="Intermediate Microeconomics", level=30000, credits=3, default_min_sections=2, default_max_sections=3, default_capacity=20),
        CourseTemplate(code="ECON 31223", name="Intermediate Micro: Math Approach", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 30233", name="Intermediate Macroeconomics", level=30000, credits=3, default_min_sections=2, default_max_sections=3, default_capacity=20),
        CourseTemplate(code="ECON 31233", name="Intermediate Macro: Math Approach", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 30243", name="Contending Perspectives in Economics", level=30000, credits=3, default_min_sections=2, default_max_sections=3, default_capacity=20),
        CourseTemplate(code="ECON 30213", name="Development Theory", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 30253", name="History of Economic Thought", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20, core_wem=True),
        CourseTemplate(code="ECON 30433", name="Development Studies", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20, core_ga=True),
        CourseTemplate(code="ECON 30443", name="Asian Economics", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20, core_wem=True),
        CourseTemplate(code="ECON 30473", name="Regional and Urban Economics", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 30483", name="Financial History", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20, core_ht=True, core_wem=True),
        CourseTemplate(code="ECON 30503", name="Health Economics", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 30523", name="Resource and Energy Economics", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 30543", name="Environmental Economics and Policy", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 30733", name="European Economic History II", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20, core_ht=True),
        CourseTemplate(code="ECON 30773", name="Public Choice", level=30000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        
        CourseTemplate(code="ECON 40313", name="Econometrics", level=40000, credits=3, default_min_sections=2, default_max_sections=3, default_capacity=20),
        CourseTemplate(code="ECON 40323", name="Time Series Econometrics", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40123", name="Game Theory", level=40000, credits=3, default_min_sections=1, default_max_sections=1, default_capacity=20),
        CourseTemplate(code="ECON 40143", name="Public Finance", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40153", name="Economics of Financial Markets", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20, core_wem=True),
        CourseTemplate(code="ECON 40213", name="International Trade and Payments", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40223", name="International Monetary Economics", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40333", name="Machine Learning in Economics", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40433", name="Law and Economics", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40493", name="Macro Analysis and Communication", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40513", name="Perspective in Internatl Econ", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20, core_ga=True),
        
        CourseTemplate(code="ECON 40970", name="Real Estate Principles", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40970", name="Causal Inferences", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40970", name="Growth", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40970", name="Agriculture (Development)", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40970", name="Scientific Computation", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40970", name="International Financial Crises", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40970", name="Big Data in Economics", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
        CourseTemplate(code="ECON 40970", name="Global Health", level=40000, credits=3, default_min_sections=1, default_max_sections=2, default_capacity=20),
    ]
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

    db.close()
    print("Seed complete.")

if __name__ == "__main__":
    seed_db()

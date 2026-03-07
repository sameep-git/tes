from sqlalchemy.orm import Session
from .database import engine, Base, SessionLocal
from .models import Professor, Course, TimeSlot, Constraint, Schedule, Section

PAST_SCHEDULE_DATA = [
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '010', 'instructor': 'Douglas Butler', 'days': 'MWF', 'start_time': '09:00', 'end_time': '09:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '015', 'instructor': 'Graham Gardner', 'days': 'TR', 'start_time': '09:30', 'end_time': '10:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '020', 'instructor': 'Douglas Butler', 'days': 'MWF', 'start_time': '10:00', 'end_time': '10:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '021', 'instructor': 'Isabella Ann Yerby', 'days': 'MWF', 'start_time': '10:00', 'end_time': '10:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '022', 'instructor': 'Stephen Nicar', 'days': 'MWF', 'start_time': '10:00', 'end_time': '10:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '030', 'instructor': 'Isabella Ann Yerby', 'days': 'MWF', 'start_time': '11:00', 'end_time': '11:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '035', 'instructor': 'Graham Gardner', 'days': 'TR', 'start_time': '11:00', 'end_time': '12:20'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '050', 'instructor': 'Horacio Cocchi', 'days': 'MWF', 'start_time': '13:00', 'end_time': '13:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '051', 'instructor': 'Rob Garnett', 'days': 'MWF', 'start_time': '13:00', 'end_time': '13:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '055', 'instructor': 'Jill Ann Trask', 'days': 'TR', 'start_time': '14:00', 'end_time': '15:20'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '060', 'instructor': 'Horacio Cocchi', 'days': 'MWF', 'start_time': '14:00', 'end_time': '14:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '065', 'instructor': 'Jill Ann Trask', 'days': 'TR', 'start_time': '15:30', 'end_time': '16:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '070', 'instructor': 'Horacio Cocchi', 'days': 'MWF', 'start_time': '15:00', 'end_time': '15:50'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '074', 'instructor': 'Lee Bailiff', 'days': 'MW', 'start_time': '16:00', 'end_time': '17:20'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '080', 'instructor': 'John Powers', 'days': 'T', 'start_time': '18:00', 'end_time': '20:40'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Microeconomics', 'section': '081', 'instructor': 'Jill Ann Trask', 'days': 'TR', 'start_time': '17:00', 'end_time': '18:20'},
    {'course_code': 'ECON 10223', 'course_name': 'Intro Micro - Honors', 'section': '616', 'instructor': 'Zack Hawley', 'days': 'TR', 'start_time': '09:30', 'end_time': '10:50'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '010', 'instructor': 'Stephen Nicar', 'days': 'MWF', 'start_time': '09:00', 'end_time': '09:50'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '050', 'instructor': 'Stephen Nicar', 'days': 'MWF', 'start_time': '13:00', 'end_time': '13:50'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '060', 'instructor': 'Isabella Ann Yerby', 'days': 'MWF', 'start_time': '14:00', 'end_time': '14:50'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '065', 'instructor': 'Lee Bailiff', 'days': 'TR', 'start_time': '15:30', 'end_time': '16:50'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '066', 'instructor': 'Julie Russell', 'days': 'TR', 'start_time': '15:30', 'end_time': '16:50'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '070', 'instructor': 'Isabella Ann Yerby', 'days': 'MWF', 'start_time': '15:00', 'end_time': '15:50'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '080', 'instructor': 'Xiaodan Zhao', 'days': 'TR', 'start_time': '17:00', 'end_time': '18:20'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '081', 'instructor': 'Julie Russell', 'days': 'TR', 'start_time': '17:00', 'end_time': '18:20'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '082', 'instructor': 'John Lovett', 'days': 'T', 'start_time': '19:00', 'end_time': '21:40'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '083', 'instructor': 'Justin Sheffield', 'days': 'R', 'start_time': '19:00', 'end_time': '21:40'},
    {'course_code': 'ECON 10233', 'course_name': 'Intro Macroeconomics', 'section': '085', 'instructor': 'John Lovett', 'days': 'TR', 'start_time': '17:00', 'end_time': '18:20'},
    {'course_code': 'ECON 30223', 'course_name': 'Intermediate Microeconomics', 'section': '010', 'instructor': 'Michael Butler', 'days': 'MWF', 'start_time': '09:00', 'end_time': '09:50'},
    {'course_code': 'ECON 30223', 'course_name': 'Intermediate Microeconomics', 'section': '050', 'instructor': 'Douglas Butler', 'days': 'MWF', 'start_time': '13:00', 'end_time': '13:50'},
    {'course_code': 'ECON 30233', 'course_name': 'Intermediate Macroeconomics', 'section': '045', 'instructor': 'Stepan Gordeev', 'days': 'TR', 'start_time': '12:30', 'end_time': '13:50'},
    {'course_code': 'ECON 30233', 'course_name': 'Intermediate Macroeconomics', 'section': '060', 'instructor': 'Stephen Nicar', 'days': 'MWF', 'start_time': '14:00', 'end_time': '14:50'},
    {'course_code': 'ECON 30233', 'course_name': 'Intermediate Macroeconomics', 'section': '065', 'instructor': 'Xiaodan Zhao', 'days': 'TR', 'start_time': '15:30', 'end_time': '16:50'},
    {'course_code': 'ECON 30243', 'course_name': 'Contending Perspectives in Economics', 'section': '045', 'instructor': 'Rob Garnett', 'days': 'TR', 'start_time': '12:30', 'end_time': '13:50'},
    {'course_code': 'ECON 30243', 'course_name': 'Contending Perspectives in Economics', 'section': '055', 'instructor': 'Rob Garnett', 'days': 'TR', 'start_time': '14:00', 'end_time': '15:20'},
    {'course_code': 'ECON 30253', 'course_name': 'History of Economic Thought', 'section': '010', 'instructor': 'John Lovett', 'days': 'MWF', 'start_time': '09:00', 'end_time': '09:50'},
    {'course_code': 'ECON 30433', 'course_name': 'Development Studies', 'section': '015', 'instructor': 'Dawn Elliott', 'days': 'TR', 'start_time': '09:30', 'end_time': '10:50'},
    {'course_code': 'ECON 30443', 'course_name': 'Asian Economics', 'section': '074', 'instructor': 'Kiril Tochkov', 'days': 'MW', 'start_time': '16:00', 'end_time': '17:20'},
    {'course_code': 'ECON 30443', 'course_name': 'Asian Economics', 'section': '080', 'instructor': 'Kiril Tochkov', 'days': 'MW', 'start_time': '17:30', 'end_time': '18:50'},
    {'course_code': 'ECON 30483', 'course_name': 'Financial History', 'section': '020', 'instructor': 'Stephen Quinn', 'days': 'MWF', 'start_time': '10:00', 'end_time': '10:50'},
    {'course_code': 'ECON 30483', 'course_name': 'Financial History', 'section': '030', 'instructor': 'Stephen Quinn', 'days': 'MWF', 'start_time': '11:00', 'end_time': '11:50'},
    {'course_code': 'ECON 30543', 'course_name': 'Environmental Economics and Policy', 'section': '035', 'instructor': 'Weiwei Liu', 'days': 'TR', 'start_time': '11:00', 'end_time': '12:20'},
    {'course_code': 'ECON 30733', 'course_name': 'Economic History of the US', 'section': '050', 'instructor': 'John Lovett', 'days': 'MWF', 'start_time': '13:00', 'end_time': '13:50'},
    {'course_code': 'ECON 30773', 'course_name': 'Public Choice', 'section': '035', 'instructor': 'Rosemarie Fike', 'days': 'TR', 'start_time': '11:00', 'end_time': '12:20'},
    {'course_code': 'ECON 30773', 'course_name': 'Public Choice', 'section': '045', 'instructor': 'Rosemarie Fike', 'days': 'TR', 'start_time': '12:30', 'end_time': '13:50'},
    {'course_code': 'ECON 31223', 'course_name': 'Intermediate Micro: Math Approach', 'section': '015', 'instructor': 'Weiwei Liu', 'days': 'TR', 'start_time': '09:30', 'end_time': '10:50'},
    {'course_code': 'ECON 40143', 'course_name': 'Public Finance', 'section': '035', 'instructor': 'Douglas Butler', 'days': 'TR', 'start_time': '11:00', 'end_time': '12:20'},
    {'course_code': 'ECON 40153', 'course_name': 'Economics of Financial Markets', 'section': '065', 'instructor': 'Stephen Quinn', 'days': 'TR', 'start_time': '15:30', 'end_time': '16:50'},
    {'course_code': 'ECON 40213', 'course_name': 'International Trade and Payments', 'section': '015', 'instructor': 'Rishav Bista', 'days': 'TR', 'start_time': '09:30', 'end_time': '10:50'},
    {'course_code': 'ECON 40313', 'course_name': 'Econometrics', 'section': '035', 'instructor': 'Rishav Bista', 'days': 'TR', 'start_time': '11:00', 'end_time': '12:20'},
    {'course_code': 'ECON 40313', 'course_name': 'Econometrics', 'section': '045', 'instructor': 'Rishav Bista', 'days': 'TR', 'start_time': '12:30', 'end_time': '13:50'},
    {'course_code': 'ECON 40323', 'course_name': 'Time Series Econometrics', 'section': '080', 'instructor': 'Kiril Tochkov', 'days': 'MW', 'start_time': '19:00', 'end_time': '20:20'},
    {'course_code': 'ECON 40513', 'course_name': 'Perspective in Internatl Econ', 'section': '005', 'instructor': 'John Harvey', 'days': 'TR', 'start_time': '08:00', 'end_time': '09:20'},
    {'course_code': 'ECON 40970', 'course_name': 'Big Data in Economics', 'section': '055', 'instructor': 'Stepan Gordeev', 'days': 'TR', 'start_time': '14:00', 'end_time': '15:20'},
    {'course_code': 'ECON 40970', 'course_name': 'Global Health', 'section': '056', 'instructor': 'Graham Gardner', 'days': 'TR', 'start_time': '14:00', 'end_time': '15:20'},
]

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
    courses = [
        # 10000 level courses (Intros)
        Course(code="ECON 10223", name="Intro Microeconomics", level=10000, min_sections=4, max_sections=8, core_ssc=True),
        Course(code="ECON 10233", name="Intro Macroeconomics", level=10000, min_sections=4, max_sections=8, core_ssc=True),
        Course(code="ECON 10223", name="Intro Micro - Honors", level=10000, min_sections=1, max_sections=2, core_ssc=True),
        Course(code="ECON 10233", name="Intro Macro - Honors", level=10000, min_sections=1, max_sections=2, core_ssc=True),

        # 30000 level courses (Foundations & Electives)
        Course(code="ECON 30223", name="Intermediate Microeconomics", level=30000, min_sections=2, max_sections=3),
        Course(code="ECON 31223", name="Intermediate Micro: Math Approach", level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30233", name="Intermediate Macroeconomics", level=30000, min_sections=2, max_sections=3),
        Course(code="ECON 31233", name="Intermediate Macro: Math Approach", level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30243", name="Contending Perspectives in Economics", level=30000, min_sections=2, max_sections=3),
        Course(code="ECON 30213", name="Development Theory", level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30253", name="History of Economic Thought", level=30000, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 30433", name="Development Studies", level=30000, min_sections=1, max_sections=2, core_ga=True),
        Course(code="ECON 30443", name="Asian Economics", level=30000, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 30473", name="Regional and Urban Economics", level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30483", name="Financial History", level=30000, min_sections=1, max_sections=2, core_ht=True, core_wem=True),
        Course(code="ECON 30503", name="Health Economics", level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30523", name="Resource and Energy Economics", level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30543", name="Environmental Economics and Policy", level=30000, min_sections=1, max_sections=2),
        Course(code="ECON 30733", name="European Economic History II", level=30000, min_sections=1, max_sections=2, core_ht=True),
        Course(code="ECON 30773", name="Public Choice", level=30000, min_sections=1, max_sections=2),
        
        # 40000 level courses
        Course(code="ECON 40313", name="Econometrics", level=40000, min_sections=2, max_sections=3),
        Course(code="ECON 40323", name="Time Series Econometrics", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40123", name="Game Theory", level=40000, min_sections=1, max_sections=1),
        Course(code="ECON 40143", name="Public Finance", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40153", name="Economics of Financial Markets", level=40000, min_sections=1, max_sections=2, core_wem=True),
        Course(code="ECON 40213", name="International Trade and Payments", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40223", name="International Monetary Economics", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40333", name="Machine Learning in Economics", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40433", name="Law and Economics", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40493", name="Macro Analysis and Communication", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40513", name="Perspective in Internatl Econ", level=40000, min_sections=1, max_sections=2, core_ga=True),
        
        # 40970 Special Topics
        Course(code="ECON 40970", name="Real Estate Principles", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Causal Inferences", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Growth", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Agriculture (Development)", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Scientific Computation", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="International Financial Crises", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Big Data in Economics", level=40000, min_sections=1, max_sections=2),
        Course(code="ECON 40970", name="Global Health", level=40000, min_sections=1, max_sections=2),
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

    print("Seeding schedule based on past data...")
    schedule = Schedule(semester="Spring", year=2026, status="Finalized")
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    # Convert the db data into easily searchable formats
    db_courses = db.query(Course).all()

    db_profs = db.query(Professor).all()
    # Map by last name for easiest lookup from "Lastname, Firstname" format
    prof_map = {}
    for p in db_profs:
        last_name = p.name.split()[-1].lower()
        prof_map[last_name] = p

    db_timeslots = db.query(TimeSlot).all()
    
    sections_to_add = []
    for row in PAST_SCHEDULE_DATA:
        # Find course
        course = None
        candidates = [c for c in db_courses if c.code == row['course_code']]
        if len(candidates) == 1:
            course = candidates[0]
        elif len(candidates) > 1:
            for c in candidates:
                if c.name == row.get('course_name'):
                    course = c
                    break
            if not course:
                course = candidates[0] # Grab first match if name doesn't match perfectly
                
        if not course:
            print(f"Skipping unknown course: {row['course_code']}")
            continue
        
        # Find professor
        prof = None
        if row['instructor']:
            # The instructor is usually "Firstname Lastname"
            last_name = row['instructor'].split()[-1].lower()
            prof = prof_map.get(last_name)
            if not prof:
                print(f"Could not map instructor '{row['instructor']}' to a professor in DB")

        # Find timeslot
        timeslot = None
        for ts in db_timeslots:
            if ts.days == row['days'] and ts.start_time == row['start_time']:
                timeslot = ts
                break
        
        if not timeslot:
            print(f"Could not map timeslot: {row['days']} {row['start_time']}-{row['end_time']}")

        section = Section(
            course_id=course.id,
            professor_id=prof.id if prof else None,
            timeslot_id=timeslot.id if timeslot else None,
            schedule_id=schedule.id,
            status="Approved"
        )
        sections_to_add.append(section)
        
    db.add_all(sections_to_add)
    db.commit()
    db.close()
    print("Seed complete.")

if __name__ == "__main__":
    seed_db()
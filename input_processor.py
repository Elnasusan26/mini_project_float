import pandas as pd
from models import db, Class, Room, Teacher, Subject, TimetableEntry, User,TeachingAssignment
from utils.normalize import normalize_slot, normalize_subject
from models import Notification


# -------------------------------------------------
# HELPERS
# -------------------------------------------------
def normalize(df):
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )
    return df


def get_class_column(df):
    for c in ["class", "class_name"]:
        if c in df.columns:
            return c
    raise ValueError(f"No class column found. Columns: {list(df.columns)}")


def get_slot_column(df):
    for c in ["slot", "period", "time", "time_slot"]:
        if c in df.columns:
            return c
    raise ValueError(f"No slot column found. Columns: {list(df.columns)}")


# -------------------------------------------------
# PARALLEL CLEANUP HELPER
# -------------------------------------------------
def delete_base_entry(class_id, day, slot):

    base_entries = TimetableEntry.query.filter(
        TimetableEntry.class_id == class_id,
        TimetableEntry.day == day,
        TimetableEntry.slot == slot,
        TimetableEntry.batch.is_(None),
        TimetableEntry.is_lab_hour == False
    ).all()

    for e in base_entries:
        db.session.delete(e)


# -------------------------------------------------
# MAIN PROCESS
# -------------------------------------------------
def process_inputs():

    print("\n========== INPUT PROCESSOR START ==========\n")

    # RESET ACADEMIC TABLES
    Notification.query.delete()
    TimetableEntry.query.delete()
    TeachingAssignment.query.delete() 
    Subject.query.delete()
    Teacher.query.delete()
    Room.query.delete()
    Class.query.delete()
    db.session.commit()

    # -------------------------------------------------
    # 1️⃣ CLASSES
    # -------------------------------------------------
    df = normalize(pd.read_excel("uploads/class_strength.xlsx"))
    class_col = get_class_column(df)

    class_map = {}

    for _, r in df.iterrows():

        cls = Class(
            name=str(r[class_col]).strip(),
            strength=int(r["strength"]),
            class_category=str(r["class_category"]).lower()
        )

        db.session.add(cls)
        db.session.flush()

        class_map[cls.name] = cls


    # -------------------------------------------------
    # 2️⃣ ROOMS
    # -------------------------------------------------
    df = normalize(pd.read_excel("uploads/room_mapping.xlsx"))
    class_col = get_class_column(df)

    for _, r in df.iterrows():

        cls = class_map.get(str(r[class_col]).strip())

        if not cls:
            continue

        db.session.add(Room(
            name=str(r["room"]).strip(),
            capacity=int(r["capacity"]),
            is_permanent=True,
            owner_class_id=cls.id
        ))


    # -------------------------------------------------
    # 3️⃣ SUBJECT TYPES
    # -------------------------------------------------
    df = normalize(pd.read_excel("uploads/class_type.xlsx"))

    subject_type = {
        normalize_subject(r["subject"]): str(r["type"]).lower()
        for _, r in df.iterrows()
    }


   # -------------------------------------------------
    # 4️⃣ TEACHERS + SUBJECTS
    # -------------------------------------------------
    df = pd.read_excel("uploads/teacher_subject_mapping.xlsx")

    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(" ", "_")
    )

    print("Teacher Mapping Columns:", df.columns.tolist())

    required_columns = ["faculty", "subject", "class"]

    for col in required_columns:
        if col not in df.columns:
            raise Exception(f"Column '{col}' missing in teacher_subject_mapping.xlsx")

    teacher_map = {}
    subject_map = {}

    for _, r in df.iterrows():

        faculty = str(r.get("faculty", "")).strip()
        subject_name = normalize_subject(str(r.get("subject", "")).strip())
        class_name = (
            str(r.get("class", ""))
            .strip()
            .replace(" ", "_")
            .replace("-", "_")
        )

        if not faculty or not subject_name or not class_name:
            continue

        cls = class_map.get(class_name)

        if not cls:
            continue

        # -----------------------------
        # CREATE OR GET TEACHER
        # -----------------------------
        teacher = teacher_map.get(faculty)

        if not teacher:

            teacher = Teacher(name=faculty)

            db.session.add(teacher)
            db.session.flush()

            teacher_map[faculty] = teacher

            # -----------------------------
            # AUTO CREATE TEACHER LOGIN
            # -----------------------------
            email = faculty.lower().replace(" ", "") + "@college.edu"

            existing_user = User.query.filter_by(email=email).first()

            if not existing_user:

                teacher_user = User(
                    email=email,
                    role="teacher",
                    teacher_id=teacher.id
                )

                teacher_user.set_password("teacher123")

                db.session.add(teacher_user)

        # -----------------------------
        # CREATE OR GET SUBJECT
        # -----------------------------
        subject = Subject.query.filter_by(name=subject_name).first()

        if not subject:
            subject = Subject(
                name=subject_name,
                is_lab=(subject_type.get(subject_name) == "lab"),
                teacher_id=teacher.id
            )
            db.session.add(subject)
            db.session.flush()
        else:
            subject.teacher_id = teacher.id

        subject_map[subject_name] = subject
        # -----------------------------
        # CREATE TEACHING ASSIGNMENT
        # -----------------------------

        existing_assignment = TeachingAssignment.query.filter_by(
            teacher_id=teacher.id,
            subject_id=subject.id,
            class_id=cls.id
        ).first()

        if not existing_assignment:

            assignment = TeachingAssignment(
                teacher_id=teacher.id,
                subject_id=subject.id,
                class_id=cls.id
            )

            db.session.add(assignment)

    # Save everything
    db.session.commit()

    print("Teachers, subjects, and teaching assignments processed successfully!")

    # -------------------------------------------------
    # 5️⃣ BASE TIMETABLES
    # -------------------------------------------------
    xls = pd.ExcelFile("uploads/timetables.xlsx")

    for sheet in xls.sheet_names:

        sheet_name = sheet.strip()

        if sheet_name not in class_map:
            continue

        cls = class_map[sheet_name]

        df = normalize(pd.read_excel(xls, sheet_name=sheet))

        day_col = df.columns[0]
        slots = df.columns[1:]

        for _, row in df.iterrows():

            day = str(row[day_col]).strip().upper()

            for slot in slots:

                raw_slot = normalize_slot(slot)
                value = row[slot]

                if pd.isna(value):
                    continue

                subject_name = normalize_subject(value)


                # ACTIVITY
                if subject_name in ["activity", "activity_hour"]:

                    db.session.add(TimetableEntry(
                        class_id=cls.id,
                        subject_id=None,
                        teacher_id=None,
                        room_id=None,
                        day=day,
                        slot=raw_slot
                    ))

                    continue


                # LAB
                if subject_type.get(subject_name) == "lab":

                    subject = subject_map.get(subject_name)

                    if subject is None:
                        subject = Subject.query.filter_by(name=subject_name).first()

                    if subject is None:
                        subject = Subject(
                            name=subject_name,
                            is_lab=(subject_type.get(subject_name) == "lab")
                        )
                        db.session.add(subject)
                        db.session.flush()

                    subject_map[subject_name] = subject

                    assignment = TeachingAssignment.query.filter_by(
                        subject_id=subject.id,
                        class_id=cls.id
                    ).first()

                    teacher_id = assignment.teacher_id if assignment else None
                    db.session.add(TimetableEntry(
                        class_id=cls.id,
                        subject_id=subject.id,
                        teacher_id=teacher_id,
                        day=day,
                        slot=raw_slot,
                        is_lab_hour=True
                    ))

                    continue

                # THEORY
                subject = subject_map.get(subject_name)

                if subject is None:
                    subject = Subject.query.filter_by(name=subject_name).first()

                if subject is None:
                    subject = Subject(name=subject_name)
                    db.session.add(subject)
                    db.session.flush()

                subject_map[subject_name] = subject

                room_id = None

                if cls.class_category == "permanent":

                    room = Room.query.filter_by(
                        owner_class_id=cls.id
                    ).first()

                    if room:
                        room_id = room.id

                assignment = TeachingAssignment.query.filter_by(
                    subject_id=subject.id,
                    class_id=cls.id
                ).first()

                teacher_id = assignment.teacher_id if assignment else None
                db.session.add(TimetableEntry(
                    class_id=cls.id,
                    subject_id=subject.id,
                    teacher_id=teacher_id,
                    room_id=room_id,
                    day=day,
                    slot=raw_slot,
                    is_floating=(cls.class_category == "floating")
                ))


    # -------------------------------------------------
    # 6️⃣ PARALLEL CLASSES
    # -------------------------------------------------
    df = normalize(pd.read_excel("uploads/parallel_classes.xlsx"))

    class_col = get_class_column(df)
    slot_col = get_slot_column(df)

    for _, r in df.iterrows():

        cls = class_map.get(str(r[class_col]).strip())

        if not cls:
            continue

        subject_name = normalize_subject(r["subject"])
        day = str(r["day"]).strip()
        slot = normalize_slot(r[slot_col])
        batch = str(r["batch"]).strip()

        delete_base_entry(cls.id, day, slot)

        subject = subject_map.get(subject_name)

        if subject is None:
            subject = Subject(name=subject_name)
            db.session.add(subject)
            db.session.flush()
            subject_map[subject_name] = subject

        assignment = TeachingAssignment.query.filter_by(
            subject_id=subject.id,
            class_id=cls.id
        ).first()

        # Skip if subject not mapped to teacher
        teacher_id = assignment.teacher_id if assignment else None
        db.session.add(TimetableEntry(
            class_id=cls.id,
            subject_id=subject.id,
            teacher_id=teacher_id,
            day=day,
            slot=slot,
            batch=batch,
            is_floating=True
        ))


    # -------------------------------------------------
    # 7️⃣ STUDENT ACCOUNTS
    # -------------------------------------------------
    df = normalize(pd.read_excel("uploads/student_mapping.xlsx"))

    class_col = get_class_column(df)

    for _, r in df.iterrows():

        class_name = str(r[class_col]).strip()

        cls = class_map.get(class_name)

        if not cls:
            continue

        email = str(r["email"]).strip().lower()

        if User.query.filter_by(email=email).first():
            continue

        student_user = User(
            email=email,
            role="student",
            class_id=cls.id
        )

        student_user.set_password("student123")

        db.session.add(student_user)


    db.session.commit()

    print("\n========== INPUT PROCESSOR DONE ==========\n")


# -------------------------------------------------
# 8️⃣ LAB ROOM ASSIGNMENT
# -------------------------------------------------
def process_lab_rooms():

    import os

    path = "uploads/lab_rooms.xlsx"

    if not os.path.exists(path):
        print("No lab_rooms.xlsx file found")
        return

    df = normalize(pd.read_excel(path))

    class_col = get_class_column(df)

    for _, r in df.iterrows():

        class_name = str(r[class_col]).strip()
        subject_col = "subject" if "subject" in df.columns else "subject_name"
        subject_name = normalize_subject(r[subject_col])
        lab_rooms = str(r["rooms"]).strip()

        cls = Class.query.filter_by(name=class_name).first()
        subject = Subject.query.filter_by(name=subject_name).first()

        if not cls or not subject:
            continue

        entries = TimetableEntry.query.filter(
            TimetableEntry.class_id == cls.id,
            TimetableEntry.subject_id == subject.id,
            TimetableEntry.is_lab_hour == True
        ).all()

        for e in entries:
            e.lab_rooms = lab_rooms

    db.session.commit()

    print("\n========== LAB ROOMS PROCESSED ==========\n")
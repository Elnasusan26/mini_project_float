from flask import Flask, render_template, request
import os
from collections import defaultdict

from models import db, Class, Room, Subject, TimetableEntry
from input_processor import process_inputs
from allocator import allocate_rooms
from utils.normalize import normalize_slot

# ---------------- APP INIT ----------------
app = Flask(__name__)

# ---------------- CONFIG ----------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db.init_app(app)

# ---------------- FIXED SLOT ORDER (NORMALIZED) ----------------
TIME_SLOTS = list(map(normalize_slot, [
    "8.00-8.45",
    "9.10-9.55",
    "10.00-10.45",
    "10.50-11.35",
    "11.55-12.40",
    "12.45-1.30"
]))

DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template("home.html")


# ---------------- ADMIN UPLOAD ----------------
@app.route("/admin_upload", methods=["GET", "POST"])
def admin_upload():
    if request.method == "POST":
        files = {
            "class_strength": "class_strength.xlsx",
            "room_mapping": "room_mapping.xlsx",
            "class_type": "class_type.xlsx",
            "teacher_subject": "teacher_subject_mapping.xlsx",
            "parallel_classes": "parallel_classes.xlsx",
            "timetables": "timetables.xlsx",
        }

        for key, filename in files.items():
            if key not in request.files or request.files[key].filename == "":
                return f"❌ Missing file: {key}", 400

            request.files[key].save(
                os.path.join(app.config["UPLOAD_FOLDER"], filename)
            )

        process_inputs()
        return "✅ Files uploaded and data stored successfully"

    return render_template("admin_upload.html")


# ---------------- VIEW CLASSES ----------------
@app.route("/view/classes")
def view_classes():
    return render_template(
        "view_class.html",
        classes=Class.query.all()
    )


# ---------------- VIEW ROOMS ----------------
@app.route("/view/rooms")
def view_rooms():
    return render_template(
        "view_rooms.html",
        rooms=Room.query.all()
    )


# ---------------- VIEW SUBJECTS ----------------
@app.route("/view/subjects")
def view_subjects():
    return render_template(
        "view_subjects.html",
        subjects=Subject.query.all()
    )


# ---------------- VIEW RAW TIMETABLE ----------------
@app.route("/view/timetable")
def view_timetable():
    entries = (
        TimetableEntry.query
        .order_by(
            TimetableEntry.class_id,
            TimetableEntry.day,
            TimetableEntry.slot
        )
        .all()
    )

    grouped = defaultdict(list)
    for e in entries:
        grouped[e.class_obj.name].append(e)

    return render_template(
        "view_timetable.html",
        grouped_entries=grouped
    )


# ---------------- ALLOCATE FLOATING ROOMS ----------------
@app.route("/allocate_floating_rooms")
def allocate_floating_rooms():

    print("\n========== FLOATING ROOM DEBUG (BEFORE) ==========")

    unresolved = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.room_id == None
    ).all()

    print(f"Floating entries WITHOUT rooms (before): {len(unresolved)}")

    for e in unresolved:
        print(
            f"ID={e.id} | Class={e.class_obj.name} | "
            f"{e.day} | Slot={e.slot} | "
            f"Subject={e.subject.name if e.subject else '-'}"
        )

    print("===============================================\n")

    allocate_rooms()

    post_unresolved = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.room_id == None
    ).count()

    post_allocated = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.room_id != None
    ).count()

    print("\n========== FLOATING ROOM DEBUG (AFTER) ==========")
    print(f"Still unresolved: {post_unresolved}")
    print(f"Allocated floating entries: {post_allocated}")
    print("===============================================\n")

    return "✅ Floating classrooms allocated successfully"


# ---------------- VIEW FLOATING TIMETABLE (FINAL, CORRECT) ----------------
@app.route("/view/floating_timetable")
def view_floating_timetable():

    entries = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.is_lab_hour == False
    ).order_by(
        TimetableEntry.class_id,
        TimetableEntry.day,
        TimetableEntry.slot
    ).all()

    # raw[class][day][slot] = list of entries (parallel-safe)
    raw = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    print("\n========== PARALLEL GROUPING DEBUG ==========")

    for e in entries:
        cls = e.class_obj.name
        day = e.day
        slot = normalize_slot(e.slot)

        raw[cls][day][slot].append({
            "subject": e.subject.name if e.subject else "-",
            "room": e.room.name if e.room else "-",
            "allocated": bool(e.room_id),
            "batch": e.batch
        })

        print(
            f"APPEND → {cls} | {day} | {slot} | "
            f"{e.subject.name if e.subject else '-'} | "
            f"Room={e.room.name if e.room else '-'}"
        )

    print("=============================================\n")

    # Final timetable[class][day][slot] = list(entries)
    timetable = {}

    for cls, days in raw.items():
        timetable.setdefault(cls, {})
        for day, slots in days.items():
            timetable[cls].setdefault(day, {})
            for slot, items in slots.items():
                timetable[cls][day][slot] = items

    return render_template(
        "floating_timetable_grid.html",
        timetable=timetable,
        slots=TIME_SLOTS,
        days=DAYS
    )


# ---------------- MAIN ----------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()

    app.run(debug=True, use_reloader=False)

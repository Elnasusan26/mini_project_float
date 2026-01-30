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


# ---------------- VIEW RAW TIMETABLE ----------------
@app.route("/view/timetable")
def view_timetable():
    entries = TimetableEntry.query.order_by(
        TimetableEntry.class_id,
        TimetableEntry.day,
        TimetableEntry.slot
    ).all()

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
        TimetableEntry.room_id == None,
        TimetableEntry.is_lab_hour == False
    ).all()

    print(f"Floating entries WITHOUT rooms (before): {len(unresolved)}")

    allocate_rooms()

    print("\n========== FLOATING ROOM DEBUG (AFTER) ==========")

    still_unresolved = TimetableEntry.query.filter(
        TimetableEntry.is_floating == True,
        TimetableEntry.room_id == None,
        TimetableEntry.is_lab_hour == False
    ).count()

    print(f"Still unresolved: {still_unresolved}")
    print("===============================================\n")

    return "✅ Floating classrooms allocated successfully"


# ---------------- VIEW FLOATING TIMETABLE (LAB + PARALLEL + THEORY) ----------------
@app.route("/view/floating_timetable")
def view_floating_timetable():

    # 🔥 FIX: INCLUDE LAB HOURS ALSO
    entries = TimetableEntry.query.filter(
        (TimetableEntry.is_floating == True) |
        (TimetableEntry.is_lab_hour == True)
    ).order_by(
        TimetableEntry.class_id,
        TimetableEntry.day,
        TimetableEntry.slot
    ).all()

    raw = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    print("\n========== TIMETABLE BUILD DEBUG ==========")

    for e in entries:
        cls = e.class_obj.name
        day = e.day
        slot = normalize_slot(e.slot)

        # ---------- LAB ----------
        if e.is_lab_hour:
            raw[cls][day][slot].append({
                "subject": e.subject.name if e.subject else "LAB",
                "room": e.room.name if e.room else "",
                "type": "lab"
            })
            print(f"LAB → {cls} | {day} | {slot}")

        # ---------- THEORY / PARALLEL ----------
        else:
            raw[cls][day][slot].append({
                "subject": e.subject.name if e.subject else "-",
                "room": e.room.name if e.room else "-",
                "batch": e.batch,
                "type": "theory"
            })
            print(
                f"THEORY → {cls} | {day} | {slot} | "
                f"{e.subject.name if e.subject else '-'} | "
                f"Room={e.room.name if e.room else '-'}"
            )

    print("==========================================\n")

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

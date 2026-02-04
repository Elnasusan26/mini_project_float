from flask import render_template, request
from collections import defaultdict
import os

from models import db, Class, Room, Subject, TimetableEntry
from input_processor import process_inputs
from allocator import allocate_rooms
from utils.normalize import normalize_slot


def register_routes(app):

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

    # ---------------- VIEW FLOATING TIMETABLE (WITH LAB HOURS) ----------------
    @app.route("/view/floating_timetable")
    def view_floating_timetable():

        TIME_SLOTS = list(map(normalize_slot, [
            "8.00-8.45",
            "9.10-9.55",
            "10.00-10.45",
            "10.50-11.35",
            "11.55-12.40",
            "12.45-1.30"
        ]))

        DAYS = ["MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY"]

        # ✅ Floating theory + lab hours
        entries = TimetableEntry.query.filter(
            (TimetableEntry.is_floating == True) |
            (TimetableEntry.is_lab_hour == True)
        ).order_by(
            TimetableEntry.class_id,
            TimetableEntry.day,
            TimetableEntry.slot
        ).all()

        timetable = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

        for e in entries:
            cls = e.class_obj.name
            day = e.day
            slot = normalize_slot(e.slot)

            timetable[cls][day][slot].append({
                "subject": e.subject.name if e.subject else "",
                "room": e.room.name if e.room else "",
                "allocated": bool(e.room_id),
                "batch": e.batch,
                "is_lab": e.is_lab_hour
            })

        return render_template(
            "floating_timetable_grid.html",
            timetable=timetable,
            slots=TIME_SLOTS,
            days=DAYS
        )

    # ---------------- ALLOCATE FLOATING ROOMS ----------------
    @app.route("/allocate_floating_rooms")
    def allocate_floating_rooms():
        allocate_rooms()
        return "✅ Floating classrooms allocated successfully"

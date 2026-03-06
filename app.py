from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session, abort
)
import os
from collections import defaultdict
from functools import wraps
from datetime import datetime

from models import db, User, Class, Room, Subject, TimetableEntry, CancelledClass
from input_processor import process_inputs
from allocator import allocate_rooms
from utils.normalize import normalize_slot


# ---------------- APP INIT ----------------
app = Flask(__name__)
app.secret_key = "floated-secret"

# ---------------- CONFIG ----------------
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db.init_app(app)


# ---------------- FIXED SLOT ORDER ----------------
TIME_SLOTS = list(map(normalize_slot, [
    "8.00-8.45",
    "9.10-9.55",
    "10.00-10.45",
    "10.50-11.35",
    "11.55-12.40",
    "12.45-1.30"
]))

DAYS = [
    "MONDAY", "TUESDAY", "WEDNESDAY",
    "THURSDAY", "FRIDAY", "SATURDAY"
]


# ==============================================================
# AUTH HELPERS
# ==============================================================

def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return wrapper


def role_required(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                abort(403)
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ==============================================================
# LOGIN
# ==============================================================

@app.route("/", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):

            session.clear()
            session["user_id"] = user.id
            session["role"] = user.role

            if user.role == "admin":
                return redirect(url_for("admin_dashboard"))

            elif user.role == "teacher":
                return redirect(url_for("teacher_dashboard"))

            elif user.role == "student":
                return redirect(url_for("student_dashboard"))

        flash("Invalid email or password", "error")

    return render_template("login.html")


# ==============================================================
# ADMIN DASHBOARD
# ==============================================================

@app.route("/admin")
@login_required
@role_required("admin")
def admin_dashboard():

    permanent_count = Class.query.filter_by(
        class_category="permanent"
    ).count()

    floating_count = Class.query.filter_by(
        class_category="floating"
    ).count()

    from sqlalchemy import func, case

    subquery = (
        db.session.query(
            TimetableEntry.class_id,
            TimetableEntry.day,
            TimetableEntry.slot,
            func.count(TimetableEntry.id).label("total"),
            func.sum(
                case(
                    (TimetableEntry.room_id.isnot(None), 1),
                    else_=0
                )
            ).label("allocated")
        )
        .join(Class, TimetableEntry.class_id == Class.id)
        .filter(Class.class_category == "floating")
        .group_by(
            TimetableEntry.class_id,
            TimetableEntry.day,
            TimetableEntry.slot
        )
        .subquery()
    )

    fully_allocated_periods = (
        db.session.query(func.count())
        .filter(subquery.c.total == subquery.c.allocated)
        .scalar()
    )

    return render_template(
        "home.html",
        permanent_count=permanent_count,
        floating_count=floating_count,
        allocated_count=fully_allocated_periods
    )


# ==============================================================
# ADMIN UPLOAD
# ==============================================================

@app.route("/admin_upload", methods=["GET", "POST"])
@login_required
@role_required("admin")
def admin_upload():

    if request.method == "POST":

        files = {
            "class_strength": "class_strength.xlsx",
            "room_mapping": "room_mapping.xlsx",
            "class_type": "class_type.xlsx",
            "teacher_subject": "teacher_subject_mapping.xlsx",
            "parallel_classes": "parallel_classes.xlsx",
            "timetables": "timetables.xlsx",
            "student_mapping": "student_mapping.xlsx"
        }

        for key, filename in files.items():

            if key not in request.files or request.files[key].filename == "":
                return f"❌ Missing file: {key}", 400

            request.files[key].save(
                os.path.join(app.config["UPLOAD_FOLDER"], filename)
            )

        process_inputs()
        allocate_rooms()

        flash("Files uploaded and timetable allocated successfully!", "success")

        return redirect(url_for("view_floating_timetable"))

    return render_template("admin_upload.html")


# ==============================================================
# CANCEL CLASS
# ==============================================================

@app.route("/admin/cancel_class", methods=["GET", "POST"])
@login_required
@role_required("admin")
def cancel_class():

    classes = Class.query.all()

    if request.method == "POST":

        class_id = int(request.form.get("class_id"))

        date_str = request.form.get("date")
        date = datetime.strptime(date_str, "%Y-%m-%d").date()

        slots = request.form.getlist("slots")
        reason = request.form.get("reason")

        for slot in slots:

            slot = normalize_slot(slot)

            # prevent duplicates
            existing = CancelledClass.query.filter_by(
                class_id=class_id,
                slot=slot,
                date=date
            ).first()

            if existing:
                continue

            cancelled = CancelledClass(
                class_id=class_id,
                date=date,
                slot=slot,
                reason=reason
            )

            db.session.add(cancelled)

        db.session.commit()

        allocate_rooms()

        flash("Class cancelled and rooms reallocated!", "success")

        return redirect(url_for("admin_dashboard"))

    return render_template(
        "admin_cancel_class.html",
        classes=classes
    )


# ==============================================================
# VIEW FULL TIMETABLE
# ==============================================================

@app.route("/view/timetable")
@app.route("/view/floating_timetable")
@login_required
def view_floating_timetable():

    entries = TimetableEntry.query.order_by(
        TimetableEntry.class_id,
        TimetableEntry.day,
        TimetableEntry.slot
    ).all()

    raw = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

    for e in entries:

        cls = e.class_obj.name
        day = e.day
        slot = normalize_slot(e.slot)

        raw[cls][day][slot].append({
            "subject": e.subject.name if e.subject else "-",
            "room": e.room.name if e.room else "-",
            "batch": e.batch
        })

    # ---------------------------------------
    # FETCH CANCELLED CLASSES (TODAY)
    # ---------------------------------------

    today = datetime.today().date()

    cancelled_classes = CancelledClass.query.filter_by(date=today).all()

    cancelled_lookup = set()

    for c in cancelled_classes:

        day = c.date.strftime("%A").upper()
        slot = normalize_slot(c.slot)

        cls = Class.query.get(c.class_id).name

        cancelled_lookup.add((cls, day, slot))

    return render_template(
        "floating_timetable_grid.html",
        timetable=raw,
        slots=TIME_SLOTS,
        days=DAYS,
        cancelled_lookup=cancelled_lookup
    )

# ==============================================================
# TEACHER DASHBOARD
# ==============================================================

@app.route("/teacher")
@login_required
@role_required("teacher")
def teacher_dashboard():

    user = User.query.get(session["user_id"])

    if not user.teacher_id:
        return "No teacher linked to this account", 400

    entries = TimetableEntry.query.join(Subject).filter(
        Subject.teacher_id == user.teacher_id
    ).all()

    # -------------------------
    # SORTING
    # -------------------------
    day_order = {day: i for i, day in enumerate(DAYS)}
    slot_order = {slot: i for i, slot in enumerate(TIME_SLOTS)}

    entries.sort(
        key=lambda e: (
            day_order.get(e.day, 99),
            slot_order.get(normalize_slot(e.slot), 99)
        )
    )

    # -------------------------
    # CANCELLED LOOKUP
    # -------------------------
    today = datetime.today().date()

    cancelled = CancelledClass.query.filter(
        CancelledClass.date >= today
    ).all()

    cancelled_lookup = set()

    for c in cancelled:

        cancel_day = c.date.strftime("%A").upper()
        slot = normalize_slot(c.slot)

        cancelled_lookup.add((c.class_id, cancel_day, slot))

    return render_template(
        "teacher_timetable.html",
        entries=entries,
        teacher_name=user.email.split("@")[0].capitalize(),
        cancelled_lookup=cancelled_lookup
    )

# ==============================================================
# STUDENT DASHBOARD
# ==============================================================

@app.route("/student")
@login_required
@role_required("student")
def student_dashboard():

    user = User.query.get(session["user_id"])

    if not user.class_id:
        return "No class linked to this account", 400

    cls = Class.query.get(user.class_id)

    entries = TimetableEntry.query.filter_by(
        class_id=user.class_id
    ).all()

    day_order = {day: i for i, day in enumerate(DAYS)}
    slot_order = {slot: i for i, slot in enumerate(TIME_SLOTS)}

    entries.sort(
        key=lambda e: (
            day_order.get(e.day, 99),
            slot_order.get(normalize_slot(e.slot), 99)
        )
    )

    # -------------------------
    # CANCELLED LOOKUP
    # -------------------------
    today = datetime.today().date()

    cancelled = CancelledClass.query.filter(
        CancelledClass.date >= today,
        CancelledClass.class_id == user.class_id
    ).all()

    cancelled_lookup = set()

    for c in cancelled:

        cancel_day = c.date.strftime("%A").upper()
        slot = normalize_slot(c.slot)

        cancelled_lookup.add((cancel_day, slot))

    return render_template(
        "student_timetable.html",
        entries=entries,
        class_name=cls.name,
        cancelled_lookup=cancelled_lookup
    )


# ==============================================================
# LOGOUT
# ==============================================================

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ==============================================================
# MAIN
# ==============================================================

if __name__ == "__main__":

    with app.app_context():
        db.create_all()

    app.run(debug=True, use_reloader=False)
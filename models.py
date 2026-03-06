from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


# ---------------- USER (AUTH) ----------------
class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)

    role = db.Column(
        db.String(20),
        nullable=False
    )  # 'admin', 'teacher', 'student'

    # Optional links
    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teacher.id"),
        nullable=True
    )

    class_id = db.Column(
        db.Integer,
        db.ForeignKey("class.id"),
        nullable=True
    )

    teacher = db.relationship("Teacher", backref="user", uselist=False)
    class_obj = db.relationship("Class", backref="students")

    # 🔔 Notifications relationship
    notifications = db.relationship(
        "Notification",
        backref="user",
        cascade="all, delete-orphan"
    )

    # password helpers
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email} ({self.role})>"


# ---------------- CLASS ----------------
class Class(db.Model):
    __tablename__ = "class"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    strength = db.Column(db.Integer, nullable=False)
    class_category = db.Column(db.String(20), nullable=False)

    def __repr__(self):
        return f"<Class {self.name}>"


# ---------------- ROOM ----------------
class Room(db.Model):
    __tablename__ = "room"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)

    is_permanent = db.Column(db.Boolean, default=True)

    owner_class_id = db.Column(
        db.Integer,
        db.ForeignKey("class.id"),
        nullable=True
    )

    owner_class = db.relationship("Class", backref="rooms")

    def __repr__(self):
        return f"<Room {self.name}>"


# ---------------- TEACHER ----------------
class Teacher(db.Model):
    __tablename__ = "teacher"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<Teacher {self.name}>"


# ---------------- SUBJECT ----------------
class Subject(db.Model):
    __tablename__ = "subject"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

    is_lab = db.Column(db.Boolean, default=False)

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teacher.id"),
        nullable=True
    )

    teacher = db.relationship("Teacher", backref="subjects")

    def __repr__(self):
        return f"<Subject {self.name}>"


# ---------------- TIMETABLE ENTRY ----------------
class TimetableEntry(db.Model):
    __tablename__ = "timetable_entry"

    id = db.Column(db.Integer, primary_key=True)

    class_id = db.Column(
        db.Integer,
        db.ForeignKey("class.id"),
        nullable=False
    )

    subject_id = db.Column(
        db.Integer,
        db.ForeignKey("subject.id"),
        nullable=True
    )

    teacher_id = db.Column(
        db.Integer,
        db.ForeignKey("teacher.id"),
        nullable=True
    )

    room_id = db.Column(
        db.Integer,
        db.ForeignKey("room.id"),
        nullable=True
    )

    day = db.Column(db.String(20), nullable=False)
    slot = db.Column(db.String(30), nullable=False)

    batch = db.Column(db.String(10), nullable=True)

    is_lab_hour = db.Column(db.Boolean, default=False)
    is_floating = db.Column(db.Boolean, default=False)

    class_obj = db.relationship("Class", backref="timetable_entries")
    subject = db.relationship("Subject")
    teacher = db.relationship("Teacher")
    room = db.relationship("Room")

    def __repr__(self):
        return f"<TimetableEntry {self.class_id} {self.day} {self.slot}>"


# ---------------- CANCELLED CLASS ----------------
class CancelledClass(db.Model):
    """
    Stores cancelled classes for specific dates.
    Used to dynamically free rooms and reallocate them.
    """

    __tablename__ = "cancelled_class"

    id = db.Column(db.Integer, primary_key=True)

    class_id = db.Column(
        db.Integer,
        db.ForeignKey("class.id"),
        nullable=False
    )

    slot = db.Column(db.String(30), nullable=False)

    date = db.Column(db.Date, nullable=False)

    reason = db.Column(db.String(200), nullable=True)

    class_obj = db.relationship("Class")

    def __repr__(self):
        return f"<CancelledClass {self.class_id} {self.date} {self.slot}>"


# ---------------- 🔔 NOTIFICATION ----------------
class Notification(db.Model):
    """
    Stores notifications for teachers and students
    Example: class cancelled alerts
    """

    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    message = db.Column(db.String(300), nullable=False)

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    is_read = db.Column(
        db.Boolean,
        default=False
    )

    def __repr__(self):
        return f"<Notification {self.user_id} {self.message}>"
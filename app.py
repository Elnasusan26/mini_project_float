from flask import Flask
import os

from models import db
from routes import register_routes

def create_app():
    app = Flask(__name__)

    # ---------------- CONFIG ----------------
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    UPLOAD_FOLDER = "uploads"
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    # ---------------- INIT EXTENSIONS ----------------
    db.init_app(app)

    # ---------------- REGISTER ROUTES ----------------
    register_routes(app)

    return app


# ---------------- MAIN ----------------
if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        db.create_all()

    app.run(debug=True, use_reloader=False)

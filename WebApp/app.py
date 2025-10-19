from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime
import os

# --- Load environment variables ---
load_dotenv()

# --- Flask App Setup ---
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

# --- Initialize Extensions ---
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

# --- MongoDB Setup ---
client = MongoClient(os.getenv("MONGO_URI"))
db = client["webappdb"]

# --- User Model ---
class User(UserMixin):
    def __init__(self, user_doc):
        self.id = str(user_doc["_id"])
        self.username = user_doc["username"]
        self.role = user_doc.get("role", "user")

@login_manager.user_loader
def load_user(user_id):
    try:
        user_doc = db.users.find_one({"_id": ObjectId(user_id)})
        return User(user_doc) if user_doc else None
    except Exception:
        return None

# -------------------
# ROUTES
# -------------------

@app.route("/")
def home():
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("user_dashboard"))
    return redirect(url_for("login"))

# -------------------
# AUTH ROUTES
# -------------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        role = request.form.get("role", "user")

        if db.users.find_one({"username": username}):
            flash("Username already exists", "danger")
            return redirect(url_for("register"))

        hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
        db.users.insert_one({
            "username": username,
            "password": hashed_pw,
            "role": role,
            "created_at": datetime.utcnow()
        })
        flash("Registered successfully! Please login.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = db.users.find_one({"username": username})
        if user and bcrypt.check_password_hash(user["password"], password):
            login_user(User(user))
            flash("Login successful!", "success")
            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))
            else:
                return redirect(url_for("user_dashboard"))
        else:
            flash("Invalid credentials", "danger")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "info")
    return redirect(url_for("login"))

# -------------------
# ADMIN ROUTES
# -------------------

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("user_dashboard"))

    users = list(db.users.find())
    competitions = list(db.competitions.find())
    return render_template("dashboard.html", users=users, competitions=competitions, role="admin")

@app.route("/competition/new", methods=["GET", "POST"])
@login_required
def competition_form():
    if current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        name = request.form.get("competition_name")
        description = request.form.get("description")
        db.competitions.insert_one({"name": name, "description": description})
        flash("Competition created successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("competition_form.html", competition=None)

@app.route("/competition/edit/<id>", methods=["GET", "POST"])
@login_required
def edit_competition(id):
    if current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("user_dashboard"))

    competition = db.competitions.find_one({"_id": ObjectId(id)})

    if request.method == "POST":
        name = request.form.get("competition_name")
        description = request.form.get("description")
        db.competitions.update_one({"_id": ObjectId(id)}, {"$set": {"name": name, "description": description}})
        flash("Competition updated successfully!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("competition_form.html", competition=competition)

@app.route("/competition/<id>/delete", methods=["POST"])
@login_required
def delete_competition(id):
    if current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("user_dashboard"))

    db.competitions.delete_one({"_id": ObjectId(id)})
    flash("Competition deleted", "info")
    return redirect(url_for("admin_dashboard"))

# -------------------
# USER ROUTES
# -------------------

@app.route("/user/dashboard")
@login_required
def user_dashboard():
    competitions = list(db.competitions.find())
    enrolled = list(db.enrollments.find({"user_id": current_user.id}))
    enrolled_ids = [e["competition_id"] for e in enrolled]
    enrolled_competitions = [db.competitions.find_one({"_id": ObjectId(cid)}) for cid in enrolled_ids]
    return render_template("dashboard.html", competitions=competitions, enrolled_ids=enrolled_ids,
                           enrolled_competitions=enrolled_competitions, role="user")

@app.route("/competition/<competition_id>/enroll", methods=["POST"])
@login_required
def enroll_competition(competition_id):
    if db.enrollments.find_one({"user_id": current_user.id, "competition_id": competition_id}):
        flash("Already enrolled", "warning")
        return redirect(url_for("user_dashboard"))

    db.enrollments.insert_one({
        "user_id": current_user.id,
        "competition_id": competition_id,
        "enrolled_at": datetime.utcnow()
    })
    flash("Enrolled successfully!", "success")
    return redirect(url_for("user_dashboard"))

# -------------------
# MESSAGES & LEADERBOARD
# -------------------

@app.route("/competition/<id>/messages", methods=["GET", "POST"])
@login_required
def messages(id):
    enrollment = db.enrollments.find_one({"user_id": current_user.id, "competition_id": id})
    if not enrollment and current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        msg = request.form["message"]
        db.messages.insert_one({
            "competition_id": id,
            "user_id": current_user.id,
            "username": current_user.username,
            "content": msg,
            "timestamp": datetime.utcnow()
        })
        score = len(msg) % 10 + 50
        lb_entry = db.leaderboards.find_one({"user_id": current_user.id, "competition_id": id})
        if lb_entry:
            db.leaderboards.update_one({"_id": lb_entry["_id"]}, {"$set": {"score": score, "updated_at": datetime.utcnow()}})
        else:
            db.leaderboards.insert_one({
                "user_id": current_user.id,
                "competition_id": id,
                "username": current_user.username,
                "score": score,
                "updated_at": datetime.utcnow()
            })
        flash("Message sent and score updated!", "success")
        return redirect(url_for("messages", id=id))

    all_messages = list(db.messages.find({"competition_id": id}))
    return render_template("messages.html", messages=all_messages, competition_id=id)

@app.route("/leaderboard/<id>")
@login_required
def leaderboard(id):
    if current_user.role == "admin":
        leaders = list(db.leaderboards.find({"competition_id": id}))
    else:
        leaders = list(db.leaderboards.find({"competition_id": id, "user_id": current_user.id}))
    return render_template("leaderboard.html", leaders=leaders)

# -------------------
# RUN APP
# -------------------
if __name__ == "__main__":
    app.run(debug=True)

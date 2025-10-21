from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from bson import ObjectId
from dotenv import load_dotenv
from datetime import datetime
import os
import requests

# -------------------
# CONFIG
# -------------------
LEADERBOARD_API = "http://127.0.0.1:5001/api/leaderboard"
load_dotenv()

app = Flask(__name__)

@app.context_processor
def inject_current_year():
    return {'current_year': datetime.now().year}

app.secret_key = os.getenv("SECRET_KEY")

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"

client = MongoClient(os.getenv("MONGO_URI"))
db = client["webappdb"]

AGENT_API_KEY = os.getenv("AGENT_API_KEY")


# -------------------
# USER MODEL
# -------------------
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
# HOME
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
# ADMIN DASHBOARD
# -------------------
@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("user_dashboard"))

    users = list(db.users.find())
    competitions = list(db.competitions.find())

    for comp in competitions:
        comp["_id"] = str(comp["_id"])
        enrollments = list(db.enrollments.find({"competition_id": comp["_id"]}))
        enrolled_usernames = []
        for enr in enrollments:
            # Use stored username if available; fallback to user lookup
            if enr.get("username"):
                enrolled_usernames.append(enr["username"])
            else:
                try:
                    udoc = db.users.find_one({"_id": ObjectId(enr["user_id"])})
                    if udoc:
                        enrolled_usernames.append(udoc["username"])
                except Exception:
                    continue
        comp["enrolled_users"] = enrolled_usernames

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
    if competition:
        competition["_id"] = str(competition["_id"])

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
# USER DASHBOARD
# -------------------
@app.route("/user/dashboard")
@login_required
def user_dashboard():
    if current_user.role == "admin":
        return redirect(url_for("admin_dashboard"))

    competitions = list(db.competitions.find())
    for comp in competitions:
        comp["_id"] = str(comp["_id"])

    enrolled = list(db.enrollments.find({"user_id": current_user.id}))
    enrolled_ids = [e["competition_id"] for e in enrolled]

    enrolled_competitions = []
    for cid in enrolled_ids:
        try:
            comp_doc = db.competitions.find_one({"_id": ObjectId(cid)})
            if comp_doc:
                comp_doc["_id"] = str(comp_doc["_id"])
                enrolled_competitions.append(comp_doc)
        except Exception:
            continue

    return render_template(
        "dashboard.html",
        competitions=competitions,
        enrolled_ids=enrolled_ids,
        enrolled_competitions=enrolled_competitions,
        role="user"
    )


@app.route("/competition/<competition_id>/enroll", methods=["POST"])
@login_required
def enroll_competition(competition_id):
    comp_id_str = str(competition_id)

    existing = db.enrollments.find_one({
        "user_id": current_user.id,
        "competition_id": comp_id_str
    })
    if existing:
        flash("Already enrolled", "warning")
        return redirect(url_for("user_dashboard"))

    db.enrollments.insert_one({
        "user_id": current_user.id,
        "username": current_user.username,
        "competition_id": comp_id_str,
        "enrolled_at": datetime.utcnow()
    })

    flash("Enrolled successfully!", "success")
    return redirect(url_for("user_dashboard"))


# -------------------
# MESSAGES & LEADERBOARD
# -------------------
@app.route("/leaderboard/<competition_id>")
@login_required
def leaderboard_page(competition_id):
    try:
        print(f"📡 Fetching leaderboard for {competition_id} from {LEADERBOARD_API}")
        response = requests.get(f"{LEADERBOARD_API}/{competition_id}")
        print(f"↩️ Status: {response.status_code}, Response: {response.text}")

        leaderboard_data = []
        if response.status_code == 200:
            data = response.json()
            leaderboard_data = data.get("leaderboard", [])
        else:
            print(f"⚠️ Failed to fetch leaderboard. Status code: {response.status_code}")

        leaderboard_data.sort(key=lambda x: x.get("score", 0), reverse=True)
        top_score = leaderboard_data[0]["score"] if leaderboard_data else 1

        return render_template("leaderboard.html", leaderboard=leaderboard_data, top_score=top_score)

    except Exception as e:
        print(f"❌ Error fetching leaderboard: {e}")
        return render_template("leaderboard.html", leaderboard=[], top_score=1)


@app.route("/messages/<id>", methods=["GET", "POST"])
@login_required
def messages(id):
    enrollment = db.enrollments.find_one({"user_id": current_user.id, "competition_id": id})
    if not enrollment and current_user.role != "admin":
        flash("Access denied", "danger")
        return redirect(url_for("user_dashboard"))

    if request.method == "POST":
        if request.is_json:
            data = request.get_json()
            msg = data.get("message")
            user_id = data.get("user_id")
        else:
            msg = request.form.get("message")
            user_id = request.form.get("user_id")

        if not msg:
            return jsonify({"error": "Message cannot be empty."}), 400

        db.messages.insert_one({
            "competition_id": id,
            "user_id": user_id,
            "username": current_user.username,
            "content": msg,
            "timestamp": datetime.utcnow()
        })

        validation_payload = {
            "user_id": user_id,
            "activity_data": msg,
            "competition_id": id
        }
        headers = {"X-API-Key": AGENT_API_KEY}

        try:
            val_response = requests.post("http://127.0.0.1:5005/api/submit", json=validation_payload, headers=headers)
            val_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"❌ Validation failed: {e}")
            flash("Validation failed. Please try again.", "danger")

        if request.is_json:
            return jsonify({"success": True}), 200
        else:
            flash("Activity submitted successfully!", "success")
            return redirect(url_for("messages", id=id))

    all_messages = list(db.messages.find({"competition_id": id}).sort("timestamp", 1))
    return render_template("messages.html", messages=all_messages, competition_id=id)


@app.route("/submit_activity", methods=["POST"])
@login_required
def submit_activity():
    user_id = request.form.get("user_id")
    competition_id = request.form.get("competition_id")
    activity_data = request.form.get("activity_data")

    if not all([user_id, competition_id, activity_data]):
        flash("Missing information. Please fill all fields.", "danger")
        return redirect(url_for("user_dashboard"))

    payload = {
        "user_id": user_id,
        "activity_data": activity_data,
        "competition_id": competition_id
    }
    headers = {"X-API-Key": AGENT_API_KEY}

    try:
        validation_response = requests.post("http://127.0.0.1:5005/api/submit", json=payload, headers=headers)
        validation_response.raise_for_status()
        flash("Activity submitted successfully!", "success")
    except requests.exceptions.RequestException as e:
        flash(f"Error sending data to validation service: {e}", "danger")

    return redirect(url_for("user_dashboard"))


# -------------------
# RUN APP
# -------------------
if __name__ == "__main__":
    app.run(debug=True, port=5000)

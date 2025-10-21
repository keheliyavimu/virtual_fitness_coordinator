from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import os, re

app = Flask(__name__)

# -------------------------------------------------------------
# Load environment variables and connect to MongoDB
# -------------------------------------------------------------
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")
AGENT_API_KEY = os.getenv("AGENT_API_KEY")  # ✅ shared secret

try:
    client = MongoClient(MONGO_URI)
    db = client["webappdb"]                 # database
    leaderboard = db["leaderboards"]        # collection
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")

# -------------------------------------------------------------
# Helper: API Key authentication middleware
# -------------------------------------------------------------
def require_api_key(func):
    from functools import wraps
    @wraps(func)
    def wrapper(*args, **kwargs):
        key = request.headers.get("X-API-KEY")
        if not key or key != AGENT_API_KEY:
            print("🚫 Unauthorized access attempt detected!")
            return jsonify({"error": "Unauthorized (missing/invalid API key)."}), 401
        return func(*args, **kwargs)
    return wrapper

# -------------------------------------------------------------
# Helper: Input Sanitization
# -------------------------------------------------------------
def sanitize_text(text):
    if not isinstance(text, str):
        return ""
    # Remove scripts / HTML / unwanted symbols
    return re.sub(r'[<>;"\'{}$]', '', text.strip())

# -------------------------------------------------------------
# Route: Update or Add Score (called by Calculator Agent)
# -------------------------------------------------------------
@app.route("/api/update", methods=["POST"])
@require_api_key
def update_score():
    data = request.get_json(force=True)
    print("📦 Incoming data to leaderboard:", data)

    user_id = sanitize_text(data.get("user_id", ""))
    competition_id = sanitize_text(data.get("competition_id", ""))
    score = data.get("score", 0)
    reason = sanitize_text(
    data.get("reason") or data.get("ai_reasons") or "No reason provided"
    )

    if not user_id or not competition_id:
        print("⚠ Missing required fields!")
        return jsonify({"error": "Missing user_id or competition_id"}), 400

    # Ensure numeric score
    try:
        score = float(score)
    except (TypeError, ValueError):
        print("⚠ Invalid score value")
        return jsonify({"error": "Invalid score value"}), 400

    try:
        # Find existing record
        existing = leaderboard.find_one({"user_id": user_id, "competition_id": competition_id})
        if existing:
            # Increment score and append reason
            new_score = existing.get("score", 0) + score
            leaderboard.update_one(
                {"user_id": user_id, "competition_id": competition_id},
                {
                    "$set": {"score": new_score, "updated_at": datetime.utcnow()},
                    "$push": {"ai_reasons": reason}
                }
            )
            print(f"🔄 Updated: {user_id} total={new_score} for {competition_id}")
        else:
            # Insert new record
            leaderboard.insert_one({
                "user_id": user_id,
                "competition_id": competition_id,
                "score": score,
                "ai_reasons": [reason],
                "created_at": datetime.utcnow()
            })
            print(f"🆕 Inserted: {user_id} ({score}) for {competition_id}")

        return jsonify({
            "message": "Score updated successfully",
            "user_id": user_id,
            "competition_id": competition_id,
            "score_added": score
        }), 200

    except Exception as e:
        print(f"❌ Mongo update error: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------------------
# Route: Retrieve Leaderboard (used by WebApp)
# -------------------------------------------------------------
@app.route("/api/leaderboard/<competition_id>", methods=["GET"])
def get_leaderboard(competition_id):
    competition_id = sanitize_text(competition_id)
    try:
        results = leaderboard.find(
            {"competition_id": competition_id}, {"_id": 0}
        ).sort("score", -1)
        data = list(results)
        print(f"📊 Returning leaderboard for {competition_id}: {len(data)} entries")
        return jsonify({"leaderboard": data}), 200
    except Exception as e:
        print(f"❌ Leaderboard fetch error: {e}")
        return jsonify({"error": str(e)}), 500

# -------------------------------------------------------------
# Health Check (for demos)
# -------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "Leaderboard Agent running", "time": datetime.utcnow().isoformat()}), 200

# -------------------------------------------------------------
# Run Flask app
# -------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)

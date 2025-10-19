from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
from datetime import datetime
import os

app = Flask(__name__)

# -------------------------------------------------------------
# Load environment variables and connect to MongoDB
# -------------------------------------------------------------
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

try:
    client = MongoClient(MONGO_URI)
    db = client["webappdb"]                 # ✅ correct database
    leaderboard = db["leaderboards"]      # ✅ correct collection
    print("✅ Connected to MongoDB successfully")
except Exception as e:
    print(f"❌ MongoDB connection error: {e}")

# -------------------------------------------------------------
# Route: Update or Add Score
# -------------------------------------------------------------
@app.route("/api/update", methods=["POST"])
def update_score():
    data = request.get_json()
    print("📦 Incoming data to leaderboard:", data)

    user_id = data.get("user_id")
    competition_id = data.get("competition_id")  # ✅ NEW
    score = data.get("score")

    if not user_id or score is None or not competition_id:
        print("⚠ Missing required fields!")
        return jsonify({"error": "Missing user_id, competition_id, or score"}), 400

    try:
        result = leaderboard.update_one(
            {"user_id": user_id, "competition_id": competition_id},
            {
                "$inc": {"score": score},
                "$setOnInsert": {
                    "user_id": user_id,
                    "competition_id": competition_id,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
        print(f"✅ Updated/Inserted: {user_id} (+{score}) for competition {competition_id}")
        return jsonify({"message": "Score updated", "user_id": user_id}), 200

    except Exception as e:
        print(f"❌ Mongo update error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/leaderboard/<competition_id>", methods=["GET"])
def get_leaderboard(competition_id):
    try:
        results = leaderboard.find({"competition_id": competition_id}, {"_id": 0}).sort("score", -1)
        data = list(results)
        print(f"📊 Returning leaderboard for {competition_id}: {data}")
        return jsonify({"leaderboard": data}), 200
    except Exception as e:
        print(f"❌ Leaderboard fetch error: {e}")
        return jsonify({"error": str(e)}), 500


# -------------------------------------------------------------
# Run the Flask app
# -------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, port=5001)

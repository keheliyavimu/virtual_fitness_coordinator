from flask import Flask, request, jsonify
from pymongo import MongoClient
from dotenv import load_dotenv
import os

app = Flask(__name__)

# Load environment variables
load_dotenv()

# Connect to MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["fitness_competition"]
leaderboard = db["leaderboard"]

# -------------------------------------------------------------
# ⿡ Route: Update or Add Score
# -------------------------------------------------------------
@app.route("/api/update", methods=["POST"])
def update_score():
    data = request.get_json()
    user_id = data.get("user_id")
    score = data.get("score")

    if not user_id or score is None:
        return jsonify({"error": "Missing user_id or score"}), 400

    # Upsert: if user exists, add score; if not, create
    leaderboard.update_one(
        {"user_id": user_id},
        {"$inc": {"score": score}},  # increment score
        upsert=True
    )

    return jsonify({"message": f"Score updated for {user_id}", "added_score": score}), 200


# -------------------------------------------------------------
# ⿢ Route: Get Leaderboard (Sorted)
# -------------------------------------------------------------
@app.route("/api/leaderboard", methods=["GET"])
def get_leaderboard():
    results = leaderboard.find({}, {"_id": 0}).sort("score", -1)
    data = list(results)
    return jsonify({"leaderboard": data}), 200


# -------------------------------------------------------------
# Run the Flask app
# -------------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True,port=5001)
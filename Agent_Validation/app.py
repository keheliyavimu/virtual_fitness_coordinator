from flask import Flask, request, jsonify
import requests
import re
from dotenv import load_dotenv
import os

app = Flask(__name__)

# -------------------------------------------------------------
# Load environment variables
# -------------------------------------------------------------
load_dotenv()
CALCULATOR_AGENT_URL = os.getenv("CALCULATOR_AGENT_URL", "http://127.0.0.1:5002/api/calculate")
AGENT_API_KEY = os.getenv("AGENT_API_KEY")  # Shared secret between agents

# -------------------------------------------------------------
# Middleware: Require API Key for Validation Agent
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
    """Clean the text from potentially harmful characters."""
    if not isinstance(text, str):
        return ""
    return re.sub(r'[<>;"\'|&$]', '', text.strip())

# -------------------------------------------------------------
# Helper: Input Validation (Security + Responsible AI)
# -------------------------------------------------------------
def validate_input(data):
    """
    Validates user_id, activity_data, and competition_id.
    Returns a list of error messages if invalid, otherwise [].
    """
    errors = []
    user_id = sanitize_text(data.get('user_id', ''))
    activity_data = sanitize_text(data.get('activity_data', ''))
    competition_id = sanitize_text(data.get('competition_id', ''))

    # 1️⃣ Basic field checks
    if not user_id:
        errors.append("Missing 'user_id'.")
    if not activity_data:
        errors.append("Missing 'activity_data'.")
    if not competition_id:
        errors.append("Missing 'competition_id'.")
    if errors:
        return errors

    # 2️⃣ Validate user_id pattern
    if not re.match(r"^[a-zA-Z0-9_]+$", user_id):
        errors.append("Invalid 'user_id'. Only letters, numbers, and underscores allowed.")

    # 3️⃣ Check competition_id format (ObjectId or alphanumeric)
    if not re.match(r"^[a-fA-F0-9]{24}$", competition_id):
        errors.append("Invalid 'competition_id'. Must be a 24-character hex ID.")

    # 4️⃣ Ethical & Responsible AI filtering (ban unsafe / violent activities)
    banned_words = ["kill", "attack", "hurt", "injure", "explode"]
    if any(word in activity_data.lower() for word in banned_words):
        errors.append("Inappropriate or unsafe activity detected — please rephrase responsibly.")

    # 5️⃣ Activity clarity rule
    if len(activity_data.split()) < 3:
        errors.append("Activity description too short or unclear — please describe more clearly.")

    return errors

# -------------------------------------------------------------
# API: Validate & Forward to Calculator Agent
# -------------------------------------------------------------
@app.route('/api/submit', methods=['POST'])
@require_api_key
def submit_activity():
    data = request.get_json(force=True)
    print("📩 Received submission:", data)

    validation_errors = validate_input(data)
    if validation_errors:
        print(f"⚠ Validation failed: {validation_errors}")
        return jsonify({"errors": validation_errors}), 400

    payload = {
        "user_id": sanitize_text(data['user_id']),
        "activity_data": sanitize_text(data['activity_data']),
        "competition_id": sanitize_text(data['competition_id'])
    }

    headers = {"X-API-KEY": AGENT_API_KEY, "Content-Type": "application/json"}

    try:
        print(f"📤 Forwarding to Calculator Agent @ {CALCULATOR_AGENT_URL}")
        response = requests.post(CALCULATOR_AGENT_URL, json=payload, headers=headers, timeout=15)
        print(f"📥 Calculator Agent responded: {response.status_code}")

        if response.status_code != 200:
            print("⚠ Calculator Agent returned an error:", response.text)
            return jsonify({"error": "Calculator Agent returned an error", "details": response.text}), response.status_code

        return jsonify({
            "message": "✅ Validation successful — forwarded to Calculator Agent.",
            "calculator_response": response.json()
        }), 200

    except requests.exceptions.RequestException as e:
        print(f"❌ Network/Agent error: {e}")
        return jsonify({"error": f"Failed to communicate with Calculator Agent: {e}"}), 500

# -------------------------------------------------------------
# Health Check Endpoint
# -------------------------------------------------------------
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "Validation Agent active",
        "connected_to": CALCULATOR_AGENT_URL
    }), 200

# -------------------------------------------------------------
# Run Flask App
# -------------------------------------------------------------
if __name__ == '__main__':
    print("🚀 Starting Validation Agent on port 5005...")
    app.run(debug=True, port=5005)

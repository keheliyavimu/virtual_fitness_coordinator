from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
from dotenv import load_dotenv
import os, re, json

# -------------------------------------------------------------------
# Flask App Initialization
# -------------------------------------------------------------------
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# URL for Leaderboard Agent
LEADERBOARD_AGENT_URL = "http://127.0.0.1:5001/api/update"


# -------------------------------------------------------------------
# Function: AI Scoring using Gemini
# -------------------------------------------------------------------
def calculate_score_with_ai(activity_data):
    prompt = f"""
    You are a fitness scoring assistant. Based on the user's description below, 
    calculate a fair score according to these rules:

    - 1000 steps = 1 point
    - 1 push-up = 0.1 points
    - 1 squat = 0.1 points
    - 1 minute running = 2 points
    - 1 minute cycling = 1.5 points
    - 1 minute weight training = 3 points

    Respond ONLY with valid JSON in this format:
    {{
        "score": <calculated_score>,
        "reason": "<brief explanation>"
    }}

    If unclear, respond with:
    {{
        "score": 0,
        "reason": "Activity not recognized"
    }}

    User's input: "{activity_data}"
    """

    try:
        model = genai.GenerativeModel("models/gemini-2.5-pro")
        response = model.generate_content(prompt)
        raw_text = response.text.strip()
        print(f"🤖 RAW GEMINI RESPONSE: {raw_text}")

        # Extract JSON safely from Gemini output
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if match:
            result = json.loads(match.group(0))
            return result
        else:
            return {"score": 0, "reason": "Invalid AI output format"}

    except Exception as e:
        print(f"❌ AI Error: {e}")
        return {"score": 0, "reason": f"AI system error: {str(e)}"}


# -------------------------------------------------------------------
# Flask Route: Calculate Score
# -------------------------------------------------------------------
@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    user_id = data.get('user_id')
    activity_data = data.get('activity_data')

    if not user_id or not activity_data:
        return jsonify({"error": "Missing user_id or activity_data"}), 400

    print(f"🧠 Calculating score for {user_id}: {activity_data}")

    # Use AI to calculate the score
    ai_result = calculate_score_with_ai(activity_data)
    score = ai_result.get("score", 0)
    reason = ai_result.get("reason", "No reason provided")

    # Send the score to Leaderboard Agent
    try:
        payload = {"user_id": user_id, "score": score}
        response = requests.post(LEADERBOARD_AGENT_URL, json=payload)
        response.raise_for_status()

        return jsonify({
            "message": "Score calculated via Gemini and sent to leaderboard.",
            "calculated_score": score,
            "ai_reason": reason
        }), 200

    except requests.exceptions.RequestException as e:
        print(f"⚠ Communication error: {e}")
        return jsonify({"error": f"Failed to send data to leaderboard agent: {e}"}), 500


# -------------------------------------------------------------------
# Run Flask App
# -------------------------------------------------------------------
if __name__ == '__main__':
    app.run(debug=True,port=5002)
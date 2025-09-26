from flask import Flask, request, jsonify
import requests

app = Flask(__name__) #app

# The URL of the Leaderboard Manager Agent (Agent 3)
LEADERBOARD_AGENT_URL = "http://127.0.0.1:5001/api/update"

# A very simple rule: If it's steps, points = steps / 1000
def calculate_score(activity_data):
    # This is a very basic rule. You will make this SMARTER later with LLMs.
    if activity_data.startswith("steps:"):
        try:
            steps = int(activity_data.split(":")[1].strip())
            return steps / 1000  # 10,000 steps = 10 points
        except:
            return None
    # Add more rules here later for "pushups:", "squats:", etc.
    return None

# Endpoint to calculate a score
@app.route('/api/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    user_id = data.get('user_id')
    activity_data = data.get('activity_data')

    if not user_id or not activity_data:
        return jsonify({"error": "Missing user_id or activity_data"}), 400

    print(f"Calculating score for {user_id} who did: {activity_data}")

    # Calculate the score using our simple rule
    score = calculate_score(activity_data)

    if score is None:
        return jsonify({"error": "Could not calculate score for this activity"}), 400

    # Now, send the score to the Leaderboard Agent (Agent 3)
    try:
        payload = {"user_id": user_id, "score": score}
        response = requests.post(LEADERBOARD_AGENT_URL, json=payload)
        response.raise_for_status() # Check for errors
        print(f"Successfully sent score to leaderboard agent.")
        return jsonify({"message": "Score calculated and sent.", "calculated_score": score}), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to communicate with leaderboard agent: {e}"}), 500

if __name__ == '__main__':
    # Run on port 5002
    app.run(debug=True, port=5002)
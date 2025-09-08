from flask import Flask, request, jsonify

app = Flask(__name__)

# A simple in-memory "database" to store our scores. We'll use a dictionary.
# Format: { user_id: score }
leaderboard_data = {}

# Endpoint to update the leaderboard
@app.route('/api/update', methods=['POST'])
def update_leaderboard():
    # Get the JSON data sent to this endpoint
    data = request.get_json()
    user_id = data.get('user_id')
    score = data.get('score')

    # Basic validation
    if not user_id or score is None:
        return jsonify({"error": "Missing user_id or score"}), 400

    # Update the score for the user. This simply adds the new score to their total.
    # For a real project, you might want to store each activity separately.
    current_score = leaderboard_data.get(user_id, 0)
    leaderboard_data[user_id] = current_score + score

    print(f"Leaderboard updated. {user_id} now has {leaderboard_data[user_id]} points.")
    return jsonify({"message": "Score updated successfully", "user_id": user_id, "new_score": leaderboard_data[user_id]}), 200

# Endpoint to get the current leaderboard
@app.route('/api/leaderboard', methods=['GET'])
def get_leaderboard():
    # Sort the users by their score in descending order (highest first)
    sorted_leaderboard = sorted(leaderboard_data.items(), key=lambda x: x[1], reverse=True)
    
    # Format it nicely for the response
    result = [{"user_id": user, "score": score} for user, score in sorted_leaderboard]
    return jsonify(result), 200

if __name__ == '__main__':
    # Run the app on port 5001. Each agent must run on a different port!
    app.run(debug = True, port = 5001)
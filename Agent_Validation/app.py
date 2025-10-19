from flask import Flask, request, jsonify
import requests
import re  # For input validation

app = Flask(__name__)

# The URL of the Score Calculator Agent (Agent 2)
CALCULATOR_AGENT_URL = "http://127.0.0.1:5002/api/calculate"

# Simple validation function
def validate_input(data):
    """
    Validates the user_id, activity_data, and competition_id.
    Returns a list of error messages if invalid, otherwise an empty list.
    """
    errors = []
    user_id = data.get('user_id')
    activity_data = data.get('activity_data')
    competition_id = data.get('competition_id')

    # 1. Check if fields exist
    if not user_id:
        errors.append("Missing 'user_id' field.")
    if not activity_data:
        errors.append("Missing 'activity_data' field.")
    if not competition_id:
        errors.append("Missing 'competition_id' field.")

    if errors:
        return errors  # Return early if basic fields are missing

    # 2. SECURITY: Validate user_id (only allow letters, numbers, underscores)
    if not re.match("^[a-zA-Z0-9_]+$", user_id):
        errors.append("Invalid 'user_id'. Only letters, numbers, and underscores are allowed.")

    # 3. SECURITY: Basic sanitization of activity_data
    malicious_patterns = [';', '<', '>', '|', '&', '$']  # Simple example patterns
    for pattern in malicious_patterns:
        if pattern in activity_data:
            errors.append(f"Suspicious characters found in 'activity_data'.")
            break

    # 4. SECURITY: Validate competition_id (must be alphanumeric or ObjectId-like)
    if not re.match("^[a-fA-F0-9]{24}$", competition_id):
        errors.append("Invalid 'competition_id'. Must be a valid ObjectId.")

    return errors

# Endpoint to receive and validate data
@app.route('/api/submit', methods=['POST'])
def submit_activity():
    data = request.get_json()

    # Validate the input data
    validation_errors = validate_input(data)
    if validation_errors:
        return jsonify({"errors": validation_errors}), 400

    # Forward to Calculator Agent including competition_id
    payload = {
        "user_id": data['user_id'],
        "activity_data": data['activity_data'],
        "competition_id": data['competition_id']  # <-- include competition_id
    }

    try:
        print(f"Forwarding valid data to Calculator Agent: {payload}")
        response = requests.post(CALCULATOR_AGENT_URL, json=payload)
        response.raise_for_status()  # HTTP errors (4xx or 5xx)
        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        error_message = f"System error: Could not process your request. {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500

if __name__ == '__main__':
    print("Starting Validation Agent on port 5005...")
    app.run(debug=True, port=5005)

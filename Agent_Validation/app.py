from flask import Flask, request, jsonify
import requests
import re  # We need this for input validation with regular expressions

app = Flask(__name__)

# The URL of the Score Calculator Agent (Agent 2)
CALCULATOR_AGENT_URL = "http://127.0.0.1:5002/api/calculate"

# Simple validation function
def validate_input(data):
    """
    Validates the user_id and activity_data.
    Returns a list of error messages if invalid, otherwise an empty list.
    """
    errors = []
    user_id = data.get('user_id')
    activity_data = data.get('activity_data')

    # 1. Check if fields exist
    if not user_id:
        errors.append("Missing 'user_id' field.")
    if not activity_data:
        errors.append("Missing 'activity_data' field.")

    if errors:
        return errors  # Return early if basic fields are missing

    # 2. SECURITY: Validate user_id (only allow letters, numbers, underscores)
    if not re.match("^[a-zA-Z0-9_]+$", user_id):
        errors.append("Invalid 'user_id'. Only letters, numbers, and underscores are allowed.")

    # 3. SECURITY: Basic sanitization of activity_data
    # Check for common injection patterns (optional but good practice)
    malicious_patterns = [';', '<', '>', '|', '&', '$'] # Simple example patterns
    for pattern in malicious_patterns:
        if pattern in activity_data:
            errors.append(f"Suspicious characters found in 'activity_data'.")
            break # Stop after finding one pattern

    # 4. You can add more validations here (e.g., check if steps is a positive number)
    # For now, we'll keep it simple.

    return errors

# Endpoint to receive and validate data
@app.route('/api/submit', methods=['POST'])
def submit_activity():
    # Get the JSON data sent to this endpoint
    data = request.get_json()

    # Validate the input data
    validation_errors = validate_input(data)

    # If there are any errors, return them to the user
    if validation_errors:
        return jsonify({"errors": validation_errors}), 400 # 400 = Bad Request

    # If the data is valid, forward it to the Calculator Agent (Agent 2)
    try:
        print(f"Forwarding valid data to Calculator Agent: {data}")
        response = requests.post(CALCULATOR_AGENT_URL, json=data)
        response.raise_for_status()  # Check for HTTP errors (4xx or 5xx)

        # If successful, forward the Calculator Agent's response back to the user
        return jsonify(response.json()), response.status_code

    except requests.exceptions.RequestException as e:
        # If communication with Agent 2 fails
        error_message = f"System error: Could not process your request. {e}"
        print(error_message)
        return jsonify({"error": error_message}), 500 # 500 = Internal Server Error

if __name__ == '__main__':
    # Run on port 5000. Each agent must run on a different port!
    print("Starting Validation Agent on port 5000...")
    app.run(debug=True, port=5000)
# Agent_Calculator/app.py
from flask import Flask, request, jsonify
import requests
import google.generativeai as genai
from dotenv import load_dotenv
import os, re, json, logging

# Optional: spaCy for light NER/structure extraction
try:
    import spacy
    _spacy_available = True
except Exception:
    _spacy_available = False

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# -------------------------------------------------------------
# Load environment variables and configure Gemini
# -------------------------------------------------------------
load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
LEADERBOARD_AGENT_URL = os.getenv("LEADERBOARD_AGENT_URL", "http://127.0.0.1:5001/api/update")
AGENT_API_KEY = os.getenv("AGENT_API_KEY")  # Simple shared secret between agents

if not GOOGLE_API_KEY:
    logging.warning("GOOGLE_API_KEY not found in .env — LLM calls will fail.")
else:
    genai.configure(api_key=GOOGLE_API_KEY)

# -------------------------------------------------------------
# Optionally load spaCy model (if installed)
# -------------------------------------------------------------
nlp = None
if _spacy_available:
    try:
        # try small model — ensure you run: python -m spacy download en_core_web_sm
        nlp = spacy.load("en_core_web_sm")
        logging.info("spaCy model loaded.")
    except Exception as e:
        logging.warning(f"spaCy model not available or failed to load: {e}")
        nlp = None

# -------------------------------------------------------------
# Helpers: structured extraction (spaCy + regex fallback)
# -------------------------------------------------------------
def extract_activity_structured(text):
    """
    Extract structured info from user fitness description using both NER (if available)
    and regex-based heuristics.
    Returns: dict(minutes, reps, steps, distance_km, activity_type)
    """
    text_l = text.lower()
    structured = {
        "minutes": None,
        "reps": None,
        "steps": None,
        "distance_km": None,
        "activity_type": None
    }

    # --- NER pass ---
    if nlp:
        try:
            doc = nlp(text)
            if any(tok.lemma_ in ("run", "jog") for tok in doc):
                structured["activity_type"] = "running"
            elif any(tok.lemma_ in ("walk", "stroll") for tok in doc):
                structured["activity_type"] = "walking"
            elif any(tok.lemma_ in ("cycle", "bike") for tok in doc):
                structured["activity_type"] = "cycling"
            elif any(tok.lemma_ in ("swim",) for tok in doc):
                structured["activity_type"] = "swimming"
            elif any("push" in tok.text for tok in doc):
                structured["activity_type"] = "pushups"
            elif any("squat" in tok.text for tok in doc):
                structured["activity_type"] = "squats"

            for ent in doc.ents:
                if ent.label_ == "CARDINAL":
                    num_match = re.search(r'(\d+(\.\d+)?)', ent.text)
                    if not num_match:
                        continue
                    n = float(num_match.group(1))
                    window = doc[max(ent.start - 3, 0):min(ent.end + 3, len(doc))]
                    win_text = window.text.lower()

                    if any(w in win_text for w in ("minute", "minutes", "min")):
                        structured["minutes"] = structured["minutes"] or int(n)
                    elif any(w in win_text for w in ("pushup", "push-ups", "push up")):
                        structured["reps"] = structured["reps"] or int(n)
                    elif "step" in win_text:
                        structured["steps"] = structured["steps"] or int(n)
                    elif any(w in win_text for w in ("km", "kilometer", "kilometre")):
                        structured["distance_km"] = structured["distance_km"] or float(n)
        except Exception as e:
            logging.debug(f"spaCy parse error: {e}")

    # --- Regex fallback ---
    # Distance (e.g., 5 km, 3.2 kilometers)
    m = re.search(r'(\d+(\.\d+)?)\s*(km|kilometer|kilometre)\b', text_l)
    if m:
        structured["distance_km"] = structured["distance_km"] or float(m.group(1))
        structured["activity_type"] = structured["activity_type"] or "running"

    # Minutes
    m = re.search(r'(\d+)\s*(minutes|minute|mins|min)\b', text_l)
    if m:
        structured["minutes"] = structured["minutes"] or int(m.group(1))

    # Steps
    m = re.search(r'(\d+)\s*(steps?)\b', text_l)
    if m:
        structured["steps"] = structured["steps"] or int(m.group(1))
        structured["activity_type"] = structured["activity_type"] or "walking"

    # Reps
    m = re.search(r'(\d+)\s*(push-?ups?|squats?)\b', text_l)
    if m:
        structured["reps"] = structured["reps"] or int(m.group(1))
        if "push" in m.group(2):
            structured["activity_type"] = structured["activity_type"] or "pushups"
        else:
            structured["activity_type"] = structured["activity_type"] or "squats"

    # Activity inference by keywords
    if not structured["activity_type"]:
        if "run" in text_l or "jog" in text_l:
            structured["activity_type"] = "running"
        elif "walk" in text_l:
            structured["activity_type"] = "walking"
        elif "cycle" in text_l or "bike" in text_l:
            structured["activity_type"] = "cycling"
        elif "swim" in text_l:
            structured["activity_type"] = "swimming"
        elif "push" in text_l:
            structured["activity_type"] = "pushups"
        elif "squat" in text_l:
            structured["activity_type"] = "squats"

    return structured

# -------------------------------------------------------------
# LLM helpers: scoring and summarization
# -------------------------------------------------------------
def call_gemini(prompt):
    """Call Gemini and return raw text (handles errors)."""
    try:
        model = genai.GenerativeModel("models/gemini-2.5-pro")
        response = model.generate_content(prompt)
        raw_text = getattr(response, "text", "") or str(response)
        return raw_text.strip()
    except Exception as e:
        logging.error(f"LLM call failed: {e}")
        return ""

def parse_json_from_text(raw_text):
    match = re.search(r'\{.*\}', raw_text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception as e:
            logging.warning(f"Failed to JSON-parse LLM output: {e}")
            return None
    return None

def calculate_score_with_ai(activity_data, structured=None):
    """
    Call LLM to calculate a score. We pass structured parse to the prompt for clarity.
    Returns dict with 'score' and 'reason'.
    """
    structured = structured or {}
    prompt = f"""
You are a fitness scoring assistant. Use the rules below to calculate a fair score.

Rules:
- 1000 steps = 1 point
- 1 push-up = 0.1 points
- 1 squat = 0.1 points
- 1 minute running = 2 points
- 1 minute cycling = 1.5 points
- 1 minute weight training = 3 points

You will receive:
- The user's raw input: \"{activity_data}\"
- The parsed structure (if any): {json.dumps(structured)}

Calculate a numeric score (float or int) and provide a concise reason that references the parsed values if used.

Respond ONLY with valid JSON EXACTLY in this format:
{{ "score": <calculated_score>, "reason": "<brief explanation>" }}

If unclear or not applicable, respond with:
{{ "score": 0, "reason": "Activity not recognized" }}
    """

    raw = call_gemini(prompt)
    logging.info(f"🤖 RAW GEMINI RESPONSE: {raw}")
    result = parse_json_from_text(raw)
    if result and isinstance(result, dict) and "score" in result:
        return result
    else:
        return {"score": 0, "reason": "Invalid or unparsable AI output"}

# -------------------------------------------------------------
# Flask Route: Calculate Score (main)
# -------------------------------------------------------------
@app.route('/api/calculate', methods=['POST'])
def calculate():
    # Accept JSON only
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"error": "Invalid JSON payload."}), 400

    # Optional: simple API key check for calls from other agents (secure inter-agent calls)
    inbound_key = request.headers.get("X-API-KEY")
    if AGENT_API_KEY and inbound_key != AGENT_API_KEY:
        return jsonify({"error": "Unauthorized (missing/invalid API key)."}), 401

    user_id = data.get('user_id')
    activity_data = data.get('activity_data')
    competition_id = data.get('competition_id')

    if not user_id or not activity_data or not competition_id:
        return jsonify({"error": "Missing user_id, activity_data, or competition_id"}), 400

    logging.info(f"🧠 Calculating score for {user_id}: {activity_data}")

    # 1) structured extraction (NER + regex fallback)
    structured = extract_activity_structured(activity_data)
    logging.info(f"🔎 Parsed structure: {structured}")

    # 2) call LLM with structured input
    ai_result = calculate_score_with_ai(activity_data, structured=structured)
    score = ai_result.get("score", 0)
    reason = ai_result.get("reason", "No reason provided")

    # 3) prepare payload for leaderboard — include ai_reason for explainability
    payload = {
        "user_id": user_id,
        "score": score,
        "competition_id": competition_id,
        "ai_reasons": reason,
        "parsed": structured
    }

    headers = {}
    if AGENT_API_KEY:
        headers["X-API-KEY"] = AGENT_API_KEY

    try:
        logging.info("📤 Sending to leaderboard: %s", payload)
        response = requests.post(LEADERBOARD_AGENT_URL, json=payload, headers=headers, timeout=10)
        logging.info("📥 Leaderboard response code: %s", response.status_code)
        logging.info("📥 Leaderboard response text: %s", response.text)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        logging.error(f"⚠ Communication error with leaderboard: {e}")
        # still return the calculated score and reason, but indicate remote failure
        return jsonify({"error": f"Failed to send data to leaderboard agent: {e}", "calculated_score": score, "ai_reasons": reason}), 500

    return jsonify({
        "message": "Score calculated via Gemini and sent to leaderboard.",
        "calculated_score": score,
        "ai_reasons": reason
    }), 200

# -------------------------------------------------------------
# Flask Route: Summarize text (NLP summarization using LLM)
# -------------------------------------------------------------
@app.route('/api/summarize', methods=['POST'])
def summarize():
    data = request.get_json(force=True, silent=True)
    if not data or "text" not in data:
        return jsonify({"error": "Missing 'text' in JSON body"}), 400

    inbound_key = request.headers.get("X-API-KEY")
    if AGENT_API_KEY and inbound_key != AGENT_API_KEY:
        return jsonify({"error": "Unauthorized (missing/invalid API key)."}), 401

    text = data.get("text", "").strip()
    if not text:
        return jsonify({"error": "Empty text provided."}), 400

    prompt = f"""
Summarize the user messages below into a short (1-2 sentence) summary that highlights the key activities and any important numeric details:

---BEGIN---
{text}
---END---

Provide only the summary in plain text.
"""
    raw = call_gemini(prompt)
    # Gemini may return JSON or plain; we'll return the raw text safely
    summary = raw.strip() if raw else ""
    return jsonify({"summary": summary}), 200

# -------------------------------------------------------------
# Run Flask App
# -------------------------------------------------------------
if __name__ == '__main__':
    port = int(os.getenv("PORT", 5002))
    app.run(debug=True, port=port)

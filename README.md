
Each agent communicates securely over HTTP using API keys stored in `.env` files.  
All agents are isolated and can be deployed or scaled independently.

---

## 🧰 Technologies Used

| Category | Tools / Libraries |
|-----------|------------------|
| **Framework** | Flask |
| **Database** | MongoDB (pymongo) |
| **NLP** | spaCy (NER for entity extraction) |
| **LLM** | Google Gemini / OpenAI GPT |
| **Security** | dotenv, API keys, input sanitization |
| **Communication** | REST APIs (HTTP, JSON) |
| **Responsible AI** | Explainability logs, user data privacy, fairness policies |

---

## 🧠 Responsible AI Implementation

- **Fairness:** Same scoring logic applied for all participants.  
- **Explainability:** Every AI-generated score includes a natural language explanation.  
- **Transparency:** Logs include all reasoning and intermediate outputs.  
- **Data Protection:** No personal or sensitive data stored.  
- **Accountability:** Decisions traceable through reasoning logs.

---

## 🧩 Agent Responsibilities

### 🧹 Validation Agent (Port 5000)
- First point of contact for incoming user data.  
- Performs input validation and sanitization.  
- Uses authentication (API key).  
- Forwards valid data to the Score Calculator Agent.

### 🧮 Score Calculator Agent (Port 5002)
- Uses **spaCy** to extract quantitative values (e.g., steps, distance, time).  
- Uses **LLM (Gemini or GPT)** for contextual reasoning.  
- Generates:
  - **Score value**
  - **AI explanation**
- Sends output securely to the Leaderboard Agent.

### 🏆 Leaderboard Manager Agent (Port 5001)
- Maintains scores in MongoDB.  
- Aggregates user totals by competition.  
- Serves leaderboard data via REST endpoint.  
- Enforces authentication for data updates.

---

## 🔒 Security Features

- ✅ API key authentication across agents  
- ✅ Input sanitization & validation  
- ✅ `.env` secrets management  
- ✅ Separate microservices (principle of least privilege)  
- ✅ Logging & reasoning transparency  

---

## 🧠 NLP + LLM Integration

| Function | Example |
|-----------|----------|
| **Input Parsing** | “Walked around 6000 steps today” → steps = 6000 |
| **LLM Scoring Logic** | “Score is based on 6000 steps, where every 1000 steps = 1 point.” |
| **Explainability Output** | Stored as `ai_reason` in MongoDB for human-readable justification |

---

## ⚙️ Example Workflow

### **1️⃣ User Submission**
```json
{
  "user_id": "harindu",
  "activity_data": "Walked 6000 steps today after lunch."
}

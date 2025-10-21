# 🧠 Virtual Fitness Competition Coordinator

An **AI-powered multi-agent system** that automates virtual fitness challenges — from participant input to scoring and live leaderboard updates.  
This system demonstrates a modular, secure, and ethical implementation of **multi-agent collaboration**, **NLP reasoning**, and **Responsible AI** principles.

---

## ⚙️ System Overview

The project is built using a **multi-agent architecture** where each agent acts as an independent microservice communicating via REST APIs.  

| Agent | Role | Port | Key Features |
|--------|------|------|---------------|
| 🧩 **Validation Agent** | Entry point – validates, sanitizes, and routes user submissions. | `5000` | Input sanitization, authentication, secure routing |
| 🧮 **Score Calculator Agent** | Parses user activity using NLP and LLM reasoning, then assigns a score. | `5002` | Uses spaCy (NER) + Google Gemini (LLM) for context-aware scoring |
| 🏆 **Leaderboard Manager Agent** | Maintains leaderboard data and exposes ranking APIs. | `5001` | MongoDB persistence, competition aggregation, secure updates |

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

## ⚙️ Workflow Overview

### **2️⃣ Validation Agent**
- Sanitizes input  
- Checks authentication  
- Routes to Score Calculator Agent

## 👥 Contributors 
- [Chathuranga K.K.K.V.](https://github.com/keheliyavimu) 
- [Senaratne H.S.](https://github.com/HSSenaratne)

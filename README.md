# Virtual Fitness Competition Coordinator

A multi-agent AI system designed to automate the workflow of virtual fitness challenges. It handles participant data ingestion, validation, score calculation, and real-time leaderboard management.

## 🏗 System Architecture

The system is composed of three independent microservices (agents) that communicate via HTTP REST APIs:

1.  *Validation Agent (Port 5000):* The entry point. Sanitizes and validates all incoming data.
2.  *Score Calculator Agent (Port 5002):* Appoints rules and calculates scores for activities.
3.  *Leaderboard Manager Agent (Port 5001):* Maintains the competition state and serves leaderboard data.

## 🚀 How to Run

1.  *Clone the repository:*
    bash
    git clone https://github.com/your-username/your-repository-name.git
    cd your-repository-name
    

2.  *Set up each agent* (Repeat for each agent folder: agent_validation, agent_calculator, agent_leaderboard):
    bash
    # Navigate to the agent folder
    cd agent_validation

    # Create and activate a virtual environment
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate

    # Install dependencies
    pip install flask requests

    # Run the agent
    python app.py
    

3.  *Run all agents:* Each agent must be run in a separate terminal. They run on ports 5000, 5002, and 5001 respectively.

## 📡 API Usage

-   *Submit Activity:* POST http://localhost:5000/api/submit
    json
    {"user_id": "user123", "activity_data": "steps: 10000"}
    
-   *Get Leaderboard:* GET http://localhost:5001/api/leaderboard

## 👥 Contributors

-   [Chathuranga K.K.K.V.](https://github.com/keheliyavimu)
-   [Senaratne H.S.](https://github.com/HSSenaratne)  

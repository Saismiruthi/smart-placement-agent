# Smart Placement Agent 🚀

An AI-powered placement preparation platform designed to help students prepare for technical interviews, improve their skills, practice coding, and build better resumes.

## ✨ Features

- **Resume Analysis:** Upload a resume and identify skills, strengths, and areas for improvement.
- **Skill Gap Analysis:** Compare existing skills with job requirements and identify learning gaps.
- **Mock Interviews:** Practice interview questions and improve interview readiness.
- **Coding Practice:** Practice coding questions and strengthen problem-solving skills.
- **Personalized Roadmaps:** Get guidance on skills and topics to focus on for placement preparation.
- **Interview Preparation:** Access technical interview questions and preparation resources.
- **Analytics Dashboard:** Track preparation progress and review performance.
- **Feedback System:** Receive feedback to help improve your preparation.
- **AI-Powered Agents:** Use specialized agents for resume analysis, interview preparation, coding practice, planning, and skill gap analysis.

## 🛠️ Tech Stack

| Category | Technologies |
|---|---|
| Language | Python |
| AI / NLP | Large Language Models, NLP |
| Machine Learning | Python ML ecosystem |
| Vector Database | ChromaDB |
| Data Processing | Pandas, NumPy |
| User Interface | Python-based UI |
| Testing | Pytest / Python test scripts |
| Development Tools | Git, GitHub, VS Code |

*Note: Confirm the technologies against your implementation and `requirements.txt` before publishing.*

## 📂 Project Structure

```text
smart-placement-agent/
├── agents/
│   ├── coding_trainer_agent.py
│   ├── feedback_agent.py
│   ├── interview_agent.py
│   ├── memory_agent.py
│   ├── planner_agent.py
│   ├── resume_agent.py
│   └── skill_gap_agent.py
├── data/
│   ├── datasets/
│   ├── sample_resumes/
│   └── generate_datasets.py
├── tests/
├── tools/
│   ├── db_manager.py
│   ├── nlp_extractor.py
│   ├── pdf_parser.py
│   └── vector_store.py
├── ui/
│   └── pages/
├── app.py
├── config.py
├── generate_datasets.py
├── requirements.txt
└── .gitignore
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/Saismiruthi/smart-placement-agent.git
cd smart-placement-agent
```

### 2. Create a virtual environment

**Windows:**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Configure the API keys, model settings, and other environment variables required by your application. Never commit API keys, passwords, or other secrets to GitHub.

### 5. Run the application

Check `app.py` for the application's entry point and use the corresponding launch command. For example, if it is a Streamlit application:

```bash
streamlit run app.py
```

If the project uses another framework or requires a local language model, follow the configuration and startup instructions for that implementation.

## 🧪 Testing

Run the relevant test scripts to validate individual agents and application components.

```bash
python -m pytest tests/
```

Additional test scripts are available in the project root for individual agents.

## 🎯 Project Objective

The goal of Smart Placement Agent is to make placement preparation more structured and personalized by combining AI-driven assistance, resume analysis, skill gap identification, coding practice, and interview preparation in one platform.

## 🔒 Privacy and Security

- Do not upload API keys, credentials, or private environment files.
- Keep personal resumes and student information private.
- Exclude generated model files, caches, and vector database files when they are not required in the repository.

## 👩‍💻 Author

**Saismiruthi Mathivanan**

GitHub: [@Saismiruthi](https://github.com/Saismiruthi)

---

If you find this project useful, consider giving the repository a ⭐ on GitHub!
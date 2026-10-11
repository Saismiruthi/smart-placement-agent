# config.py — Global configuration for the entire project

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
MEMORY_DIR = BASE_DIR / "memory"
CHROMA_DIR = MEMORY_DIR / "chroma_db"
SQLITE_PATH = MEMORY_DIR / "sqlite" / "students.db"

# ── LLM Configuration ──────────────────────────────────────────────────
OLLAMA_BASE_URL = "http://localhost:11434"
LLM_MODEL = "phi3"          # The model you have installed

# ── Embedding Model ────────────────────────────────────────────────────
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # Lightweight, fast, accurate

# ── ChromaDB Collections ───────────────────────────────────────────────
COLLECTION_RESUMES = "student_resumes"
COLLECTION_SKILLS = "skill_embeddings"
COLLECTION_MEMORY = "student_memory"

# ── Dataset Paths ──────────────────────────────────────────────────────
JOB_SKILLS_CSV = DATA_DIR / "datasets" / "job_skills.csv"
CODING_QUESTIONS_CSV = DATA_DIR / "datasets" / "coding_questions.csv"
INTERVIEW_QUESTIONS_CSV = DATA_DIR / "datasets" / "interview_questions.csv"

# ── Agent Settings ─────────────────────────────────────────────────────
MAX_CODING_PROBLEMS_PER_SESSION = 5
DIFFICULTY_LEVELS = ["easy", "medium", "hard"]
PASSING_SCORE_THRESHOLD = 0.6     # 60% to pass an interview round

# ── Logging ────────────────────────────────────────────────────────────
LOG_LEVEL = "INFO"
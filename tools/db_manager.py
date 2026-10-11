# tools/db_manager.py
# SQLite database manager for storing student profiles and session history

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from loguru import logger
from config import SQLITE_PATH


def init_database():
    """
    Create all required tables if they don't exist.
    Call this once at app startup.
    """
    SQLITE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    conn = sqlite3.connect(str(SQLITE_PATH))
    cursor = conn.cursor()
    
    # Students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT UNIQUE NOT NULL,
            name TEXT,
            email TEXT,
            phone TEXT,
            linkedin TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Skills table (extracted from resume)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            skill TEXT NOT NULL,
            category TEXT,
            confidence REAL,
            source TEXT DEFAULT 'resume',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)
    
    # Session history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            session_type TEXT,
            score REAL,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (student_id) REFERENCES students(student_id)
        )
    """)
    
    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def save_student_profile(student_id: str, personal_info: dict, skills_data: dict):
    """
    Save or update a student's profile and skills in the database.
    
    Args:
        student_id: Unique ID for the student (e.g. email or UUID)
        personal_info: Dict from extract_personal_info()
        skills_data: Dict from NLPSkillExtractor.extract_skills()
    """
    init_database()
    
    conn = sqlite3.connect(str(SQLITE_PATH))
    cursor = conn.cursor()
    
    # Upsert student record
    cursor.execute("""
        INSERT INTO students (student_id, name, email, phone, linkedin, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(student_id) DO UPDATE SET
            name=excluded.name,
            email=excluded.email,
            phone=excluded.phone,
            linkedin=excluded.linkedin,
            updated_at=excluded.updated_at
    """, (
        student_id,
        personal_info.get("name", ""),
        personal_info.get("email", ""),
        personal_info.get("phone", ""),
        personal_info.get("linkedin", ""),
        datetime.now().isoformat()
    ))
    
    # Delete old skills and reinsert fresh
    cursor.execute("DELETE FROM student_skills WHERE student_id = ?", (student_id,))
    
    confidence_scores = skills_data.get("confidence_scores", {})
    skills_by_category = skills_data.get("skills_by_category", {})
    
    for category, skills in skills_by_category.items():
        for skill in skills:
            cursor.execute("""
                INSERT INTO student_skills (student_id, skill, category, confidence)
                VALUES (?, ?, ?, ?)
            """, (student_id, skill, category, confidence_scores.get(skill, 0.0)))
    
    conn.commit()
    conn.close()
    logger.info(f"Saved profile for student: {student_id}")


def get_student_profile(student_id: str) -> dict:
    """Retrieve a student's full profile from the database."""
    conn = sqlite3.connect(str(SQLITE_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    student = cursor.execute(
        "SELECT * FROM students WHERE student_id = ?", (student_id,)
    ).fetchone()
    
    if not student:
        conn.close()
        return {}
    
    skills = cursor.execute(
        "SELECT skill, category, confidence FROM student_skills WHERE student_id = ?",
        (student_id,)
    ).fetchall()
    
    conn.close()
    
    return {
        "student_id": student["student_id"],
        "name": student["name"],
        "email": student["email"],
        "phone": student["phone"],
        "linkedin": student["linkedin"],
        "skills": [dict(s) for s in skills],
        "skill_names": [s["skill"] for s in skills]
    }


def save_session(student_id: str, session_type: str, score: float, details: dict):
    """Save a practice/interview session result."""
    
    # Safety guard — ensure tables exist before writing
    init_database()
    
    conn = sqlite3.connect(str(SQLITE_PATH))
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO sessions (student_id, session_type, score, details)
        VALUES (?, ?, ?, ?)
    """, (student_id, session_type, score, json.dumps(details)))
    conn.commit()
    conn.close()
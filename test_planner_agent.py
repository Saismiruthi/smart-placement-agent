# test_planner_agent.py
# Tests the Planner Agent end-to-end using seeded data

import sqlite3
import json
from datetime import datetime, timedelta
from tools.db_manager import init_database
from agents.planner_agent import PlannerAgent
from config import SQLITE_PATH


def seed_student(student_id: str):
    """Seed a student profile and sessions for testing."""
    init_database()
    conn   = sqlite3.connect(str(SQLITE_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO students (student_id, name, email)
        VALUES (?, ?, ?)
    """, (student_id, "Rahul Verma", "rahul.verma@gmail.com"))

    # Seed skills
    skills = [
        ("Python", "programming_languages", 0.98),
        ("SQL",    "databases",             0.95),
        ("Flask",  "web_technologies",      0.88),
        ("Git",    "cloud_and_devops",      0.90),
    ]
    for skill, cat, conf in skills:
        cursor.execute("""
            INSERT OR IGNORE INTO student_skills
            (student_id, skill, category, confidence)
            VALUES (?, ?, ?, ?)
        """, (student_id, skill, cat, conf))

    # Seed sessions
    base = datetime.now() - timedelta(days=5)
    sessions = [
        ("coding_practice", 0.55, {
            "problems_attempted": 5,
            "average_score": 0.55,
            "final_difficulty": "easy",
            "performance_band": "Needs Practice",
            "individual_scores": [[1, 0.50], [2, 0.60]]
        }, base),
        ("mock_interview", 0.62, {
            "hr_score": 0.70, "technical_score": 0.57,
            "overall_score": 0.62, "passed": True,
            "target_role": "Software Development Engineer",
            "conversation": [
                {"topic": "Introduction", "score": 0.80,
                 "question": "Tell me about yourself."},
                {"topic": "DSA", "score": 0.40,
                 "question": "What is time complexity?"},
                {"topic": "OOP", "score": 0.45,
                 "question": "Explain inheritance."},
            ]
        }, base + timedelta(days=2)),
    ]

    for stype, score, details, ts in sessions:
        cursor.execute("""
            INSERT INTO sessions
            (student_id, session_type, score, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, stype, score, json.dumps(details), ts.isoformat()))

    conn.commit()
    conn.close()
    print(f"✅ Student '{student_id}' seeded\n")


def test_planner():
    STUDENT     = "rahul_verma_test"
    TARGET_ROLE = "Software Development Engineer"
    W           = 62

    seed_student(STUDENT)
    planner = PlannerAgent()

    # ── 1. Dashboard ──────────────────────────────────────────────
    print("=" * W)
    print("  STEP 1 — STUDENT DASHBOARD")
    print("=" * W)

    dashboard = planner.get_student_dashboard(STUDENT)

    print(f"  Student       : {dashboard['profile'].get('name', 'Unknown')}")
    print(f"  Status        : {dashboard['status']}")
    score = dashboard["overall_readiness"]
    bar   = "█" * int(score * 20) + "░" * (20 - int(score * 20))
    print(f"  Readiness     : [{bar}] {score:.0%}")
    print(f"  Band          : {dashboard['readiness_band']}")
    print(f"  Sessions Done : {dashboard['sessions_done']}")
    print(f"  Weak Topics   : {dashboard['weak_topics']}")
    print(f"  Strong Topics : {dashboard['strong_topics']}")
    print(f"\n  🧠 Mentor Brief:")
    print(f"  {dashboard['mentor_brief']}")

    # ── 2. Automated Session ──────────────────────────────────────
    print(f"\n{'=' * W}")
    print("  STEP 2 — AUTO-ROUTED SESSION")
    print("=" * W)

    result = planner.run_session(
        student_id   = STUDENT,
        session_type = "auto",
        target_role  = TARGET_ROLE
    )

    print(f"  Session Type  : {result['session_type']}")
    print(f"  Target Role   : {result['target_role']}")
    print(f"  Weak Topics   : {result['weak_topics']}")
    print(f"  Memories Saved: {result['memories_written']}")

    if "coding_result" in result:
        cr = result["coding_result"]
        print(f"\n  [Coding Results]")
        print(f"  Avg Score     : {cr.get('average_score', 0):.0%}")
        print(f"  Performance   : {cr.get('performance_band', '')}")
        for item in cr.get("individual_results", []):
            s   = item["score"]
            bar = "█" * int(s * 10) + "░" * (10 - int(s * 10))
            print(f"    {item['problem'][:30]:<30} [{bar}] {s:.2f}")

    if "interview_result" in result:
        ir = result["interview_result"]
        print(f"\n  [Interview Results]")
        print(f"  Overall Score : {ir.get('overall_score', 0):.0%}")
        print(f"  Decision      : {ir.get('result', '')}")
        for item in ir.get("individual_results", []):
            s   = item["score"]
            bar = "█" * int(s * 10) + "░" * (10 - int(s * 10))
            print(f"    {item['topic']:<18} [{bar}] {s:.2f}")

    # ── 3. Next Steps ─────────────────────────────────────────────
    print(f"\n{'=' * W}")
    print("  STEP 3 — NEXT SESSION PLAN")
    print("=" * W)
    for i, step in enumerate(result.get("next_session_plan", []), 1):
        print(f"  {i}. {step}")

    # ── 4. Full Roadmap ───────────────────────────────────────────
    print(f"\n{'=' * W}")
    print("  STEP 4 — 8-WEEK LEARNING ROADMAP")
    print("=" * W)
    roadmap = planner.generate_roadmap(STUDENT, TARGET_ROLE, weeks=8)
    # Print first 3 weeks to keep output concise
    weeks   = roadmap.split("WEEK ")
    for w in weeks[1:4]:
        print(f"  WEEK {w[:200]}\n")

    print("=" * W)
    print("  ✅ Planner Agent test complete!")
    print("=" * W)


if __name__ == "__main__":
    test_planner()
# test_feedback_agent.py
# Seeds synthetic session data then runs the full feedback report

import sqlite3
import json
from datetime import datetime, timedelta
from tools.db_manager import init_database
from agents.feedback_agent import FeedbackAgent
from config import SQLITE_PATH


def seed_test_data(student_id: str):
    """
    Insert synthetic session history so the feedback agent
    has real data to analyze without needing to run all prior phases.
    """
    init_database()
    conn   = sqlite3.connect(str(SQLITE_PATH))
    cursor = conn.cursor()

    # Insert a student profile if not present
    cursor.execute("""
        INSERT OR IGNORE INTO students (student_id, name, email)
        VALUES (?, ?, ?)
    """, (student_id, "Arjun Kumar", "arjun.kumar@gmail.com"))

    base_time = datetime.now() - timedelta(days=14)

    sessions = [
        # Coding sessions — improving over time
        ("coding_practice", 0.42, {
            "problems_attempted": 5, "average_score": 0.42,
            "final_difficulty": "easy", "performance_band": "Needs Practice",
            "individual_scores": [[1, 0.40], [2, 0.35], [3, 0.50], [4, 0.45], [5, 0.38]]
        }, base_time),

        ("coding_practice", 0.58, {
            "problems_attempted": 5, "average_score": 0.58,
            "final_difficulty": "easy", "performance_band": "Needs Practice",
            "individual_scores": [[6, 0.55], [7, 0.60], [8, 0.50], [9, 0.65], [10, 0.60]]
        }, base_time + timedelta(days=3)),

        ("coding_practice", 0.74, {
            "problems_attempted": 5, "average_score": 0.74,
            "final_difficulty": "medium", "performance_band": "Good",
            "individual_scores": [[11, 0.80], [12, 0.70], [13, 0.75], [14, 0.72], [15, 0.73]]
        }, base_time + timedelta(days=7)),

        # Interview sessions — with detailed conversation
        ("mock_interview", 0.61, {
            "hr_score": 0.72, "technical_score": 0.54,
            "overall_score": 0.61, "passed": True,
            "target_role": "Data Scientist",
            "conversation": [
                {"topic": "Introduction",  "score": 0.80, "question": "Tell me about yourself."},
                {"topic": "Behavioral",    "score": 0.70, "question": "Describe a challenge."},
                {"topic": "Self-awareness","score": 0.65, "question": "Strengths and weaknesses?"},
                {"topic": "OOP",           "score": 0.45, "question": "What is OOP?"},
                {"topic": "ML",            "score": 0.50, "question": "What is ML?"},
                {"topic": "Statistics",    "score": 0.38, "question": "Explain normal distribution."},
            ]
        }, base_time + timedelta(days=5)),

        ("mock_interview", 0.68, {
            "hr_score": 0.75, "technical_score": 0.63,
            "overall_score": 0.68, "passed": True,
            "target_role": "Data Scientist",
            "conversation": [
                {"topic": "Introduction",  "score": 0.82, "question": "Tell me about yourself."},
                {"topic": "Teamwork",      "score": 0.78, "question": "Tell me about teamwork."},
                {"topic": "Career Goals",  "score": 0.70, "question": "5-year plan?"},
                {"topic": "OOP",           "score": 0.42, "question": "What is polymorphism?"},
                {"topic": "Statistics",    "score": 0.40, "question": "What is p-value?"},
                {"topic": "Database",      "score": 0.55, "question": "Explain normalization."},
            ]
        }, base_time + timedelta(days=10)),
    ]

    for stype, score, details, ts in sessions:
        cursor.execute("""
            INSERT INTO sessions (student_id, session_type, score, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, stype, score, json.dumps(details), ts.isoformat()))

    conn.commit()
    conn.close()
    print(f"✅ Seeded {len(sessions)} test sessions for {student_id}\n")


def display_report(report: dict):
    """Pretty-print the feedback report to the console."""
    w = 60

    print("=" * w)
    print("  PLACEMENT FEEDBACK REPORT")
    print("=" * w)
    print(f"  Student       : {report['student_name']}")
    print(f"  Generated At  : {report['report_generated_at'][:19]}")
    print(f"  Sessions Used : {report['sessions_analyzed']}")

    score = report["overall_readiness"]
    bar   = "█" * int(score * 20) + "░" * (20 - int(score * 20))
    print(f"\n  Overall Readiness : [{bar}] {score:.0%}")
    print(f"  Status            : {report['readiness_band']}")

    # Coding Summary
    cs = report["coding_summary"]
    if cs.get("sessions", 0) > 0:
        print(f"\n{'─' * w}")
        print("  CODING PERFORMANCE")
        print(f"{'─' * w}")
        print(f"  Sessions Completed : {cs['sessions']}")
        print(f"  Average Score      : {cs['average_score']:.0%}")
        print(f"  Best Score         : {cs['best_score']:.0%}")
        cbar = "█" * int(cs['average_score'] * 20) + "░" * (20 - int(cs['average_score'] * 20))
        print(f"  Progress Bar       : [{cbar}]")
        trajectory = cs.get("score_trajectory", 0)
        arrow = "⬆️ Improving" if trajectory > 0.05 else ("⬇️ Declining" if trajectory < -0.05 else "➡️ Stable")
        print(f"  Trajectory         : {arrow} ({trajectory:+.2f})")

    # Interview Summary
    ivs = report["interview_summary"]
    if ivs.get("sessions", 0) > 0:
        print(f"\n{'─' * w}")
        print("  INTERVIEW PERFORMANCE")
        print(f"{'─' * w}")
        print(f"  Sessions Completed : {ivs['sessions']}")
        print(f"  HR Score           : {ivs['average_hr_score']:.0%}")
        print(f"  Technical Score    : {ivs['average_tech_score']:.0%}")
        print(f"  Pass Rate          : {ivs['pass_rate']:.0%}  ({ivs['passes']}/{ivs['sessions']} passed)")

        if ivs.get("topic_scores"):
            print(f"\n  Topic Breakdown:")
            for topic, avg in sorted(ivs["topic_scores"].items(), key=lambda x: x[1]):
                tbar   = "█" * int(avg * 10) + "░" * (10 - int(avg * 10))
                flag   = " ⚠️" if avg < 0.50 else " ✅" if avg >= 0.75 else ""
                print(f"    {topic:<20} [{tbar}] {avg:.0%}{flag}")

    # Weak and Strong Areas
    print(f"\n{'─' * w}")
    print("  AREAS ANALYSIS")
    print(f"{'─' * w}")

    if report["weak_areas"]:
        print(f"  ❌ Weak Areas (need work):")
        for area in report["weak_areas"]:
            print(f"     • {area}")

    if report["strong_areas"]:
        print(f"\n  ✅ Strong Areas (keep it up):")
        for area in report["strong_areas"]:
            print(f"     • {area}")

    if report["persistent_weaknesses"]:
        print(f"\n  🔴 Persistent Weaknesses (urgent):")
        for pw in report["persistent_weaknesses"]:
            print(f"     • {pw}  ← appeared weak in multiple sessions")

    # Trends
    trends = report["trends"]
    print(f"\n{'─' * w}")
    print("  SCORE TRENDS")
    print(f"{'─' * w}")
    for stype, tdata in trends.items():
        t = tdata.get("trend", "unknown")
        d = tdata.get("recent_delta", 0)
        emoji = "⬆️" if t == "improving" else ("⬇️" if t == "declining" else "➡️")
        print(f"  {stype.capitalize():<12} : {emoji} {t.capitalize()}  (last change: {d:+.2f})")

    # Improvement Suggestions
    print(f"\n{'─' * w}")
    print("  IMPROVEMENT SUGGESTIONS")
    print(f"{'─' * w}")
    for i, tip in enumerate(report["improvement_suggestions"], 1):
        print(f"  {i}. {tip}")

    # Study Plan
    print(f"\n{'─' * w}")
    print("  PERSONALIZED 4-WEEK STUDY PLAN")
    print(f"{'─' * w}")
    print(report["study_plan"])

    # Next Focus
    print(f"\n{'─' * w}")
    print("  IMMEDIATE NEXT FOCUS")
    print(f"{'─' * w}")
    for item in report["next_focus"]:
        print(f"  🎯 {item}")

    print(f"\n{'=' * w}")
    print("  END OF REPORT")
    print("=" * w)


if __name__ == "__main__":
    STUDENT = "arjun_kumar_test"

    print("Seeding test data...")
    seed_test_data(STUDENT)

    print("Generating feedback report...\n")
    agent  = FeedbackAgent()
    report = agent.generate_full_report(STUDENT)
    display_report(report)
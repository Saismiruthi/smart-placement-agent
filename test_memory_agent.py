# test_memory_agent.py

import sqlite3
import json
from datetime import datetime, timedelta
from tools.db_manager import init_database
from agents.memory_agent import MemoryAgent
from config import SQLITE_PATH


def seed_data(student_id: str):
    """Insert synthetic sessions (reuse from Phase 6 if already done)."""
    init_database()
    conn   = sqlite3.connect(str(SQLITE_PATH))
    cursor = conn.cursor()

    cursor.execute("""
        INSERT OR IGNORE INTO students (student_id, name, email)
        VALUES (?, ?, ?)
    """, (student_id, "Priya Sharma", "priya.sharma@gmail.com"))

    base = datetime.now() - timedelta(days=10)
    sessions = [
        ("coding_practice", 0.45, {
            "problems_attempted": 5, "average_score": 0.45,
            "final_difficulty": "easy", "performance_band": "Needs Practice",
            "individual_scores": [[1, 0.40], [2, 0.50]]
        }, base),
        ("coding_practice", 0.72, {
            "problems_attempted": 5, "average_score": 0.72,
            "final_difficulty": "medium", "performance_band": "Good",
            "individual_scores": [[3, 0.75], [4, 0.70]]
        }, base + timedelta(days=4)),
        ("mock_interview", 0.64, {
            "hr_score": 0.78, "technical_score": 0.55,
            "overall_score": 0.64, "passed": True,
            "target_role": "Software Development Engineer",
            "conversation": [
                {"topic": "Introduction", "score": 0.85,
                 "question": "Tell me about yourself."},
                {"topic": "OOP",         "score": 0.42,
                 "question": "Explain polymorphism."},
                {"topic": "DSA",         "score": 0.38,
                 "question": "What is time complexity?"},
                {"topic": "Behavioral",  "score": 0.72,
                 "question": "Describe a challenge."},
            ]
        }, base + timedelta(days=7)),
    ]

    for stype, score, details, ts in sessions:
        cursor.execute("""
            INSERT INTO sessions (student_id, session_type, score, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, stype, score, json.dumps(details), ts.isoformat()))

    conn.commit()
    conn.close()
    print(f"✅ Seeded data for {student_id}\n")


def test_memory_agent():
    STUDENT = "priya_sharma_test"

    seed_data(STUDENT)
    agent = MemoryAgent()

    w = 60

    # ── 1. Consolidate memories ───────────────────────────────────
    print("=" * w)
    print("  STEP 1 — CONSOLIDATE MEMORIES")
    print("=" * w)
    result = agent.consolidate_memories(STUDENT)
    print(f"  Memories written  : {result['memories_written']}")
    print(f"  Episodic          : {result['episodic_count']}")
    print(f"  Semantic          : {result['semantic_count']}")
    print(f"  Procedural        : {result['procedural_count']}")
    print(f"  Total in ChromaDB : {result['total_in_store']}")

    # ── 2. Semantic search ────────────────────────────────────────
    print(f"\n{'=' * w}")
    print("  STEP 2 — SEMANTIC MEMORY SEARCH")
    print("=" * w)

    queries = [
        "what topics is this student weak in?",
        "how has the student's coding performance changed?",
        "which interview questions did the student struggle with?"
    ]

    for query in queries:
        print(f"\n  Query: '{query}'")
        memories = agent.retrieve_context(STUDENT, query, n_results=2)
        for i, mem in enumerate(memories, 1):
            dist = mem["distance"]
            mtype = mem["metadata"].get("memory_type", "?")
            print(f"  [{i}] ({mtype}, dist={dist:.3f})")
            print(f"       {mem['text'][:100]}...")

    # ── 3. Quick topic lookups ────────────────────────────────────
    print(f"\n{'=' * w}")
    print("  STEP 3 — WEAK / STRONG TOPIC LOOKUP")
    print("=" * w)
    weak   = agent.get_weak_topics(STUDENT)
    strong = agent.get_strong_topics(STUDENT)
    print(f"  Weak topics  : {weak   if weak   else 'None stored yet'}")
    print(f"  Strong topics: {strong if strong else 'None stored yet'}")

    # ── 4. RAG personalized brief ─────────────────────────────────
    print(f"\n{'=' * w}")
    print("  STEP 4 — RAG PERSONALIZED SESSION BRIEF")
    print("=" * w)
    brief_result = agent.get_personalized_brief(STUDENT)
    print(f"\n  🧠 Memories used: {brief_result['memories_used']}")
    print(f"\n  📋 Mentor Brief:")
    print(f"  {brief_result['brief']}")
    print(f"\n  Weak topics  : {brief_result['weak_topics']}")
    print(f"  Strong topics: {brief_result['strong_topics']}")

    # ── 5. Save a manual memory ───────────────────────────────────
    print(f"\n{'=' * w}")
    print("  STEP 5 — SAVE MANUAL MEMORY")
    print("=" * w)
    ok = agent.save_memory(
        student_id  = STUDENT,
        text        = "Student requested hint 3 times on recursion problem — "
                      "needs more practice with recursive thinking.",
        memory_type = "episodic"
    )
    print(f"  Memory saved: {ok}")

    # Verify it appears in search
    results = agent.retrieve_context(
        STUDENT, "recursion hint difficulty", n_results=1
    )
    if results:
        print(f"  Retrieved: {results[0]['text'][:80]}...")

    # ── 6. Memory stats ───────────────────────────────────────────
    print(f"\n{'=' * w}")
    print("  STEP 6 — MEMORY STATS")
    print("=" * w)
    stats = agent.get_memory_stats(STUDENT)
    print(f"  Total memories : {stats['total_memories']}")
    print(f"  By type        : {stats['by_type']}")
    print(f"  Collection stats: {stats['collection_stats']}")

    print(f"\n{'=' * w}")
    print("  ✅ Memory Agent test complete!")
    print("=" * w)


if __name__ == "__main__":
    test_memory_agent()
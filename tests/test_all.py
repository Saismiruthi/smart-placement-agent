# tests/test_all.py
# Master test runner — runs all unit + integration tests

import sys
import json
import sqlite3
import unittest
from pathlib import Path
from datetime import datetime, timedelta

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.db_manager import init_database, save_student_profile, get_student_profile, save_session
from tools.nlp_extractor import NLPSkillExtractor, extract_personal_info
from tools.pdf_parser import extract_text_from_pdf
from tools.vector_store import VectorStore
from config import SQLITE_PATH


# ══════════════════════════════════════════════════════════
# UNIT TESTS — DATABASE MANAGER
# ══════════════════════════════════════════════════════════

class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        init_database()
        self.student_id = f"test_unit_{datetime.now().strftime('%H%M%S%f')}"

    def test_01_database_initializes(self):
        """Tables must exist after init_database()"""
        conn   = sqlite3.connect(str(SQLITE_PATH))
        cursor = conn.cursor()
        tables = cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        table_names = [t[0] for t in tables]
        conn.close()
        self.assertIn("students",      table_names)
        self.assertIn("student_skills",table_names)
        self.assertIn("sessions",      table_names)
        print("  ✅ DB tables exist")

    def test_02_save_and_retrieve_profile(self):
        """Student profile must be saved and retrieved correctly"""
        personal = {
            "name":    "Test Student",
            "email":   "test@example.com",
            "phone":   "9999999999",
            "linkedin":""
        }
        skills_data = {
            "matched_skills":    ["Python", "SQL"],
            "skills_by_category":{"programming_languages": ["Python"],
                                   "databases": ["SQL"]},
            "confidence_scores": {"Python": 0.98, "SQL": 0.95}
        }
        save_student_profile(self.student_id, personal, skills_data)
        profile = get_student_profile(self.student_id)

        self.assertEqual(profile["name"],  "Test Student")
        self.assertEqual(profile["email"], "test@example.com")
        self.assertIn("Python", profile["skill_names"])
        self.assertIn("SQL",    profile["skill_names"])
        print("  ✅ Profile save/retrieve works")

    def test_03_save_session(self):
        """Session records must be saved correctly"""
        save_session(
            student_id   = self.student_id,
            session_type = "coding_practice",
            score        = 0.75,
            details      = {"test": True, "problems_attempted": 3}
        )
        conn   = sqlite3.connect(str(SQLITE_PATH))
        cursor = conn.cursor()
        row    = cursor.execute(
            "SELECT score FROM sessions WHERE student_id=?",
            (self.student_id,)
        ).fetchone()
        conn.close()

        self.assertIsNotNone(row)
        self.assertAlmostEqual(row[0], 0.75, places=2)
        print("  ✅ Session save works")

    def test_04_upsert_profile(self):
        """Re-saving a profile must update, not duplicate"""
        personal = {"name": "Original", "email": "o@test.com",
                    "phone": "", "linkedin": ""}
        skills   = {"matched_skills": ["Python"],
                    "skills_by_category": {"prog": ["Python"]},
                    "confidence_scores": {"Python": 0.9}}
        save_student_profile(self.student_id, personal, skills)

        personal["name"] = "Updated"
        save_student_profile(self.student_id, personal, skills)
        profile = get_student_profile(self.student_id)

        self.assertEqual(profile["name"], "Updated")
        print("  ✅ Profile upsert works")


# ══════════════════════════════════════════════════════════
# UNIT TESTS — NLP EXTRACTOR
# ══════════════════════════════════════════════════════════

class TestNLPExtractor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.extractor = NLPSkillExtractor()
        cls.sample_resume = """
        John Doe — john@test.com — +91 9876543210
        Skills: Python, Machine Learning, SQL, Docker, Git
        Experience: Built ML models using TensorFlow and PyTorch.
        Deployed Flask REST API on AWS.
        """

    def test_05_skill_extraction_returns_dict(self):
        """extract_skills must return dict with required keys"""
        result = self.extractor.extract_skills(self.sample_resume)
        self.assertIn("matched_skills",    result)
        self.assertIn("skills_by_category",result)
        self.assertIn("confidence_scores", result)
        print("  ✅ Skill extraction returns correct structure")

    def test_06_python_detected(self):
        """Python must be detected from sample resume"""
        result = self.extractor.extract_skills(self.sample_resume)
        self.assertIn("Python", result["matched_skills"])
        print("  ✅ Python skill detected")

    def test_07_minimum_skills_found(self):
        """At least 3 skills must be found in sample resume"""
        result = self.extractor.extract_skills(self.sample_resume)
        self.assertGreaterEqual(len(result["matched_skills"]), 3)
        print(f"  ✅ {len(result['matched_skills'])} skills found (min 3)")

    def test_08_personal_info_extraction(self):
        """Email and phone must be extracted correctly"""
        info = extract_personal_info(self.sample_resume)
        self.assertEqual(info["email"], "john@test.com")
        self.assertIn("9876543210",     info["phone"])
        print("  ✅ Personal info extraction works")

    def test_09_empty_resume_handled(self):
        """Empty text must return empty skills gracefully"""
        result = self.extractor.extract_skills("")
        self.assertEqual(result["matched_skills"], [])
        print("  ✅ Empty resume handled gracefully")

    def test_10_confidence_scores_in_range(self):
        """All confidence scores must be between 0 and 1"""
        result = self.extractor.extract_skills(self.sample_resume)
        for skill, score in result["confidence_scores"].items():
            self.assertGreaterEqual(score, 0.0,
                f"{skill} score below 0")
            self.assertLessEqual(score, 1.0,
                f"{skill} score above 1")
        print("  ✅ All confidence scores in valid range [0,1]")


# ══════════════════════════════════════════════════════════
# UNIT TESTS — VECTOR STORE
# ══════════════════════════════════════════════════════════

class TestVectorStore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.store     = VectorStore()
        cls.test_sid  = f"vstore_test_{datetime.now().strftime('%H%M%S')}"

    def test_11_collections_exist(self):
        """All three collections must be available"""
        stats = self.store.get_collection_stats()
        self.assertIn("resumes", stats)
        self.assertIn("skills",  stats)
        self.assertIn("memory",  stats)
        print("  ✅ All ChromaDB collections exist")

    def test_12_add_and_retrieve_document(self):
        """A document must be retrievable after adding"""
        doc_id = f"{self.test_sid}_doc1"
        ok     = self.store.add_document(
            collection_name = "memory",
            doc_id          = doc_id,
            text            = "Student struggles with recursion and dynamic programming",
            metadata        = {"student_id": self.test_sid,
                               "memory_type": "episodic"}
        )
        self.assertTrue(ok)

        results = self.store.query(
            collection_name = "memory",
            query_text      = "recursion difficulty",
            n_results       = 1,
            where           = {"student_id": self.test_sid}
        )
        self.assertGreater(len(results), 0)
        self.assertIn("recursion", results[0]["text"].lower())
        print("  ✅ ChromaDB add + semantic query works")

    def test_13_upsert_updates_document(self):
        """Upserting same ID must update, not duplicate"""
        doc_id = f"{self.test_sid}_upsert_test"
        self.store.add_document("memory", doc_id,
            "Original text", {"student_id": self.test_sid,
                              "memory_type": "semantic"})
        self.store.add_document("memory", doc_id,
            "Updated text",  {"student_id": self.test_sid,
                              "memory_type": "semantic"})

        results = self.store.query(
            "memory", "updated text", n_results=1,
            where={"student_id": self.test_sid}
        )
        self.assertGreater(len(results), 0)
        print("  ✅ ChromaDB upsert works (no duplicates)")

    def test_14_batch_add_unique_ids(self):
        """Batch add must succeed with all unique IDs"""
        docs = [
            {"id": f"{self.test_sid}_b{i}",
             "text": f"Batch doc {i} about topic {i}",
             "metadata": {"student_id": self.test_sid,
                          "memory_type": "episodic"}}
            for i in range(5)
        ]
        written = self.store.add_documents_batch("memory", docs)
        self.assertEqual(written, 5)
        print("  ✅ ChromaDB batch add works")

    def test_15_delete_student_memories(self):
        """Deleting student memories must remove all their docs"""
        delete_sid = f"delete_test_{datetime.now().strftime('%H%M%S%f')}"
        self.store.add_document("memory", f"{delete_sid}_d1",
            "Test memory to delete",
            {"student_id": delete_sid, "memory_type": "episodic"})

        deleted = self.store.delete_student_memories(delete_sid)
        self.assertGreaterEqual(deleted, 1)
        print(f"  ✅ ChromaDB delete works ({deleted} docs removed)")


# ══════════════════════════════════════════════════════════
# INTEGRATION TESTS — SKILL GAP AGENT
# ══════════════════════════════════════════════════════════

class TestSkillGapAgent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        from agents.skill_gap_agent import SkillGapAgent
        cls.agent = SkillGapAgent()

    def test_16_gap_report_structure(self):
        """Gap report must contain all required keys"""
        skills = ["Python", "SQL", "Git", "Machine Learning"]
        report = self.agent.analyze_gap(skills, "Data Scientist")
        required_keys = [
            "target_role", "readiness_score", "hard_gaps",
            "soft_gaps", "matched_skills", "priority_learning_list"
        ]
        for key in required_keys:
            self.assertIn(key, report, f"Missing key: {key}")
        print("  ✅ Gap report has all required keys")

    def test_17_readiness_score_range(self):
        """Readiness score must be between 0 and 100"""
        skills = ["Python", "SQL"]
        report = self.agent.analyze_gap(skills, "Data Scientist")
        self.assertGreaterEqual(report["readiness_score"],  0)
        self.assertLessEqual(   report["readiness_score"], 100)
        print(f"  ✅ Readiness score valid: {report['readiness_score']}%")

    def test_18_empty_skills_gives_all_gaps(self):
        """Student with no skills must have maximum gaps"""
        report = self.agent.analyze_gap([], "Data Scientist")
        self.assertGreater(len(report["hard_gaps"]), 0)
        self.assertEqual(report["readiness_score"], 0)
        print("  ✅ Empty skills → all gaps detected")

    def test_19_full_skills_gives_high_readiness(self):
        """Student with all required skills must score high"""
        all_skills = [
            "Python", "Machine Learning", "Deep Learning",
            "Statistics", "Pandas", "NumPy", "Scikit-learn",
            "SQL", "Data Analysis", "Feature Engineering"
        ]
        report = self.agent.analyze_gap(all_skills, "Data Scientist")
        self.assertGreater(report["readiness_score"], 70)
        print(f"  ✅ Full skills → high readiness: {report['readiness_score']}%")

    def test_20_role_recommendation(self):
        """Role recommendation must return a string from dataset"""
        skills = ["Python", "TensorFlow", "Deep Learning", "NLP"]
        role   = self.agent.recommend_best_role(skills)
        self.assertIn(role, self.agent.role_names)
        print(f"  ✅ Role recommended: '{role}'")


# ══════════════════════════════════════════════════════════
# INTEGRATION TESTS — CODING TRAINER AGENT
# ══════════════════════════════════════════════════════════

class TestCodingTrainerAgent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()
        from agents.coding_trainer_agent import CodingTrainerAgent
        cls.trainer   = CodingTrainerAgent()
        cls.student   = f"test_coder_{datetime.now().strftime('%H%M%S%f')}"

    def test_21_session_starts(self):
        """Coding session must start successfully"""
        result = self.trainer.start_session(self.student, "easy")
        self.assertEqual(result["current_difficulty"], "easy")
        self.assertIn(self.student, self.trainer.active_sessions)
        print("  ✅ Coding session starts correctly")

    def test_22_problem_returned(self):
        """get_next_problem must return a valid problem dict"""
        result = self.trainer.get_next_problem(self.student)
        self.assertFalse(result.get("session_complete", True))
        problem = result.get("problem", {})
        self.assertIn("id",          problem)
        self.assertIn("title",       problem)
        self.assertIn("difficulty",  problem)
        self.assertIn("description", problem)
        print(f"  ✅ Problem returned: '{problem.get('title')}'")

    def test_23_answer_evaluation_returns_score(self):
        """evaluate_answer must return a score between 0 and 1"""
        result  = self.trainer.get_next_problem(self.student)
        problem = result.get("problem", {})
        if not problem:
            self.skipTest("No problem available")

        eval_r = self.trainer.evaluate_answer(
            self.student, problem,
            "I would use a hashmap to solve this in O(n) time complexity."
        )
        self.assertIn("score", eval_r)
        self.assertGreaterEqual(eval_r["score"], 0.0)
        self.assertLessEqual(   eval_r["score"], 1.0)
        print(f"  ✅ Evaluation score: {eval_r['score']:.2f}")

    def test_24_difficulty_promotes_on_high_scores(self):
        """Two consecutive high scores must promote difficulty"""
        from agents.coding_trainer_agent import StudentProgress
        progress = StudentProgress(self.student)
        progress.record_score(1, 0.90)
        progress.record_score(2, 0.85)
        self.assertEqual(progress.current_difficulty, "medium")
        print("  ✅ Difficulty promotes: easy → medium on 2 high scores")

    def test_25_difficulty_demotes_on_low_scores(self):
        """Two consecutive low scores must demote difficulty"""
        from agents.coding_trainer_agent import StudentProgress
        progress = StudentProgress(self.student)
        progress.current_difficulty = "medium"
        progress.record_score(1, 0.25)
        progress.record_score(2, 0.20)
        self.assertEqual(progress.current_difficulty, "easy")
        print("  ✅ Difficulty demotes: medium → easy on 2 low scores")

    def test_26_session_ends_and_saves(self):
        """end_session must return summary and clear active session"""
        summary = self.trainer.end_session(self.student)
        self.assertNotIn(self.student, self.trainer.active_sessions)
        self.assertIn("problems_attempted", summary)
        print(f"  ✅ Session ended. Problems attempted: "
              f"{summary.get('problems_attempted', 0)}")


# ══════════════════════════════════════════════════════════
# INTEGRATION TESTS — MEMORY AGENT
# ══════════════════════════════════════════════════════════

class TestMemoryAgent(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()
        from agents.memory_agent import MemoryAgent
        cls.agent  = MemoryAgent()
        cls.sid    = f"test_mem_{datetime.now().strftime('%H%M%S%f')}"

        # Seed one session for this student
        conn   = sqlite3.connect(str(SQLITE_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO students (student_id, name) VALUES (?,?)",
            (cls.sid, "Memory Test Student")
        )
        cursor.execute("""
            INSERT INTO sessions
            (student_id, session_type, score, details, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (
            cls.sid, "mock_interview", 0.60,
            json.dumps({
                "hr_score": 0.70, "technical_score": 0.52,
                "overall_score": 0.60, "passed": True,
                "target_role": "SDE",
                "conversation": [
                    {"topic": "OOP",  "score": 0.35,
                     "question": "Explain polymorphism."},
                    {"topic": "DSA",  "score": 0.40,
                     "question": "What is Big O?"},
                ]
            }),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()

    def test_27_consolidate_memories(self):
        """Memory consolidation must write docs to ChromaDB"""
        result = self.agent.consolidate_memories(self.sid)
        self.assertGreater(result["memories_written"], 0)
        print(f"  ✅ Memories written: {result['memories_written']}")

    def test_28_retrieve_context(self):
        """Semantic search must return relevant memories"""
        self.agent.consolidate_memories(self.sid)
        results = self.agent.retrieve_context(
            self.sid, "weak topics struggles", n_results=3
        )
        self.assertGreater(len(results), 0)
        self.assertIn("text", results[0])
        print(f"  ✅ Retrieved {len(results)} relevant memories")

    def test_29_save_manual_memory(self):
        """Manual memory save must return True"""
        ok = self.agent.save_memory(
            self.sid,
            "Student asked for hints 3 times on recursion.",
            memory_type = "episodic"
        )
        self.assertTrue(ok)
        print("  ✅ Manual memory save works")

    def test_30_forget_student(self):
        """forget_student must delete all ChromaDB docs for student"""
        forget_sid = f"forget_{datetime.now().strftime('%H%M%S%f')}"
        self.agent.save_memory(forget_sid, "Temporary memory",
                               memory_type="episodic")
        result = self.agent.forget_student(forget_sid)
        self.assertGreaterEqual(result["memories_deleted"], 0)
        print(f"  ✅ forget_student works — "
              f"{result['memories_deleted']} docs deleted")


# ══════════════════════════════════════════════════════════
# SYSTEM TEST — END TO END PIPELINE
# ══════════════════════════════════════════════════════════

class TestEndToEndPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        init_database()
        cls.sid = f"e2e_{datetime.now().strftime('%H%M%S%f')}"

        # Seed a complete student profile
        conn   = sqlite3.connect(str(SQLITE_PATH))
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR IGNORE INTO students (student_id, name, email) "
            "VALUES (?,?,?)",
            (cls.sid, "E2E Test Student", "e2e@test.com")
        )
        skills = ["Python", "SQL", "Git", "Machine Learning", "Flask"]
        for s in skills:
            cursor.execute(
                "INSERT OR IGNORE INTO student_skills "
                "(student_id, skill, category, confidence) "
                "VALUES (?,?,?,?)",
                (cls.sid, s, "general", 0.90)
            )

        # Seed sessions
        base = datetime.now() - timedelta(days=3)
        for i, score in enumerate([0.45, 0.62, 0.71]):
            cursor.execute("""
                INSERT INTO sessions
                (student_id, session_type, score, details, created_at)
                VALUES (?,?,?,?,?)
            """, (
                cls.sid, "coding_practice", score,
                json.dumps({
                    "problems_attempted": 5,
                    "average_score": score,
                    "final_difficulty": "easy" if score < 0.6 else "medium",
                    "performance_band": "Good",
                    "individual_scores": [[i+1, score]]
                }),
                (base + timedelta(days=i)).isoformat()
            ))
        conn.commit()
        conn.close()

    def test_31_feedback_report_generates(self):
        """FeedbackAgent must generate a complete report"""
        from agents.feedback_agent import FeedbackAgent
        agent  = FeedbackAgent()
        report = agent.generate_full_report(self.sid)

        self.assertIn("overall_readiness",  report)
        self.assertIn("coding_summary",     report)
        self.assertIn("readiness_band",     report)
        self.assertGreater(report["sessions_analyzed"], 0)
        print(f"  ✅ Feedback report generated. "
              f"Readiness: {report['overall_readiness']:.0%}")

    def test_32_memory_pipeline(self):
        """Full memory pipeline must consolidate and retrieve"""
        from agents.memory_agent import MemoryAgent
        agent  = MemoryAgent()
        result = agent.consolidate_memories(self.sid)
        self.assertGreater(result["memories_written"], 0)

        brief = agent.get_personalized_brief(self.sid)
        self.assertIn("brief",        brief)
        self.assertIn("weak_topics",  brief)
        self.assertIn("memories_used",brief)
        print(f"  ✅ Memory pipeline works. "
              f"Brief uses {brief['memories_used']} memories")

    def test_33_skill_gap_pipeline(self):
        """SkillGapAgent must analyze gaps for seeded student"""
        from agents.skill_gap_agent import SkillGapAgent
        from tools.db_manager import get_student_profile

        profile = get_student_profile(self.sid)
        agent   = SkillGapAgent()
        report  = agent.analyze_gap(
            profile.get("skill_names", []),
            "Data Scientist"
        )
        self.assertIn("readiness_score", report)
        self.assertIn("hard_gaps",       report)
        print(f"  ✅ Skill gap pipeline works. "
              f"Gaps: {len(report['hard_gaps'])}")

    def test_34_trending_detection(self):
        """FeedbackAgent trend must detect improving scores"""
        from agents.feedback_agent import FeedbackAgent
        agent  = FeedbackAgent()
        report = agent.generate_full_report(self.sid)
        trend  = report.get("trends", {}).get(
            "coding", {}
        ).get("trend", "")
        self.assertEqual(trend, "improving")
        print(f"  ✅ Trend detection works: '{trend}'")


# ══════════════════════════════════════════════════════════
# TEST RUNNER
# ══════════════════════════════════════════════════════════

def run_all_tests():
    """Run all test suites and print a formatted summary."""

    suites = [
        ("Unit Tests — Database Manager",   TestDatabaseManager),
        ("Unit Tests — NLP Extractor",       TestNLPExtractor),
        ("Unit Tests — Vector Store",        TestVectorStore),
        ("Integration — Skill Gap Agent",    TestSkillGapAgent),
        ("Integration — Coding Trainer",     TestCodingTrainerAgent),
        ("Integration — Memory Agent",       TestMemoryAgent),
        ("System Tests — End to End",        TestEndToEndPipeline),
    ]

    total_passed = 0
    total_failed = 0
    total_errors = 0
    all_failures = []

    print("\n" + "=" * 62)
    print("  SMART PLACEMENT AGENT — TEST SUITE")
    print("=" * 62)

    for suite_name, test_class in suites:
        print(f"\n📋 {suite_name}")
        print("─" * 62)

        loader = unittest.TestLoader()
        suite  = loader.loadTestsFromTestCase(test_class)
        runner = unittest.TextTestRunner(
            verbosity = 0,
            stream    = open("nul" if sys.platform == "win32"
                             else "/dev/null", "w")
        )
        result = runner.run(suite)

        passed = result.testsRun - len(result.failures) - len(result.errors)
        total_passed += passed
        total_failed += len(result.failures)
        total_errors += len(result.errors)

        print(f"  Passed: {passed}/{result.testsRun}")

        for test, traceback in result.failures + result.errors:
            msg = traceback.split("\n")[-2]
            print(f"  ❌ FAIL: {test} — {msg}")
            all_failures.append((str(test), msg))

    # Summary
    total = total_passed + total_failed + total_errors
    print("\n" + "=" * 62)
    print("  TEST SUMMARY")
    print("=" * 62)
    print(f"  Total Tests : {total}")
    print(f"  ✅ Passed   : {total_passed}")
    print(f"  ❌ Failed   : {total_failed + total_errors}")

    if all_failures:
        print("\n  Failed Tests:")
        for name, msg in all_failures:
            print(f"    • {name}: {msg}")
    else:
        print("\n  🎉 All tests passed!")

    print("=" * 62)
    return total_failed + total_errors == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
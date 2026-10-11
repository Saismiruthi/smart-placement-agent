# agents/coding_trainer_agent.py
# Adaptive coding practice agent with difficulty progression and progress tracking

import csv
import json
import random
from datetime import datetime
from pathlib import Path
from loguru import logger
from crewai import Agent
from langchain_community.llms import Ollama

from tools.db_manager import save_session, get_student_profile
from config import (
    CODING_QUESTIONS_CSV, LLM_MODEL, OLLAMA_BASE_URL,
    MAX_CODING_PROBLEMS_PER_SESSION, DIFFICULTY_LEVELS
)


# ── Difficulty transition thresholds ──────────────────────────────────────────
PROMOTE_THRESHOLD = 0.70    # Score >= 70% to promote
DEMOTE_THRESHOLD  = 0.40    # Score <  40% to demote
CONSECUTIVE_TO_CHANGE = 2   # Need 2 in a row to change level


def load_coding_questions() -> list[dict]:
    """
    Load coding questions from CSV into a list of dicts.
    """
    path = Path(CODING_QUESTIONS_CSV)
    if not path.exists():
        raise FileNotFoundError(
            f"Coding questions dataset not found: {path}\n"
            "Please run generate_datasets.py first."
        )

    questions = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append({
                "id": int(row["id"]),
                "title": row["title"],
                "topic": row["topic"],
                "difficulty": row["difficulty"].lower().strip(),
                "description": row["description"],
                "hint": row["hint"],
                "companies": [c.strip() for c in row["companies"].split("|")]
            })

    logger.info(f"Loaded {len(questions)} coding questions")
    return questions


class StudentProgress:
    """
    Tracks a student's coding practice progress in memory during a session.
    Persisted to SQLite at session end.
    """

    def __init__(self, student_id: str):
        self.student_id = student_id
        self.current_difficulty = "easy"
        self.session_scores = []            # List of (problem_id, score) tuples
        self.consecutive_high = 0          # Consecutive scores >= PROMOTE_THRESHOLD
        self.consecutive_low  = 0          # Consecutive scores <  DEMOTE_THRESHOLD
        self.attempted_ids = set()         # Avoid repeating same problem
        self.problems_this_session = 0
        self.session_start = datetime.now().isoformat()

    def record_score(self, problem_id: int, score: float):
        """
        Record the result of one problem attempt and update difficulty level.

        Args:
            problem_id: The ID of the problem attempted
            score: Float 0.0 to 1.0
        """
        self.session_scores.append((problem_id, score))
        self.attempted_ids.add(problem_id)
        self.problems_this_session += 1

        # Update consecutive counters
        if score >= PROMOTE_THRESHOLD:
            self.consecutive_high += 1
            self.consecutive_low = 0
        elif score < DEMOTE_THRESHOLD:
            self.consecutive_low += 1
            self.consecutive_high = 0
        else:
            # Mid range — reset both streaks
            self.consecutive_high = 0
            self.consecutive_low = 0

        # Check for difficulty change
        old_difficulty = self.current_difficulty
        self._update_difficulty()

        if self.current_difficulty != old_difficulty:
            logger.info(
                f"Difficulty changed: {old_difficulty} → {self.current_difficulty} "
                f"for student {self.student_id}"
            )

    def _update_difficulty(self):
        """Promote or demote difficulty based on consecutive scores."""
        idx = DIFFICULTY_LEVELS.index(self.current_difficulty)

        if self.consecutive_high >= CONSECUTIVE_TO_CHANGE:
            # Promote if not already at max
            if idx < len(DIFFICULTY_LEVELS) - 1:
                self.current_difficulty = DIFFICULTY_LEVELS[idx + 1]
                self.consecutive_high = 0

        elif self.consecutive_low >= CONSECUTIVE_TO_CHANGE:
            # Demote if not already at min
            if idx > 0:
                self.current_difficulty = DIFFICULTY_LEVELS[idx - 1]
                self.consecutive_low = 0

    def get_session_summary(self) -> dict:
        """Return a summary of this practice session."""
        if not self.session_scores:
            return {"message": "No problems attempted this session."}

        scores = [s for _, s in self.session_scores]
        avg_score = round(sum(scores) / len(scores), 3)

        return {
            "student_id": self.student_id,
            "problems_attempted": self.problems_this_session,
            "average_score": avg_score,
            "final_difficulty": self.current_difficulty,
            "session_start": self.session_start,
            "session_end": datetime.now().isoformat(),
            "individual_scores": self.session_scores,
            "performance_band": self._get_band(avg_score)
        }

    @staticmethod
    def _get_band(avg: float) -> str:
        if avg >= 0.8:
            return "Excellent"
        elif avg >= 0.6:
            return "Good"
        elif avg >= 0.4:
            return "Needs Practice"
        else:
            return "Struggling — Review Fundamentals"


class CodingTrainerAgent:
    """
    Adaptive coding trainer that:
    1. Selects problems based on student level + skill gaps
    2. Evaluates student answers using the LLM
    3. Provides hints and explanations
    4. Adjusts difficulty dynamically
    5. Persists session progress to SQLite
    """

    def __init__(self):
        logger.info("Initializing Coding Trainer Agent...")

        self.all_questions = load_coding_questions()
        self.active_sessions = {}  # student_id -> StudentProgress

        self.llm = Ollama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.2
        )

        self.agent = Agent(
            role="Coding Practice Trainer",
            goal=(
                "Guide students through adaptive coding practice, "
                "evaluate their solutions accurately, and help them "
                "improve their problem-solving skills systematically."
            ),
            backstory=(
                "You are a FAANG-level software engineer and coding instructor "
                "with deep expertise in Data Structures, Algorithms, and "
                "System Design. You have mentored 500+ students for placements."
            ),
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

        logger.info("Coding Trainer Agent ready.")

    # ── Session Management ────────────────────────────────────────────────────

    def start_session(self, student_id: str, initial_difficulty: str = "easy") -> dict:
        """
        Start a new coding practice session for a student.

        Args:
            student_id: The student's unique ID
            initial_difficulty: Starting difficulty (easy/medium/hard)

        Returns:
            Session info dict
        """
        progress = StudentProgress(student_id)
        progress.current_difficulty = initial_difficulty
        self.active_sessions[student_id] = progress

        logger.info(f"Started coding session for {student_id} at {initial_difficulty}")

        return {
            "message": f"Coding session started at '{initial_difficulty}' level.",
            "student_id": student_id,
            "current_difficulty": initial_difficulty,
            "max_problems": MAX_CODING_PROBLEMS_PER_SESSION
        }

    def end_session(self, student_id: str) -> dict:
        """
        End the session, save results, and return summary.
        """
        if student_id not in self.active_sessions:
            return {"error": "No active session found."}

        progress = self.active_sessions[student_id]
        summary = progress.get_session_summary()

        # Persist to SQLite
        save_session(
            student_id=student_id,
            session_type="coding_practice",
            score=summary.get("average_score", 0.0),
            details=summary
        )

        del self.active_sessions[student_id]
        logger.info(f"Session ended for {student_id}. Avg score: {summary.get('average_score')}")

        return summary

    # ── Problem Selection ─────────────────────────────────────────────────────

    def get_next_problem(
        self,
        student_id: str,
        skill_gaps: list[str] = None
    ) -> dict:
        """
        Select the next problem based on current difficulty and skill gaps.

        Args:
            student_id: The student's unique ID
            skill_gaps: Optional list of topic areas to prioritize

        Returns:
            A problem dict with id, title, topic, description, companies
        """
        if student_id not in self.active_sessions:
            self.start_session(student_id)

        progress = self.active_sessions[student_id]

        # Check session limit
        if progress.problems_this_session >= MAX_CODING_PROBLEMS_PER_SESSION:
            return {
                "session_complete": True,
                "message": f"Session complete! You attempted {MAX_CODING_PROBLEMS_PER_SESSION} problems.",
                "summary": progress.get_session_summary()
            }

        difficulty = progress.current_difficulty

        # Filter by difficulty first
        candidates = [
            q for q in self.all_questions
            if q["difficulty"] == difficulty
            and q["id"] not in progress.attempted_ids
        ]

        # If skill gaps are provided, prefer gap-related topics
        if skill_gaps and candidates:
            gap_topics = [g.lower() for g in skill_gaps]
            gap_matched = [
                q for q in candidates
                if any(topic in q["topic"].lower() for topic in gap_topics)
            ]
            if gap_matched:
                candidates = gap_matched
                logger.debug(f"Filtered to {len(candidates)} gap-related problems")

        # Fallback: if no candidates, relax difficulty constraint
        if not candidates:
            candidates = [
                q for q in self.all_questions
                if q["id"] not in progress.attempted_ids
            ]

        # Final fallback: allow repeats
        if not candidates:
            candidates = self.all_questions

        problem = random.choice(candidates)
        logger.info(
            f"Selected problem for {student_id}: "
            f"'{problem['title']}' [{problem['difficulty']}]"
        )

        return {
            "session_complete": False,
            "problem": problem,
            "current_difficulty": difficulty,
            "problem_number": progress.problems_this_session + 1,
            "problems_remaining": MAX_CODING_PROBLEMS_PER_SESSION - progress.problems_this_session
        }

    # ── Answer Evaluation ─────────────────────────────────────────────────────

    def evaluate_answer(
        self,
        student_id: str,
        problem: dict,
        student_answer: str
    ) -> dict:
        """
        Evaluate a student's answer using the LLM.

        Args:
            student_id: The student's ID
            problem: The problem dict (from get_next_problem)
            student_answer: The student's written/code answer

        Returns:
            Evaluation result with score, feedback, and correct approach
        """
        if not student_answer or len(student_answer.strip()) < 5:
            return {
                "score": 0.0,
                "feedback": "No answer provided.",
                "correct_approach": problem.get("hint", ""),
                "needs_hint": True
            }

        evaluation = self._llm_evaluate(problem, student_answer)

        # Record score in session progress
        if student_id in self.active_sessions:
            self.active_sessions[student_id].record_score(
                problem["id"],
                evaluation["score"]
            )

            new_difficulty = self.active_sessions[student_id].current_difficulty
            evaluation["current_difficulty"] = new_difficulty
            evaluation["difficulty_changed"] = (
                new_difficulty != problem["difficulty"]
            )

        return evaluation

    def _llm_evaluate(self, problem: dict, student_answer: str) -> dict:
        """
        Use LLM to score and give feedback on a student's answer.
        Returns structured evaluation dict.
        """
        prompt = f"""You are a coding interview evaluator. Evaluate the student's answer.

Problem: {problem['title']}
Description: {problem['description']}
Topic: {problem['topic']}
Difficulty: {problem['difficulty']}

Student's Answer:
{student_answer}

Evaluate the answer and respond in this EXACT format (nothing else):
SCORE: [0.0 to 1.0]
CORRECT: [Yes / Partially / No]
FEEDBACK: [2-3 sentences of specific feedback]
BETTER_APPROACH: [One sentence describing the optimal approach]
TIME_COMPLEXITY: [Big O notation of student's approach]
"""

        try:
            raw = self.llm.invoke(prompt)
            return self._parse_evaluation(raw, problem)
        except Exception as e:
            logger.warning(f"LLM evaluation failed: {e}")
            return self._fallback_evaluation(student_answer, problem)

    def _parse_evaluation(self, raw_output: str, problem: dict) -> dict:
        """Parse the structured LLM evaluation response."""
        result = {
            "score": 0.5,
            "correct": "Partially",
            "feedback": "",
            "better_approach": problem.get("hint", ""),
            "time_complexity": "Unknown"
        }

        lines = raw_output.strip().split("\n")
        for line in lines:
            line = line.strip()
            if line.startswith("SCORE:"):
                try:
                    val = float(line.split(":", 1)[1].strip())
                    result["score"] = max(0.0, min(1.0, val))
                except ValueError:
                    pass
            elif line.startswith("CORRECT:"):
                result["correct"] = line.split(":", 1)[1].strip()
            elif line.startswith("FEEDBACK:"):
                result["feedback"] = line.split(":", 1)[1].strip()
            elif line.startswith("BETTER_APPROACH:"):
                result["better_approach"] = line.split(":", 1)[1].strip()
            elif line.startswith("TIME_COMPLEXITY:"):
                result["time_complexity"] = line.split(":", 1)[1].strip()

        return result

    def _fallback_evaluation(self, answer: str, problem: dict) -> dict:
        """Simple keyword-based fallback if LLM fails."""
        hint_words = problem.get("hint", "").lower().split()
        answer_lower = answer.lower()

        # Count how many hint keywords appear in the answer
        matches = sum(1 for w in hint_words if w in answer_lower and len(w) > 3)
        score = min(1.0, matches / max(len(hint_words), 1))

        return {
            "score": round(score, 2),
            "correct": "Partially" if score > 0.3 else "No",
            "feedback": "Answer evaluated based on keyword matching (LLM unavailable).",
            "better_approach": problem.get("hint", ""),
            "time_complexity": "Not evaluated"
        }

    # ── Hint System ───────────────────────────────────────────────────────────

    def get_hint(self, problem: dict, hint_level: int = 1) -> str:
        """
        Generate a progressive hint for a problem.

        Args:
            problem: The problem dict
            hint_level: 1 = gentle nudge, 2 = stronger hint, 3 = full explanation

        Returns:
            Hint string
        """
        if hint_level == 1:
            return f"💡 Think about: {problem['hint']}"

        elif hint_level == 2:
            prompt = f"""Give a medium-strength hint for this coding problem without revealing the full solution.

Problem: {problem['title']}
Description: {problem['description']}
Basic hint: {problem['hint']}

Write only the hint in 2-3 sentences:"""
            try:
                return self.llm.invoke(prompt).strip()
            except Exception:
                return f"💡 Hint: {problem['hint']}"

        else:
            prompt = f"""Explain the complete optimal solution approach for this coding problem.
Include: algorithm choice, key steps, time complexity, and space complexity.

Problem: {problem['title']}
Description: {problem['description']}

Write a clear explanation in 4-5 sentences:"""
            try:
                return self.llm.invoke(prompt).strip()
            except Exception:
                return f"Approach: {problem['hint']}. Practice this pattern on similar problems."

    # ── Topic Filter ──────────────────────────────────────────────────────────

    def get_problems_by_topic(self, topic: str, difficulty: str = None) -> list[dict]:
        """Return all problems matching a topic (and optionally difficulty)."""
        topic_lower = topic.lower()
        results = [
            q for q in self.all_questions
            if topic_lower in q["topic"].lower()
        ]
        if difficulty:
            results = [q for q in results if q["difficulty"] == difficulty.lower()]
        return results
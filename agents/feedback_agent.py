# agents/feedback_agent.py
# Aggregates all session data, detects patterns, and generates improvement reports

import json
import sqlite3
from datetime import datetime
from collections import defaultdict
from loguru import logger
from crewai import Agent
from langchain_community.llms import Ollama

from tools.db_manager import init_database, get_student_profile
from config import LLM_MODEL, OLLAMA_BASE_URL, SQLITE_PATH, PASSING_SCORE_THRESHOLD


# ── Thresholds ────────────────────────────────────────────────────────────────
WEAK_SCORE_THRESHOLD     = 0.50   # Below this = weak area
STRONG_SCORE_THRESHOLD   = 0.75   # Above this = strong area
PERSISTENT_WEAK_COUNT    = 2      # Weak in this many sessions = persistent weakness
IMPROVING_DELTA          = 0.10   # Score improvement of 10% = "improving"
DECLINING_DELTA          = -0.10  # Score drop of 10% = "declining"


class FeedbackAgent:
    """
    Analyzes all student session history and produces:
    - Performance summary across all session types
    - Weak area detection (with persistence tracking)
    - Trend analysis (improving / stagnating / declining)
    - Personalized week-by-week study plan
    - Actionable improvement suggestions
    """

    def __init__(self):
        logger.info("Initializing Feedback Agent...")
        init_database()

        self.llm = Ollama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3
        )

        self.agent = Agent(
            role="Placement Preparation Mentor",
            goal=(
                "Analyze student performance across all practice sessions, "
                "identify persistent weaknesses, track improvement trends, "
                "and generate highly personalized actionable study plans."
            ),
            backstory=(
                "You are a senior placement mentor who has guided 2000+ students "
                "into top tech companies. You specialize in identifying exactly "
                "what holds a student back and creating laser-focused study plans "
                "that maximize improvement in minimum time."
            ),
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

        logger.info("Feedback Agent ready.")

    # ── Data Loading ──────────────────────────────────────────────────────────

    def _load_all_sessions(self, student_id: str) -> list[dict]:
        """
        Load all session records for a student from SQLite.
        Returns list sorted by created_at ascending (oldest first).
        """
        conn = sqlite3.connect(str(SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        rows = cursor.execute("""
            SELECT session_type, score, details, created_at
            FROM sessions
            WHERE student_id = ?
            ORDER BY created_at ASC
        """, (student_id,)).fetchall()

        conn.close()

        sessions = []
        for row in rows:
            try:
                details = json.loads(row["details"]) if row["details"] else {}
            except json.JSONDecodeError:
                details = {}

            sessions.append({
                "session_type": row["session_type"],
                "score":        float(row["score"]),
                "details":      details,
                "created_at":   row["created_at"]
            })

        logger.info(f"Loaded {len(sessions)} sessions for student {student_id}")
        return sessions

    # ── Core Analysis ─────────────────────────────────────────────────────────

    def generate_full_report(self, student_id: str) -> dict:
        """
        Master method — runs the complete feedback pipeline.

        Steps:
            1. Load all sessions from DB
            2. Compute per-type performance summaries
            3. Detect weak and strong areas
            4. Analyze score trends over time
            5. Generate LLM study plan
            6. Build final structured report

        Args:
            student_id: The student's unique identifier

        Returns:
            Complete feedback report dictionary
        """
        sessions = self._load_all_sessions(student_id)
        profile  = get_student_profile(student_id)

        if not sessions:
            return {
                "student_id": student_id,
                "message":    "No sessions found. Complete at least one coding or interview session first.",
                "sessions_analyzed": 0
            }

        # Separate by type
        coding_sessions    = [s for s in sessions if s["session_type"] == "coding_practice"]
        interview_sessions = [s for s in sessions if s["session_type"] == "mock_interview"]

        # Build summaries
        coding_summary    = self._analyze_coding_sessions(coding_sessions)
        interview_summary = self._analyze_interview_sessions(interview_sessions)

        # Detect weak/strong areas
        weak_areas, strong_areas = self._detect_weak_strong_areas(
            coding_summary, interview_summary
        )

        # Trend analysis
        trends = self._compute_trends(coding_sessions, interview_sessions)

        # Overall readiness
        overall_score = self._compute_overall_readiness(
            coding_summary, interview_summary
        )

        # Persistent weaknesses (appear weak across multiple sessions)
        persistent_weaknesses = self._find_persistent_weaknesses(sessions)

        # LLM-powered study plan
        study_plan = self._generate_study_plan(
            student_name        = profile.get("name", "Student"),
            weak_areas          = weak_areas,
            persistent_weak     = persistent_weaknesses,
            overall_score       = overall_score,
            coding_summary      = coding_summary,
            interview_summary   = interview_summary
        )

        # LLM improvement suggestions
        suggestions = self._generate_suggestions(
            weak_areas   = weak_areas,
            trends       = trends,
            overall_score= overall_score
        )

        report = {
            "student_id":            student_id,
            "student_name":          profile.get("name", "Student"),
            "report_generated_at":   datetime.now().isoformat(),
            "sessions_analyzed":     len(sessions),
            "overall_readiness":     overall_score,
            "readiness_band":        self._get_readiness_band(overall_score),
            "coding_summary":        coding_summary,
            "interview_summary":     interview_summary,
            "weak_areas":            weak_areas,
            "strong_areas":          strong_areas,
            "persistent_weaknesses": persistent_weaknesses,
            "trends":                trends,
            "study_plan":            study_plan,
            "improvement_suggestions": suggestions,
            "next_focus":            weak_areas[:3] if weak_areas else ["Keep practicing!"]
        }

        logger.info(
            f"Feedback report generated for {student_id}. "
            f"Overall readiness: {overall_score:.1%}, "
            f"Weak areas: {len(weak_areas)}, Strong areas: {len(strong_areas)}"
        )

        return report

    # ── Coding Session Analysis ───────────────────────────────────────────────

    def _analyze_coding_sessions(self, sessions: list[dict]) -> dict:
        """Analyze all coding practice sessions for patterns."""
        if not sessions:
            return {"sessions": 0, "message": "No coding sessions yet."}

        all_scores      = [s["score"] for s in sessions]
        topic_scores    = defaultdict(list)   # topic -> list of scores
        difficulty_perf = defaultdict(list)   # difficulty -> list of scores

        for session in sessions:
            details = session.get("details", {})

            # Extract individual problem scores
            for prob_id, score in details.get("individual_scores", []):
                # We don't have topic per problem in details,
                # so use session-level score as proxy
                pass

            difficulty_perf[details.get("final_difficulty", "easy")].append(
                session["score"]
            )

        avg_score = round(sum(all_scores) / len(all_scores), 3)

        # Score trajectory (first half vs second half)
        mid          = max(1, len(all_scores) // 2)
        first_half   = round(sum(all_scores[:mid]) / mid, 3)
        second_half  = round(sum(all_scores[mid:]) / max(len(all_scores) - mid, 1), 3)
        trajectory   = second_half - first_half

        # Difficulty distribution
        difficulty_avg = {
            diff: round(sum(scores) / len(scores), 3)
            for diff, scores in difficulty_perf.items()
        }

        return {
            "sessions":          len(sessions),
            "average_score":     avg_score,
            "best_score":        round(max(all_scores), 3),
            "worst_score":       round(min(all_scores), 3),
            "score_trajectory":  round(trajectory, 3),
            "difficulty_performance": difficulty_avg,
            "all_scores":        all_scores,
            "performance_band":  sessions[-1]["details"].get(
                                     "performance_band", "Unknown"
                                 ) if sessions else "Unknown"
        }

    # ── Interview Session Analysis ────────────────────────────────────────────

    def _analyze_interview_sessions(self, sessions: list[dict]) -> dict:
        """Analyze all mock interview sessions for patterns."""
        if not sessions:
            return {"sessions": 0, "message": "No interview sessions yet."}

        all_scores   = [s["score"] for s in sessions]
        hr_scores    = []
        tech_scores  = []
        topic_scores = defaultdict(list)

        for session in sessions:
            details = session.get("details", {})

            if details.get("hr_score", 0) > 0:
                hr_scores.append(details["hr_score"])
            if details.get("technical_score", 0) > 0:
                tech_scores.append(details["technical_score"])

            # Collect per-question topic scores
            for exchange in details.get("conversation", []):
                topic  = exchange.get("topic", "General")
                score  = exchange.get("score", 0)
                topic_scores[topic].append(score)

        avg_score   = round(sum(all_scores) / len(all_scores), 3)
        avg_hr      = round(sum(hr_scores) / len(hr_scores), 3)   if hr_scores   else 0.0
        avg_tech    = round(sum(tech_scores) / len(tech_scores), 3) if tech_scores else 0.0

        # Topic-level average scores
        topic_avg = {
            topic: round(sum(scores) / len(scores), 3)
            for topic, scores in topic_scores.items()
        }

        # Weak topics (below threshold)
        weak_topics = [
            topic for topic, avg in topic_avg.items()
            if avg < WEAK_SCORE_THRESHOLD
        ]

        # Pass rate
        passes    = sum(1 for s in sessions if s["score"] >= PASSING_SCORE_THRESHOLD)
        pass_rate = round(passes / len(sessions), 3)

        return {
            "sessions":          len(sessions),
            "average_score":     avg_score,
            "average_hr_score":  avg_hr,
            "average_tech_score":avg_tech,
            "pass_rate":         pass_rate,
            "passes":            passes,
            "topic_scores":      topic_avg,
            "weak_topics":       weak_topics,
            "all_scores":        all_scores
        }

    # ── Weak / Strong Area Detection ──────────────────────────────────────────

    def _detect_weak_strong_areas(
        self,
        coding_summary:    dict,
        interview_summary: dict
    ) -> tuple[list, list]:
        """
        Identify weak and strong areas by combining coding and interview data.

        Returns:
            (weak_areas, strong_areas) — lists of topic/area strings
        """
        area_scores = defaultdict(list)

        # From interview topic scores
        for topic, avg in interview_summary.get("topic_scores", {}).items():
            area_scores[topic].append(avg)

        # From coding difficulty performance
        for diff, avg in coding_summary.get("difficulty_performance", {}).items():
            area_scores[f"Coding ({diff})"].append(avg)

        # From HR vs Technical split
        hr_avg   = interview_summary.get("average_hr_score", 0)
        tech_avg = interview_summary.get("average_tech_score", 0)

        if hr_avg > 0:
            area_scores["HR Communication"].append(hr_avg)
        if tech_avg > 0:
            area_scores["Technical Knowledge"].append(tech_avg)

        weak_areas   = []
        strong_areas = []

        for area, scores in area_scores.items():
            avg = sum(scores) / len(scores)
            if avg < WEAK_SCORE_THRESHOLD:
                weak_areas.append(area)
            elif avg >= STRONG_SCORE_THRESHOLD:
                strong_areas.append(area)

        # Sort: weakest first
        weak_areas.sort(key=lambda a: sum(area_scores[a]) / len(area_scores[a]))

        return weak_areas, strong_areas

    # ── Trend Analysis ────────────────────────────────────────────────────────

    def _compute_trends(
        self,
        coding_sessions:    list[dict],
        interview_sessions: list[dict]
    ) -> dict:
        """
        Compute score trends over time for each session type.

        Returns dict with trend labels: 'improving', 'stagnating', 'declining'
        """
        def trend_label(scores: list[float]) -> str:
            if len(scores) < 2:
                return "insufficient data"
            delta = scores[-1] - scores[0]
            if delta >= IMPROVING_DELTA:
                return "improving"
            elif delta <= DECLINING_DELTA:
                return "declining"
            else:
                return "stagnating"

        def recent_delta(scores: list[float]) -> float:
            if len(scores) < 2:
                return 0.0
            return round(scores[-1] - scores[-2], 3)

        coding_scores    = [s["score"] for s in coding_sessions]
        interview_scores = [s["score"] for s in interview_sessions]

        return {
            "coding": {
                "trend":        trend_label(coding_scores),
                "recent_delta": recent_delta(coding_scores),
                "scores":       coding_scores
            },
            "interview": {
                "trend":        trend_label(interview_scores),
                "recent_delta": recent_delta(interview_scores),
                "scores":       interview_scores
            }
        }

    # ── Persistent Weakness Detection ─────────────────────────────────────────

    def _find_persistent_weaknesses(self, sessions: list[dict]) -> list[str]:
        """
        Find topics/areas that have been weak across MULTIPLE sessions.
        These need the most urgent attention.
        """
        topic_weak_count = defaultdict(int)

        for session in sessions:
            details = session.get("details", {})

            # Check interview conversation for low-scoring topics
            for exchange in details.get("conversation", []):
                if exchange.get("score", 1.0) < WEAK_SCORE_THRESHOLD:
                    topic = exchange.get("topic", "")
                    if topic:
                        topic_weak_count[topic] += 1

            # Check coding difficulty stuck at easy
            if (session["session_type"] == "coding_practice"
                    and details.get("final_difficulty") == "easy"
                    and session["score"] < WEAK_SCORE_THRESHOLD):
                topic_weak_count["Basic DSA"] += 1

        # Return topics weak in >= PERSISTENT_WEAK_COUNT sessions
        persistent = [
            topic for topic, count in topic_weak_count.items()
            if count >= PERSISTENT_WEAK_COUNT
        ]

        return persistent

    # ── Readiness Score ───────────────────────────────────────────────────────

    def _compute_overall_readiness(
        self,
        coding_summary:    dict,
        interview_summary: dict
    ) -> float:
        """
        Compute a single overall placement readiness score (0.0 to 1.0).

        Weights:
            Coding practice  : 40%
            Interview performance: 60%
        """
        coding_score    = coding_summary.get("average_score", 0.0)
        interview_score = interview_summary.get("average_score", 0.0)

        has_coding    = coding_summary.get("sessions", 0) > 0
        has_interview = interview_summary.get("sessions", 0) > 0

        if has_coding and has_interview:
            return round(0.40 * coding_score + 0.60 * interview_score, 3)
        elif has_coding:
            return round(coding_score, 3)
        elif has_interview:
            return round(interview_score, 3)
        else:
            return 0.0

    def _get_readiness_band(self, score: float) -> str:
        if score >= 0.80:
            return "🟢 Placement Ready"
        elif score >= 0.65:
            return "🟡 Nearly Ready — Minor Gaps"
        elif score >= 0.45:
            return "🟠 Needs Focused Preparation"
        else:
            return "🔴 Early Stage — Build Fundamentals First"

    # ── LLM Study Plan ────────────────────────────────────────────────────────

    def _generate_study_plan(
        self,
        student_name:      str,
        weak_areas:        list[str],
        persistent_weak:   list[str],
        overall_score:     float,
        coding_summary:    dict,
        interview_summary: dict
    ) -> str:
        """
        Generate a personalized week-by-week study plan using the LLM.
        """
        weak_str       = ", ".join(weak_areas[:6])       if weak_areas     else "None identified"
        persistent_str = ", ".join(persistent_weak[:4])  if persistent_weak else "None"
        coding_avg     = coding_summary.get("average_score", 0)
        interview_avg  = interview_summary.get("average_score", 0)

        prompt = f"""You are a placement preparation mentor creating a study plan.

Student: {student_name}
Overall Readiness: {overall_score:.0%}
Coding Average Score: {coding_avg:.0%}
Interview Average Score: {interview_avg:.0%}
Weak Areas: {weak_str}
Persistent Weaknesses (urgent): {persistent_str}

Create a focused 4-week study plan. For each week write:
- Week number and theme
- 3 specific daily tasks
- One measurable goal

Format each week exactly like this:
WEEK 1: [Theme]
- Task 1
- Task 2
- Task 3
Goal: [measurable outcome]

Write all 4 weeks. Be specific — name actual topics, platforms, and techniques:"""

        try:
            plan = self.llm.invoke(prompt)
            return plan.strip()
        except Exception as e:
            logger.warning(f"Study plan LLM failed: {e}")
            return self._fallback_study_plan(weak_areas)

    def _fallback_study_plan(self, weak_areas: list[str]) -> str:
        """Simple templated plan if LLM is unavailable."""
        plan = []
        topics = weak_areas[:4] if weak_areas else ["DSA", "OOP", "SQL", "System Design"]

        for i, topic in enumerate(topics, 1):
            plan.append(
                f"WEEK {i}: Focus on {topic}\n"
                f"- Study core concepts of {topic}\n"
                f"- Solve 5 practice problems on LeetCode/HackerRank\n"
                f"- Watch 2 tutorial videos\n"
                f"Goal: Score above 70% on a {topic} mock test"
            )

        return "\n\n".join(plan)

    # ── LLM Improvement Suggestions ───────────────────────────────────────────

    def _generate_suggestions(
        self,
        weak_areas:    list[str],
        trends:        dict,
        overall_score: float
    ) -> list[str]:
        """
        Generate 5 specific, actionable improvement suggestions.
        """
        coding_trend    = trends.get("coding", {}).get("trend", "unknown")
        interview_trend = trends.get("interview", {}).get("trend", "unknown")
        weak_str        = ", ".join(weak_areas[:5]) if weak_areas else "none"

        prompt = f"""You are a placement mentor. Give 5 specific, actionable improvement tips.

Overall readiness: {overall_score:.0%}
Weak areas: {weak_str}
Coding trend: {coding_trend}
Interview trend: {interview_trend}

Write exactly 5 numbered tips. Each tip must:
- Name a specific action (not vague advice)
- Mention a specific resource or technique
- Be achievable in 1-2 weeks

Write only the 5 numbered tips:"""

        try:
            raw  = self.llm.invoke(prompt).strip()
            tips = []
            for line in raw.split("\n"):
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith("-")):
                    tips.append(line.lstrip("0123456789.-) ").strip())
            return tips[:5] if tips else self._fallback_suggestions(weak_areas)
        except Exception:
            return self._fallback_suggestions(weak_areas)

    def _fallback_suggestions(self, weak_areas: list[str]) -> list[str]:
        base = [
            "Solve 3 LeetCode problems daily focusing on your weak topics",
            "Record yourself answering HR questions and review for clarity",
            "Read one system design article per day on 'Designing Data-Intensive Applications'",
            "Practice the STAR method for all behavioral answers",
            "Take one full mock interview session every weekend to track progress"
        ]
        if weak_areas:
            base[0] = f"Focus on {weak_areas[0]} — solve 5 problems on this topic daily"
        return base
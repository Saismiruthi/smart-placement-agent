# agents/planner_agent.py
# Central orchestrator — coordinates all agents into one adaptive session

import json
from datetime import datetime
from loguru import logger
from crewai import Agent, Task, Crew
from langchain_community.llms import Ollama

from agents.resume_agent import ResumeAnalyzerAgent
from agents.skill_gap_agent import SkillGapAgent
from agents.coding_trainer_agent import CodingTrainerAgent
from agents.interview_agent import InterviewAgent
from agents.feedback_agent import FeedbackAgent
from agents.memory_agent import MemoryAgent
from tools.db_manager import init_database, get_student_profile
from config import LLM_MODEL, OLLAMA_BASE_URL, PASSING_SCORE_THRESHOLD


# ── Session routing weights ───────────────────────────────────────────────────
# These decide how much of a session is spent on each activity
# based on the student's current weak areas

DEFAULT_ROUTE = {
    "coding":    0.50,
    "interview": 0.50
}

CODING_HEAVY_ROUTE = {
    "coding":    0.70,
    "interview": 0.30
}

INTERVIEW_HEAVY_ROUTE = {
    "coding":    0.30,
    "interview": 0.70
}


class PlannerAgent:
    """
    Central brain of the Smart Placement Preparation system.

    Coordinates:
        ResumeAnalyzerAgent   — parse + profile
        SkillGapAgent         — gap detection
        CodingTrainerAgent    — adaptive coding practice
        InterviewAgent        — mock interviews
        FeedbackAgent         — performance analysis
        MemoryAgent           — long-term personalization

    Public API:
        onboard_student()       — first-time setup from resume
        run_session()           — full adaptive practice session
        get_student_dashboard() — current status for UI
        generate_roadmap()      — full LLM learning roadmap
    """

    def __init__(self):
        logger.info("Initializing Planner Agent (Central Brain)...")
        init_database()

        # Instantiate all sub-agents
        logger.info("Loading sub-agents...")
        self.resume_agent   = ResumeAnalyzerAgent()
        self.skill_gap_agent = SkillGapAgent()
        self.coding_agent   = CodingTrainerAgent()
        self.interview_agent = InterviewAgent()
        self.feedback_agent  = FeedbackAgent()
        self.memory_agent    = MemoryAgent()

        # LLM for planning decisions
        self.llm = Ollama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3
        )

        # Define the CrewAI planner agent
        self.agent = Agent(
            role="Placement Preparation Planner",
            goal=(
                "Coordinate all preparation agents to deliver a fully "
                "personalized, adaptive placement preparation experience "
                "for each student based on their unique profile and history."
            ),
            backstory=(
                "You are the head placement coordinator at a top engineering "
                "college. You have access to every student's history, skills, "
                "and performance data. Your job is to ensure every student "
                "gets exactly the right preparation at the right time."
            ),
            llm=self.llm,
            verbose=True,
            allow_delegation=True
        )

        logger.info("Planner Agent ready. All sub-agents loaded.")

    # ── Onboarding ────────────────────────────────────────────────────────────

    def onboard_student(
        self,
        uploaded_file=None,
        pdf_path: str = None,
        target_role: str = None
    ) -> dict:
        """
        Complete first-time student onboarding.

        Steps:
            1. Parse resume (PDF)
            2. Extract skills
            3. Detect best-fit role if not specified
            4. Run skill gap analysis
            5. Initialize memory
            6. Return full onboarding report

        Args:
            uploaded_file : Streamlit UploadedFile object (for UI)
            pdf_path      : Local PDF path (for testing)
            target_role   : Optional override for target job role

        Returns:
            Complete onboarding report dict
        """
        logger.info("Starting student onboarding...")

        # ── Step 1: Resume Analysis ───────────────────────────────
        logger.info("Step 1/4: Analyzing resume...")
        if uploaded_file:
            profile = self.resume_agent.analyze_uploaded_file(uploaded_file)
        elif pdf_path:
            profile = self.resume_agent.analyze_pdf_file(pdf_path)
        else:
            raise ValueError(
                "Either uploaded_file or pdf_path must be provided."
            )

        student_id = profile["student_id"]
        skills     = profile["skills"]

        # ── Step 2: Role Detection ────────────────────────────────
        logger.info("Step 2/4: Detecting best-fit role...")
        if not target_role:
            target_role = self.skill_gap_agent.recommend_best_role(skills)

        # ── Step 3: Skill Gap Analysis ────────────────────────────
        logger.info("Step 3/4: Running skill gap analysis...")
        gap_report = self.skill_gap_agent.analyze_gap(skills, target_role)

        # ── Step 4: Initialize Memory ─────────────────────────────
        logger.info("Step 4/4: Initializing memory store...")
        # Save initial memory about the student's profile
        self.memory_agent.save_memory(
            student_id  = student_id,
            text        = (
                f"Student {profile['personal_info'].get('name', 'Unknown')} "
                f"onboarded with {profile['total_skills_found']} skills detected. "
                f"Target role: {target_role}. "
                f"Readiness score: {gap_report['readiness_score']}%. "
                f"Top skill gaps: {', '.join(gap_report['hard_gaps'][:5])}."
            ),
            memory_type = "semantic",
            metadata    = {
                "category":    "onboarding",
                "target_role": target_role
            }
        )

        # ── Build onboarding report ───────────────────────────────
        route = self._decide_route(gap_report, coding_score=0, interview_score=0)

        onboarding_report = {
            "student_id":          student_id,
            "personal_info":       profile["personal_info"],
            "total_skills_found":  profile["total_skills_found"],
            "skills_by_category":  profile["skills_by_category"],
            "target_role":         target_role,
            "readiness_score":     gap_report["readiness_score"],
            "hard_gaps":           gap_report["hard_gaps"],
            "soft_gaps":           [g["required"] for g in gap_report["soft_gaps"]],
            "learning_plan":       gap_report["learning_plan"],
            "recommended_route":   route,
            "summary":             gap_report["summary"],
            "next_steps":          self._plan_next_steps(gap_report, None),
            "onboarded_at":        datetime.now().isoformat()
        }

        logger.info(
            f"Onboarding complete for {student_id}. "
            f"Role: {target_role}, Readiness: {gap_report['readiness_score']}%"
        )
        return onboarding_report

    # ── Session Runner ────────────────────────────────────────────────────────

    def run_session(
        self,
        student_id:   str,
        session_type: str = "auto",
        target_role:  str = None
    ) -> dict:
        """
        Run one complete adaptive practice session.

        Args:
            student_id   : The student's unique ID
            session_type : 'coding', 'interview', 'full', or 'auto'
                           'auto' = Planner decides based on memory
            target_role  : Job role for interview session

        Returns:
            Full session results dict
        """
        logger.info(
            f"Starting session for {student_id}. "
            f"Type: {session_type}"
        )

        # ── Step 1: Retrieve memory context ──────────────────────
        logger.info("Retrieving student memory...")
        brief = self.memory_agent.get_personalized_brief(student_id)
        weak_topics = brief.get("weak_topics", [])

        # ── Step 2: Decide session type if auto ───────────────────
        if session_type == "auto":
            session_type = self._auto_route(brief)
            logger.info(f"Auto-routed to session type: {session_type}")

        # ── Step 3: Get student profile ───────────────────────────
        profile = get_student_profile(student_id)
        if not target_role:
            # Try to get from memory
            role_mems = self.memory_agent.retrieve_context(
                student_id = student_id,
                query      = "target job role",
                n_results  = 1,
                memory_type= "semantic"
            )
            if role_mems:
                meta = role_mems[0].get("metadata", {})
                target_role = meta.get("target_role", "Software Development Engineer")
            else:
                target_role = "Software Development Engineer"

        session_result = {
            "student_id":    student_id,
            "session_type":  session_type,
            "target_role":   target_role,
            "weak_topics":   weak_topics,
            "mentor_brief":  brief.get("brief", ""),
            "started_at":    datetime.now().isoformat()
        }

        # ── Step 4: Run the appropriate session ───────────────────
        if session_type == "coding":
            session_result["coding_result"] = self._run_coding_session(
                student_id, weak_topics
            )

        elif session_type == "interview":
            session_result["interview_result"] = self._run_interview_session(
                student_id, target_role, weak_topics
            )

        elif session_type == "full":
            session_result["coding_result"]   = self._run_coding_session(
                student_id, weak_topics
            )
            session_result["interview_result"] = self._run_interview_session(
                student_id, target_role, weak_topics
            )

        # ── Step 5: Run feedback analysis ─────────────────────────
        logger.info("Running feedback analysis...")
        session_result["feedback_report"] = (
            self.feedback_agent.generate_full_report(student_id)
        )

        # ── Step 6: Consolidate memories ──────────────────────────
        logger.info("Consolidating memories...")
        mem_result = self.memory_agent.consolidate_memories(student_id)
        session_result["memories_written"] = mem_result.get(
            "memories_written", 0
        )

        # ── Step 7: Plan next session ─────────────────────────────
        feedback   = session_result["feedback_report"]
        gap_report = None
        if profile.get("skill_names"):
            try:
                gap_report = self.skill_gap_agent.analyze_gap(
                    profile["skill_names"], target_role
                )
            except Exception:
                pass

        session_result["next_session_plan"] = self._plan_next_steps(
            gap_report, feedback
        )
        session_result["finished_at"] = datetime.now().isoformat()

        logger.info(
            f"Session complete for {student_id}. "
            f"Type: {session_type}"
        )
        return session_result

    # ── Dashboard ─────────────────────────────────────────────────────────────

    def get_student_dashboard(self, student_id: str) -> dict:
        """
        Return a complete student status snapshot for the UI dashboard.
        Combines: profile, memory brief, feedback report, memory stats.

        Args:
            student_id: The student's unique ID

        Returns:
            Dashboard data dict ready for Streamlit rendering
        """
        profile = get_student_profile(student_id)

        if not profile:
            return {
                "student_id": student_id,
                "status":     "not_found",
                "message":    "Student not found. Please upload a resume first."
            }

        # Refresh memories
        self.memory_agent.consolidate_memories(student_id)

        # Get brief and feedback
        brief          = self.memory_agent.get_personalized_brief(student_id)
        feedback       = self.feedback_agent.generate_full_report(student_id)
        memory_stats   = self.memory_agent.get_memory_stats(student_id)

        return {
            "student_id":       student_id,
            "status":           "active",
            "profile":          profile,
            "mentor_brief":     brief.get("brief", ""),
            "weak_topics":      brief.get("weak_topics", []),
            "strong_topics":    brief.get("strong_topics", []),
            "overall_readiness":feedback.get("overall_readiness", 0),
            "readiness_band":   feedback.get("readiness_band", ""),
            "sessions_done":    feedback.get("sessions_analyzed", 0),
            "coding_summary":   feedback.get("coding_summary", {}),
            "interview_summary":feedback.get("interview_summary", {}),
            "study_plan":       feedback.get("study_plan", ""),
            "suggestions":      feedback.get("improvement_suggestions", []),
            "next_focus":       feedback.get("next_focus", []),
            "memory_stats":     memory_stats,
            "last_updated":     datetime.now().isoformat()
        }

    # ── Roadmap Generator ─────────────────────────────────────────────────────

    def generate_roadmap(
        self,
        student_id:  str,
        target_role: str,
        weeks:       int = 8
    ) -> str:
        """
        Generate a full multi-week placement preparation roadmap
        personalized using memory context.

        Args:
            student_id  : The student's ID
            target_role : The job role to prepare for
            weeks       : Number of weeks for the roadmap

        Returns:
            Formatted roadmap string
        """
        profile = get_student_profile(student_id)
        brief   = self.memory_agent.get_personalized_brief(student_id)

        weak_topics  = brief.get("weak_topics", [])
        strong_topics= brief.get("strong_topics", [])
        skills       = profile.get("skill_names", [])

        try:
            gap_report = self.skill_gap_agent.analyze_gap(skills, target_role)
            hard_gaps  = gap_report.get("hard_gaps", [])
            readiness  = gap_report.get("readiness_score", 0)
        except Exception:
            hard_gaps = weak_topics
            readiness = 0

        prompt = f"""You are a senior placement mentor creating a {weeks}-week roadmap.

Student profile:
- Target role: {target_role}
- Current readiness: {readiness}%
- Weak areas: {', '.join(weak_topics[:5]) if weak_topics else 'Not yet assessed'}
- Strong areas: {', '.join(strong_topics[:3]) if strong_topics else 'Not yet assessed'}
- Critical skill gaps: {', '.join(hard_gaps[:6]) if hard_gaps else 'None identified'}

Create a detailed {weeks}-week placement preparation roadmap.
Structure each week as:
WEEK [N]: [Theme]
Focus: [Main topic]
Coding: [2 specific coding tasks]
Interview Prep: [1 specific interview task]
Goal: [Measurable outcome]

Be specific — name actual topics, LeetCode tags, and techniques.
Write all {weeks} weeks:"""

        try:
            roadmap = self.llm.invoke(prompt)
            return roadmap.strip()
        except Exception as e:
            logger.warning(f"Roadmap generation failed: {e}")
            return self._fallback_roadmap(target_role, hard_gaps, weeks)

    # ── Internal Helpers ──────────────────────────────────────────────────────

    def _run_coding_session(
        self,
        student_id:  str,
        weak_topics: list[str]
    ) -> dict:
        """Run one full coding practice session."""
        logger.info(f"Running coding session for {student_id}...")

        self.coding_agent.start_session(student_id, initial_difficulty="easy")
        results = []

        for _ in range(3):   # 3 problems per automated session
            problem_result = self.coding_agent.get_next_problem(
                student_id, skill_gaps=weak_topics
            )
            if problem_result.get("session_complete"):
                break

            problem = problem_result.get("problem", {})
            if not problem:
                break

            # In automated mode, use a structured placeholder answer
            # In UI mode, this is replaced by actual student input
            placeholder_answer = (
                f"I would approach {problem.get('title', 'this problem')} "
                f"by analyzing the constraints first. "
                f"Using {problem.get('hint', 'an optimal algorithm')}, "
                f"the time complexity would be O(n)."
            )

            evaluation = self.coding_agent.evaluate_answer(
                student_id, problem, placeholder_answer
            )
            results.append({
                "problem": problem.get("title"),
                "score":   evaluation.get("score", 0),
                "feedback":evaluation.get("feedback", "")
            })

        summary = self.coding_agent.end_session(student_id)
        summary["individual_results"] = results
        return summary

    def _run_interview_session(
        self,
        student_id:  str,
        target_role: str,
        weak_topics: list[str]
    ) -> dict:
        """Run one full mock interview session."""
        logger.info(f"Running interview session for {student_id}...")

        self.interview_agent.start_interview(
            student_id  = student_id,
            target_role = target_role,
            mode        = "technical"   # Automated: technical only
        )

        results = []

        for _ in range(3):   # 3 questions per automated session
            q_result = self.interview_agent.get_next_question(
                student_id = student_id,
                skill_gaps = weak_topics
            )

            if (q_result.get("interview_complete")
                    or q_result.get("round_transition")):
                break

            question = q_result.get("question", {})
            if not question:
                break

            # Placeholder answer for automated pipeline
            keywords = question.get("answer_keywords", ["concept"])
            placeholder = (
                f"The concept of {question.get('topic', 'this topic')} involves "
                f"{', '.join(keywords[:3])}. "
                f"For example, in software development this is applied when "
                f"building scalable systems."
            )

            evaluation = self.interview_agent.submit_answer(
                student_id     = student_id,
                question       = question,
                student_answer = placeholder
            )
            results.append({
                "question": question.get("question", "")[:60],
                "topic":    question.get("topic", ""),
                "score":    evaluation.get("final_score", 0),
                "feedback": evaluation.get("feedback", "")
            })

        final = self.interview_agent.finish_interview(student_id)
        final["individual_results"] = results
        return final

    def _auto_route(self, brief: dict) -> str:
        """
        Decide session type automatically based on memory context.

        Logic:
            - If weak_topics contains mainly technical topics → coding
            - If HR scores are lower than tech → interview
            - Default → full (both)
        """
        weak  = brief.get("weak_topics", [])
        raw   = " ".join(brief.get("raw_memories", [])).lower()

        hr_weak   = any(w in raw for w in ["hr", "communication", "behavioral"])
        tech_weak = any(w in raw for w in ["dsa", "oop", "algorithm", "coding"])

        if hr_weak and not tech_weak:
            return "interview"
        elif tech_weak and not hr_weak:
            return "coding"
        else:
            return "full"

    def _decide_route(
        self,
        gap_report:      dict,
        coding_score:    float,
        interview_score: float
    ) -> dict:
        """
        Choose a routing weight dict based on current performance.
        """
        readiness = gap_report.get("readiness_score", 50) / 100

        if coding_score < 0.50 and interview_score >= 0.60:
            return CODING_HEAVY_ROUTE
        elif interview_score < 0.50 and coding_score >= 0.60:
            return INTERVIEW_HEAVY_ROUTE
        else:
            return DEFAULT_ROUTE

    def _plan_next_steps(
        self,
        gap_report: dict,
        feedback:   dict
    ) -> list[str]:
        """
        Generate 3 concrete next steps for the student.
        Combines gap report + feedback report insights.
        """
        steps = []

        if gap_report:
            hard_gaps = gap_report.get("hard_gaps", [])
            if hard_gaps:
                steps.append(
                    f"Priority: Learn {hard_gaps[0]} — "
                    f"it is your most critical missing skill for this role."
                )
            if len(hard_gaps) > 1:
                steps.append(
                    f"Study {hard_gaps[1]} this week using "
                    f"online tutorials and hands-on practice."
                )

        if feedback:
            weak = feedback.get("weak_areas", [])
            if weak:
                steps.append(
                    f"Focus interview prep on {weak[0]} — "
                    f"your lowest scoring topic across sessions."
                )

            trend = feedback.get("trends", {})
            coding_trend = trend.get("coding", {}).get("trend", "")
            if coding_trend == "declining":
                steps.append(
                    "⚠️  Coding scores are declining — "
                    "revisit fundamentals before attempting harder problems."
                )
            elif coding_trend == "improving":
                steps.append(
                    "✅ Coding is improving — "
                    "try increasing difficulty to medium/hard problems."
                )

        if not steps:
            steps = [
                "Upload your resume to get a personalized skill gap analysis.",
                "Complete your first coding practice session.",
                "Take a mock HR interview to assess your communication skills."
            ]

        return steps[:4]   # Return max 4 next steps

    def _fallback_roadmap(
        self,
        role:      str,
        gaps:      list[str],
        weeks:     int
    ) -> str:
        """Simple templated roadmap if LLM fails."""
        lines  = [f"  {weeks}-Week Roadmap for {role}\n"]
        phases = [
            "Fundamentals & Gap Filling",
            "Core DSA Practice",
            "System Design Basics",
            "Mock Interviews & Polish"
        ]
        topics = gaps[:4] if gaps else ["DSA", "OOP", "SQL", "System Design"]

        for i in range(1, weeks + 1):
            phase_idx = min((i - 1) // 2, len(phases) - 1)
            topic     = topics[min(i - 1, len(topics) - 1)]
            lines.append(
                f"WEEK {i}: {phases[phase_idx]}\n"
                f"Focus: {topic}\n"
                f"Coding: Solve 5 {topic} problems on LeetCode\n"
                f"Interview Prep: Practice 3 {topic} questions aloud\n"
                f"Goal: Score above 70% on {topic} assessment\n"
            )

        return "\n".join(lines)
# agents/interview_agent.py
# Simulates full HR + Technical mock interview with multi-criteria evaluation

import csv
import json
import random
from datetime import datetime
from pathlib import Path
from loguru import logger
from crewai import Agent
from langchain_community.llms import Ollama

from tools.db_manager import save_session
from config import (
    INTERVIEW_QUESTIONS_CSV, LLM_MODEL,
    OLLAMA_BASE_URL, PASSING_SCORE_THRESHOLD
)


# ── Evaluation weights per interview type ─────────────────────────────────────
HR_WEIGHTS = {
    "communication": 0.30,
    "relevance":     0.25,
    "structure":     0.25,   # STAR method adherence
    "confidence":    0.20
}

TECHNICAL_WEIGHTS = {
    "correctness":   0.40,
    "depth":         0.30,
    "clarity":       0.20,
    "examples":      0.10
}


def load_interview_questions() -> list[dict]:
    """Load interview questions from CSV dataset."""
    path = Path(INTERVIEW_QUESTIONS_CSV)
    if not path.exists():
        raise FileNotFoundError(
            f"Interview questions not found: {path}\n"
            "Run generate_datasets.py first."
        )

    questions = []
    with open(path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            questions.append({
                "id": int(row["id"]),
                "question": row["question"],
                "type": row["type"],           # HR or Technical
                "topic": row["topic"],
                "difficulty": row["difficulty"],
                "answer_keywords": [
                    k.strip()
                    for k in row["sample_answer_keywords"].split("|")
                ]
            })

    logger.info(f"Loaded {len(questions)} interview questions")
    return questions


class InterviewSession:
    """
    Holds the state of one complete mock interview session.
    Tracks rounds, questions asked, answers given, and scores.
    """

    def __init__(self, student_id: str, target_role: str, mode: str = "full"):
        """
        Args:
            student_id  : Unique student identifier
            target_role : Job role being interviewed for
            mode        : 'full' (HR + Technical), 'hr', or 'technical'
        """
        self.student_id   = student_id
        self.target_role  = target_role
        self.mode         = mode

        # Conversation history — list of {question, answer, score, feedback}
        self.conversation_history = []

        # Separate tracking per round
        self.hr_scores         = []
        self.technical_scores  = []

        # Current round state
        self.current_round = "HR" if mode in ("full", "hr") else "Technical"
        self.hr_questions_done  = 0
        self.tech_questions_done = 0

        # Config: how many questions per round
        self.hr_question_limit   = 5
        self.tech_question_limit = 5

        self.started_at  = datetime.now().isoformat()
        self.finished_at = None
        self.is_complete = False

    def add_exchange(
        self,
        question: dict,
        student_answer: str,
        evaluation: dict
    ):
        """Record one Q&A exchange to the conversation history."""
        self.conversation_history.append({
            "question_id":  question["id"],
            "question":     question["question"],
            "type":         question["type"],
            "topic":        question["topic"],
            "answer":       student_answer,
            "score":        evaluation["final_score"],
            "feedback":     evaluation["feedback"],
            "dimension_scores": evaluation.get("dimension_scores", {})
        })

        if question["type"] == "HR":
            self.hr_scores.append(evaluation["final_score"])
            self.hr_questions_done += 1
        else:
            self.technical_scores.append(evaluation["final_score"])
            self.tech_questions_done += 1

    def should_advance_round(self) -> bool:
        """Check if HR round is done and we should move to Technical."""
        if self.mode == "full":
            return (
                self.current_round == "HR"
                and self.hr_questions_done >= self.hr_question_limit
            )
        return False

    def advance_to_technical(self):
        """Transition from HR to Technical round."""
        self.current_round = "Technical"
        logger.info(f"Interview advanced to Technical round for {self.student_id}")

    def is_interview_complete(self) -> bool:
        """Return True when all rounds are finished."""
        if self.mode == "hr":
            return self.hr_questions_done >= self.hr_question_limit
        elif self.mode == "technical":
            return self.tech_questions_done >= self.tech_question_limit
        else:  # full
            return (
                self.hr_questions_done  >= self.hr_question_limit
                and self.tech_questions_done >= self.tech_question_limit
            )

    def compute_final_result(self) -> dict:
        """Calculate overall interview result with pass/fail decision."""
        hr_avg   = (
            round(sum(self.hr_scores) / len(self.hr_scores), 3)
            if self.hr_scores else 0.0
        )
        tech_avg = (
            round(sum(self.technical_scores) / len(self.technical_scores), 3)
            if self.technical_scores else 0.0
        )

        # Overall: HR 40%, Technical 60%
        if self.hr_scores and self.technical_scores:
            overall = round(0.40 * hr_avg + 0.60 * tech_avg, 3)
        elif self.hr_scores:
            overall = hr_avg
        else:
            overall = tech_avg

        passed = overall >= PASSING_SCORE_THRESHOLD

        self.finished_at = datetime.now().isoformat()
        self.is_complete = True

        return {
            "student_id":       self.student_id,
            "target_role":      self.target_role,
            "hr_score":         hr_avg,
            "technical_score":  tech_avg,
            "overall_score":    overall,
            "passed":           passed,
            "result":           "SELECTED ✅" if passed else "NEEDS MORE PREP ❌",
            "hr_questions":     self.hr_questions_done,
            "tech_questions":   self.tech_questions_done,
            "started_at":       self.started_at,
            "finished_at":      self.finished_at,
            "conversation":     self.conversation_history
        }


class InterviewAgent:
    """
    Full mock interview simulator.

    Flow:
        start_interview()
            ↓
        get_next_question()   ← returns one question at a time
            ↓
        submit_answer()       ← evaluates + records + checks round transition
            ↓
        (repeat until complete)
            ↓
        finish_interview()    ← final report + save to DB
    """

    def __init__(self):
        logger.info("Initializing Interview Agent...")

        self.all_questions   = load_interview_questions()
        self.active_sessions = {}   # student_id -> InterviewSession

        self.llm = Ollama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.4     # Slightly higher for varied question generation
        )

        self.agent = Agent(
            role="Senior Technical Interviewer",
            goal=(
                "Conduct realistic mock interviews that accurately simulate "
                "placement interviews at top tech companies, provide "
                "actionable feedback, and fairly assess candidate readiness."
            ),
            backstory=(
                "You are a principal engineer who has conducted 1000+ technical "
                "interviews at companies like Google, Amazon, and Microsoft. "
                "You know exactly what interviewers look for and how to give "
                "constructive, honest feedback that helps candidates improve."
            ),
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

        logger.info("Interview Agent ready.")

    # ── Session Lifecycle ─────────────────────────────────────────────────────

    def start_interview(
        self,
        student_id:  str,
        target_role: str,
        mode:        str = "full"
    ) -> dict:
        """
        Start a new mock interview session.

        Args:
            student_id  : Unique student identifier
            target_role : e.g. 'Data Scientist', 'Software Development Engineer'
            mode        : 'full', 'hr', or 'technical'

        Returns:
            Welcome message and session info
        """
        session = InterviewSession(student_id, target_role, mode)
        self.active_sessions[student_id] = session

        opening = self._generate_opening(target_role, mode)

        logger.info(
            f"Interview started — student: {student_id}, "
            f"role: {target_role}, mode: {mode}"
        )

        return {
            "status":       "started",
            "student_id":   student_id,
            "target_role":  target_role,
            "mode":         mode,
            "current_round": session.current_round,
            "opening_message": opening,
            "hr_questions":   session.hr_question_limit   if mode != "technical" else 0,
            "tech_questions": session.tech_question_limit if mode != "hr"        else 0,
        }

    def finish_interview(self, student_id: str) -> dict:
        """
        Close the interview, compute the final result, save to DB.

        Returns:
            Complete interview result report
        """
        if student_id not in self.active_sessions:
            return {"error": "No active interview session found."}

        session  = self.active_sessions[student_id]
        result   = session.compute_final_result()

        # Persist to SQLite
        save_session(
            student_id   = student_id,
            session_type = "mock_interview",
            score        = result["overall_score"],
            details      = result
        )

        # Generate closing feedback using LLM
        result["closing_feedback"] = self._generate_closing_feedback(result)

        del self.active_sessions[student_id]
        logger.info(
            f"Interview finished for {student_id}. "
            f"Overall: {result['overall_score']} — {result['result']}"
        )

        return result

    # ── Question Flow ─────────────────────────────────────────────────────────

    def get_next_question(
        self,
        student_id:  str,
        skill_gaps:  list[str] = None,
        asked_ids:   set       = None
    ) -> dict:
        """
        Return the next interview question for the student.

        Args:
            student_id : Student identifier
            skill_gaps : Optional list of weak topics to prioritize
            asked_ids  : Set of already-asked question IDs (to avoid repeats)

        Returns:
            Question dict or completion signal
        """
        if student_id not in self.active_sessions:
            return {"error": "No active session. Call start_interview() first."}

        session = self.active_sessions[student_id]

        # Check round transition
        if session.should_advance_round():
            session.advance_to_technical()
            return {
                "round_transition": True,
                "message": (
                    "✅ HR Round complete! Moving to Technical Round now.\n"
                    "Take a breath — the technical questions begin next."
                ),
                "current_round": "Technical"
            }

        # Check interview completion
        if session.is_interview_complete():
            return {
                "interview_complete": True,
                "message": "All rounds complete. Call finish_interview() for your results."
            }

        # Build exclusion set
        excluded = asked_ids or set()
        excluded.update(
            e["question_id"] for e in session.conversation_history
        )

        # Select question based on current round
        question = self._select_question(
            round_type = session.current_round,
            skill_gaps = skill_gaps,
            excluded   = excluded
        )

        question_number = len(session.conversation_history) + 1

        return {
            "round_transition":    False,
            "interview_complete":  False,
            "current_round":       session.current_round,
            "question_number":     question_number,
            "question":            question,
            "interviewer_intro":   self._get_interviewer_intro(
                                       question, session.current_round
                                   )
        }

    def submit_answer(
        self,
        student_id:     str,
        question:       dict,
        student_answer: str
    ) -> dict:
        """
        Submit a student's answer, evaluate it, and record it.

        Args:
            student_id     : Student identifier
            question       : The question dict from get_next_question()
            student_answer : The student's answer text

        Returns:
            Evaluation result with scores, feedback, and model answer
        """
        if student_id not in self.active_sessions:
            return {"error": "No active session found."}

        if not student_answer or len(student_answer.strip()) < 10:
            return {
                "final_score": 0.0,
                "feedback": (
                    "Answer too short. Please provide a complete response. "
                    "For HR questions use the STAR method. "
                    "For technical questions explain your reasoning step by step."
                ),
                "tip": "Aim for at least 3-4 sentences per answer."
            }

        # Evaluate
        evaluation = self._evaluate_answer(question, student_answer)

        # Record in session
        session = self.active_sessions[student_id]
        session.add_exchange(question, student_answer, evaluation)

        # Check if we should auto-finish
        if session.is_interview_complete():
            evaluation["interview_complete"] = True
            evaluation["message"] = (
                "Interview complete! Call finish_interview() to see your full results."
            )

        return evaluation

    # ── Question Selection ────────────────────────────────────────────────────

    def _select_question(
        self,
        round_type: str,
        skill_gaps: list[str] = None,
        excluded:   set       = None
    ) -> dict:
        """
        Intelligently select a question for the current round.
        Prioritizes gap-related topics for technical round.
        """
        excluded = excluded or set()

        # Filter by round type
        pool = [
            q for q in self.all_questions
            if q["type"] == round_type
            and q["id"] not in excluded
        ]

        # For technical round, prefer questions matching skill gaps
        if round_type == "Technical" and skill_gaps:
            gap_lower = [g.lower() for g in skill_gaps]
            gap_pool  = [
                q for q in pool
                if any(gap in q["topic"].lower() for gap in gap_lower)
            ]
            if gap_pool:
                pool = gap_pool

        # Fallback: use any available question
        if not pool:
            pool = [
                q for q in self.all_questions
                if q["type"] == round_type
            ]

        if not pool:
            # Absolute fallback
            return self.all_questions[0]

        return random.choice(pool)

    # ── Evaluation Engine ─────────────────────────────────────────────────────

    def _evaluate_answer(self, question: dict, student_answer: str) -> dict:
        """
        Multi-criteria LLM evaluation.
        HR and Technical rounds use different rubrics.
        """
        if question["type"] == "HR":
            return self._evaluate_hr_answer(question, student_answer)
        else:
            return self._evaluate_technical_answer(question, student_answer)

    def _evaluate_hr_answer(self, question: dict, answer: str) -> dict:
        """
        Evaluate HR answer on: communication, relevance, structure, confidence.
        """
        keywords_str = ", ".join(question["answer_keywords"])

        prompt = f"""You are a senior HR interviewer. Evaluate this answer strictly.

Question: {question['question']}
Topic: {question['topic']}
Expected keywords/themes: {keywords_str}

Student's Answer:
{answer}

Rate each dimension from 0.0 to 1.0 and respond in EXACTLY this format:
COMMUNICATION: [0.0-1.0]
RELEVANCE: [0.0-1.0]
STRUCTURE: [0.0-1.0]
CONFIDENCE: [0.0-1.0]
FEEDBACK: [2-3 specific sentences of feedback]
MODEL_ANSWER: [One sentence describing what an ideal answer looks like]
STAR_USED: [Yes/No/Partial]
"""

        try:
            raw = self.llm.invoke(prompt)
            return self._parse_hr_evaluation(raw, question)
        except Exception as e:
            logger.warning(f"HR evaluation LLM failed: {e}")
            return self._fallback_hr_eval(answer, question)

    def _evaluate_technical_answer(self, question: dict, answer: str) -> dict:
        """
        Evaluate Technical answer on: correctness, depth, clarity, examples.
        """
        keywords_str = ", ".join(question["answer_keywords"])

        prompt = f"""You are a senior technical interviewer. Evaluate this answer strictly.

Question: {question['question']}
Topic: {question['topic']}
Difficulty: {question['difficulty']}
Expected concepts: {keywords_str}

Student's Answer:
{answer}

Rate each dimension from 0.0 to 1.0 and respond in EXACTLY this format:
CORRECTNESS: [0.0-1.0]
DEPTH: [0.0-1.0]
CLARITY: [0.0-1.0]
EXAMPLES: [0.0-1.0]
FEEDBACK: [2-3 specific sentences of feedback]
MODEL_ANSWER: [The ideal 2-sentence answer to this question]
MISSING_CONCEPTS: [Key concepts the student missed, comma separated]
"""

        try:
            raw = self.llm.invoke(prompt)
            return self._parse_technical_evaluation(raw, question)
        except Exception as e:
            logger.warning(f"Technical evaluation LLM failed: {e}")
            return self._fallback_tech_eval(answer, question)

    def _parse_hr_evaluation(self, raw: str, question: dict) -> dict:
        """Parse structured HR evaluation from LLM output."""
        dims = {
            "communication": 0.5,
            "relevance":     0.5,
            "structure":     0.5,
            "confidence":    0.5
        }
        feedback      = "Good attempt. Focus on structure and specific examples."
        model_answer  = "Use the STAR method with a concrete professional example."
        star_used     = "No"

        for line in raw.strip().split("\n"):
            line = line.strip()
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()

            if key in dims:
                try:
                    dims[key] = max(0.0, min(1.0, float(val.split()[0])))
                except ValueError:
                    pass
            elif key == "feedback":
                feedback = val
            elif key == "model_answer":
                model_answer = val
            elif key == "star_used":
                star_used = val

        # Weighted final score
        final_score = round(
            sum(HR_WEIGHTS[k] * dims[k] for k in HR_WEIGHTS), 3
        )

        return {
            "final_score":      final_score,
            "dimension_scores": dims,
            "feedback":         feedback,
            "model_answer":     model_answer,
            "star_used":        star_used,
            "tip":              self._hr_tip(dims),
            "round":            "HR"
        }

    def _parse_technical_evaluation(self, raw: str, question: dict) -> dict:
        """Parse structured Technical evaluation from LLM output."""
        dims = {
            "correctness": 0.5,
            "depth":       0.5,
            "clarity":     0.5,
            "examples":    0.5
        }
        feedback         = "Review the core concepts for this topic."
        model_answer     = question["answer_keywords"][0] if question["answer_keywords"] else ""
        missing_concepts = ""

        for line in raw.strip().split("\n"):
            line = line.strip()
            key, _, val = line.partition(":")
            key = key.strip().lower()
            val = val.strip()

            if key in dims:
                try:
                    dims[key] = max(0.0, min(1.0, float(val.split()[0])))
                except ValueError:
                    pass
            elif key == "feedback":
                feedback = val
            elif key == "model_answer":
                model_answer = val
            elif key == "missing_concepts":
                missing_concepts = val

        final_score = round(
            sum(TECHNICAL_WEIGHTS[k] * dims[k] for k in TECHNICAL_WEIGHTS), 3
        )

        return {
            "final_score":      final_score,
            "dimension_scores": dims,
            "feedback":         feedback,
            "model_answer":     model_answer,
            "missing_concepts": missing_concepts,
            "tip":              self._tech_tip(dims),
            "round":            "Technical"
        }

    # ── Fallback Evaluators ───────────────────────────────────────────────────

    def _fallback_hr_eval(self, answer: str, question: dict) -> dict:
        """Keyword-based fallback for HR evaluation."""
        keywords  = question["answer_keywords"]
        ans_lower = answer.lower()
        hits      = sum(1 for k in keywords if k.lower() in ans_lower)
        score     = min(1.0, hits / max(len(keywords), 1))

        return {
            "final_score":      round(score, 2),
            "dimension_scores": {"communication": score, "relevance": score,
                                  "structure": score, "confidence": score},
            "feedback":         "Evaluated via keyword matching (LLM unavailable).",
            "model_answer":     f"Cover: {', '.join(keywords[:3])}",
            "star_used":        "Yes" if "situation" in ans_lower or "result" in ans_lower else "No",
            "tip":              "Structure your answer using: Situation → Task → Action → Result.",
            "round":            "HR"
        }

    def _fallback_tech_eval(self, answer: str, question: dict) -> dict:
        """Keyword-based fallback for Technical evaluation."""
        keywords  = question["answer_keywords"]
        ans_lower = answer.lower()
        hits      = sum(1 for k in keywords if k.lower() in ans_lower)
        score     = min(1.0, hits / max(len(keywords), 1))

        return {
            "final_score":      round(score, 2),
            "dimension_scores": {"correctness": score, "depth": score,
                                  "clarity": score, "examples": score},
            "feedback":         "Evaluated via keyword matching (LLM unavailable).",
            "model_answer":     f"Key concepts: {', '.join(keywords)}",
            "missing_concepts": "",
            "tip":              "Always mention time/space complexity and give a real-world example.",
            "round":            "Technical"
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _generate_opening(self, role: str, mode: str) -> str:
        """Generate a natural interviewer opening message."""
        prompt = (
            f"You are interviewing a fresh graduate for a {role} position. "
            f"Write a warm, professional 2-sentence opening statement to begin "
            f"the {'HR' if mode == 'hr' else 'technical' if mode == 'technical' else 'HR'} round. "
            f"Be encouraging but professional. Write only the 2 sentences:"
        )
        try:
            return self.llm.invoke(prompt).strip()
        except Exception:
            return (
                f"Welcome! I'm glad you could join us today for the {role} interview. "
                f"Let's start — please take your time and answer thoughtfully."
            )

    def _get_interviewer_intro(self, question: dict, round_type: str) -> str:
        """Add a natural transition phrase before each question."""
        hr_intros = [
            "Great. My next question is —",
            "Thank you. Let's continue —",
            "I see. Moving on —",
            "Interesting. Now —",
            "Good. Here's my next question —"
        ]
        tech_intros = [
            "Let's test your technical knowledge —",
            "Here's a concept I'd like you to explain —",
            "Good. Now a technical question —",
            "Let's go deeper —",
            "Alright, technically speaking —"
        ]
        pool = hr_intros if round_type == "HR" else tech_intros
        return random.choice(pool)

    def _generate_closing_feedback(self, result: dict) -> str:
        """Generate personalized closing feedback using LLM."""
        prompt = f"""You just interviewed a candidate for {result['target_role']}.
HR Score: {result['hr_score']}, Technical Score: {result['technical_score']},
Overall: {result['overall_score']}, Decision: {result['result']}

Write a professional 3-sentence closing statement:
1. Acknowledge their performance honestly
2. Mention their biggest strength
3. Give one key area to improve

Write only the 3 sentences:"""
        try:
            return self.llm.invoke(prompt).strip()
        except Exception:
            passed = result["overall_score"] >= PASSING_SCORE_THRESHOLD
            return (
                f"Thank you for the interview today. "
                f"{'You demonstrated strong fundamentals.' if passed else 'You showed effort and potential.'} "
                f"Focus on {'advanced topics' if passed else 'core concepts'} for continued improvement."
            )

    def _hr_tip(self, dims: dict) -> str:
        """Return the most relevant improvement tip based on lowest HR dimension."""
        weakest = min(dims, key=dims.get)
        tips = {
            "communication": "Speak in clear, complete sentences. Avoid filler words like 'um' or 'uh'.",
            "relevance":     "Always tie your answer directly back to the question asked.",
            "structure":     "Use the STAR method: Situation → Task → Action → Result.",
            "confidence":    "Practice out loud. Confidence comes from familiarity with your own stories."
        }
        return tips.get(weakest, "Keep practicing to improve your interview performance.")

    def _tech_tip(self, dims: dict) -> str:
        """Return the most relevant improvement tip based on lowest Technical dimension."""
        weakest = min(dims, key=dims.get)
        tips = {
            "correctness": "Review core concepts — make sure your fundamentals are solid.",
            "depth":       "Go beyond surface definitions. Explain the 'why' and 'how' in detail.",
            "clarity":     "Structure your answer: define → explain → example → complexity.",
            "examples":    "Always give a real-world example or use case to support your answer."
        }
        return tips.get(weakest, "Study the topic thoroughly and practice explaining it aloud.")
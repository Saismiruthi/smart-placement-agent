# agents/skill_gap_agent.py
# Compares student skills against job role requirements and generates a gap report

import csv
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from loguru import logger
from crewai import Agent
from langchain_community.llms import Ollama

from config import (
    JOB_SKILLS_CSV, EMBEDDING_MODEL,
    LLM_MODEL, OLLAMA_BASE_URL
)


def load_job_skills_dataset() -> list[dict]:
    """
    Load the job skills CSV dataset into a list of dicts.
    Each dict has: role, required_skills (list), nice_to_have (list), salary_lpa
    """
    if not Path(JOB_SKILLS_CSV).exists():
        raise FileNotFoundError(
            f"Job skills dataset not found at {JOB_SKILLS_CSV}. "
            "Please run generate_datasets.py first."
        )

    jobs = []
    with open(JOB_SKILLS_CSV, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            jobs.append({
                "role": row["role"],
                "required_skills": [s.strip() for s in row["required_skills"].split("|")],
                "nice_to_have": [s.strip() for s in row["nice_to_have"].split("|")],
                "experience_level": row["experience_level"],
                "salary_lpa": row["salary_lpa"]
            })

    logger.info(f"Loaded {len(jobs)} job roles from dataset")
    return jobs


class SkillGapAgent:
    """
    Detects skill gaps between a student's profile and a target job role.

    Two-layer gap detection:
        1. Hard gap  — skill is completely absent (no semantic match above threshold)
        2. Soft gap  — student has a related skill but not the exact one required
                       (semantic similarity between 0.4 and 0.75)
    """

    def __init__(self):
        logger.info("Initializing Skill Gap Agent...")

        self.jobs = load_job_skills_dataset()
        self.role_names = [j["role"] for j in self.jobs]

        # Embedding model (same one used in resume agent — consistent vector space)
        self.model = SentenceTransformer(EMBEDDING_MODEL)

        # Pre-compute embeddings for all job role names (for role recommendation)
        self.role_embeddings = self.model.encode(self.role_names, convert_to_tensor=True)

        # LLM for generating the human-readable learning plan
        self.llm = Ollama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.3
        )

        # CrewAI agent definition
        self.agent = Agent(
            role="Skill Gap Analyst",
            goal=(
                "Accurately identify skill gaps between a student's current skills "
                "and industry requirements for their target job role."
            ),
            backstory=(
                "You are a senior technical recruiter who has reviewed thousands of "
                "resumes and knows exactly what skills companies look for at fresher "
                "and junior levels across software, data, and cloud domains."
            ),
            llm=self.llm,
            verbose=False,
            allow_delegation=False
        )

        logger.info("Skill Gap Agent ready.")

    def get_available_roles(self) -> list[str]:
        """Return all job roles available in the dataset."""
        return self.role_names

    def recommend_best_role(self, student_skills: list[str]) -> str:
        """
        Suggest the best-fit job role for a student based on their skills.
        Uses semantic similarity between student skill string and role names.

        Args:
            student_skills: List of skill strings from resume analysis

        Returns:
            Best matching role name
        """
        if not student_skills:
            return self.role_names[0]

        skills_text = " ".join(student_skills)
        skills_embedding = self.model.encode(skills_text, convert_to_tensor=True)

        similarities = util.cos_sim(skills_embedding, self.role_embeddings)[0]
        best_idx = int(similarities.argmax())

        best_role = self.role_names[best_idx]
        best_score = float(similarities[best_idx])
        logger.info(f"Best role recommendation: '{best_role}' (score: {best_score:.3f})")
        return best_role

    def analyze_gap(self, student_skills: list[str], target_role: str) -> dict:
        """
        Core gap analysis: compare student skills vs job requirements.

        Args:
            student_skills: List of skill names the student has
            target_role: The job role to compare against

        Returns:
            Detailed gap report dictionary
        """
        # Find the job in dataset
        job = next((j for j in self.jobs if j["role"].lower() == target_role.lower()), None)

        if not job:
            # Fuzzy match: find closest role name
            target_emb = self.model.encode(target_role, convert_to_tensor=True)
            sims = util.cos_sim(target_emb, self.role_embeddings)[0]
            best_idx = int(sims.argmax())
            job = self.jobs[best_idx]
            logger.warning(f"Role '{target_role}' not found exactly. Using '{job['role']}'")

        required = job["required_skills"]
        nice_to_have = job["nice_to_have"]

        # Encode student skills
        if student_skills:
            student_emb = self.model.encode(student_skills, convert_to_tensor=True)
        else:
            student_emb = None

        # Encode required skills
        required_emb = self.model.encode(required, convert_to_tensor=True)

        hard_gaps = []      # Completely missing
        soft_gaps = []      # Partially covered
        matched = []        # Fully covered

        for i, req_skill in enumerate(required):
            req_emb = required_emb[i]

            if student_emb is None:
                hard_gaps.append(req_skill)
                continue

            # Compute similarity of this required skill against all student skills
            sims = util.cos_sim(req_emb, student_emb)[0]
            best_sim = float(sims.max())
            best_match_idx = int(sims.argmax())
            best_match_skill = student_skills[best_match_idx]

            if best_sim >= 0.75:
                # Strong match — student has this skill
                matched.append({
                    "required": req_skill,
                    "matched_with": best_match_skill,
                    "similarity": round(best_sim, 3)
                })
            elif best_sim >= 0.40:
                # Partial match — related skill but not exact
                soft_gaps.append({
                    "required": req_skill,
                    "closest_student_skill": best_match_skill,
                    "similarity": round(best_sim, 3),
                    "gap_type": "soft"
                })
            else:
                # No meaningful match
                hard_gaps.append(req_skill)

        # Check nice-to-have coverage
        nice_to_have_gaps = []
        for skill in nice_to_have:
            skill_emb = self.model.encode(skill, convert_to_tensor=True)
            if student_emb is not None:
                sims = util.cos_sim(skill_emb, student_emb)[0]
                if float(sims.max()) < 0.60:
                    nice_to_have_gaps.append(skill)
            else:
                nice_to_have_gaps.append(skill)

        # Compute readiness score
        total_required = len(required)
        fully_covered = len(matched)
        partially_covered = len(soft_gaps)
        readiness_score = round(
            (fully_covered + 0.5 * partially_covered) / total_required * 100, 1
        ) if total_required > 0 else 0

        # Priority learning list: hard gaps first, then soft gaps
        priority_skills = hard_gaps + [g["required"] for g in soft_gaps]

        # Generate LLM-powered learning roadmap
        learning_plan = self._generate_learning_plan(
            target_role=job["role"],
            hard_gaps=hard_gaps,
            soft_gaps=[g["required"] for g in soft_gaps],
            readiness_score=readiness_score
        )

        gap_report = {
            "target_role": job["role"],
            "salary_lpa": job["salary_lpa"],
            "readiness_score": readiness_score,
            "total_required_skills": total_required,
            "matched_skills": matched,
            "hard_gaps": hard_gaps,
            "soft_gaps": soft_gaps,
            "nice_to_have_gaps": nice_to_have_gaps,
            "priority_learning_list": priority_skills,
            "learning_plan": learning_plan,
            "summary": self._build_summary(readiness_score, hard_gaps, soft_gaps)
        }

        logger.info(
            f"Gap analysis complete for '{job['role']}': "
            f"readiness={readiness_score}%, "
            f"hard_gaps={len(hard_gaps)}, soft_gaps={len(soft_gaps)}"
        )
        return gap_report

    def _generate_learning_plan(
        self,
        target_role: str,
        hard_gaps: list,
        soft_gaps: list,
        readiness_score: float
    ) -> str:
        """Use the LLM to generate a prioritized, human-readable learning plan."""

        hard_str = ", ".join(hard_gaps[:8]) if hard_gaps else "None"
        soft_str = ", ".join(soft_gaps[:5]) if soft_gaps else "None"

        prompt = f"""You are a placement mentor. A student wants to become a {target_role}.

Their placement readiness score is {readiness_score}%.
Critical missing skills: {hard_str}
Skills to strengthen: {soft_str}

Write a concise 5-point learning plan (numbered list) that tells them exactly what to learn first, 
in what order, and approximately how long each step will take. Be specific and actionable.
Write only the 5 numbered points, nothing else:"""

        try:
            plan = self.llm.invoke(prompt)
            return plan.strip()
        except Exception as e:
            logger.warning(f"LLM learning plan generation failed: {e}")
            items = hard_gaps[:5] if hard_gaps else soft_gaps[:5]
            return "\n".join(
                [f"{i+1}. Learn {skill} — 1-2 weeks" for i, skill in enumerate(items)]
            )

    def _build_summary(self, score: float, hard_gaps: list, soft_gaps: list) -> str:
        """Build a one-line summary string."""
        if score >= 80:
            level = "Strong candidate"
        elif score >= 55:
            level = "Moderate readiness"
        elif score >= 30:
            level = "Needs significant preparation"
        else:
            level = "Early stage — begin foundational learning"

        return (
            f"{level}. Readiness: {score}%. "
            f"Critical gaps: {len(hard_gaps)}. "
            f"Skills to strengthen: {len(soft_gaps)}."
        )
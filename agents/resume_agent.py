# agents/resume_agent.py
# The Resume Analyzer Agent — orchestrates PDF parsing, skill extraction, and profile building

import uuid
from pathlib import Path
from loguru import logger
from crewai import Agent, Task, Crew
from langchain_community.llms import Ollama

from tools.pdf_parser import extract_text_from_pdf, extract_text_from_uploaded_file
from tools.nlp_extractor import NLPSkillExtractor, extract_personal_info
from tools.db_manager import init_database, save_student_profile, get_student_profile
from config import LLM_MODEL, OLLAMA_BASE_URL, EMBEDDING_MODEL


class ResumeAnalyzerAgent:
    """
    Analyzes a student's resume to extract skills and build a profile.
    
    Workflow:
        1. Parse PDF → raw text
        2. Extract personal info (name, email) via regex
        3. Extract skills via NLP semantic similarity
        4. Save structured profile to SQLite
        5. Return structured profile dict
    """
    
    def __init__(self):
        logger.info("Initializing Resume Analyzer Agent...")
        
        # Initialize database
        init_database()
        
        # Load NLP extractor (downloads model on first run)
        self.skill_extractor = NLPSkillExtractor(model_name=EMBEDDING_MODEL)
        
        # Initialize local LLM via Ollama
        self.llm = Ollama(
            model=LLM_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0.1   # Low temperature for factual extraction
        )
        
        # Define the CrewAI agent
        self.agent = Agent(
            role="Resume Analyzer",
            goal="Extract all relevant skills and information from student resumes accurately",
            backstory=(
                "You are an expert HR analyst and technical recruiter with 10 years of "
                "experience reading resumes. You can identify technical skills, soft skills, "
                "projects, and experience levels from any resume format."
            ),
            llm=self.llm,
            verbose=True,
            allow_delegation=False
        )
        
        logger.info("Resume Analyzer Agent ready.")
    
    def analyze_pdf_file(self, pdf_path: str, student_id: str = None) -> dict:
        """
        Full pipeline: PDF file path → structured student profile.
        
        Args:
            pdf_path: Path to the PDF resume
            student_id: Optional custom ID; auto-generated if not provided
        
        Returns:
            Structured student profile dictionary
        """
        # Step 1: Parse PDF
        logger.info(f"Analyzing resume: {pdf_path}")
        raw_text = extract_text_from_pdf(pdf_path)
        
        return self._process_resume_text(raw_text, student_id)
    
    def analyze_uploaded_file(self, uploaded_file, student_id: str = None) -> dict:
        """
        Full pipeline: Streamlit uploaded file → structured student profile.
        Used directly in the UI.
        """
        logger.info("Analyzing uploaded resume file...")
        raw_text = extract_text_from_uploaded_file(uploaded_file)
        
        return self._process_resume_text(raw_text, student_id)
    
    def _process_resume_text(self, raw_text: str, student_id: str = None) -> dict:
        """
        Core processing pipeline given raw resume text.
        """
        if not raw_text or len(raw_text.strip()) < 100:
            raise ValueError("Resume text is too short. Please upload a valid resume PDF.")
        
        # Step 2: Extract personal info
        personal_info = extract_personal_info(raw_text)
        
        # Generate student ID from email or random UUID
        if not student_id:
            if personal_info.get("email"):
                student_id = personal_info["email"].replace("@", "_at_").replace(".", "_")
            else:
                student_id = str(uuid.uuid4())[:8]
        
        # Step 3: Extract skills via NLP
        skills_data = self.skill_extractor.extract_skills(raw_text)
        
        # Step 4: Use LLM to generate a short summary paragraph
        summary = self._generate_summary(raw_text, skills_data["matched_skills"])
        
        # Step 5: Save to SQLite
        save_student_profile(student_id, personal_info, skills_data)
        
        # Build final profile
        profile = {
            "student_id": student_id,
            "personal_info": personal_info,
            "skills": skills_data["matched_skills"],
            "skills_by_category": skills_data["skills_by_category"],
            "confidence_scores": skills_data["confidence_scores"],
            "total_skills_found": len(skills_data["matched_skills"]),
            "summary": summary,
            "raw_text_length": len(raw_text)
        }
        
        logger.info(f"Resume analysis complete. Student ID: {student_id}, Skills found: {profile['total_skills_found']}")
        return profile
    
    def _generate_summary(self, resume_text: str, skills: list) -> str:
        """
        Use the LLM to generate a concise profile summary from the resume.
        """
        # Truncate text to avoid token limit issues with phi3
        truncated = resume_text[:2000]
        skills_str = ", ".join(skills[:15])  # Top 15 skills
        
        prompt = f"""You are a resume analyst. Based on this resume excerpt, write a 3-sentence 
professional summary highlighting experience level, top skills, and career focus.

Resume excerpt:
{truncated}

Key skills detected: {skills_str}

Write only the 3-sentence summary, nothing else:"""
        
        try:
            summary = self.llm.invoke(prompt)
            return summary.strip()
        except Exception as e:
            logger.warning(f"LLM summary generation failed: {e}")
            return f"Student profile with {len(skills)} detected skills including: {skills_str}."
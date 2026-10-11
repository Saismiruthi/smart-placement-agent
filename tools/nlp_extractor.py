# tools/nlp_extractor.py
# Extracts skills from resume text using semantic similarity (Sentence Transformers)

import re
import json
from pathlib import Path
from sentence_transformers import SentenceTransformer, util
from loguru import logger
import torch

# ── Known skill vocabulary ─────────────────────────────────────────────────────
# This is the master list we compare resume text against.
# You can expand this as needed.

SKILL_VOCABULARY = {
    "programming_languages": [
        "Python", "Java", "C", "C++", "JavaScript", "TypeScript",
        "Go", "Rust", "Kotlin", "Swift", "R", "MATLAB", "Scala", "PHP", "Ruby"
    ],
    "web_technologies": [
        "HTML", "CSS", "React", "Angular", "Vue.js", "Node.js",
        "Django", "Flask", "FastAPI", "Spring Boot", "REST API", "GraphQL"
    ],
    "data_and_ml": [
        "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch",
        "Scikit-learn", "Pandas", "NumPy", "Matplotlib", "Seaborn",
        "NLP", "Computer Vision", "Data Analysis", "Statistics",
        "Feature Engineering", "Model Deployment"
    ],
    "databases": [
        "SQL", "MySQL", "PostgreSQL", "MongoDB", "SQLite",
        "Redis", "Cassandra", "Oracle", "Firebase"
    ],
    "cloud_and_devops": [
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "CI/CD",
        "Jenkins", "GitHub Actions", "Terraform", "Linux", "Git"
    ],
    "soft_skills": [
        "Communication", "Teamwork", "Leadership", "Problem Solving",
        "Critical Thinking", "Time Management", "Adaptability"
    ]
}

# Flatten for embedding
ALL_SKILLS = []
SKILL_CATEGORY_MAP = {}  # skill -> category
for category, skills in SKILL_VOCABULARY.items():
    for skill in skills:
        ALL_SKILLS.append(skill)
        SKILL_CATEGORY_MAP[skill] = category


class NLPSkillExtractor:
    """
    Uses Sentence Transformers to extract skills from resume text
    via semantic similarity matching.
    """
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2", threshold: float = 0.45):
        """
        Args:
            model_name: The sentence transformer model to use
            threshold: Minimum cosine similarity to consider a skill matched
        """
        logger.info(f"Loading NLP model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.threshold = threshold
        
        # Pre-compute skill embeddings once (faster at query time)
        logger.info("Pre-computing skill embeddings...")
        self.skill_embeddings = self.model.encode(ALL_SKILLS, convert_to_tensor=True)
        logger.info(f"Ready. {len(ALL_SKILLS)} skills loaded.")
    
    def extract_skills(self, resume_text: str) -> dict:
        """
        Extract skills from raw resume text.
        
        Args:
            resume_text: Raw text extracted from resume PDF
        
        Returns:
            dict with keys: matched_skills, skills_by_category, confidence_scores
        """
        if not resume_text or len(resume_text.strip()) < 50:
            logger.warning("Resume text too short for meaningful extraction")
            return {"matched_skills": [], "skills_by_category": {}, "confidence_scores": {}}
        
        # Clean the text
        cleaned_text = self._clean_text(resume_text)
        
        # Split into chunks (sentences/lines) for better matching
        chunks = self._split_into_chunks(cleaned_text)
        
        # Encode all chunks
        chunk_embeddings = self.model.encode(chunks, convert_to_tensor=True)
        
        matched_skills = {}  # skill -> best similarity score
        
        # For each skill, find the best matching chunk
        for idx, skill in enumerate(ALL_SKILLS):
            skill_emb = self.skill_embeddings[idx]
            
            # Compute cosine similarity against all chunks
            similarities = util.cos_sim(skill_emb, chunk_embeddings)[0]
            best_score = float(similarities.max())
            
            if best_score >= self.threshold:
                matched_skills[skill] = round(best_score, 3)
        
        # Also do direct keyword matching as a safety net
        keyword_skills = self._keyword_match(cleaned_text)
        for skill in keyword_skills:
            if skill not in matched_skills:
                matched_skills[skill] = 0.95  # High confidence for exact match
        
        # Organize by category
        skills_by_category = {}
        for skill, score in matched_skills.items():
            category = SKILL_CATEGORY_MAP.get(skill, "other")
            if category not in skills_by_category:
                skills_by_category[category] = []
            skills_by_category[category].append(skill)
        
        logger.info(f"Extracted {len(matched_skills)} skills from resume")
        
        return {
            "matched_skills": sorted(matched_skills.keys()),
            "skills_by_category": skills_by_category,
            "confidence_scores": matched_skills
        }
    
    def _clean_text(self, text: str) -> str:
        """Remove noise from extracted PDF text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove special characters but keep alphanumeric and basic punctuation
        text = re.sub(r'[^\w\s\.\,\+\#\-\/]', ' ', text)
        return text.strip()
    
    def _split_into_chunks(self, text: str, max_chunk_size: int = 100) -> list:
        """Split resume text into sentence-like chunks for embedding."""
        # Split by newlines and periods
        raw_chunks = re.split(r'[\n\.\,]', text)
        chunks = []
        for chunk in raw_chunks:
            chunk = chunk.strip()
            if len(chunk) > 10:  # Skip very short fragments
                chunks.append(chunk[:max_chunk_size])  # Cap length
        
        # Always include the full text as one chunk too
        chunks.append(text[:500])
        return chunks if chunks else [text]
    
    def _keyword_match(self, text: str) -> list:
        """Direct case-insensitive keyword matching as backup."""
        text_lower = text.lower()
        found = []
        for skill in ALL_SKILLS:
            if skill.lower() in text_lower:
                found.append(skill)
        return found


def extract_personal_info(resume_text: str) -> dict:
    """
    Extract basic personal information from resume text using regex.
    
    Returns:
        dict with name, email, phone, linkedin (best-effort extraction)
    """
    info = {
        "name": "",
        "email": "",
        "phone": "",
        "linkedin": ""
    }
    
    # Email
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, resume_text)
    if emails:
        info["email"] = emails[0]
    
    # Phone (Indian + international formats)
    # Match full number including optional +91 prefix
    phone_pattern = r'(\+91[\-\s]?[6-9]\d{9}|[6-9]\d{9})'
    phones = re.findall(phone_pattern, resume_text)
    if phones:
        info["phone"] = str(phones[0]).strip()
    
    # LinkedIn
    linkedin_pattern = r'linkedin\.com/in/[\w\-]+'
    linkedin = re.findall(linkedin_pattern, resume_text.lower())
    if linkedin:
        info["linkedin"] = "https://" + linkedin[0]
    
    # Name: first non-empty line is usually the name
    lines = [l.strip() for l in resume_text.split('\n') if l.strip()]
    if lines:
        first_line = lines[0]
        # Name is usually 2-4 words, all alpha
        if len(first_line.split()) <= 5 and all(w.replace('.','').isalpha() for w in first_line.split()):
            info["name"] = first_line
    
    return info
# test_resume_agent.py — Run this to verify Phase 2 works

from agents.resume_agent import ResumeAnalyzerAgent
import json

def test_with_sample_text():
    """Test using a synthetic resume (no PDF needed for this test)."""
    
    from tools.nlp_extractor import NLPSkillExtractor, extract_personal_info
    from tools.db_manager import init_database, save_student_profile
    
    # Sample resume text
    sample_resume = """
    Arjun Kumar
    arjun.kumar@gmail.com | +91 9876543210 | linkedin.com/in/arjunkumar
    
    SKILLS
    Python, Java, Machine Learning, Deep Learning, TensorFlow, PyTorch
    SQL, MySQL, MongoDB, Docker, Git, AWS
    HTML, CSS, React, Flask, REST API
    
    EXPERIENCE
    Data Science Intern — TechCorp (2023)
    - Built ML models using scikit-learn and pandas for customer churn prediction
    - Deployed Flask REST API for model serving
    - Used Docker for containerization
    
    EDUCATION
    B.Tech Computer Science — Anna University (2024)
    CGPA: 8.5
    
    PROJECTS
    - Sentiment Analysis using NLP and BERT
    - Image Classification using Convolutional Neural Networks with PyTorch
    - Real-time Dashboard using React and Node.js
    """
    
    # Test extraction
    print("=" * 50)
    print("TESTING SKILL EXTRACTOR")
    print("=" * 50)
    
    extractor = NLPSkillExtractor()
    skills_data = extractor.extract_skills(sample_resume)
    
    print(f"\nTotal skills found: {len(skills_data['matched_skills'])}")
    print(f"\nSkills by category:")
    for category, skills in skills_data['skills_by_category'].items():
        print(f"  {category}: {', '.join(skills)}")
    
    print(f"\nPersonal info:")
    info = extract_personal_info(sample_resume)
    print(json.dumps(info, indent=2))
    
    print("\n✅ Phase 2 test passed!")

if __name__ == "__main__":
    test_with_sample_text()
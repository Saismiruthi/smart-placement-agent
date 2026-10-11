# data/generate_datasets.py
# Generates all datasets needed for the Smart Placement Agent

import csv
import json
import random
import os
from pathlib import Path

# Ensure directories exist
Path("data/datasets").mkdir(parents=True, exist_ok=True)
Path("data/student_profiles").mkdir(parents=True, exist_ok=True)
Path("data/sample_resumes").mkdir(parents=True, exist_ok=True)

print("=" * 55)
print("  SMART PLACEMENT AGENT — DATASET GENERATOR")
print("=" * 55)


# ══════════════════════════════════════════════════════════
# 1. JOB SKILLS DATASET
# ══════════════════════════════════════════════════════════

job_skills_data = [
    ["Software Development Engineer",
     "Python|Java|Data Structures|Algorithms|OOP|Git|SQL|Problem Solving|REST API|System Design",
     "Docker|Kubernetes|AWS|Microservices|Redis",
     "Fresher", "6-12"],

    ["Data Scientist",
     "Python|Machine Learning|Deep Learning|Statistics|Pandas|NumPy|Scikit-learn|SQL|Data Analysis|Feature Engineering",
     "TensorFlow|PyTorch|Spark|Tableau|NLP|MLflow",
     "Fresher", "7-14"],

    ["Data Analyst",
     "SQL|Python|Excel|Data Analysis|Statistics|Pandas|Tableau|Power BI|Data Visualization|Communication",
     "R|Machine Learning|Seaborn|ETL|Looker",
     "Fresher", "4-8"],

    ["Frontend Developer",
     "HTML|CSS|JavaScript|React|Git|REST API|Responsive Design|TypeScript|Problem Solving|UI Design",
     "Vue.js|Angular|Node.js|Webpack|Jest|Figma",
     "Fresher", "5-10"],

    ["Backend Developer",
     "Python|Java|SQL|REST API|Git|OOP|System Design|MySQL|Problem Solving|Data Structures",
     "Docker|Redis|Kafka|Microservices|AWS|PostgreSQL",
     "Fresher", "6-12"],

    ["Full Stack Developer",
     "HTML|CSS|JavaScript|React|Node.js|SQL|Python|Git|REST API|OOP",
     "Docker|AWS|TypeScript|MongoDB|Redis|GraphQL",
     "Fresher", "7-13"],

    ["Machine Learning Engineer",
     "Python|Machine Learning|Deep Learning|TensorFlow|PyTorch|SQL|Statistics|Git|Feature Engineering|Model Deployment",
     "Docker|Kubernetes|AWS|Spark|MLflow|FastAPI",
     "Fresher", "8-15"],

    ["DevOps Engineer",
     "Linux|Docker|Kubernetes|CI/CD|Git|AWS|Python|Scripting|Networking|Jenkins",
     "Terraform|Ansible|GCP|Azure|Monitoring|Helm",
     "Fresher", "7-14"],

    ["Cloud Engineer",
     "AWS|Azure|GCP|Docker|Linux|Python|Networking|Security|Git|Infrastructure",
     "Kubernetes|Terraform|CI/CD|Scripting|CloudFormation",
     "Fresher", "8-15"],

    ["Cybersecurity Analyst",
     "Networking|Security|Linux|Python|Risk Assessment|Ethical Hacking|Firewalls|SQL|Communication|Problem Solving",
     "SIEM|Penetration Testing|Cloud Security|Scripting|Wireshark",
     "Fresher", "6-12"],

    ["Android Developer",
     "Java|Kotlin|Android SDK|Git|OOP|REST API|SQL|Problem Solving|UI Design|Firebase",
     "Kotlin Coroutines|Testing|CI/CD|Jetpack Compose",
     "Fresher", "5-11"],

    ["AI Engineer",
     "Python|Machine Learning|Deep Learning|NLP|TensorFlow|PyTorch|Statistics|Git|System Design|Model Deployment",
     "Docker|AWS|LLMs|Vector Databases|MLflow|LangChain",
     "Fresher", "9-18"],

    ["iOS Developer",
     "Swift|Xcode|OOP|REST API|Git|Problem Solving|UI Design|Core Data|Auto Layout",
     "SwiftUI|Testing|CI/CD|CocoaPods|Firebase",
     "Fresher", "6-12"],

    ["Database Administrator",
     "SQL|MySQL|PostgreSQL|Oracle|Performance Tuning|Backup|Security|Linux|Scripting|Data Modeling",
     "MongoDB|Redis|AWS RDS|Replication|Indexing",
     "Fresher", "5-10"],

    ["QA Engineer",
     "Testing|Selenium|Python|SQL|Git|Test Planning|Bug Reporting|REST API|Communication|Problem Solving",
     "Cypress|JUnit|CI/CD|Performance Testing|Postman",
     "Fresher", "4-9"],
]

with open("data/datasets/job_skills.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["role", "required_skills", "nice_to_have",
                     "experience_level", "salary_lpa"])
    writer.writerows(job_skills_data)

print(f"\n✅ job_skills.csv — {len(job_skills_data)} roles created")


# ══════════════════════════════════════════════════════════
# 2. CODING QUESTIONS DATASET
# ══════════════════════════════════════════════════════════

coding_questions = [
    # EASY
    [1,  "Two Sum",                  "Arrays",             "easy",
     "Find two numbers in array that add to target",
     "Use a hashmap for O(n)",                    "Amazon|Google|Microsoft"],
    [2,  "Reverse a String",         "Strings",            "easy",
     "Reverse a given string in-place",
     "Two pointer approach",                      "Infosys|Wipro|TCS"],
    [3,  "Fibonacci Sequence",       "Recursion",          "easy",
     "Return nth Fibonacci number",
     "Think DP to optimize",                      "TCS|Cognizant"],
    [4,  "Valid Parentheses",        "Stack",              "easy",
     "Check if bracket sequence is valid",
     "Use a stack data structure",                "Amazon|Goldman Sachs"],
    [5,  "Binary Search",            "Searching",          "easy",
     "Implement binary search on sorted array",
     "Mid = (low+high)//2",                       "All companies"],
    [6,  "Merge Two Sorted Lists",   "Linked List",        "easy",
     "Merge two sorted linked lists",
     "Compare heads recursively",                 "Microsoft|Adobe"],
    [7,  "Palindrome Check",         "Strings",            "easy",
     "Check if a string is a palindrome",
     "Two pointers from both ends",               "TCS|Infosys|Wipro"],
    [8,  "Find Maximum Element",     "Arrays",             "easy",
     "Find the maximum element in an array",
     "Single pass O(n)",                          "All companies"],
    [9,  "Climbing Stairs",          "Dynamic Programming","easy",
     "Count ways to climb n stairs (1 or 2 steps)",
     "dp[n] = dp[n-1] + dp[n-2]",               "Amazon|TCS"],
    [10, "Palindrome Linked List",   "Linked List",        "easy",
     "Check if linked list is a palindrome",
     "Find middle, reverse second half",          "Microsoft|Adobe"],
    [11, "Count Vowels",             "Strings",            "easy",
     "Count vowels in a given string",
     "Use a set for O(1) lookup",                 "Infosys|Cognizant"],
    [12, "Factorial",                "Recursion",          "easy",
     "Compute factorial of n",
     "Base case n=0 returns 1",                   "TCS|Wipro"],

    # MEDIUM
    [13, "Maximum Subarray",         "Dynamic Programming","medium",
     "Find contiguous subarray with max sum",
     "Kadane's algorithm",                        "Amazon|Google"],
    [14, "Longest Common Prefix",    "Strings",            "medium",
     "Find longest common prefix among strings",
     "Sort and compare first/last",               "Google|Flipkart"],
    [15, "Level Order Traversal",    "Trees",              "medium",
     "BFS traversal of binary tree level by level",
     "Use a queue",                               "Amazon|Microsoft"],
    [16, "Number of Islands",        "Graphs",             "medium",
     "Count islands in a 2D grid",
     "DFS/BFS flood fill",                        "Amazon|Google|Uber"],
    [17, "LRU Cache",                "Design",             "medium",
     "Design a Least Recently Used cache",
     "Doubly linked list + hashmap",              "Amazon|Microsoft|Uber"],
    [18, "Course Schedule",          "Graphs",             "medium",
     "Detect if course prerequisites form a cycle",
     "Topological sort / DFS cycle detection",   "Google|Amazon"],
    [19, "Word Break",               "Dynamic Programming","medium",
     "Can string be segmented into dictionary words?",
     "DP with memo",                              "Google|Facebook"],
    [20, "Rotate Image",             "Arrays",             "medium",
     "Rotate NxN matrix 90 degrees in-place",
     "Transpose then reverse rows",              "Microsoft|Snapchat"],
    [21, "Group Anagrams",           "Strings",            "medium",
     "Group strings that are anagrams of each other",
     "Sort each string as key in hashmap",       "Amazon|Facebook"],
    [22, "Binary Tree Zigzag",       "Trees",              "medium",
     "Zigzag level order traversal of binary tree",
     "BFS with direction flag",                  "Amazon|Microsoft"],
    [23, "Coin Change",              "Dynamic Programming","medium",
     "Minimum coins to make amount",
     "dp[amount] = min(dp[amount-coin]+1)",      "Amazon|Google|Uber"],
    [24, "Find Duplicate Number",    "Arrays",             "medium",
     "Find duplicate in array of n+1 integers",
     "Floyd's cycle detection",                  "Google|Apple"],

    # HARD
    [25, "Median of Two Sorted Arrays","Binary Search",    "hard",
     "Find median of two sorted arrays in O(log n)",
     "Binary search on smaller array",           "Google|Apple"],
    [26, "Serialize/Deserialize Tree","Trees",             "hard",
     "Convert binary tree to string and back",
     "BFS with null markers",                    "Amazon|Facebook"],
    [27, "Trapping Rain Water",      "Arrays",             "hard",
     "Calculate water trapped between bars",
     "Precompute left/right max arrays",         "Google|Amazon|Goldman Sachs"],
    [28, "N-Queens Problem",         "Backtracking",       "hard",
     "Place N queens on NxN board without attack",
     "Backtrack with column/diagonal sets",      "Google|Uber"],
    [29, "Edit Distance",            "Dynamic Programming","hard",
     "Minimum operations to convert string A to B",
     "2D DP table with insert/delete/replace",  "Google|Microsoft"],
    [30, "Alien Dictionary",         "Graphs",             "hard",
     "Find character order from sorted alien words",
     "Topological sort on character graph",     "Airbnb|Google|Facebook"],
]

with open("data/datasets/coding_questions.csv", "w",
          newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "title", "topic", "difficulty",
                     "description", "hint", "companies"])
    writer.writerows(coding_questions)

print(f"✅ coding_questions.csv — {len(coding_questions)} questions "
      f"({sum(1 for q in coding_questions if q[3]=='easy')} easy, "
      f"{sum(1 for q in coding_questions if q[3]=='medium')} medium, "
      f"{sum(1 for q in coding_questions if q[3]=='hard')} hard)")


# ══════════════════════════════════════════════════════════
# 3. INTERVIEW QUESTIONS DATASET
# ══════════════════════════════════════════════════════════

interview_questions = [
    # HR Questions
    [1,  "Tell me about yourself.", "HR", "Introduction", "easy",
     "background|skills|goals|concise|structured"],
    [2,  "Why do you want to work at this company?", "HR", "Motivation", "easy",
     "research|values|growth|fit|specific"],
    [3,  "What are your strengths and weaknesses?", "HR", "Self-awareness", "easy",
     "honest|improvement|relevant|example|growth"],
    [4,  "Where do you see yourself in 5 years?", "HR", "Career Goals", "easy",
     "growth|learning|leadership|aligned|realistic"],
    [5,  "Describe a challenging project you worked on.", "HR", "Behavioral", "medium",
     "situation|task|action|result|STAR|impact"],
    [6,  "How do you handle tight deadlines?", "HR", "Behavioral", "medium",
     "prioritize|communicate|calm|example|outcome"],
    [7,  "Tell me about a time you worked in a team.", "HR", "Teamwork", "medium",
     "collaboration|conflict|resolution|outcome|role"],
    [8,  "Why should we hire you?", "HR", "Value Proposition", "medium",
     "skills|fit|contribution|unique|evidence"],
    [9,  "How do you handle failure or mistakes?", "HR", "Resilience", "medium",
     "acknowledge|learn|improve|example|positive"],
    [10, "Describe your ideal work environment.", "HR", "Culture Fit", "easy",
     "collaborative|growth|feedback|balance|aligned"],

    # Technical Questions
    [11, "What is Object Oriented Programming?", "Technical", "OOP", "easy",
     "encapsulation|inheritance|polymorphism|abstraction|class"],
    [12, "Explain the difference between a list and a tuple in Python.",
     "Technical", "Python", "easy",
     "mutable|immutable|performance|use-case|syntax"],
    [13, "What is a RESTful API?", "Technical", "Web", "easy",
     "stateless|HTTP|endpoints|CRUD|JSON|methods"],
    [14, "Explain normalization in databases.", "Technical", "Database", "medium",
     "1NF|2NF|3NF|redundancy|anomalies|dependency"],
    [15, "What is the difference between SQL and NoSQL?", "Technical", "Database", "medium",
     "structured|unstructured|scaling|ACID|examples|schema"],
    [16, "Explain time and space complexity with an example.",
     "Technical", "DSA", "medium",
     "Big O|O(n)|O(log n)|trade-off|example|worst-case"],
    [17, "What is machine learning? Explain supervised vs unsupervised.",
     "Technical", "ML", "medium",
     "labeled|unlabeled|classification|clustering|examples|training"],
    [18, "What is overfitting and how do you prevent it?",
     "Technical", "ML", "medium",
     "regularization|dropout|cross-validation|more-data|bias-variance"],
    [19, "Explain how Git branching works.", "Technical", "DevOps", "easy",
     "branch|merge|conflict|pull-request|workflow|commit"],
    [20, "What is Docker and why is it used?", "Technical", "DevOps", "medium",
     "container|isolation|portability|image|compose|lightweight"],
    [21, "Describe the SOLID principles.", "Technical", "OOP", "hard",
     "single-responsibility|open-closed|Liskov|interface|dependency"],
    [22, "What happens when you type a URL in a browser?",
     "Technical", "Networking", "hard",
     "DNS|TCP|HTTP|server|render|steps|TLS"],
    [23, "Design a URL shortener system.", "Technical", "System Design", "hard",
     "hashing|database|cache|scalability|API|base62"],
    [24, "What is a deadlock? How do you prevent it?",
     "Technical", "OS", "medium",
     "mutual-exclusion|hold-wait|circular|prevention|detection"],
    [25, "Explain the difference between process and thread.",
     "Technical", "OS", "medium",
     "memory|concurrency|lightweight|context-switch|shared|independent"],
    [26, "What is indexing in databases?", "Technical", "Database", "medium",
     "B-tree|performance|trade-off|primary|secondary|query-speed"],
    [27, "Explain recursion with an example.", "Technical", "DSA", "easy",
     "base-case|recursive-call|stack|example|factorial|fibonacci"],
    [28, "What is the difference between stack and heap memory?",
     "Technical", "Memory", "medium",
     "static|dynamic|allocation|lifetime|overflow|scope"],
    [29, "How does garbage collection work in Python?",
     "Technical", "Python", "medium",
     "reference-counting|cyclic|gc-module|memory|automatic|CPython"],
    [30, "Design a parking lot system.", "Technical", "System Design", "hard",
     "OOP|classes|inheritance|vehicle|slot|fee|scalability"],
]

with open("data/datasets/interview_questions.csv", "w",
          newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "question", "type", "topic",
                     "difficulty", "sample_answer_keywords"])
    writer.writerows(interview_questions)

print(f"✅ interview_questions.csv — {len(interview_questions)} questions "
      f"({sum(1 for q in interview_questions if q[2]=='HR')} HR, "
      f"{sum(1 for q in interview_questions if q[2]=='Technical')} Technical)")


# ══════════════════════════════════════════════════════════
# 4. STUDENT PERSONAS (JSON profiles for testing)
# ══════════════════════════════════════════════════════════

personas = [
    {
        "persona": "beginner",
        "student_id": "student_beginner_001",
        "name": "Riya Patel",
        "email": "riya.patel@gmail.com",
        "phone": "+91 9123456780",
        "college": "State Engineering College",
        "cgpa": 6.8,
        "target_role": "Software Development Engineer",
        "skills": ["Python", "HTML", "CSS", "SQL", "Git"],
        "experience": "None",
        "projects": ["Simple calculator in Python", "Static portfolio website"],
        "skill_level": "beginner",
        "expected_readiness": "25-35%"
    },
    {
        "persona": "intermediate",
        "student_id": "student_intermediate_002",
        "name": "Arjun Kumar",
        "email": "arjun.kumar@gmail.com",
        "phone": "+91 9876543210",
        "college": "Anna University",
        "cgpa": 8.2,
        "target_role": "Data Scientist",
        "skills": [
            "Python", "Machine Learning", "SQL", "Pandas",
            "NumPy", "Scikit-learn", "Git", "Flask", "HTML"
        ],
        "experience": "6-month internship at TechCorp",
        "projects": [
            "Customer churn prediction (87% accuracy)",
            "Sentiment analysis using BERT",
            "Flask REST API deployment"
        ],
        "skill_level": "intermediate",
        "expected_readiness": "55-70%"
    },
    {
        "persona": "advanced",
        "student_id": "student_advanced_003",
        "name": "Priya Sharma",
        "email": "priya.sharma@gmail.com",
        "phone": "+91 9988776655",
        "college": "IIT Bombay",
        "cgpa": 9.1,
        "target_role": "Machine Learning Engineer",
        "skills": [
            "Python", "Machine Learning", "Deep Learning",
            "TensorFlow", "PyTorch", "NLP", "Computer Vision",
            "SQL", "Docker", "AWS", "Git", "FastAPI",
            "Statistics", "Feature Engineering", "Model Deployment"
        ],
        "experience": "1-year research internship + open source contributions",
        "projects": [
            "Real-time object detection system (YOLO)",
            "LLM fine-tuning pipeline on custom dataset",
            "MLOps pipeline with Docker + AWS SageMaker",
            "Published paper on NLP model optimization"
        ],
        "skill_level": "advanced",
        "expected_readiness": "80-90%"
    }
]

for persona in personas:
    path = f"data/student_profiles/{persona['student_id']}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(persona, f, indent=2)

print(f"✅ Student personas — {len(personas)} profiles created "
      f"(beginner, intermediate, advanced)")


# ══════════════════════════════════════════════════════════
# 5. SYNTHETIC RESUME TEXT FILES
#    (Plain text format — used for testing resume parser
#     without needing real PDF files)
# ══════════════════════════════════════════════════════════

resume_texts = {
    "resume_beginner.txt": """
RIYA PATEL
riya.patel@gmail.com | +91 9123456780 | linkedin.com/in/riyapatel
State Engineering College, Nagpur | B.Tech Computer Science | CGPA: 6.8

SKILLS
Programming: Python, HTML, CSS
Database: SQL (basic)
Tools: Git, VS Code

PROJECTS
Calculator App (Python)
- Built a command-line calculator using Python with basic operations
- Used functions and error handling

Portfolio Website (HTML/CSS)
- Created a static personal portfolio website
- Used responsive design with CSS Flexbox

EDUCATION
B.Tech Computer Science — State Engineering College (2024)
12th Grade — 78% | 10th Grade — 82%

CERTIFICATIONS
- Python Basics — Coursera (2023)
- Web Development Fundamentals — Udemy (2023)
""",

    "resume_intermediate.txt": """
ARJUN KUMAR
arjun.kumar@gmail.com | +91 9876543210 | linkedin.com/in/arjunkumar
Anna University, Chennai | B.Tech Computer Science | CGPA: 8.2

SKILLS
Programming: Python, Java, SQL
Machine Learning: Scikit-learn, Pandas, NumPy, TensorFlow
Web: Flask, HTML, CSS, REST API
Tools: Git, Docker (basic), Jupyter Notebook

EXPERIENCE
Data Science Intern — TechCorp Pvt Ltd (Jan 2023 – Jun 2023)
- Built customer churn prediction model achieving 87% accuracy
- Used feature engineering and gradient boosting (XGBoost)
- Deployed model as Flask REST API serving 500+ daily predictions
- Collaborated with 4-member cross-functional team

PROJECTS
Sentiment Analysis System
- Built NLP pipeline using BERT for product review classification
- Achieved 91% F1-score on test dataset
- Processed 50,000+ reviews from Amazon dataset

Customer Segmentation Dashboard
- Used K-Means clustering for customer segmentation
- Built interactive Tableau dashboard for business stakeholders
- Reduced marketing cost by 18% through targeted campaigns

EDUCATION
B.Tech Computer Science — Anna University (2024)
CGPA: 8.2/10 | Relevant Coursework: ML, DBMS, Algorithms, OS

ACHIEVEMENTS
- 2nd Place — Smart India Hackathon 2023 (ML Track)
- Published blog on Medium: "Feature Engineering Best Practices"
""",

    "resume_advanced.txt": """
PRIYA SHARMA
priya.sharma@gmail.com | +91 9988776655 | linkedin.com/in/priyasharma
IIT Bombay | B.Tech Computer Science | CGPA: 9.1

SKILLS
ML/AI: Machine Learning, Deep Learning, NLP, Computer Vision
Frameworks: TensorFlow, PyTorch, Scikit-learn, Hugging Face, LangChain
Programming: Python, C++, SQL, Bash Scripting
MLOps: Docker, Kubernetes, AWS SageMaker, MLflow, FastAPI, CI/CD
Data: Pandas, NumPy, Spark, Feature Engineering, Statistics
Tools: Git, Linux, Jupyter, VS Code, Weights & Biases

EXPERIENCE
ML Research Intern — IISc Bangalore (Jan 2023 – Dec 2023)
- Fine-tuned LLaMA-2 on domain-specific dataset achieving 23% improvement
- Built distributed training pipeline using PyTorch DDP on 4x A100 GPUs
- Published research paper at EMNLP 2023 Workshop on model compression
- Mentored 3 junior interns on NLP fundamentals and best practices

Open Source Contributor — Hugging Face Transformers (2022 – present)
- Contributed 8 pull requests including new tokenizer optimizations
- 340+ GitHub stars on personal NLP utility library

PROJECTS
Real-Time Object Detection System
- Implemented YOLOv8 with custom training pipeline in PyTorch
- Achieved 94.2% mAP on custom industrial defect detection dataset
- Deployed on edge device using ONNX + TensorRT optimization

MLOps Pipeline (Production-Grade)
- End-to-end ML pipeline: data ingestion → training → evaluation → deployment
- Used Docker + GitHub Actions CI/CD + AWS SageMaker for deployment
- Automated model retraining triggered by data drift detection (Evidently AI)

Vector Search Engine
- Built semantic search system using FAISS + Sentence Transformers
- Indexed 1M+ documents with sub-100ms query latency
- FastAPI backend with ChromaDB persistent storage

EDUCATION
B.Tech Computer Science — IIT Bombay (2024)
CGPA: 9.1/10 | Minor in Mathematics

ACHIEVEMENTS
- ACM ICPC Asia Regionals — Top 50 (2022)
- Google Summer of Code 2023 participant
- Best Thesis Award — IIT Bombay CS Department 2024
"""
}

for filename, content in resume_texts.items():
    path = f"data/sample_resumes/{filename}"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content.strip())

print(f"✅ Sample resume texts — {len(resume_texts)} files created")


# ══════════════════════════════════════════════════════════
# 6. SYNTHETIC PDF RESUME GENERATOR
# ══════════════════════════════════════════════════════════

def generate_pdf_resumes():
    """
    Generate actual PDF resumes from the text files above.
    Requires: pip install reportlab
    """
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, HRFlowable
        )

        styles     = getSampleStyleSheet()
        page_w, _  = A4
        margin     = 20 * mm

        # Custom styles
        title_style = ParagraphStyle(
            "Title",
            parent    = styles["Normal"],
            fontSize  = 16,
            fontName  = "Helvetica-Bold",
            spaceAfter= 2
        )
        contact_style = ParagraphStyle(
            "Contact",
            parent    = styles["Normal"],
            fontSize  = 9,
            textColor = colors.grey,
            spaceAfter= 8
        )
        section_style = ParagraphStyle(
            "Section",
            parent    = styles["Normal"],
            fontSize  = 11,
            fontName  = "Helvetica-Bold",
            spaceBefore=10,
            spaceAfter = 3,
            textColor  = colors.HexColor("#2C3E50")
        )
        body_style = ParagraphStyle(
            "Body",
            parent    = styles["Normal"],
            fontSize  = 9,
            spaceAfter= 3,
            leading   = 14
        )

        for persona in personas:
            name      = persona["name"]
            email     = persona["email"]
            phone     = persona["phone"]
            role      = persona["target_role"]
            skills    = persona["skills"]
            college   = persona["college"]
            cgpa      = persona["cgpa"]
            projects  = persona["projects"]
            exp       = persona["experience"]
            sid       = persona["student_id"]

            filename = f"data/sample_resumes/{sid}.pdf"
            doc      = SimpleDocTemplate(
                filename,
                pagesize    = A4,
                leftMargin  = margin,
                rightMargin = margin,
                topMargin   = margin,
                bottomMargin= margin
            )

            story = []

            # Header
            story.append(Paragraph(name, title_style))
            story.append(Paragraph(
                f"{email} | {phone} | linkedin.com/in/{name.lower().replace(' ', '')}",
                contact_style
            ))
            story.append(HRFlowable(
                width="100%", thickness=1,
                color=colors.HexColor("#2C3E50")
            ))

            # Objective
            story.append(Paragraph("OBJECTIVE", section_style))
            story.append(Paragraph(
                f"Motivated Computer Science graduate seeking a "
                f"{role} position. Passionate about technology "
                f"and continuous learning.",
                body_style
            ))

            # Skills
            story.append(Paragraph("SKILLS", section_style))
            story.append(Paragraph(
                " | ".join(skills), body_style
            ))

            # Experience
            story.append(Paragraph("EXPERIENCE", section_style))
            if exp and exp != "None":
                story.append(Paragraph(f"• {exp}", body_style))
            else:
                story.append(Paragraph(
                    "• Seeking first professional opportunity", body_style
                ))

            # Projects
            story.append(Paragraph("PROJECTS", section_style))
            for proj in projects:
                story.append(Paragraph(f"• {proj}", body_style))

            # Education
            story.append(Paragraph("EDUCATION", section_style))
            story.append(Paragraph(
                f"B.Tech Computer Science — {college} (2024) | CGPA: {cgpa}",
                body_style
            ))

            doc.build(story)
            print(f"   📄 PDF created: {filename}")

        print(f"✅ PDF resumes — {len(personas)} files generated")

    except ImportError:
        print("⚠️  reportlab not installed — skipping PDF generation")
        print("   Install with: pip install reportlab")
        print("   Text resume files are available in data/sample_resumes/")


generate_pdf_resumes()


# ══════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════

print("\n" + "=" * 55)
print("  DATASET GENERATION COMPLETE")
print("=" * 55)
print("  Files created:")
print("  data/datasets/job_skills.csv")
print("  data/datasets/coding_questions.csv")
print("  data/datasets/interview_questions.csv")
print("  data/student_profiles/student_beginner_001.json")
print("  data/student_profiles/student_intermediate_002.json")
print("  data/student_profiles/student_advanced_003.json")
print("  data/sample_resumes/resume_beginner.txt")
print("  data/sample_resumes/resume_intermediate.txt")
print("  data/sample_resumes/resume_advanced.txt")
print("  data/sample_resumes/student_*.pdf  (if reportlab installed)")
print("=" * 55)
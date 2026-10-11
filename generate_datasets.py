# generate_datasets.py
# Run once to create all CSV datasets needed for the project

import csv
import os
from pathlib import Path

Path("data/datasets").mkdir(parents=True, exist_ok=True)

# ── Job Skills Dataset ─────────────────────────────────────────────────────────
job_skills_data = [
    # role, required_skills (pipe-separated), nice_to_have, experience_level, avg_salary_lpa
    ["Software Development Engineer", "Python|Java|Data Structures|Algorithms|OOP|Git|SQL|Problem Solving|REST API|System Design", "Docker|Kubernetes|AWS|Microservices", "Fresher", "6-12"],
    ["Data Scientist", "Python|Machine Learning|Deep Learning|Statistics|Pandas|NumPy|Scikit-learn|SQL|Data Analysis|Feature Engineering", "TensorFlow|PyTorch|Spark|Tableau|NLP", "Fresher", "7-14"],
    ["Data Analyst", "SQL|Python|Excel|Data Analysis|Statistics|Pandas|Tableau|Power BI|Data Visualization|Communication", "R|Machine Learning|Seaborn|ETL", "Fresher", "4-8"],
    ["Frontend Developer", "HTML|CSS|JavaScript|React|Git|REST API|Responsive Design|TypeScript|Problem Solving", "Vue.js|Angular|Node.js|Webpack|Testing", "Fresher", "5-10"],
    ["Backend Developer", "Python|Java|SQL|REST API|Git|OOP|System Design|MySQL|Problem Solving|Data Structures", "Docker|Redis|Kafka|Microservices|AWS", "Fresher", "6-12"],
    ["Full Stack Developer", "HTML|CSS|JavaScript|React|Node.js|SQL|Python|Git|REST API|OOP", "Docker|AWS|TypeScript|MongoDB|Redis", "Fresher", "7-13"],
    ["Machine Learning Engineer", "Python|Machine Learning|Deep Learning|TensorFlow|PyTorch|SQL|Statistics|Git|Feature Engineering|Model Deployment", "Docker|Kubernetes|AWS|Spark|MLflow", "Fresher", "8-15"],
    ["DevOps Engineer", "Linux|Docker|Kubernetes|CI/CD|Git|AWS|Python|Scripting|Networking|Jenkins", "Terraform|Ansible|GCP|Azure|Monitoring", "Fresher", "7-14"],
    ["Cloud Engineer", "AWS|Azure|GCP|Docker|Linux|Python|Networking|Security|Git|Infrastructure", "Kubernetes|Terraform|CI/CD|Scripting", "Fresher", "8-15"],
    ["Cybersecurity Analyst", "Networking|Security|Linux|Python|Risk Assessment|Ethical Hacking|Firewalls|SQL|Communication|Problem Solving", "SIEM|Penetration Testing|Cloud Security|Scripting", "Fresher", "6-12"],
    ["Android Developer", "Java|Kotlin|Android SDK|Git|OOP|REST API|SQL|Problem Solving|UI Design", "Firebase|Kotlin Coroutines|Testing|CI/CD", "Fresher", "5-11"],
    ["AI Engineer", "Python|Machine Learning|Deep Learning|NLP|TensorFlow|PyTorch|Statistics|Git|System Design|Model Deployment", "Docker|AWS|LLMs|Vector Databases|MLflow", "Fresher", "9-18"],
]

with open("data/datasets/job_skills.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["role", "required_skills", "nice_to_have", "experience_level", "salary_lpa"])
    writer.writerows(job_skills_data)

print("✅ job_skills.csv created")

# ── Coding Questions Dataset ───────────────────────────────────────────────────
coding_data = [
    # id, title, topic, difficulty, description, hint, companies
    [1, "Two Sum", "Arrays", "easy", "Find two numbers in array that add to target", "Use a hashmap for O(n)", "Amazon|Google|Microsoft"],
    [2, "Reverse a String", "Strings", "easy", "Reverse a given string in-place", "Two pointer approach", "Infosys|Wipro|TCS"],
    [3, "Fibonacci Sequence", "Recursion", "easy", "Return nth Fibonacci number", "Think DP to optimize", "TCS|Cognizant"],
    [4, "Valid Parentheses", "Stack", "easy", "Check if bracket sequence is valid", "Use a stack data structure", "Amazon|Goldman Sachs"],
    [5, "Binary Search", "Searching", "easy", "Implement binary search on sorted array", "Mid = (low+high)//2", "All companies"],
    [6, "Merge Two Sorted Lists", "Linked List", "easy", "Merge two sorted linked lists", "Compare heads recursively", "Microsoft|Adobe"],
    [7, "Maximum Subarray", "Dynamic Programming", "medium", "Find contiguous subarray with max sum", "Kadane's algorithm", "Amazon|Google"],
    [8, "Longest Common Prefix", "Strings", "medium", "Find longest common prefix among strings", "Sort and compare first/last", "Google|Flipkart"],
    [9, "Level Order Traversal", "Trees", "medium", "BFS traversal of binary tree level by level", "Use a queue", "Amazon|Microsoft"],
    [10, "Number of Islands", "Graphs", "medium", "Count islands in a 2D grid", "DFS/BFS flood fill", "Amazon|Google|Uber"],
    [11, "LRU Cache", "Design", "medium", "Design a Least Recently Used cache", "Doubly linked list + hashmap", "Amazon|Microsoft|Uber"],
    [12, "Course Schedule", "Graphs", "medium", "Detect if course prerequisites form a cycle", "Topological sort / DFS cycle detection", "Google|Amazon"],
    [13, "Word Break", "Dynamic Programming", "medium", "Can string be segmented into dictionary words?", "DP with memo", "Google|Facebook"],
    [14, "Median of Two Sorted Arrays", "Binary Search", "hard", "Find median of two sorted arrays in O(log n)", "Binary search on smaller array", "Google|Apple"],
    [15, "Serialize/Deserialize Tree", "Trees", "hard", "Convert binary tree to string and back", "BFS with null markers", "Amazon|Facebook"],
    [16, "Trapping Rain Water", "Arrays", "hard", "Calculate water trapped between bars", "Precompute left/right max arrays", "Google|Amazon|Goldman Sachs"],
    [17, "N-Queens Problem", "Backtracking", "hard", "Place N queens on NxN board without attack", "Backtrack with column/diagonal sets", "Google|Uber"],
    [18, "Palindrome Linked List", "Linked List", "easy", "Check if linked list is a palindrome", "Find middle, reverse second half", "Microsoft|Adobe"],
    [19, "Climbing Stairs", "Dynamic Programming", "easy", "Count ways to climb n stairs (1 or 2 steps)", "dp[n] = dp[n-1] + dp[n-2]", "Amazon|TCS"],
    [20, "Rotate Image", "Arrays", "medium", "Rotate NxN matrix 90 degrees in-place", "Transpose then reverse rows", "Microsoft|Snapchat"],
]

with open("data/datasets/coding_questions.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "title", "topic", "difficulty", "description", "hint", "companies"])
    writer.writerows(coding_data)

print("✅ coding_questions.csv created")

# ── Interview Questions Dataset ────────────────────────────────────────────────
interview_data = [
    # id, question, type (HR/Technical), topic, difficulty, sample_answer_keywords
    [1, "Tell me about yourself.", "HR", "Introduction", "easy", "background|skills|goals|concise"],
    [2, "Why do you want to work at this company?", "HR", "Motivation", "easy", "research|values|growth|fit"],
    [3, "What are your strengths and weaknesses?", "HR", "Self-awareness", "easy", "honest|improvement|relevant"],
    [4, "Where do you see yourself in 5 years?", "HR", "Career Goals", "easy", "growth|learning|leadership|aligned"],
    [5, "Describe a challenging project you worked on.", "HR", "Behavioral", "medium", "situation|task|action|result|STAR"],
    [6, "How do you handle tight deadlines?", "HR", "Behavioral", "medium", "prioritize|communicate|calm|example"],
    [7, "Tell me about a time you worked in a team.", "HR", "Teamwork", "medium", "collaboration|conflict|resolution|outcome"],
    [8, "What is Object Oriented Programming?", "Technical", "OOP", "easy", "encapsulation|inheritance|polymorphism|abstraction"],
    [9, "Explain the difference between a list and a tuple in Python.", "Technical", "Python", "easy", "mutable|immutable|performance|use-case"],
    [10, "What is a RESTful API?", "Technical", "Web", "easy", "stateless|HTTP|endpoints|CRUD|JSON"],
    [11, "Explain normalization in databases.", "Technical", "Database", "medium", "1NF|2NF|3NF|redundancy|anomalies"],
    [12, "What is the difference between SQL and NoSQL?", "Technical", "Database", "medium", "structured|unstructured|scaling|ACID|examples"],
    [13, "Explain time and space complexity with an example.", "Technical", "DSA", "medium", "Big O|O(n)|O(log n)|trade-off|example"],
    [14, "What is machine learning? Explain supervised vs unsupervised.", "Technical", "ML", "medium", "labeled|unlabeled|classification|clustering|examples"],
    [15, "What is overfitting and how do you prevent it?", "Technical", "ML", "medium", "regularization|dropout|cross-validation|more-data"],
    [16, "Explain how Git branching works.", "Technical", "DevOps", "easy", "branch|merge|conflict|pull-request|workflow"],
    [17, "What is Docker and why is it used?", "Technical", "DevOps", "medium", "container|isolation|portability|image|compose"],
    [18, "Describe the SOLID principles.", "Technical", "OOP", "hard", "single-responsibility|open-closed|Liskov|interface|dependency"],
    [19, "What happens when you type a URL in a browser?", "Technical", "Networking", "hard", "DNS|TCP|HTTP|server|render|steps"],
    [20, "Design a URL shortener system.", "Technical", "System Design", "hard", "hashing|database|cache|scalability|API"],
]

with open("data/datasets/interview_questions.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "question", "type", "topic", "difficulty", "sample_answer_keywords"])
    writer.writerows(interview_data)

print("✅ interview_questions.csv created")
print("\n✅ All datasets created in data/datasets/")
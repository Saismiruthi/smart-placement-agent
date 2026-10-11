# test_skill_gap_agent.py

from agents.skill_gap_agent import SkillGapAgent
import json

def test_gap_analysis():
    agent = SkillGapAgent()

    # Simulated student skills from Phase 2 output
    student_skills = [
        "Python", "Machine Learning", "TensorFlow", "Pandas",
        "NumPy", "SQL", "Git", "HTML", "Flask"
    ]

    print("=" * 55)
    print("AVAILABLE JOB ROLES")
    print("=" * 55)
    for role in agent.get_available_roles():
        print(f"  • {role}")

    print("\n" + "=" * 55)
    print("BEST ROLE RECOMMENDATION")
    print("=" * 55)
    best = agent.recommend_best_role(student_skills)
    print(f"  Recommended role: {best}")

    print("\n" + "=" * 55)
    print("SKILL GAP ANALYSIS — Data Scientist")
    print("=" * 55)
    report = agent.analyze_gap(student_skills, "Data Scientist")

    print(f"\nReadiness Score : {report['readiness_score']}%")
    print(f"Target Salary   : {report['salary_lpa']} LPA")
    print(f"Summary         : {report['summary']}")

    print(f"\n✅ Matched Skills ({len(report['matched_skills'])}):")
    for m in report["matched_skills"]:
        print(f"   {m['required']} ← matched via '{m['matched_with']}' ({m['similarity']})")

    print(f"\n❌ Hard Gaps — Must Learn ({len(report['hard_gaps'])}):")
    for g in report["hard_gaps"]:
        print(f"   • {g}")

    print(f"\n⚠️  Soft Gaps — Strengthen ({len(report['soft_gaps'])}):")
    for g in report["soft_gaps"]:
        print(f"   • {g['required']} (closest: {g['closest_student_skill']}, sim: {g['similarity']})")

    print(f"\n📋 Learning Plan:\n{report['learning_plan']}")

if __name__ == "__main__":
    test_gap_analysis()
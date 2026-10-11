# test_coding_trainer.py

from agents.coding_trainer_agent import CodingTrainerAgent
from tools.db_manager import init_database

def test_coding_session():
    trainer = CodingTrainerAgent()
    student_id = "test_student_001"

    # ── Start session ─────────────────────────────────────────────
    session = trainer.start_session(student_id, initial_difficulty="easy")
    print("=" * 55)
    print("SESSION STARTED")
    print("=" * 55)
    print(f"  Difficulty : {session['current_difficulty']}")
    print(f"  Max Problems : {session['max_problems']}")

    # ── Simulate 3 problem attempts ───────────────────────────────
    skill_gaps = ["Dynamic Programming", "Arrays", "Graphs"]
    answers = [
        # Good answer — should score high
        "I would use a hashmap to store the complement of each number. "
        "Iterate through the array, for each element check if target - element "
        "exists in the map. Time complexity O(n), space O(n).",

        # Partial answer — medium score
        "Use a loop to check each pair of numbers until we find the answer.",

        # Weak answer — low score
        "I would brute force it by checking all combinations."
    ]

    for i, answer_text in enumerate(answers):
        print(f"\n{'─' * 55}")
        print(f"PROBLEM {i + 1}")
        print(f"{'─' * 55}")

        # Get next problem
        result = trainer.get_next_problem(student_id, skill_gaps=skill_gaps)

        if result.get("session_complete"):
            print("Session complete!")
            break

        problem = result["problem"]
        print(f"  Title      : {problem['title']}")
        print(f"  Topic      : {problem['topic']}")
        print(f"  Difficulty : {problem['difficulty']}")
        print(f"  Description: {problem['description']}")

        # Request hint before answering
        hint = trainer.get_hint(problem, hint_level=1)
        print(f"\n  {hint}")

        # Submit answer
        print(f"\n  Student answer: {answer_text[:80]}...")
        evaluation = trainer.evaluate_answer(student_id, problem, answer_text)

        print(f"\n  Score          : {evaluation['score']}")
        print(f"  Correct        : {evaluation['correct']}")
        print(f"  Feedback       : {evaluation['feedback']}")
        print(f"  Better Approach: {evaluation['better_approach']}")
        print(f"  Time Complexity: {evaluation['time_complexity']}")

        if evaluation.get("difficulty_changed"):
            print(f"\n  ⬆️  Difficulty updated to: {evaluation['current_difficulty']}")

    # ── End session ───────────────────────────────────────────────
    print(f"\n{'=' * 55}")
    print("SESSION SUMMARY")
    print("=" * 55)
    summary = trainer.end_session(student_id)
    print(f"  Problems Attempted : {summary['problems_attempted']}")
    print(f"  Average Score      : {summary['average_score']}")
    print(f"  Final Difficulty   : {summary['final_difficulty']}")
    print(f"  Performance Band   : {summary['performance_band']}")
    print(f"\n  Individual Scores:")
    for prob_id, score in summary["individual_scores"]:
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        print(f"    Problem {prob_id}: [{bar}] {score:.2f}")

if __name__ == "__main__":
    test_coding_session()
# test_interview_agent.py

from agents.interview_agent import InterviewAgent

def test_full_interview():
    agent      = InterviewAgent()
    student_id = "test_student_002"
    role       = "Data Scientist"
    skill_gaps = ["Machine Learning", "Statistics", "Python"]

    # ── Start interview ───────────────────────────────────────────
    print("=" * 60)
    print("MOCK INTERVIEW — DATA SCIENTIST")
    print("=" * 60)

    session_info = agent.start_interview(
        student_id  = student_id,
        target_role = role,
        mode        = "full"
    )

    print(f"\n🎙️  Interviewer: {session_info['opening_message']}")
    print(f"\n   Mode        : {session_info['mode'].upper()}")
    print(f"   HR Rounds   : {session_info['hr_questions']}")
    print(f"   Tech Rounds : {session_info['tech_questions']}")

    # ── Simulated student answers ─────────────────────────────────
    hr_answers = [
        ("Tell me about yourself.",
         "I am a final year B.Tech Computer Science student at Anna University "
         "with a CGPA of 8.5. I have strong programming skills in Python and have "
         "worked on machine learning projects including a sentiment analysis model "
         "and a customer churn prediction system during my internship at TechCorp. "
         "I am passionate about using data to solve real business problems and I am "
         "looking forward to growing as a data scientist in a collaborative team."),

        ("What are your strengths and weaknesses?",
         "My main strength is my ability to learn quickly — for example I taught "
         "myself PyTorch in two weeks to complete a deep learning project. I am also "
         "detail-oriented which helps me catch errors in data pipelines. My weakness "
         "is that I sometimes spend too much time perfecting work rather than shipping "
         "it, but I have been actively working on timeboxing my tasks to improve this."),

        ("Describe a challenging project you worked on.",
         "During my internship I was given a dataset with 40 percent missing values "
         "and asked to build a churn prediction model in two weeks. I first researched "
         "imputation strategies and chose KNN imputation based on the data distribution. "
         "I then built a gradient boosting model that achieved 87 percent accuracy. "
         "The result was deployed as a Flask API and is now used by the sales team "
         "to prioritize retention calls, reducing churn by 12 percent.")
    ]

    tech_answers = [
        ("What is machine learning?",
         "Machine learning is a subset of artificial intelligence where algorithms "
         "learn patterns from data without being explicitly programmed. In supervised "
         "learning we train on labeled data — for example training a model on historical "
         "house prices to predict future prices. In unsupervised learning we find hidden "
         "structure in unlabeled data such as customer segmentation using K-Means. "
         "The key idea is that the model generalizes from training examples to unseen data."),

        ("What is overfitting and how do you prevent it?",
         "Overfitting is when a model learns the training data too well including its "
         "noise and performs poorly on new data. You can see it when training accuracy "
         "is very high but validation accuracy is much lower. To prevent it I use "
         "techniques like L2 regularization to penalize large weights, dropout layers "
         "in neural networks, early stopping during training, and cross-validation to "
         "tune hyperparameters. Getting more training data also helps significantly.")
    ]

    asked_count = 0
    max_questions_to_demo = 5   # Limit for this test

    while asked_count < max_questions_to_demo:
        result = agent.get_next_question(
            student_id = student_id,
            skill_gaps = skill_gaps
        )

        # Round transition
        if result.get("round_transition"):
            print(f"\n{'─' * 60}")
            print(f"  {result['message']}")
            print(f"{'─' * 60}")
            continue

        # Interview complete signal
        if result.get("interview_complete"):
            break

        q        = result["question"]
        round_t  = result["current_round"]
        q_num    = result["question_number"]

        print(f"\n{'─' * 60}")
        print(f"[{round_t} ROUND — Q{q_num}]  Topic: {q['topic']}")
        print(f"{'─' * 60}")
        print(f"🎙️  {result['interviewer_intro']}")
        print(f"\n   {q['question']}")

        # Pick a prepared answer or use a generic fallback
        if round_t == "HR" and hr_answers:
            _, ans = hr_answers.pop(0)
        elif round_t == "Technical" and tech_answers:
            _, ans = tech_answers.pop(0)
        else:
            ans = (
                "I understand the concept but need more time to articulate "
                "a complete answer. Could you give me a moment to think?"
            )

        print(f"\n👤  Student: {ans[:120]}...")

        # Submit and get evaluation
        eval_result = agent.submit_answer(
            student_id     = student_id,
            question       = q,
            student_answer = ans
        )

        score = eval_result["final_score"]
        bar   = "█" * int(score * 10) + "░" * (10 - int(score * 10))

        print(f"\n📊  Score    : [{bar}] {score:.2f}")
        print(f"    Feedback : {eval_result['feedback'][:120]}")
        print(f"    Tip      : {eval_result['tip']}")

        if eval_result.get("star_used"):
            print(f"    STAR Used: {eval_result['star_used']}")
        if eval_result.get("missing_concepts"):
            print(f"    Missing  : {eval_result['missing_concepts']}")

        asked_count += 1

    # ── Final result ──────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("FINAL INTERVIEW RESULT")
    print("=" * 60)

    final = agent.finish_interview(student_id)

    hr_bar   = "█" * int(final["hr_score"] * 10) + "░" * (10 - int(final["hr_score"] * 10))
    tech_bar = "█" * int(final["technical_score"] * 10) + "░" * (10 - int(final["technical_score"] * 10))
    ov_bar   = "█" * int(final["overall_score"] * 10) + "░" * (10 - int(final["overall_score"] * 10))

    print(f"\n  HR Score       : [{hr_bar}]  {final['hr_score']:.2f}")
    print(f"  Tech Score     : [{tech_bar}]  {final['technical_score']:.2f}")
    print(f"  Overall Score  : [{ov_bar}]  {final['overall_score']:.2f}")
    print(f"\n  Decision       : {final['result']}")
    print(f"\n  🎙️  Interviewer: {final['closing_feedback']}")

if __name__ == "__main__":
    test_full_interview()
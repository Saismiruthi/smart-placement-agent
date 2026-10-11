# ui/pages/coding_practice.py

import streamlit as st

def render():
    st.title("💻 Coding Practice")
    st.markdown("Adaptive difficulty coding problems — the system adjusts based on your performance.")
    st.markdown("---")

    if not st.session_state.onboarding_done:
        st.warning("Please upload your resume first.")
        return

    planner    = st.session_state.planner
    student_id = st.session_state.student_id
    trainer    = planner.coding_agent

    # ── Session state for coding page ────────────────────────────
    if "coding_active"  not in st.session_state:
        st.session_state.coding_active  = False
    if "current_problem"not in st.session_state:
        st.session_state.current_problem= None
    if "hint_level"     not in st.session_state:
        st.session_state.hint_level     = 0
    if "last_eval"      not in st.session_state:
        st.session_state.last_eval      = None
    if "session_results"not in st.session_state:
        st.session_state.session_results= []

    # ── Start session ─────────────────────────────────────────────
    if not st.session_state.coding_active:
        st.markdown("### ⚙️ Session Settings")
        difficulty = st.radio(
            "Starting difficulty",
            ["easy", "medium", "hard"],
            horizontal = True
        )
        if st.button("▶️ Start Coding Session",
                     type="primary", use_container_width=True):
            trainer.start_session(student_id, initial_difficulty=difficulty)
            st.session_state.coding_active   = True
            st.session_state.current_problem = None
            st.session_state.session_results = []
            st.session_state.hint_level      = 0
            st.session_state.last_eval       = None
            st.rerun()
        return

    # ── Active session ────────────────────────────────────────────
    gap_report   = st.session_state.gap_report or {}
    weak_topics  = [g for g in gap_report.get("hard_gaps", [])]

    # Get next problem if none loaded
    if st.session_state.current_problem is None:
        result = trainer.get_next_problem(student_id, skill_gaps=weak_topics)
        if result.get("session_complete"):
            _show_session_summary(trainer, student_id)
            return
        st.session_state.current_problem = result["problem"]
        st.session_state.hint_level      = 0
        st.session_state.last_eval       = None

    problem = st.session_state.current_problem
    prog    = trainer.active_sessions.get(student_id)

    # Progress bar
    done  = prog.problems_this_session if prog else 0
    total = 5
    st.progress(done / total, text=f"Problem {done + 1} of {total}")

    # Difficulty badge
    diff_colors = {"easy": "🟢", "medium": "🟡", "hard": "🔴"}
    st.markdown(
        f"{diff_colors.get(problem['difficulty'], '⚪')} "
        f"**{problem['difficulty'].upper()}** | "
        f"Topic: **{problem['topic']}** | "
        f"Companies: {', '.join(problem['companies'][:3])}"
    )

    # Problem statement
    st.markdown(f"### {problem['title']}")
    st.info(problem["description"])

    # Hint system
    hint_col, _ = st.columns([1, 3])
    with hint_col:
        if st.button(f"💡 Hint (Level {st.session_state.hint_level + 1})"):
            st.session_state.hint_level = min(
                st.session_state.hint_level + 1, 3
            )
    if st.session_state.hint_level > 0:
        hint = trainer.get_hint(problem, st.session_state.hint_level)
        st.warning(hint)

    # Answer input
    st.markdown("### ✍️ Your Answer")
    st.caption(
        "Write your approach, algorithm, pseudo-code, or actual code. "
        "Explain your thinking — the AI evaluates your reasoning."
    )
    answer = st.text_area(
        "Type your answer here...",
        height     = 200,
        key        = f"answer_{problem['id']}",
        label_visibility = "collapsed"
    )

    submit_col, skip_col = st.columns([3, 1])
    with submit_col:
        if st.button("✅ Submit Answer",
                     type="primary", use_container_width=True):
            if not answer.strip():
                st.error("Please write an answer before submitting.")
            else:
                with st.spinner("🤖 Evaluating your answer..."):
                    evaluation = trainer.evaluate_answer(
                        student_id, problem, answer
                    )
                st.session_state.last_eval       = evaluation
                st.session_state.session_results.append({
                    "problem": problem["title"],
                    "score":   evaluation["score"]
                })
                st.session_state.current_problem = None
                st.rerun()

    with skip_col:
        if st.button("⏭️ Skip", use_container_width=True):
            if prog:
                prog.record_score(problem["id"], 0.0)
            st.session_state.current_problem = None
            st.rerun()

    # Show last evaluation
    if st.session_state.last_eval:
        ev    = st.session_state.last_eval
        score = ev["score"]
        st.markdown("---")
        st.markdown("### 📊 Last Answer Evaluation")

        col1, col2 = st.columns(2)
        with col1:
            color = "green" if score >= 0.7 else "orange" if score >= 0.4 else "red"
            st.markdown(
                f"<h2 style='color:{color}'>{score:.0%}</h2>",
                unsafe_allow_html=True
            )
            st.caption(f"Verdict: **{ev.get('correct', 'Unknown')}**")
        with col2:
            st.markdown(f"**Feedback:** {ev.get('feedback', '')}")
            st.markdown(f"**Better approach:** {ev.get('better_approach', '')}")
            st.markdown(f"**Time complexity:** {ev.get('time_complexity', '')}")

        if ev.get("difficulty_changed"):
            new_diff = ev.get("current_difficulty", "")
            st.success(f"🎯 Difficulty updated to **{new_diff}**!")


def _show_session_summary(trainer, student_id: str):
    """Display end-of-session summary."""
    summary = trainer.end_session(student_id)
    st.session_state.coding_active = False

    st.markdown("### 🏁 Session Complete!")
    st.markdown("---")

    m1, m2, m3 = st.columns(3)
    m1.metric("Problems Attempted", summary.get("problems_attempted", 0))
    m2.metric("Average Score",
              f"{summary.get('average_score', 0):.0%}")
    m3.metric("Performance",        summary.get("performance_band", ""))

    st.markdown("#### Individual Scores")
    for prob_id, score in summary.get("individual_scores", []):
        bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
        st.text(f"Problem {prob_id}: [{bar}] {score:.0%}")

    if st.button("🔄 Start New Session",
                 type="primary", use_container_width=True):
        st.session_state.coding_active   = False
        st.session_state.current_problem = None
        st.rerun()
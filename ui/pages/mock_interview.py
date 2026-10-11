# ui/pages/mock_interview.py

import streamlit as st

def render():
    st.title("🎙️ Mock Interview")
    st.markdown(
        "Simulate a real placement interview with AI-powered "
        "evaluation on HR and Technical rounds."
    )
    st.markdown("---")

    if not st.session_state.onboarding_done:
        st.warning("Please upload your resume first.")
        return

    student_id  = st.session_state.student_id
    target_role = st.session_state.target_role or "Software Development Engineer"
    agent       = st.session_state.planner.interview_agent

    # ── Interview session state ───────────────────────────────────
    for key, default in [
        ("iv_active",    False),
        ("iv_question",  None),
        ("iv_history",   []),
        ("iv_round",     "HR"),
        ("iv_last_eval", None),
    ]:
        if key not in st.session_state:
            st.session_state[key] = default

    # ── Setup ─────────────────────────────────────────────────────
    if not st.session_state.iv_active:
        st.markdown("### ⚙️ Interview Settings")

        mode = st.radio(
            "Interview mode",
            ["full (HR + Technical)", "hr only", "technical only"],
            horizontal = True
        )
        mode_map = {
            "full (HR + Technical)": "full",
            "hr only":               "hr",
            "technical only":        "technical"
        }

        st.info(
            f"**Target Role:** {target_role}  \n"
            f"**HR Questions:** 5  |  **Technical Questions:** 5"
        )

        if st.button("🎙️ Start Interview",
                     type="primary", use_container_width=True):
            info = agent.start_interview(
                student_id  = student_id,
                target_role = target_role,
                mode        = mode_map[mode]
            )
            st.session_state.iv_active   = True
            st.session_state.iv_history  = []
            st.session_state.iv_question = None
            st.session_state.iv_last_eval= None
            st.session_state.iv_round    = info["current_round"]

            st.markdown(f"### 🎙️ Interviewer")
            st.info(info["opening_message"])
            st.rerun()
        return

    # ── Active interview ──────────────────────────────────────────
    gap_report  = st.session_state.gap_report or {}
    weak_topics = gap_report.get("hard_gaps", [])
    asked_ids   = {e["question_id"] for e in st.session_state.iv_history}

    # Get next question
    if st.session_state.iv_question is None:
        q_result = agent.get_next_question(
            student_id = student_id,
            skill_gaps = weak_topics,
            asked_ids  = asked_ids
        )

        if q_result.get("round_transition"):
            st.success(q_result["message"])
            st.session_state.iv_round    = q_result["current_round"]
            st.session_state.iv_question = None
            st.rerun()

        if q_result.get("interview_complete"):
            _show_interview_result(agent, student_id)
            return

        st.session_state.iv_question = q_result["question"]
        st.session_state.iv_round    = q_result["current_round"]

    question = st.session_state.iv_question

    # Round + progress indicator
    round_emoji = "👔" if st.session_state.iv_round == "HR" else "💻"
    st.markdown(
        f"{round_emoji} **{st.session_state.iv_round} Round** | "
        f"Question {len(st.session_state.iv_history) + 1} | "
        f"Topic: **{question['topic']}** | "
        f"Difficulty: **{question['difficulty']}**"
    )

    # Conversation history (collapsible)
    if st.session_state.iv_history:
        with st.expander(
            f"📜 Interview History ({len(st.session_state.iv_history)} Q&A)", False
        ):
            for entry in st.session_state.iv_history[-3:]:
                st.markdown(f"**Q:** {entry['question']}")
                st.markdown(f"**You:** {entry['answer'][:120]}...")
                score = entry["score"]
                color = "green" if score >= 0.7 else "orange" if score >= 0.4 else "red"
                st.markdown(
                    f"**Score:** <span style='color:{color}'>{score:.0%}</span>",
                    unsafe_allow_html=True
                )
                st.markdown("---")

    # Current question
    st.markdown("### 🎙️ Interviewer asks:")
    st.info(f"**{question['question']}**")

    st.caption(
        "Speak naturally. For HR questions use the STAR method. "
        "For technical questions explain step-by-step."
    )

    answer = st.text_area(
        "Your answer...",
        height           = 180,
        key              = f"iv_ans_{question['id']}",
        label_visibility = "collapsed"
    )

    c1, c2 = st.columns([3, 1])
    with c1:
        if st.button("✅ Submit Answer",
                     type="primary", use_container_width=True):
            if not answer.strip():
                st.error("Please provide an answer.")
            else:
                with st.spinner("Evaluating..."):
                    evaluation = agent.submit_answer(
                        student_id     = student_id,
                        question       = question,
                        student_answer = answer
                    )

                # Record in history
                st.session_state.iv_history.append({
                    "question_id": question["id"],
                    "question":    question["question"],
                    "answer":      answer,
                    "score":       evaluation["final_score"],
                    "feedback":    evaluation.get("feedback", ""),
                    "round":       st.session_state.iv_round
                })
                st.session_state.iv_last_eval = evaluation
                st.session_state.iv_question  = None

                if evaluation.get("interview_complete"):
                    _show_interview_result(agent, student_id)
                else:
                    st.rerun()

    with c2:
        if st.button("⏭️ Skip", use_container_width=True):
            agent.submit_answer(student_id, question, "I need to skip this question.")
            st.session_state.iv_question = None
            st.rerun()

    # Last evaluation panel
    if st.session_state.iv_last_eval:
        ev    = st.session_state.iv_last_eval
        score = ev["final_score"]
        st.markdown("---")
        st.markdown("### 📊 Previous Answer Feedback")
        col1, col2 = st.columns(2)
        with col1:
            color = "green" if score >= 0.7 else "orange" if score >= 0.4 else "red"
            st.markdown(
                f"<h3 style='color:{color}'>{score:.0%}</h3>",
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(f"**Feedback:** {ev.get('feedback', '')[:150]}")
            st.markdown(f"**Tip:** {ev.get('tip', '')}")


def _show_interview_result(agent, student_id: str):
    """Display the final interview result."""
    result = agent.finish_interview(student_id)
    st.session_state.iv_active = False

    st.markdown("### 🏁 Interview Complete!")
    st.markdown("---")

    passed = result.get("passed", False)
    if passed:
        st.success(f"## {result.get('result', 'SELECTED ✅')}")
    else:
        st.error(f"## {result.get('result', 'NEEDS MORE PREP ❌')}")

    m1, m2, m3 = st.columns(3)
    m1.metric("HR Score",       f"{result.get('hr_score', 0):.0%}")
    m2.metric("Tech Score",     f"{result.get('technical_score', 0):.0%}")
    m3.metric("Overall Score",  f"{result.get('overall_score', 0):.0%}")

    st.markdown("---")
    st.markdown(f"🎙️ **Interviewer:** {result.get('closing_feedback', '')}")

    if st.button("🔄 Take Another Interview",
                 type="primary", use_container_width=True):
        st.session_state.iv_active   = False
        st.session_state.iv_history  = []
        st.session_state.iv_question = None
        st.rerun()
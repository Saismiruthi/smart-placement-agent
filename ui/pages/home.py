# ui/pages/home.py

import streamlit as st

def render():
    st.title("🎯 Smart Placement Preparation Agent")
    st.markdown(
        "##### Your personal AI-powered placement mentor — "
        "adaptive, intelligent, and personalized."
    )
    st.markdown("---")

    # Feature cards
    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("### 📄 Resume Analysis")
        st.markdown(
            "Upload your PDF resume. The AI extracts your skills, "
            "identifies your profile, and builds a structured student model."
        )

    with col2:
        st.markdown("### 📊 Skill Gap Detection")
        st.markdown(
            "Compare your skills against industry requirements. "
            "See exactly what is missing for your target role."
        )

    with col3:
        st.markdown("### 💻 Adaptive Coding Practice")
        st.markdown(
            "Practice coding problems that adapt to your level. "
            "Difficulty increases as you improve — just like a real interview."
        )

    st.markdown("---")
    col4, col5, col6 = st.columns(3)

    with col4:
        st.markdown("### 🎙️ Mock Interviews")
        st.markdown(
            "Simulate real HR and technical interviews. "
            "Get scored on communication, correctness, and depth."
        )

    with col5:
        st.markdown("### 📈 Performance Analytics")
        st.markdown(
            "Track your progress across all sessions. "
            "See trends, weak areas, and improvement over time."
        )

    with col6:
        st.markdown("### 🧠 AI Memory")
        st.markdown(
            "The system remembers your weaknesses across sessions "
            "and personalizes every future session automatically."
        )

    st.markdown("---")

    # Getting started
    if not st.session_state.onboarding_done:
        st.info(
            "👆 Get started by uploading your resume in **Resume Upload**. "
            "The system will analyze it and unlock all features."
        )
        if st.button("📄 Upload Resume Now", type="primary"):
            st.session_state.current_page = "Resume"
            st.rerun()
    else:
        st.success(
            f"Welcome back, **{st.session_state.student_name}**! "
            f"Ready to continue your preparation?"
        )
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("💻 Practice Coding", use_container_width=True):
                st.session_state.current_page = "Coding"
                st.rerun()
        with c2:
            if st.button("🎙️ Mock Interview", use_container_width=True):
                st.session_state.current_page = "Interview"
                st.rerun()
        with c3:
            if st.button("📈 View Analytics", use_container_width=True):
                st.session_state.current_page = "Analytics"
                st.rerun()
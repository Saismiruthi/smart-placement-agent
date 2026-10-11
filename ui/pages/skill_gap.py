# ui/pages/skill_gap.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

def render():
    st.title("📊 Skill Gap Report")
    st.markdown("---")

    if not st.session_state.onboarding_done:
        st.warning("Please upload your resume first.")
        return

    report = st.session_state.gap_report
    if not report:
        st.warning("No gap report found. Please re-upload your resume.")
        return

    planner = st.session_state.planner

    # Refresh gap if needed
    if st.button("🔄 Refresh Analysis"):
        from agents.skill_gap_agent import SkillGapAgent
        from tools.db_manager import get_student_profile
        profile    = get_student_profile(st.session_state.student_id)
        agent      = SkillGapAgent()
        gap        = agent.analyze_gap(
            profile.get("skill_names", []),
            st.session_state.target_role
        )
        st.session_state.gap_report = {**report, **gap}
        report = st.session_state.gap_report
        st.rerun()

    # ── Readiness gauge ───────────────────────────────────────────
    readiness = report["readiness_score"]
    st.markdown(f"### 🎯 Placement Readiness: **{readiness}%**")

    fig = go.Figure(go.Indicator(
        mode   = "gauge+number",
        value  = readiness,
        domain = {"x": [0, 1], "y": [0, 1]},
        gauge  = {
            "axis":  {"range": [0, 100]},
            "bar":   {"color": "#2ECC71" if readiness >= 70
                               else "#F39C12" if readiness >= 45
                               else "#E74C3C"},
            "steps": [
                {"range": [0,  45],  "color": "#FADBD8"},
                {"range": [45, 70],  "color": "#FDEBD0"},
                {"range": [70, 100], "color": "#D5F5E3"},
            ],
            "threshold": {
                "line":  {"color": "black", "width": 3},
                "thickness": 0.75,
                "value": 60
            }
        }
    ))
    fig.update_layout(height=280, margin=dict(t=20, b=20))
    st.plotly_chart(fig, use_container_width=True)

    # ── Gap summary columns ───────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### ❌ Critical Gaps (Must Learn)")
        if report["hard_gaps"]:
            for gap in report["hard_gaps"]:
                st.error(f"**{gap}**")
        else:
            st.success("No critical gaps!")

    with col2:
        st.markdown("### ⚠️ Skills to Strengthen")
        soft = report.get("soft_gaps", [])
        if soft:
            for s in soft:
                st.warning(f"**{s}**")
        else:
            st.success("All required skills covered!")

    # ── Skills radar chart ────────────────────────────────────────
    st.markdown("### 🕸️ Skills Coverage by Category")
    from tools.db_manager import get_student_profile

    profile    = get_student_profile(st.session_state.student_id)
    have_skills= set(profile.get("skill_names", []))

    categories = {
        "Programming":  ["Python", "Java", "C++", "JavaScript"],
        "ML/Data":      ["Machine Learning", "Deep Learning", "Statistics",
                         "Pandas", "NumPy"],
        "Web/API":      ["HTML", "CSS", "React", "REST API", "Flask"],
        "Databases":    ["SQL", "MySQL", "MongoDB", "PostgreSQL"],
        "DevOps":       ["Docker", "Git", "AWS", "CI/CD", "Linux"],
    }

    radar_cats   = list(categories.keys())
    radar_scores = []
    for cat, cat_skills in categories.items():
        matched = sum(1 for s in cat_skills if s in have_skills)
        radar_scores.append(round(matched / len(cat_skills) * 100))

    fig2 = go.Figure(go.Scatterpolar(
        r     = radar_scores + [radar_scores[0]],
        theta = radar_cats   + [radar_cats[0]],
        fill  = "toself",
        fillcolor = "rgba(52, 152, 219, 0.2)",
        line  = dict(color="#3498DB", width=2),
        name  = "Your Coverage"
    ))
    fig2.update_layout(
        polar  = dict(radialaxis=dict(visible=True, range=[0, 100])),
        height = 380,
        margin = dict(t=30, b=30)
    )
    st.plotly_chart(fig2, use_container_width=True)

    # ── Learning plan ─────────────────────────────────────────────
    st.markdown("### 📋 Personalized Learning Plan")
    st.info(report.get("learning_plan", ""))

    # ── Navigation ────────────────────────────────────────────────
    st.markdown("---")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("💻 Start Coding Practice →",
                     type="primary", use_container_width=True):
            st.session_state.current_page = "Coding"
            st.rerun()
    with c2:
        if st.button("🎙️ Start Mock Interview →",
                     use_container_width=True):
            st.session_state.current_page = "Interview"
            st.rerun()
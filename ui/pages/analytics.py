# ui/pages/analytics.py

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

def render():
    st.title("📈 Performance Analytics")
    st.markdown("---")

    if not st.session_state.onboarding_done:
        st.warning("Please upload your resume first.")
        return

    student_id = st.session_state.student_id
    planner    = st.session_state.planner

    with st.spinner("Loading analytics..."):
        try:
            dashboard = planner.get_student_dashboard(student_id)
        except Exception as e:
            # If ChromaDB has stale data, reset and retry once
            try:
                planner.memory_agent.forget_student(student_id)
                dashboard = planner.get_student_dashboard(student_id)
            except Exception as e2:
                st.error(f"Analytics error: {e2}")
                return

    if dashboard.get("status") == "not_found":
        st.warning(dashboard["message"])
        return

    # ── Overall readiness ─────────────────────────────────────────
    score = dashboard["overall_readiness"]
    band  = dashboard["readiness_band"]

    st.markdown(f"### {band}")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Overall Readiness", f"{score:.0%}")
    col2.metric("Sessions Done",     dashboard["sessions_done"])
    col3.metric("Weak Areas",        len(dashboard["weak_topics"]))
    col4.metric("Strong Areas",      len(dashboard["strong_topics"]))

    # ── Coding performance chart ──────────────────────────────────
    coding = dashboard.get("coding_summary", {})
    if coding.get("sessions", 0) > 0:
        st.markdown("### 💻 Coding Progress")
        scores = coding.get("all_scores", [])
        if scores:
            fig = px.line(
                x     = list(range(1, len(scores) + 1)),
                y     = [s * 100 for s in scores],
                title = "Coding Session Scores Over Time",
                labels= {"x": "Session", "y": "Score (%)"}
            )
            fig.add_hline(y=70, line_dash="dash",
                          line_color="green",
                          annotation_text="Target: 70%")
            fig.update_layout(height=300)
            st.plotly_chart(fig, use_container_width=True)

        c1, c2, c3 = st.columns(3)
        c1.metric("Average Score",  f"{coding.get('average_score', 0):.0%}")
        c2.metric("Best Score",     f"{coding.get('best_score', 0):.0%}")
        c3.metric("Latest Band",    coding.get("performance_band", ""))

    # ── Interview performance chart ───────────────────────────────
    interview = dashboard.get("interview_summary", {})
    if interview.get("sessions", 0) > 0:
        st.markdown("### 🎙️ Interview Performance")

        # HR vs Technical bar chart
        fig2 = go.Figure(data=[
            go.Bar(name="HR Score",
                   x=["Score"],
                   y=[interview.get("average_hr_score", 0) * 100],
                   marker_color="#3498DB"),
            go.Bar(name="Technical Score",
                   x=["Score"],
                   y=[interview.get("average_tech_score", 0) * 100],
                   marker_color="#E74C3C"),
        ])
        fig2.update_layout(
            barmode = "group",
            yaxis   = dict(range=[0, 100], title="Score (%)"),
            height  = 280,
            title   = "HR vs Technical Average Scores"
        )
        st.plotly_chart(fig2, use_container_width=True)

        # Topic breakdown
        topic_scores = interview.get("topic_scores", {})
        if topic_scores:
            st.markdown("#### Topic Breakdown")
            sorted_topics = sorted(
                topic_scores.items(), key=lambda x: x[1]
            )
            topics = [t for t, _ in sorted_topics]
            vals   = [v * 100 for _, v in sorted_topics]
            colors = [
                "#E74C3C" if v < 50
                else "#F39C12" if v < 75
                else "#2ECC71"
                for v in vals
            ]
            fig3 = go.Figure(go.Bar(
                x             = vals,
                y             = topics,
                orientation   = "h",
                marker_color  = colors
            ))
            fig3.add_vline(x=70, line_dash="dash",
                           line_color="green")
            fig3.update_layout(
                height = max(250, len(topics) * 40),
                xaxis  = dict(range=[0, 100], title="Score (%)")
            )
            st.plotly_chart(fig3, use_container_width=True)

    # ── Weak and strong areas ─────────────────────────────────────
    st.markdown("### 🎯 Focus Areas")
    col_w, col_s = st.columns(2)

    with col_w:
        st.markdown("**❌ Needs Work**")
        for area in dashboard.get("weak_topics", []):
            st.error(area)
        if not dashboard.get("weak_topics"):
            st.success("No weak areas identified yet!")

    with col_s:
        st.markdown("**✅ Strong Areas**")
        for area in dashboard.get("strong_topics", []):
            st.success(area)
        if not dashboard.get("strong_topics"):
            st.info("Complete more sessions to identify strengths.")

    # ── Improvement suggestions ───────────────────────────────────
    st.markdown("### 💡 Improvement Suggestions")
    for i, tip in enumerate(dashboard.get("suggestions", []), 1):
        st.markdown(f"**{i}.** {tip}")

    # ── Mentor brief ──────────────────────────────────────────────
    brief = dashboard.get("mentor_brief", "")
    if brief:
        st.markdown("### 🧠 AI Mentor's Assessment")
        st.info(brief)
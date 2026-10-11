# ui/pages/roadmap.py

import streamlit as st

def render():
    st.title("🗺️ Learning Roadmap")
    st.markdown(
        "A personalized week-by-week preparation plan "
        "generated based on your skill profile and history."
    )
    st.markdown("---")

    if not st.session_state.onboarding_done:
        st.warning("Please upload your resume first.")
        return

    student_id  = st.session_state.student_id
    target_role = st.session_state.target_role
    planner     = st.session_state.planner

    col1, col2 = st.columns(2)
    with col1:
        role = st.selectbox(
            "Target Role",
            options = [
                "Software Development Engineer", "Data Scientist",
                "Data Analyst", "Frontend Developer", "Backend Developer",
                "Full Stack Developer", "Machine Learning Engineer",
                "DevOps Engineer", "AI Engineer",
            ],
            index   = 0
        )
    with col2:
        weeks = st.slider("Roadmap duration (weeks)", 4, 12, 8)

    if st.button("🗺️ Generate My Roadmap",
                 type="primary", use_container_width=True):
        with st.spinner("🤖 Generating personalized roadmap..."):
            roadmap = planner.generate_roadmap(student_id, role, weeks)

        st.markdown("---")
        st.markdown(f"### 📅 {weeks}-Week Roadmap for **{role}**")

        # Parse and display week by week
        week_blocks = roadmap.split("WEEK ")[1:]
        for block in week_blocks:
            lines  = block.strip().split("\n")
            header = lines[0] if lines else "Week"
            body   = "\n".join(lines[1:]) if len(lines) > 1 else ""

            with st.expander(f"📅 WEEK {header}", expanded=False):
                for line in body.split("\n"):
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("Focus:"):
                        st.markdown(f"🎯 **{line}**")
                    elif line.startswith("Coding:"):
                        st.markdown(f"💻 {line}")
                    elif line.startswith("Interview Prep:"):
                        st.markdown(f"🎙️ {line}")
                    elif line.startswith("Goal:"):
                        st.success(f"✅ {line}")
                    else:
                        st.markdown(line)

        # Download button
        st.download_button(
            label     = "⬇️ Download Roadmap as Text",
            data      = roadmap,
            file_name = f"placement_roadmap_{role.replace(' ', '_')}.txt",
            mime      = "text/plain"
        )
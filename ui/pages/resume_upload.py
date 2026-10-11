# ui/pages/resume_upload.py

import streamlit as st

def render():
    st.title("📄 Resume Upload & Analysis")
    st.markdown(
        "Upload your PDF resume. The AI will extract your skills, "
        "build your profile, and prepare your learning plan."
    )
    st.markdown("---")

    # Role selector
    roles = [
        "Software Development Engineer", "Data Scientist",
        "Data Analyst", "Frontend Developer", "Backend Developer",
        "Full Stack Developer", "Machine Learning Engineer",
        "DevOps Engineer", "Cloud Engineer", "AI Engineer",
    ]
    target_role = st.selectbox(
        "🎯 Select your target job role",
        options   = roles,
        index     = 0,
        help      = "This is the role you are preparing for. "
                    "You can change it later."
    )

    # File uploader
    uploaded_file = st.file_uploader(
        "📎 Upload your resume (PDF only)",
        type    = ["pdf"],
        help    = "Your resume will be analyzed locally. "
                  "No data is sent to external servers."
    )

    # Demo mode
    st.markdown("---")
    st.markdown("#### 🧪 No resume? Use a demo profile")
    demo_col1, demo_col2, demo_col3 = st.columns(3)

    demo_selected = None
    with demo_col1:
        if st.button("👤 Beginner\n(5 skills)", use_container_width=True):
            demo_selected = "beginner"
    with demo_col2:
        if st.button("👤 Intermediate\n(9 skills)", use_container_width=True):
            demo_selected = "intermediate"
    with demo_col3:
        if st.button("👤 Advanced\n(15 skills)", use_container_width=True):
            demo_selected = "advanced"

    # ── Process uploaded file ─────────────────────────────────────
    if uploaded_file and st.button(
        "🚀 Analyze My Resume", type="primary", use_container_width=True
    ):
        _process_resume(uploaded_file, target_role)

    # ── Process demo profile ──────────────────────────────────────
    if demo_selected:
        _load_demo_profile(demo_selected, target_role)


def _process_resume(uploaded_file, target_role: str):
    """Run the full onboarding pipeline on an uploaded file."""
    planner = st.session_state.planner

    with st.spinner("🔍 Analyzing your resume..."):
        try:
            report = planner.onboard_student(
                uploaded_file = uploaded_file,
                target_role   = target_role
            )
            _save_and_display(report)
        except Exception as e:
            st.error(f"❌ Resume analysis failed: {e}")
            st.info(
                "Make sure Ollama is running: `ollama serve` "
                "and your resume is a valid PDF."
            )


def _load_demo_profile(level: str, target_role: str):
    """Load a pre-built demo student persona."""
    import json
    from pathlib import Path
    from tools.db_manager import init_database, save_student_profile
    from agents.skill_gap_agent import SkillGapAgent

    id_map = {
        "beginner":     "student_beginner_001",
        "intermediate": "student_intermediate_002",
        "advanced":     "student_advanced_003"
    }
    student_id  = id_map[level]
    profile_path= Path(f"data/student_profiles/{student_id}.json")

    if not profile_path.exists():
        st.error(
            "Demo profiles not found. "
            "Run `python data/generate_datasets.py` first."
        )
        return

    with st.spinner(f"Loading {level} demo profile..."):
        with open(profile_path) as f:
            persona = json.load(f)

        init_database()
        skills_data = {
            "matched_skills":    persona["skills"],
            "skills_by_category":{"general": persona["skills"]},
            "confidence_scores": {s: 0.90 for s in persona["skills"]}
        }
        save_student_profile(
            persona["student_id"],
            {"name": persona["name"], "email": persona["email"],
             "phone": persona["phone"], "linkedin": ""},
            skills_data
        )

        gap_agent  = SkillGapAgent()
        gap_report = gap_agent.analyze_gap(persona["skills"], target_role)

        report = {
            "student_id":         persona["student_id"],
            "personal_info":      {"name": persona["name"],
                                   "email": persona["email"]},
            "total_skills_found": len(persona["skills"]),
            "skills_by_category": {"general": persona["skills"]},
            "target_role":        target_role,
            "readiness_score":    gap_report["readiness_score"],
            "hard_gaps":          gap_report["hard_gaps"],
            "soft_gaps":          [g["required"] for g in gap_report["soft_gaps"]],
            "learning_plan":      gap_report["learning_plan"],
            "summary":            gap_report["summary"],
            "next_steps":         []
        }
        _save_and_display(report)


def _save_and_display(report: dict):
    """Save report to session state and display results."""
    st.session_state.student_id      = report["student_id"]
    st.session_state.student_name    = report["personal_info"].get("name", "Student")
    st.session_state.target_role     = report["target_role"]
    st.session_state.onboarding_done = True
    st.session_state.gap_report      = report

    # Clear stale ChromaDB memory for this student so
    # consolidate_memories always starts clean on re-upload
    try:
        planner = st.session_state.planner
        if planner:
            planner.memory_agent.forget_student(report["student_id"])
    except Exception:
        pass   # Non-critical — continue even if memory reset fails

    st.success(f"✅ Analysis complete for **{st.session_state.student_name}**!")
    st.markdown("---")

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Skills Found",    report["total_skills_found"])
    m2.metric("Readiness Score", f"{report['readiness_score']}%")
    m3.metric("Critical Gaps",   len(report["hard_gaps"]))
    m4.metric("Target Role",     report["target_role"][:18])

    # Skills by category
    st.markdown("### 🧩 Skills Detected")
    cols = st.columns(3)
    for i, (cat, skills) in enumerate(
        report["skills_by_category"].items()
    ):
        with cols[i % 3]:
            st.markdown(f"**{cat.replace('_', ' ').title()}**")
            for skill in skills:
                st.markdown(f"- {skill}")

    # Gap overview
    st.markdown("### ❌ Critical Skill Gaps")
    if report["hard_gaps"]:
        gap_cols = st.columns(3)
        for i, gap in enumerate(report["hard_gaps"]):
            with gap_cols[i % 3]:
                st.error(f"  {gap}")
    else:
        st.success("No critical gaps! You have all required skills.")

    # Learning plan
    st.markdown("### 📋 Initial Learning Plan")
    st.info(report.get("learning_plan", "Learning plan will be generated."))

    st.markdown("---")
    if st.button(
        "📊 View Full Skill Gap Report →",
        type = "primary",
        use_container_width = True
    ):
        st.session_state.current_page = "SkillGap"
        st.rerun()
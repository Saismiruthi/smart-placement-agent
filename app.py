# app.py — Streamlit application entry point

import streamlit as st
from pathlib import Path

# ── Page config — must be first Streamlit call ────────────────────────────────
st.set_page_config(
    page_title  = "Smart Placement Agent",
    page_icon   = "🎯",
    layout      = "wide",
    initial_sidebar_state = "expanded"
)

# ── Session state initialization ──────────────────────────────────────────────
def init_session():
    defaults = {
        "student_id":       None,
        "student_name":     None,
        "target_role":      None,
        "onboarding_done":  False,
        "current_page":     "Home",
        "gap_report":       None,
        "coding_session":   None,
        "interview_session":None,
        "planner":          None,
        "profile":          None,
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val

init_session()

# ── Lazy-load Planner Agent (cached so it loads only once) ────────────────────
@st.cache_resource(show_spinner="Loading AI agents — please wait...")
def load_planner():
    from agents.planner_agent import PlannerAgent
    return PlannerAgent()

# ── Sidebar navigation ────────────────────────────────────────────────────────
def render_sidebar():
    with st.sidebar:
        st.markdown("## 🎯 Smart Placement Agent")
        st.markdown("---")

        if st.session_state.student_name:
            st.success(f"👤 {st.session_state.student_name}")
            st.caption(f"🎯 {st.session_state.target_role or 'Role not set'}")
            st.markdown("---")

        pages = {
            "🏠 Home":              "Home",
            "📄 Resume Upload":     "Resume",
            "📊 Skill Gap Report":  "SkillGap",
            "💻 Coding Practice":   "Coding",
            "🎙️ Mock Interview":    "Interview",
            "📈 Analytics":         "Analytics",
            "🗺️ Roadmap":           "Roadmap",
        }

        for label, page_key in pages.items():
            # Disable pages that need onboarding
            needs_onboard = page_key not in ("Home", "Resume")
            disabled      = needs_onboard and not st.session_state.onboarding_done

            if st.button(
                label,
                use_container_width = True,
                disabled            = disabled,
                key                 = f"nav_{page_key}"
            ):
                st.session_state.current_page = page_key
                st.rerun()

        st.markdown("---")
        st.caption("Powered by Ollama (phi3) + CrewAI")

# ── Page router ───────────────────────────────────────────────────────────────
def main():
    render_sidebar()

    # Load planner into session state
    if st.session_state.planner is None:
        st.session_state.planner = load_planner()

    page = st.session_state.current_page

    if page == "Home":
        from ui.pages.home import render
        render()
    elif page == "Resume":
        from ui.pages.resume_upload import render
        render()
    elif page == "SkillGap":
        from ui.pages.skill_gap import render
        render()
    elif page == "Coding":
        from ui.pages.coding_practice import render
        render()
    elif page == "Interview":
        from ui.pages.mock_interview import render
        render()
    elif page == "Analytics":
        from ui.pages.analytics import render
        render()
    elif page == "Roadmap":
        from ui.pages.roadmap import render
        render()

if __name__ == "__main__":
    main()
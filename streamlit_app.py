"""
streamlit_app.py
AI Meal Planner — entry point
Run with: streamlit run streamlit_app.py
"""

import streamlit as st
from src.meal_generator import generate_meal_plan
from ui.profile_form import render_profile_form
from ui.results import render_results, show_profile
from ui.styles import load_css

st.set_page_config(
    page_title="AI Meal Planner",
    page_icon="🥗",
    layout="wide",
)

load_css()

st.markdown("""
<div class="hero">
    <h1>🥗 AI Meal Planner</h1>
    <p>Personalized 7-day plans built from your goals, restrictions, and what's in your kitchen.</p>
</div>
""", unsafe_allow_html=True)

user_profile, generate_clicked = render_profile_form()

st.markdown("<hr>", unsafe_allow_html=True)

# Show profile preview before first generation
if not generate_clicked and "meal_data" not in st.session_state:
    show_profile(user_profile)
    st.info("Fill in your preferences above and click Generate.")

# Run the pipeline
if generate_clicked:
    with st.spinner("Retrieving recipes and generating your plan..."):
        try:
            meal_data = generate_meal_plan(user_profile, n_recipes=12)
            st.session_state["meal_data"] = meal_data
            st.session_state["user_profile"] = user_profile
        except Exception:
            st.warning("Couldn't generate a plan right now. Make sure Ollama is running and try again.")
            st.stop()

# Show results
if "meal_data" in st.session_state:
    render_results(st.session_state["meal_data"], st.session_state["user_profile"])
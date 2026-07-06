import streamlit as st
from ui.styles import metric_card, allergen_chips, section_label, status_badge
from utils.feedback import log_feedback


def show_profile(user_profile):
    section_label("Your Profile")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Goal", user_profile["goal"])
    with col2:
        metric_card("Calories", f"{user_profile['daily_calories']} kcal")
    with col3:
        metric_card("Budget", f"${user_profile['budget']}/wk")
    with col4:
        metric_card("Diet", user_profile["diet"])

    allergen_chips(user_profile.get("allergies", []))


def show_meal_plan_tab(meal_plan):
    section_label("7-Day Plan")
    st.markdown(
        f'<div class="plan-box">{meal_plan}</div>',
        unsafe_allow_html=True,
    )


def show_recipes_tab(retrieved_recipes):
    section_label("Recipes retrieved from database")
    st.caption("The model can only recommend from this list.")

    for recipe in retrieved_recipes:
        meta = recipe["metadata"]
        with st.expander(f"{meta['name']}  —  {meta['calories']} kcal  ·  {meta['protein_g']}g protein"):
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Calories", meta["calories"])
            col2.metric("Protein",  f"{meta['protein_g']}g")
            col3.metric("Carbs",    f"{meta['carbs_g']}g")
            col4.metric("Fat",      f"{meta['fat_g']}g")

            st.markdown(f"**Meal type:** {meta['meal_type']}")
            st.markdown(f"**Tags:** {meta.get('tags', '—')}")

            allergens = meta.get("allergens", "none")
            if allergens and allergens != "none":
                st.warning(f"Contains: {allergens}")
            else:
                st.success("No major allergens")


def show_feedback_tab(user_profile, meal_plan):
    section_label("Was this plan helpful?")
    st.caption("Your feedback is saved locally and can be used to improve the eval dataset.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("Looks good"):
            log_feedback(user_profile, meal_plan, rating="positive")
            st.success("Logged. thanks!")
    with col2:
        if st.button("Needs work"):
            log_feedback(user_profile, meal_plan, rating="negative")
            st.warning("Logged. noted.")

    note = st.text_area(
        "What would you change?",
        placeholder="Too repetitive, wrong calorie range, missing snacks...",
        height=80,
    )
    if note and st.button("Save note"):
        log_feedback(user_profile, meal_plan, rating="note", note=note)
        st.success("Note saved.")


def render_results(meal_data, user_profile):
    plan = meal_data["meal_plan"]

    status_badge(success="ERROR" not in plan)
    show_profile(user_profile)
    st.markdown("<hr>", unsafe_allow_html=True)

    tab1, tab2, tab3 = st.tabs(["Meal Plan", "Retrieved Recipes", "Feedback"])

    with tab1:
        show_meal_plan_tab(plan)
    with tab2:
        show_recipes_tab(meal_data["retrieved_recipes"])
    with tab3:
        show_feedback_tab(user_profile, plan)
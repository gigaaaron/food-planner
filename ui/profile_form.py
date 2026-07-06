import streamlit as st


def render_profile_form():
    st.markdown("## Your Profile")

    col1, col2 = st.columns(2)
    with col1:
        goal = st.selectbox(
            "Goal",
            ["Muscle Gain", "Lose Weight", "General Health", "Maintain Weight", "Athletic Performance"],
        )
        diet = st.selectbox(
            "Diet",
            ["None", "Vegetarian", "Vegan", "Gluten-Free", "Dairy-Free", "Keto", "Paleo"],
        )
    with col2:
        daily_calories = st.slider("Daily Calories", 1200, 4000, 2000, step=50)
        weekly_budget = st.slider("Weekly Budget ($)", 30, 200, 70, step=5)

    allergies = st.multiselect(
        "Allergies",
        ["Peanuts", "Tree Nuts", "Dairy", "Eggs", "Gluten", "Soy", "Shellfish", "Fish"],
        placeholder="Select any allergies",
    )

    ingredients_text = st.text_input(
        "Ingredients you already have",
        placeholder="chicken, rice, eggs, spinach",
    )

    generate_clicked = st.button("Generate Meal Plan", use_container_width=True)

    user_profile = {
        "goal": goal,
        "diet": diet,
        "allergies": allergies,
        "daily_calories": daily_calories,
        "budget": weekly_budget,
        "available_ingredients": [i.strip() for i in ingredients_text.split(",") if i.strip()],
    }

    return user_profile, generate_clicked
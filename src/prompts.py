"""
prompts.py
Prompt templates for the meal planning assistant.
Keeping prompts in one file makes them easy to version and compare.
"""


def build_meal_plan_prompt(profile: dict, retrieved_recipes: list[dict]) -> str:
    # Build the full prompt to send to the LLM.

    # Format retrieved recipes into readable context
    recipe_context = ""
    for i, r in enumerate(retrieved_recipes, 1):
        recipe_context += f"\n--- Recipe {i} ---\n{r['document']}\n"

    # Format user profile
    allergies  = ", ".join(profile.get("allergies", [])) or "none"
    diet       = profile.get("diet", "no restriction")
    goal       = profile.get("goal", "general health")
    calories   = profile.get("daily_calories", 2000)
    budget     = profile.get("budget", 75)
    ingredients = ", ".join(profile.get("available_ingredients", [])) or "no preference"

    prompt = f"""You are a certified nutrition assistant. Your job is to create personalized 7-day meal plans.

IMPORTANT RULES:
- Use ONLY the recipes provided below. Do not invent new recipes.
- Every meal you recommend must come from the list below.
- If you cannot fill a slot with a safe recipe, say so — do not guess.
- Always check allergens carefully before recommending a recipe.

USER PROFILE:
- Goal: {goal}
- Diet: {diet}
- Allergies: {allergies}
- Daily calorie target: {calories} kcal
- Weekly budget: ${budget}
- Available ingredients at home: {ingredients}

AVAILABLE RECIPES (use ONLY these):
{recipe_context}

TASK:
Create a 7-day meal plan (breakfast, lunch, dinner, 1 snack per day) using ONLY the recipes above.

For each day, provide:
1. Breakfast, Lunch, Dinner, Snack (recipe name only)
2. Daily calorie total
3. Daily protein / carbs / fat totals

After the 7-day plan, provide:
- A consolidated shopping list (combine all ingredients, remove duplicates)
- Estimated weekly cost range (use $3-5 for proteins, $1-2 for produce, $2-4 for grains as rough guides)
- A brief note (2-3 sentences) explaining why this plan fits the user's goal

Format your response clearly with headers for each day.
End with a "Sources" section listing which recipes you used.
"""
    return prompt


def build_eval_prompt(question: str, retrieved_recipes: list[dict]) -> str:
    recipe_context = "\n".join(
        f"- {r['metadata']['name']}: {r['document']}" for r in retrieved_recipes
    )

    return f"""You are a nutrition assistant. Answer the question below using ONLY the context provided.
If the answer is not in the context, say "I don't have enough information to answer that."

CONTEXT:
{recipe_context}

QUESTION: {question}

Answer concisely and cite which recipe(s) you referenced."""
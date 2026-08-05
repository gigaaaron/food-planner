"""
prompts.py
Prompt templates for the meal planning assistant.
Keeping prompts in one file makes them easy to version and compare.
"""


MEAL_SLOT_CALORIE_SHARE = {
    "Breakfast": 0.25,
    "Lunch":     0.30,
    "Dinner":    0.35,
    "Snack":     0.10,
}


def build_meal_plan_prompt(profile: dict, retrieved_recipes: list[dict]) -> str:
    # Build the full prompt to send to the LLM.

    # Format retrieved recipes into readable context. Built from metadata
    # rather than the full embedded document — cooking instructions and the
    # source URL aren't needed to build the plan, and skipping them keeps
    # the prompt (and generation time) down significantly on real recipe
    # data, which runs much longer than the placeholder set did.
    recipe_context = ""
    for i, r in enumerate(retrieved_recipes, 1):
        meta = r["metadata"]
        recipe_context += (
            f"\n--- Recipe {i} ---\n"
            f"Name: {meta['name']}\n"
            f"Meal type: {meta['meal_type']}\n"
            f"Calories: {meta['calories']} kcal | Protein: {meta['protein_g']}g | "
            f"Carbs: {meta['carbs_g']}g | Fat: {meta['fat_g']}g\n"
            f"Ingredients: {meta.get('ingredients', '')}\n"
            f"Tags: {meta.get('tags', '')}\n"
            f"Allergens: {meta.get('allergens', 'none')}\n"
        )

    # Format user profile
    allergies  = ", ".join(profile.get("allergies", [])) or "none"
    diet       = profile.get("diet", "no restriction")
    goal       = profile.get("goal", "general health")
    calories   = profile.get("daily_calories", 2000)
    budget     = profile.get("budget", 75)
    ingredients = ", ".join(profile.get("available_ingredients", [])) or "no preference"

    # Per-meal-slot calorie targets, so the model has explicit numeric
    # anchors instead of having to infer a daily split on its own.
    slot_targets = "\n".join(
        f"- {slot}: ~{round(calories * share)} kcal"
        for slot, share in MEAL_SLOT_CALORIE_SHARE.items()
    )

    # Flat numeric lookup table for every retrieved recipe, so the model can
    # sum totals directly instead of re-deriving numbers from prose.
    calorie_reference = "\n".join(
        f"- {r['metadata']['name']} ({r['metadata']['meal_type']}): "
        f"{r['metadata']['calories']} kcal, {r['metadata']['protein_g']}g protein, "
        f"{r['metadata']['carbs_g']}g carbs, {r['metadata']['fat_g']}g fat"
        for r in retrieved_recipes
    )

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

MEAL SLOT CALORIE TARGETS (guide, not strict — should sum to about {calories} kcal):
{slot_targets}

QUICK CALORIE REFERENCE (use these exact numbers for arithmetic — do not estimate):
{calorie_reference}

AVAILABLE RECIPES (use ONLY these):
{recipe_context}

TASK:
Create a 7-day meal plan (breakfast, lunch, dinner, 1 snack per day) using ONLY the recipes above.
When choosing meals, use the Meal Slot Calorie Targets above as a guide for each slot.

For each day, provide:
1. Breakfast, Lunch, Dinner, Snack (recipe name only)
2. Daily calorie total (sum the kcal values from the Quick Calorie Reference above — do not estimate)
3. Daily protein / carbs / fat totals (sum from the Quick Calorie Reference above)

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


def build_judge_prompt(question: str, response: str, expected_concepts: list[str]) -> str:
    concepts = ", ".join(expected_concepts) if expected_concepts else "no specific criteria"

    return f"""You are grading an AI nutrition assistant's answer for quality.

QUESTION:
{question}

CANDIDATE ANSWER:
{response}

EXAMPLES of on-topic recipes/concepts for this question (this is NOT a checklist —
the answer does not need to mention all, or even more than one, of these; they only
illustrate what a correct answer could look like. Judge whether the answer is correct
and relevant on its own merits, including recipes or phrasing not listed here):
{concepts}

Rate the candidate answer's correctness and relevance to the question on an integer
scale from 0 to 10:
- 0-2 = irrelevant, incorrect, or off-topic
- 3-4 = weakly relevant, mostly misses the question
- 5-6 = partially answers the question but is incomplete or has minor issues
- 7-8 = solid, correct, relevant answer with only small gaps
- 9-10 = fully correct, relevant, and well-supported answer

Use the full range — do not default to the middle of the scale unless the answer is
genuinely middling.

Respond with ONLY a JSON object and no other text:
{{"score": <integer 0-10>, "reasoning": "<one sentence>"}}"""
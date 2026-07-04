import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval  import get_recipes_for_user, filter_by_allergens
from src.meal_generator import generate_meal_plan

def make_profile(**kwargs) -> dict:
    base = {
        "goal": "General Health",
        "diet": "None",
        "allergies": [],
        "daily_calories": 2000,
        "budget": 70,
        "available_ingredients": [],
    }
    base.update(kwargs)
    return base

class TestOutputStructure:
 
    def test_result_has_required_keys(self):
        """
        generate_meal_plan must always return all three keys.
        If 'prompt' or 'retrieved_recipes' are missing, the eval
        suite and UI won't have the data they need.
        """
        profile = make_profile()
        result  = generate_meal_plan(profile, n_recipes=6)
        for key in ["meal_plan", "retrieved_recipes", "prompt"]:
            assert key in result, f"Missing key: '{key}'"
 
    def test_meal_plan_mentions_seven_days(self):
        """
        The LLM should structure output across all 7 days.
        Missing days means the model truncated or ignored the prompt.
        """
        profile = make_profile()
        result  = generate_meal_plan(profile, n_recipes=8)
        plan    = result["meal_plan"].lower()
        for day in ["day 1", "day 2", "day 3", "day 4", "day 5", "day 6", "day 7"]:
            assert day in plan, f"Meal plan is missing '{day}'"
 
    def test_meal_plan_contains_shopping_list(self):
        """
        The prompt explicitly asks for a shopping list.
        If it's missing, the model ignored a key instruction — prompt issue.
        """
        profile = make_profile()
        result  = generate_meal_plan(profile, n_recipes=8)
        assert "shopping" in result["meal_plan"].lower()
 
    def test_meal_plan_contains_sources_section(self):
        """
        Sources section proves the model is citing retrieved recipes
        rather than hallucinating new ones. Missing sources = red flag.
        """
        profile = make_profile(goal="Muscle Gain")
        result  = generate_meal_plan(profile, n_recipes=8)
        assert "source" in result["meal_plan"].lower(), (
            "Missing Sources section — model may be hallucinating recipes"
        )
 
    def test_meal_plan_is_non_empty(self):
        profile = make_profile()
        result  = generate_meal_plan(profile, n_recipes=6)
        assert len(result["meal_plan"]) > 200

class TestAllergenSafety:

    def test_peanut_allergy_not_in_retrieval(self):
        profile = make_profile(allergies=["peanuts"])
        result = generate_meal_plan(profile, n_recipes=8)
        plan = result["meal_plan"].lower()
        assert "peanut butter" not in plan and "peanuts" not in plan, (
            "SAFETY FAILURE: Meal plan mentioned peanuts for a peanut-allergic user"
        )

    def test_shellfish_allergy_not_in_output(self):
        profile = make_profile(allergies=["shellfish"])
        result = generate_meal_plan(profile, n_recipes=8)
        plan = result["meal_plan"].lower()
        assert "shrimp" not in plan, (
            "SAFETY FAILURE: Meal plan mentioned shrimp for a shellfish-allergic user"
        )

    def test_retrieved_recipes_respect_allergy(self):
        profile = make_profile(allergies=["peanuts"])
        result  = generate_meal_plan(profile, n_recipes=8)
        for r in result["retrieved_recipes"]:
            allergens = r["metadata"].get("allergens", "").lower()
            assert "peanut" not in allergens, (
                f"'{r['metadata']['name']}' with peanuts was passed into the prompt"
            )

class TestGoalAlignment:
 
    def test_muscle_gain_plan_mentions_protein(self):
        profile = make_profile(goal="Muscle Gain", daily_calories=2200)
        result = generate_meal_plan(profile, n_recipes=8)
        assert "protein" in result["meal_plan"].lower()
 
    def test_weight_loss_plan_mentions_calories(self):
        profile = make_profile(goal="Lose Weight", daily_calories=1600)
        result = generate_meal_plan(profile, n_recipes=8)
        plan = result["meal_plan"].lower()
        assert "calor" in plan
 
    def test_vegan_plan_note_aligns_with_goal(self):
        profile = make_profile(diet="Vegan")
        result= generate_meal_plan(profile, n_recipes=8)
        plan = result["meal_plan"].lower()
        assert "vegan" in plan or "plant" in plan

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval import get_recipes_for_user, filter_by_allergens
from src.meal_generator import generate_meal_plan

def make_profile(**kwargs) -> dict:
    base = {
        "goal":                  "General Health",
        "diet":                  "None",
        "allergies":             [],
        "daily_calories":        2000,
        "budget":                70,
        "available_ingredients": [],
    }
    base.update(kwargs)
    return base


class TestAllergenSafety:

    def test_peanut_allergy_not_in_retrieval(self):
        profile = make_profile(allergies=["peanuts"])
        recipes = get_recipes_for_user(profile, n_results=20)
        for r in recipes:
            allergens = r["metadata"].get("allergens", "").lower()
            assert "peanut" not in allergens, (
                f"Recipe '{r['metadata']['name']}' contains peanuts but was retrieved "
                f"for a peanut-allergic user."
            )

    def test_shellfish_allergy_not_in_retrieval(self):
        profile = make_profile(allergies=["shellfish"])
        recipes = get_recipes_for_user(profile, n_results=20)
        for r in recipes:
            allergens = r["metadata"].get("allergens", "").lower()
            assert "shellfish" not in allergens, (
                f"Recipe '{r['metadata']['name']}' contains shellfish but was retrieved "
                f"for a shellfish-allergic user."
            )

    def test_multiple_allergies_all_excluded(self):
        profile = make_profile(allergies=["peanuts", "shellfish", "dairy"])
        recipes = get_recipes_for_user(profile, n_results=20)
        for r in recipes:
            allergens = r["metadata"].get("allergens", "").lower()
            for allergen in ["peanut", "shellfish", "dairy"]:
                assert allergen not in allergens, (
                    f"Recipe '{r['metadata']['name']}' contains '{allergen}' "
                    f"but user is allergic to it."
                )

    def test_filter_by_allergens_removes_correctly(self):
        mock_recipes = [
            {"metadata": {"name": "Safe Recipe", "allergens": "none"}},
            {"metadata": {"name": "Peanut Recipe", "allergens": "peanuts"}},
            {"metadata": {"name": "Dairy Recipe", "allergens": "dairy, gluten"}},
        ]
        result = filter_by_allergens(mock_recipes, allergies=["peanuts"])
        names  = [r["metadata"]["name"] for r in result]
        assert "Peanut Recipe" not in names
        assert "Safe Recipe" in names
        assert "Dairy Recipe" in names 

    def test_no_allergy_returns_all_recipes(self):
        profile = make_profile(allergies=[])
        recipes = get_recipes_for_user(profile, n_results=12)
        assert len(recipes) == 12

class TestDietaryConstraints:

    def test_vegan_retrieval_excludes_meat(self):
        profile = make_profile(diet="Vegan", goal="Weight Loss")
        recipes = get_recipes_for_user(profile, n_results=8)
        non_vegan_count = sum(
            1 for r in recipes
            if "vegan" not in r["metadata"].get("tags", "").lower()
        )
        assert non_vegan_count <= 4, (
            f"Too many non-vegan recipes returned for vegan user: {non_vegan_count}/8"
        )

    def test_muscle_gain_retrieves_high_protein(self):
        profile = make_profile(goal="Muscle Gain", daily_calories=2200)
        recipes = get_recipes_for_user(profile, n_results=8)
        avg_protein = sum(r["metadata"]["protein_g"] for r in recipes) / len(recipes)
        assert avg_protein >= 20, (
            f"Average protein in retrieved recipes too low for muscle gain: {avg_protein:.1f}g"
        )

    def test_weight_loss_retrieves_lower_calories(self):
        profile = make_profile(goal="Lose Weight", daily_calories=1600)
        recipes = get_recipes_for_user(profile, n_results=8)
        avg_calories = sum(r["metadata"]["calories"] for r in recipes) / len(recipes)
        assert avg_calories <= 480, (
            f"Average calories in retrieved recipes too high for weight loss: {avg_calories:.1f}"
        )

class TestRetrievalQuality:

    def test_retrieval_returns_expected_count(self):
        profile  = make_profile()
        recipes  = get_recipes_for_user(profile, n_results=5)
        assert len(recipes) == 5

    def test_ingredient_match_chicken_and_rice(self):
        profile  = make_profile(available_ingredients=["chicken", "rice"])
        recipes  = get_recipes_for_user(profile, n_results=5)
        top_docs = " ".join(r["document"].lower() for r in recipes)
        assert "chicken" in top_docs, "Chicken not found in top retrieved recipes"
        assert "rice"    in top_docs, "Rice not found in top retrieved recipes"

    def test_all_retrieved_recipes_have_required_metadata(self):
        profile  = make_profile()
        recipes  = get_recipes_for_user(profile, n_results=10)
        required = ["name", "meal_type", "calories", "protein_g", "carbs_g", "fat_g"]
        for r in recipes:
            for field in required:
                assert field in r["metadata"], (
                    f"Recipe '{r['metadata'].get('name', 'unknown')}' missing field '{field}'"
                )

    def test_retrieved_documents_are_non_empty(self):
        profile = make_profile()
        recipes = get_recipes_for_user(profile, n_results=5)
        for r in recipes:
            assert len(r["document"]) > 50, "Retrieved document text is too short"


class TestMealPlanOutput:

    def test_meal_plan_contains_sources_section(self):
        profile = make_profile(goal="Muscle Gain", allergies=["peanuts"])
        result  = generate_meal_plan(profile, n_recipes=8)
        assert "source" in result["meal_plan"].lower(), (
            "Meal plan is missing a Sources section — possible hallucination risk"
        )

    def test_meal_plan_mentions_seven_days(self):
        profile = make_profile()
        result  = generate_meal_plan(profile, n_recipes=8)
        plan    = result["meal_plan"].lower()
        for day in ["day 1", "day 2", "day 3", "day 4", "day 5", "day 6", "day 7"]:
            assert day in plan, f"Meal plan missing '{day}'"

    def test_meal_plan_no_peanuts_for_allergic_user(self):
        profile = make_profile(allergies=["peanuts"])
        result  = generate_meal_plan(profile, n_recipes=8)
        plan    = result["meal_plan"].lower()
        assert "peanut butter" not in plan and "peanuts" not in plan, (
            "Meal plan mentioned peanuts for a peanut-allergic user — SAFETY FAILURE"
        )

    def test_meal_plan_contains_shopping_list(self):
        profile = make_profile()
        result  = generate_meal_plan(profile, n_recipes=8)
        plan    = result["meal_plan"].lower()
        assert "shopping" in plan, "Meal plan is missing a shopping list"

    def test_result_has_required_keys(self):
        profile = make_profile()
        result  = generate_meal_plan(profile, n_recipes=6)
        for key in ["meal_plan", "retrieved_recipes", "prompt"]:
            assert key in result, f"generate_meal_plan result missing key: '{key}'"
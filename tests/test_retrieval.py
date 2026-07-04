import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.retrieval import get_recipes_for_user, filter_by_allergens, build_query

def make_profile(**kwargs) -> dict:
    base = {
        "goal": "General Health",
        "diet": "None",
        "allergies": [],
        "daily_calories": 2000,
        "available_ingredients": [],
    }
    base.update(kwargs)
    return base

class TestQueryBuilder:

    def test_query_includes_goal(self):
        profile = make_profile(goal="Muscle Gain")
        query   = build_query(profile)
        assert "muscle gain" in query.lower()

    def test_query_includes_diet(self):
        profile = make_profile(diet="Vegan")
        query   = build_query(profile)
        assert "vegan" in query.lower()

    def test_query_includes_calories(self):
        profile = make_profile(daily_calories=1800)
        query   = build_query(profile)
        assert "1800" in query

    def test_query_includes_ingredients(self):
        profile = make_profile(available_ingredients=["chicken", "rice"])
        query   = build_query(profile)
        assert "chicken" in query.lower()
        assert "rice"    in query.lower()

    def test_empty_profile_returns_default_query(self):
        profile = make_profile()
        query   = build_query(profile)
        assert len(query) > 0

class TestAllergenFilter:

    def test_removes_peanut_recipes(self):
        mock_recipes = [
            {"metadata": {"name": "Safe Dish",    "allergens": "none"}},
            {"metadata": {"name": "Peanut Sauce", "allergens": "peanuts"}},
        ]
        result = filter_by_allergens(mock_recipes, ["peanuts"])
        names  = [r["metadata"]["name"] for r in result]
        assert "Peanut Sauce" not in names
        assert "Safe Dish"    in names

    def test_removes_multiple_allergens(self):
        mock_recipes = [
            {"metadata": {"name": "Safe",     "allergens": "none"}},
            {"metadata": {"name": "Has Dairy", "allergens": "dairy"}},
            {"metadata": {"name": "Has Soy",   "allergens": "soy"}},
        ]
        result = filter_by_allergens(mock_recipes, ["dairy", "soy"])
        names  = [r["metadata"]["name"] for r in result]
        assert "Has Dairy" not in names
        assert "Has Soy"   not in names
        assert "Safe"      in names

    def test_no_allergies_returns_all(self):
        mock_recipes = [
            {"metadata": {"name": "Recipe A", "allergens": "peanuts"}},
            {"metadata": {"name": "Recipe B", "allergens": "dairy"}},
        ]
        result = filter_by_allergens(mock_recipes, [])
        assert len(result) == 2

    def test_case_insensitive_matching(self):
        mock_recipes = [
            {"metadata": {"name": "Risky", "allergens": "Peanuts"}},
        ]
        result = filter_by_allergens(mock_recipes, ["peanuts"])
        assert len(result) == 0

    def test_none_allergen_field_is_safe(self):
        mock_recipes = [
            {"metadata": {"name": "Clean Recipe", "allergens": "none"}},
        ]
        result = filter_by_allergens(mock_recipes, ["peanuts", "dairy"])
        assert len(result) == 1

class TestChromaRetrieval:

    def test_returns_correct_count(self):
        profile = make_profile()
        results = get_recipes_for_user(profile, n_results=5)
        assert len(results) == 5

    def test_results_have_document_and_metadata(self):
        profile = make_profile()
        results = get_recipes_for_user(profile, n_results=3)
        for r in results:
            assert "document" in r,  "Missing 'document' key in result"
            assert "metadata" in r,  "Missing 'metadata' key in result"

    def test_metadata_has_required_fields(self):
        profile  = make_profile()
        results  = get_recipes_for_user(profile, n_results=5)
        required = ["name", "meal_type", "calories", "protein_g", "carbs_g", "fat_g"]
        for r in results:
            for field in required:
                assert field in r["metadata"], (
                    f"Recipe '{r['metadata'].get('name', '?')}' missing field '{field}'"
                )

    def test_document_text_is_substantial(self):
        profile = make_profile()
        results = get_recipes_for_user(profile, n_results=3)
        for r in results:
            assert len(r["document"]) > 50, (
                f"Document for '{r['metadata'].get('name')}' is too short to be useful"
            )

    def test_chicken_query_returns_chicken_recipes(self):
        profile  = make_profile(available_ingredients=["chicken"])
        results  = get_recipes_for_user(profile, n_results=5)
        all_docs = " ".join(r["document"].lower() for r in results)
        assert "chicken" in all_docs

    def test_vegan_query_returns_vegan_tagged_recipes(self):
        profile = make_profile(diet="Vegan")
        results = get_recipes_for_user(profile, n_results=8)
        vegan_count = sum(
            1 for r in results
            if "vegan" in r["metadata"].get("tags", "").lower()
        )
        assert vegan_count >= 2, (
            f"Expected at least 2 vegan recipes for vegan query, got {vegan_count}"
        )

    def test_peanut_allergy_excluded_from_results(self):
        profile = make_profile(allergies=["peanuts"])
        results = get_recipes_for_user(profile, n_results=20)
        for r in results:
            allergens = r["metadata"].get("allergens", "").lower()
            assert "peanut" not in allergens, (
                f"'{r['metadata']['name']}' contains peanuts but was returned "
                f"for a peanut-allergic user"
            )
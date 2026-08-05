import html
import json
import os
import re
import time

import requests

API_KEY     = os.getenv("SPOONACULAR_API_KEY", "")
BASE_URL    = "https://api.spoonacular.com/recipes/complexSearch"
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "recipes.json")

BUCKETS = [
    ("breakfast", {"type": "breakfast"}, 12),
    ("lunch",     {"type": "main course", "sort": "popularity"}, 12),
    ("dinner",    {"type": "main course", "sort": "healthiness", "offset": 12}, 12),
    ("snack",     {"type": "snack"}, 8),
]

ALLERGEN_KEYWORDS = {
    "dairy":     ["milk", "cheese", "butter", "cream", "yogurt", "parmesan", "mozzarella", "ricotta"],
    "eggs":      ["egg"],
    "gluten":    ["wheat", "flour", "bread", "pasta", "noodle", "barley", "rye", "tortilla", "bun", "cracker"],
    "peanuts":   ["peanut"],
    "tree-nuts": ["almond", "walnut", "cashew", "pecan", "pistachio", "hazelnut", "macadamia"],
    "soy":       ["soy", "tofu", "edamame", "tempeh"],
    "shellfish": ["shrimp", "crab", "lobster", "prawn", "scallop"],
    "fish":      ["salmon", "tuna", "cod", "tilapia", "anchovy", "halibut", "trout"],
    "sesame":    ["sesame", "tahini"],
}

def strip_html(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()

def derive_allergens(ingredient_names: list[str]) -> list[str]:
    joined = " ".join(ingredient_names).lower()
    return sorted(a for a, keywords in ALLERGEN_KEYWORDS.items() if any(k in joined for k in keywords))

def derive_tags(recipe: dict, calories: float, protein_g: float, carbs_g: float, fat_g: float) -> list[str]:
    tags = []
    if recipe.get("vegan"):
        tags.append("vegan")
    if recipe.get("vegetarian"):
        tags.append("vegetarian")
    if recipe.get("glutenFree"):
        tags.append("gluten-free")
    if recipe.get("dairyFree"):
        tags.append("dairy-free")
    if recipe.get("cheap"):
        tags.append("budget-friendly")
    if recipe.get("readyInMinutes", 999) <= 20:
        tags.append("quick")
    if protein_g >= 25:
        tags.append("high-protein")
    if carbs_g <= 20:
        tags.append("low-carb")
    if calories <= 300:
        tags.append("low-calorie")
    if fat_g <= 8:
        tags.append("low-fat")
    return tags

def extract_nutrient(nutrients: list[dict], name: str) -> int:
    for n in nutrients:
        if n.get("name") == name:
            return round(n.get("amount", 0))
    return 0

def extract_instructions(recipe: dict) -> str:
    steps = []
    for block in recipe.get("analyzedInstructions", []):
        for step in block.get("steps", []):
            steps.append(step.get("step", ""))
    if steps:
        return " ".join(steps)
    if recipe.get("instructions"):
        return strip_html(recipe["instructions"])
    return "See full recipe instructions at the source link."

def fetch_bucket(meal_type: str, params: dict, number: int) -> list[dict]:
    query = {
        "apiKey": API_KEY,
        "number": number,
        "addRecipeInformation": "true",
        "addRecipeNutrition": "true",
        "fillIngredients": "true",
        **params,
    }
    resp = requests.get(BASE_URL, params=query, timeout=30)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    print(f"  {meal_type}: fetched {len(results)} recipes")

    recipes = []
    for r in results:
        nutrients = r.get("nutrition", {}).get("nutrients", [])
        calories  = extract_nutrient(nutrients, "Calories")
        protein_g = extract_nutrient(nutrients, "Protein")
        carbs_g   = extract_nutrient(nutrients, "Carbohydrates")
        fat_g     = extract_nutrient(nutrients, "Fat")

        ingredient_names = [
            ing.get("name", "") for ing in r.get("nutrition", {}).get("ingredients", [])
        ] or [ing.get("name", "") for ing in r.get("extendedIngredients", [])]
        ingredient_names = [n for n in ingredient_names if n]

        recipes.append({
            "id":           f"r{r['id']}",
            "name":         r.get("title", "Untitled recipe"),
            "calories":     calories,
            "protein_g":    protein_g,
            "carbs_g":      carbs_g,
            "fat_g":        fat_g,
            "ingredients":  ingredient_names,
            "tags":         derive_tags(r, calories, protein_g, carbs_g, fat_g),
            "allergens":    derive_allergens(ingredient_names),
            "meal_type":    meal_type,
            "instructions": extract_instructions(r),
            "source_url":   r.get("sourceUrl") or r.get("spoonacularSourceUrl", ""),
        })
    return recipes

def fetch_all_recipes() -> list[dict]:
    if not API_KEY:
        raise SystemExit(
            "SPOONACULAR_API_KEY is not set. Get a free key at "
            "https://spoonacular.com/food-api and add it to your .env file."
        )

    all_recipes = []
    seen_ids = set()
    for meal_type, params, number in BUCKETS:
        for r in fetch_bucket(meal_type, params, number):
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                all_recipes.append(r)
        time.sleep(1)  # stay polite to the free-tier rate limit

    return all_recipes

def main():
    print("Fetching real recipes from Spoonacular...")
    recipes = fetch_all_recipes()
    print(f"Fetched {len(recipes)} unique recipes total.")

    with open(OUTPUT_PATH, "w") as f:
        json.dump(recipes, f, indent=2)

    print(f"Wrote {OUTPUT_PATH}")
    print("Run 'python -m src.ingest' next to rebuild the vector database.")


if __name__ == "__main__":
    main()

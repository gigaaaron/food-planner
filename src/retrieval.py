"""
retrieval.py
Query ChromaDB to retrieve the most relevant recipes
for a given user profile and query.
"""

import os
import chromadb
from chromadb.utils import embedding_functions

CHROMA_DIR      = os.path.join(os.path.dirname(__file__), "..", "chroma_db")
MODEL_NAME = "all-MiniLM-L6-v2"


def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=MODEL_NAME
    )
    return client.get_collection(name="recipes", embedding_function=embedding_fn)


def build_query(profile: dict) -> str:
    # Turn a user profile into a natural language search query.
    parts = []

    if profile.get("goal"):
        parts.append(f"meals for {profile['goal'].lower()}")

    if profile.get("diet"):
        parts.append(f"{profile['diet'].lower()} diet")

    if profile.get("allergies"):
        allergen_str = ", ".join(profile["allergies"])
        parts.append(f"no {allergen_str}")

    if profile.get("daily_calories"):
        parts.append(f"around {profile['daily_calories']} calories per day")

    if profile.get("available_ingredients"):
        ing_str = ", ".join(profile["available_ingredients"])
        parts.append(f"using {ing_str}")

    return " ".join(parts) if parts else "healthy balanced meals"


def retrieve_recipes(profile: dict, n_results: int = 10) -> list[dict]:
    # Retrieve the top-N most relevant recipes for a user profile.
    # Returns a list of dicts with 'document' and 'metadata' keys.
    collection = get_collection()
    query      = build_query(profile)

    print(f"  Search query: '{query}'")

    results = collection.query(
        query_texts=[query],
        n_results=n_results,
    )

    recipes = []
    for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
        recipes.append({"document": doc, "metadata": meta})

    return recipes


def filter_by_allergens(recipes: list[dict], allergies: list[str]) -> list[dict]:
    # Hard filter: remove any recipe that contains an allergen the user listed.
    if not allergies:
        return recipes

    allergies_lower = [a.lower() for a in allergies]
    safe = []
    for r in recipes:
        recipe_allergens = r["metadata"].get("allergens", "none").lower()
        if not any(a in recipe_allergens for a in allergies_lower):
            safe.append(r)

    return safe


def get_recipes_for_user(profile: dict, n_results: int = 10) -> list[dict]:
    recipes = retrieve_recipes(profile, n_results=n_results + 5)  # over-fetch then filter
    recipes = filter_by_allergens(recipes, profile.get("allergies", []))
    return recipes[:n_results]


# Quick test 
if __name__ == "__main__":
    test_profile = {
        "goal":       "Muscle Gain",
        "diet":       "None",
        "allergies":  ["peanuts"],
        "daily_calories": 2200,
        "available_ingredients": ["chicken", "rice", "eggs"],
    }

    print("Retrieving recipes for test profile...")
    results = get_recipes_for_user(test_profile, n_results=5)

    print(f"\nTop {len(results)} recipes retrieved:\n")
    for r in results:
        m = r["metadata"]
        print(f"  • {m['name']} ({m['meal_type']}) — {m['calories']} kcal, {m['protein_g']}g protein")
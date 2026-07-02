"""
ingest.py
Loads recipes from data/recipes.json and stores them in ChromaDB.
"""

import json
import os
import chromadb
from chromadb.utils import embedding_functions

RECIPES_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "recipes.json")
CHROMA_DIR   = os.path.join(os.path.dirname(__file__), "..", "chroma_db")

MODEL_NAME = "all-MiniLM-L6-v2"


def load_recipes(path: str) -> list[dict]:
    with open(path, "r") as f:
        return json.load(f)


def recipe_to_document(recipe: dict) -> str:
    return (
        f"Recipe: {recipe['name']}\n"
        f"Meal type: {recipe['meal_type']}\n"
        f"Calories: {recipe['calories']} kcal\n"
        f"Protein: {recipe['protein_g']}g | Carbs: {recipe['carbs_g']}g | Fat: {recipe['fat_g']}g\n"
        f"Ingredients: {', '.join(recipe['ingredients'])}\n"
        f"Tags: {', '.join(recipe['tags'])}\n"
        f"Allergens: {', '.join(recipe['allergens']) if recipe['allergens'] else 'none'}\n"
        f"Instructions: {recipe['instructions']}"
    )


def build_vector_db():
    print("Loading recipes...")
    recipes = load_recipes(RECIPES_PATH)
    print(f"  Found {len(recipes)} recipes.")

    print("Connecting to ChromaDB...")
    client = chromadb.PersistentClient(path=CHROMA_DIR)

    embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=MODEL_NAME
    )

    # Delete existing collection so re-runs start fresh
    try:
        client.delete_collection("recipes")
        print("  Cleared existing 'recipes' collection.")
    except Exception:
        pass

    collection = client.create_collection(
        name="recipes",
        embedding_function=embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )

    print("Embedding and storing recipes...")
    documents = [recipe_to_document(r) for r in recipes]
    ids       = [r["id"] for r in recipes]
    metadatas = [
        {
            "name":       r["name"],
            "meal_type":  r["meal_type"],
            "calories":   r["calories"],
            "protein_g":  r["protein_g"],
            "carbs_g":    r["carbs_g"],
            "fat_g":      r["fat_g"],
            "tags":       ", ".join(r["tags"]),
            "allergens":  ", ".join(r["allergens"]) if r["allergens"] else "none",
        }
        for r in recipes
    ]

    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    print(f"  Stored {len(documents)} recipes in ChromaDB.")
    print(f"  Database saved to: {CHROMA_DIR}")
    print("Done")


if __name__ == "__main__":
    build_vector_db()
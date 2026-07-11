"""
meal_generator.py
Orchestrates the full RAG pipeline:
  1. Retrieve relevant recipes from ChromaDB
  2. Build a prompt
  3. Call Llama 3 via Ollama
  4. Return the meal plan
"""

import os
import requests
from src.retrieval import get_recipes_for_user
from src.prompts   import build_meal_plan_prompt

OLLAMA_URL   = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3")


def call_ollama(prompt: str, model: str = OLLAMA_MODEL) -> str:
    payload = {
        "model":  model,
        "prompt": prompt,
        "stream": False,
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()
        return response.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        return (
            "ERROR: Could not connect to Ollama. "
            "Make sure Ollama is running (run 'ollama serve' in a terminal)."
        )
    except requests.exceptions.Timeout:
        return "ERROR: Ollama request timed out. The model may still be loading — try again."
    except Exception as e:
        return f"ERROR: {str(e)}"


def generate_meal_plan(profile: dict, n_recipes: int = 12) -> dict:
    print("Step 1: Retrieving relevant recipes...")
    recipes = get_recipes_for_user(profile, n_results=n_recipes)
    print(f"  Retrieved {len(recipes)} recipes.")

    print("Step 2: Building prompt...")
    prompt = build_meal_plan_prompt(profile, recipes)

    print("Step 3: Calling Llama 3 via Ollama...")
    meal_plan = call_ollama(prompt)
    print("  Done.")

    return {
        "meal_plan":         meal_plan,
        "retrieved_recipes": recipes,
        "prompt":            prompt,
    }


# Quick test
if __name__ == "__main__":
    test_profile = {
        "goal":                  "Muscle Gain",
        "diet":                  "None",
        "allergies":             ["peanuts"],
        "daily_calories":        2200,
        "budget":                70,
        "available_ingredients": ["chicken", "rice", "eggs", "spinach"],
    }

    result = generate_meal_plan(test_profile)

    print("\n" + "="*60)
    print("MEAL PLAN")
    print("="*60)
    print(result["meal_plan"])

    print("\n" + "="*60)
    print("RECIPES USED AS CONTEXT")
    print("="*60)
    for r in result["retrieved_recipes"]:
        m = r["metadata"]
        print(f"  • {m['name']} ({m['meal_type']}) — {m['calories']} kcal")
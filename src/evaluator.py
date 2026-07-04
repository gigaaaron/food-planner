import json
import os
import time
from src.retrieval import get_recipes_for_user
from src.meal_generator import call_ollama
from src.prompts import build_eval_prompt

EVAL_DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "eval_dataset.json")
RESULTS_PATH      = os.path.join(os.path.dirname(__file__), "..", "tests", "eval_results.json")


def score_keyword_hit(response: str, expected_keywords: list[str]) -> float:
    """
    What fraction of expected keywords appear in the response?
    Score: 0.0 to 1.0
    """
    if not expected_keywords:
        return 1.0
    response_lower = response.lower()
    hits = sum(1 for kw in expected_keywords if kw.lower() in response_lower)
    return hits / len(expected_keywords)


def score_allergen_safety(response: str, must_not_contain: list[str]) -> float:
    if not must_not_contain:
        return 1.0
    response_lower = response.lower()
    violations = [word for word in must_not_contain if word.lower() in response_lower]
    if violations:
        return 0.0
    return 1.0


def score_context_precision(question: str, retrieved_recipes: list[dict]) -> float:
    question_words = set(question.lower().split())
    stopwords = {"a", "an", "the", "is", "i", "for", "with", "what", "can", "me",
                 "if", "of", "and", "to", "my", "are", "have", "good", "some"}
    question_words -= stopwords

    relevant_count = 0
    for r in retrieved_recipes:
        doc_lower = r["document"].lower()
        if any(word in doc_lower for word in question_words):
            relevant_count += 1

    return relevant_count / len(retrieved_recipes) if retrieved_recipes else 0.0


def score_answer_relevance(question: str, response: str) -> float:
    question_words = set(question.lower().split())
    stopwords = {"a", "an", "the", "is", "i", "for", "with", "what", "can", "me",
                 "if", "of", "and", "to", "my", "are", "have", "good", "some",
                 "suggest", "give", "need", "want"}
    question_words -= stopwords

    if not question_words:
        return 1.0

    response_lower = response.lower()
    hits = sum(1 for w in question_words if w in response_lower)
    return min(hits / len(question_words), 1.0)

def run_eval(max_questions: int = 30, delay_seconds: float = 1.0) -> dict:
    with open(EVAL_DATASET_PATH) as f:
        dataset = json.load(f)[:max_questions]

    results       = []
    category_scores = {}

    print(f"\nRunning eval on {len(dataset)} questions...\n")
    print(f"{'#':<5} {'Category':<22} {'KW Hit':>7} {'Safety':>7} {'Ctx Prec':>9} {'Ans Rel':>8} {'Overall':>8}")
    print("-" * 70)

    for i, item in enumerate(dataset, 1):
        # build a minimal profile for retrieval
        profile = {
            "goal":       "General Health",
            "diet":       "None",
            "allergies":  [],
            "daily_calories": 2000,
        }

        # retrieve context
        retrieved = get_recipes_for_user(profile, n_results=6)

        # build and send prompt
        prompt   = build_eval_prompt(item["question"], retrieved)
        response = call_ollama(prompt)

        # Score
        kw_score = score_keyword_hit(response, item["expected_keywords"])
        safety_score = score_allergen_safety(response, item["must_not_contain"])
        ctx_score  = score_context_precision(item["question"], retrieved)
        rel_score = score_answer_relevance(item["question"], response)
        overall = (kw_score * 0.3 + safety_score * 0.4 + ctx_score * 0.15 + rel_score * 0.15)

        result = {
            "id":               item["id"],
            "category":         item["category"],
            "question":         item["question"],
            "response":         response,
            "keyword_hit":      round(kw_score,     3),
            "allergen_safety":  round(safety_score, 3),
            "context_precision":round(ctx_score,    3),
            "answer_relevance": round(rel_score,    3),
            "overall":          round(overall,      3),
            "passed":           overall >= 0.6 and safety_score == 1.0,
        }
        results.append(result)

        cat = item["category"]
        if cat not in category_scores:
            category_scores[cat] = []
        category_scores[cat].append(overall)

        print(
            f"{i:<5} {cat:<22} {kw_score:>7.2f} {safety_score:>7.2f} "
            f"{ctx_score:>9.2f} {rel_score:>8.2f} {overall:>8.2f}"
        )

        time.sleep(delay_seconds)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    avg_kw  = sum(r["keyword_hit"] for r in results) / total
    avg_safety = sum(r["allergen_safety"] for r in results) / total
    avg_ctx = sum(r["context_precision"] for r in results) / total
    avg_rel = sum(r["answer_relevance"] for r in results) / total
    avg_overall = sum(r["overall"] for r in results) / total

    summary = {
        "total_questions":     total,
        "passed":              passed,
        "pass_rate":           round(passed / total, 3),
        "avg_keyword_hit":     round(avg_kw,      3),
        "avg_allergen_safety": round(avg_safety,  3),
        "avg_context_precision": round(avg_ctx,   3),
        "avg_answer_relevance":  round(avg_rel,   3),
        "avg_overall_score":   round(avg_overall, 3),
        "by_category": {
            cat: round(sum(scores) / len(scores), 3)
            for cat, scores in category_scores.items()
        },
        "individual_results":  results,
    }

    # save results
    with open(RESULTS_PATH, "w") as f:
        json.dump(summary, f, indent=2)

    print("\n" + "=" * 70)
    print("EVAL SUMMARY")
    print("=" * 70)
    print(f"  Questions run   : {total}")
    print(f"  Passed (≥0.6)   : {passed}/{total}  ({passed/total*100:.1f}%)")
    print(f"  Keyword Hit Rate: {avg_kw*100:.1f}%")
    print(f"  Allergen Safety : {avg_safety*100:.1f}%")
    print(f"  Context Precision:{avg_ctx*100:.1f}%")
    print(f"  Answer Relevance: {avg_rel*100:.1f}%")
    print(f"  Overall Score   : {avg_overall*100:.1f}%")
    print("\n  By category:")
    for cat, score in summary["by_category"].items():
        print(f"    {cat:<22} {score*100:.1f}%")
    print(f"\n  Full results saved to: {RESULTS_PATH}")

    return summary


if __name__ == "__main__":
    # run_eval(max_questions=5) # run quick 5 questions
    run_eval()
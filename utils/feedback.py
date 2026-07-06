import csv
import os
from datetime import datetime

FEEDBACK_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "feedback_log.csv")

HEADERS = ["timestamp", "goal", "diet", "allergies", "calories", "budget", "rating", "note", "plan_length"]


def log_feedback(user_profile: dict, meal_plan: str, rating: str, note: str = ""):
    file_exists = os.path.exists(FEEDBACK_PATH)

    with open(FEEDBACK_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not file_exists:
            writer.writerow(HEADERS)

        writer.writerow([
            datetime.now().isoformat(),
            user_profile.get("goal"),
            user_profile.get("diet"),
            "|".join(user_profile.get("allergies", [])),
            user_profile.get("daily_calories"),
            user_profile.get("budget"),
            rating,
            note.replace("\n", " "),
            len(meal_plan),
        ])
#!/usr/bin/env python3
"""
FinalRanking.py  (patched)

Changes:
- candidates with only 1 valid score are no longer skipped
- a decay of 0.08 is applied to make 1-score resumes rank lower without exclusion
- log skipped candidates with full score breakdown
"""

import json
from pathlib import Path

# Absolute paths from your current pipeline
INPUT_FILE = Path("Ranking/Scores.json")
OUTPUT_FILE = Path("Ranking/Final_Ranking.json")
SKIPPED_FILE = Path("Ranking/Skipped.json")
DISPLAY_FILE = Path("Ranking/DisplayRanks.txt")

# Score weights (unchanged)
WEIGHTS = {
    "project_aggregate": 0.35,
    "Semantic_Score": 0.35,
    "Keyword_Score": 0.3,
}

# decay to apply when exactly 1 score available
ONE_SCORE_DECAY = 0.08


def compute_final_score(entry: dict) -> float | None:
    """Return final weighted score or None if no useful score exists."""
    raw_scores = {
        "project_aggregate": entry.get("project_aggregate", 0.0),
        "Semantic_Score": entry.get("Semantic_Score", 0.0),
        "Keyword_Score": entry.get("Keyword_Score", 0.0),
    }

    # valid scores = >0.0 values
    valid_scores = {k: v for k, v in raw_scores.items() if isinstance(v, (int, float)) and v > 0.0}

    # SKIP only if *all* scores are zero
    if len(valid_scores) == 0:
        return None

    # If exactly one valid score → apply minimal constant decay
    if len(valid_scores) == 1:
        score_value = list(valid_scores.values())[0]
        adjusted = max(score_value - ONE_SCORE_DECAY, 0.0)
        return round(adjusted, 3)

    # 2 or 3 valid scores → weighted formula (normalized weights)
    total_weight = sum(WEIGHTS[k] for k in valid_scores)
    final = sum((WEIGHTS[k] / total_weight) * valid_scores[k] for k in valid_scores)
    return round(final, 3)


def main():
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        candidates = json.load(f)

    ranked, skipped = [], []

    print("\n🔍 Log of skipped resumes (if any):\n")

    for cand in candidates:
        final_score = compute_final_score(cand)

        if final_score is None:
            skipped.append(cand)
            print(
                f"⛔ SKIPPED → {cand.get('name')}"
                f" | Project={cand.get('project_aggregate')}"
                f" | Semantic={cand.get('Semantic_Score')}"
                f" | Keyword={cand.get('Keyword_Score')}"
            )
            continue

        cand["Final_Score"] = final_score
        ranked.append(cand)

    # Sort in descending order
    ranked.sort(key=lambda x: x["Final_Score"], reverse=True)

    # Guarantee ranking file folder exists
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON outputs
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=4)

    with SKIPPED_FILE.open("w", encoding="utf-8") as f:
        json.dump(skipped, f, indent=4)

    # Write human-readable text ranking
    with DISPLAY_FILE.open("w", encoding="utf-8") as f:
        for i, cand in enumerate(ranked, start=1):
            f.write(f"{i}. {cand['name']} | {cand['Final_Score']}\n")

    print(f"\n🏆 Final ranking written → {OUTPUT_FILE} ({len(ranked)} candidates)")
    print(f"⚠️ Skipped entries written → {SKIPPED_FILE} ({len(skipped)} candidates)")
    print(f"📄 HR-friendly display → {DISPLAY_FILE}\n")


if __name__ == "__main__":
    main()

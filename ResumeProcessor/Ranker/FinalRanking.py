#!/usr/bin/env python3
"""
FinalRanking.py

Usage:
    python3 FinalRanking.py

What it does:
- Reads candidate scores from /home/harshchinchakar/WORK Files/HR Bot/Ranking/Scores.json
- Computes weighted final scores (priority: Project > Semantic > Keyword)
- Skips candidates with <2 valid scores
- Writes:
    Final_Ranking.json (sorted JSON)
    Skipped.json (skipped candidates)
    DisplayRanks.txt (ranked names + scores for HR)
"""

import json
from pathlib import Path

# Absolute paths
INPUT_FILE = Path("/home/keeda/HR BOT/Ranking/Scores.json")
OUTPUT_FILE = Path("/home/keeda/HR BOT/Ranking/Final_Ranking.json")
SKIPPED_FILE = Path("Ranking/Skipped.json")
DISPLAY_FILE = Path("Ranking/DisplayRanks.txt")

# Base weights
WEIGHTS = {
    "project_aggregate": 0.35,
    "Semantic_Score": 0.35,
    "Keyword_Score": 0.3,
}

def compute_final_score(entry: dict) -> float | None:
    """Compute weighted score. Returns None if <2 valid scores."""
    scores = {
        k: v for k, v in {
            "project_aggregate": entry.get("project_aggregate", 0.0),
            "Semantic_Score": entry.get("Semantic_Score", 0.0),
            "Keyword_Score": entry.get("Keyword_Score", 0.0),
        }.items()
        if v and v > 0.0
    }

    if len(scores) < 2:
        return None  # insufficient data

    # Normalize weights for available scores
    total_weight = sum(WEIGHTS[k] for k in scores)
    final = sum((WEIGHTS[k] / total_weight) * scores[k] for k in scores)
    return round(final, 3)

def main():
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        candidates = json.load(f)

    ranked, skipped = [], []

    for cand in candidates:
        final_score = compute_final_score(cand)
        if final_score is None:
            cand["reason"] = "insufficient scores (<2 valid)"
            skipped.append(cand)
        else:
            cand["Final_Score"] = final_score
            ranked.append(cand)

    # Sort by final score
    ranked.sort(key=lambda x: x["Final_Score"], reverse=True)

    # Write JSON outputs
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=4)

    with SKIPPED_FILE.open("w", encoding="utf-8") as f:
        json.dump(skipped, f, indent=4)

    # Write HR-friendly text display
    with DISPLAY_FILE.open("w", encoding="utf-8") as f:
        for i, cand in enumerate(ranked, start=1):
            f.write(f"{i}. {cand['name']} | {cand['Final_Score']}\n")

    print(f"🏆 Final ranking written: {OUTPUT_FILE} ({len(ranked)} candidates)")
    print(f"⚠️ Skipped entries written: {SKIPPED_FILE} ({len(skipped)} candidates)")
    print(f"📄 HR Display file written: {DISPLAY_FILE}")

if __name__ == "__main__":
    main()

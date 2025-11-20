#!/usr/bin/env python3
"""
FinalRanking.py — Fixed pathing + safe write for Cloud / GitHub runs
"""

import json
from pathlib import Path

ROOT = Path(".")
INPUT_FILE = ROOT / "Ranking/Scores.json"
OUTPUT_FILE = ROOT / "Ranking/Final_Ranking.json"
SKIPPED_FILE = ROOT / "Ranking/Skipped.json"
DISPLAY_FILE = ROOT / "Ranking/DisplayRanks.txt"   # HR friendly

# Pre-allocation (RAM copy for Streamlit live rendering)
RANKING_RAM = []

WEIGHTS = {
    "project_aggregate": 0.35,
    "Semantic_Score": 0.35,
    "Keyword_Score": 0.3,
}

def compute_final_score(entry: dict):
    scores = {
        k: v for k, v in {
            "project_aggregate": entry.get("project_aggregate"),
            "Semantic_Score": entry.get("Semantic_Score"),
            "Keyword_Score": entry.get("Keyword_Score"),
        }.items() if isinstance(v, (int, float)) and v > 0
    }
    if len(scores) < 2:
        return None

    total_w = sum(WEIGHTS[k] for k in scores)
    return round(sum((WEIGHTS[k]/total_w) * scores[k] for k in scores), 3)

def run_ranking():
    global RANKING_RAM

    if not INPUT_FILE.exists():
        print(f"❌ Scores.json missing: {INPUT_FILE}")
        return []

    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        candidates = json.load(f)

    ranked = []
    skipped = []

    for entry in candidates:
        score = compute_final_score(entry)
        if score is None:
            entry["reason"] = "insufficient scoring (<2 valid metrics)"
            skipped.append(entry)
        else:
            entry["Final_Score"] = score
            ranked.append(entry)

    ranked.sort(key=lambda x: x["Final_Score"], reverse=True)
    RANKING_RAM = ranked   # update in-memory version for UI

    # Write storage files (works even on local)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(ranked, f, indent=4)
    with open(SKIPPED_FILE, "w", encoding="utf-8") as f:
        json.dump(skipped, f, indent=4)
    with open(DISPLAY_FILE, "w", encoding="utf-8") as f:
        for i, cand in enumerate(ranked, start=1):
            f.write(f"{i}. {cand['name']} | {cand['Final_Score']}\n")

    print(f"🏆 Ranking complete ({len(ranked)} candidates)")
    return ranked

if __name__ == "__main__":
    run_ranking()

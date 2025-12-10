

##!/usr/bin/env python3
import json
from pathlib import Path

OUTPUT_FILE = Path("Ranking/Scores.json")
PROCESSED_JSON_DIR = Path("ProcessedJson")


def normalize_name(name: str) -> str:
    """Normalize candidate name consistently across all modules."""
    if not name or not isinstance(name, str):
        return ""
    return " ".join(name.strip().title().split())

# Define weights for weighted average
WEIGHTS = {
    "difficulty": 0.142857,
    "novelty": 0.142857,
    "skill_relevance": 0.142857,
    "complexity": 0.142857,
    "technical_depth": 0.142857,
    "domain_relevance": 0.142857,
    "execution_quality": 0.142857
}

def calculate_weighted_score(metrics: dict) -> float:
    total_score = 0
    total_weight = 0
    for metric, weight in WEIGHTS.items():
        if metric in metrics:
            total_score += metrics[metric] * weight
            total_weight += weight
    return round(total_score / total_weight, 3) if total_weight > 0 else 0.0

def process_resume(json_path: Path):
    if json_path.name == "example_output.json":
        return None
    try:
        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print(f"⚠️ Skipping invalid JSON: {json_path}")
        return None

    candidate_id = data.get("candidate_id")
    candidate_name = normalize_name(data.get("name", "Unknown"))
    projects = data.get("projects", [])
    if not projects:
        aggregate_score = 0.0
    else:
        project_scores = [calculate_weighted_score(p.get("metrics", {})) for p in projects]
        aggregate_score = round(sum(project_scores) / len(project_scores), 3)

    result = {"name": candidate_name, "project_aggregate": aggregate_score}
    if candidate_id:
        result["candidate_id"] = candidate_id
    return result

def main():
    results = []
    json_files = sorted(PROCESSED_JSON_DIR.glob("*.json"))
    for json_file in json_files:
        result = process_resume(json_file)
        if result:
            results.append(result)
            # print(f"✅ Processed {result['name']} | Project Aggregate: {result['project_aggregate']}")

    # Load existing scores
    if OUTPUT_FILE.exists():
        with OUTPUT_FILE.open("r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except json.JSONDecodeError:
                existing_data = []
    else:
        existing_data = []

    # Build existing map for update - prioritize candidate_id, fallback to normalized name
    existing_map_by_id = {}
    existing_map_by_name = {}
    for r in existing_data:
        if isinstance(r, dict):
            if r.get("candidate_id"):
                existing_map_by_id[r["candidate_id"]] = r
            if r.get("name"):
                normalized_name = normalize_name(r["name"])
                if normalized_name:
                    existing_map_by_name[normalized_name] = r
    
    # Merge new results - use candidate_id first, then normalized name
    for r in results:
        candidate_id = r.get("candidate_id")
        normalized_name = normalize_name(r.get("name", ""))
        
        if candidate_id and candidate_id in existing_map_by_id:
            # Update by candidate_id (most reliable)
            existing_map_by_id[candidate_id].update(r)
        elif normalized_name and normalized_name in existing_map_by_name:
            # Update by normalized name (fallback)
            existing_map_by_name[normalized_name].update(r)
        else:
            # New entry
            if candidate_id:
                existing_map_by_id[candidate_id] = r
            if normalized_name:
                existing_map_by_name[normalized_name] = r
    
    # Combine maps, prioritizing candidate_id entries
    updated_scores = list(existing_map_by_id.values())
    # Add entries that only exist in name map (for backward compatibility)
    for name, entry in existing_map_by_name.items():
        if not entry.get("candidate_id") or entry["candidate_id"] not in existing_map_by_id:
            updated_scores.append(entry)
    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(updated_scores, f, indent=4)

    print(f"\n📂 All results written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

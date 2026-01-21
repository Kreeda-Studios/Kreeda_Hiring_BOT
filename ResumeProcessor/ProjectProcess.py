

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
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    # Only process files in root ProcessedJson directory (exclude FilteredResumes subdirectory)
    json_files = sorted([
        f for f in PROCESSED_JSON_DIR.glob("*.json") 
        if f.name != "example_output.json" and f.parent == PROCESSED_JSON_DIR
    ])
    
    # #region agent log
    with open(".cursor/debug.log", "a", encoding="utf-8") as log:
        log.write(json.dumps({"sessionId":"debug-session","runId":"project-process","hypothesisId":"I8","location":"ProjectProcess.py:66","message":"Starting project processing","data":{"total_files":len(json_files)},"timestamp":int(__import__("time").time()*1000)})+"\n")
    # #endregion
    
    # Check for parallel processing flag
    parallel = os.getenv("ENABLE_PARALLEL", "false").lower() == "true"
    max_workers = int(os.getenv("MAX_WORKERS", "5"))
    
    results = []
    processed_count = 0
    error_count = 0
    
    if parallel and len(json_files) > 1:
        # Parallel processing
        print(f"[INFO] Processing {len(json_files)} resumes in parallel with {max_workers} workers...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_resume, json_file): json_file for json_file in json_files}
            
            for future in as_completed(futures):
                json_file = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                        processed_count += 1
                    else:
                        error_count += 1
                except Exception as e:
                    error_count += 1
                    print(f"⚠️ Error processing {json_file.name}: {e}")
                    # #region agent log
                    with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                        log.write(json.dumps({"sessionId":"debug-session","runId":"project-process","hypothesisId":"I8","location":"ProjectProcess.py:90","message":"Error processing resume","data":{"file":json_file.name,"error":str(e)},"timestamp":int(__import__("time").time()*1000)})+"\n")
                    # #endregion
    else:
        # Sequential processing
        for json_file in json_files:
            try:
                result = process_resume(json_file)
                if result:
                    results.append(result)
                    processed_count += 1
                else:
                    error_count += 1
            except Exception as e:
                error_count += 1
                print(f"⚠️ Error processing {json_file.name}: {e}")
                # #region agent log
                with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                    log.write(json.dumps({"sessionId":"debug-session","runId":"project-process","hypothesisId":"I8","location":"ProjectProcess.py:107","message":"Error processing resume","data":{"file":json_file.name,"error":str(e)},"timestamp":int(__import__("time").time()*1000)})+"\n")
                # #endregion
    
    print(f"[SUMMARY] ProjectProcess: {processed_count} processed, {error_count} errors out of {len(json_files)} total")
    # #region agent log
    with open(".cursor/debug.log", "a", encoding="utf-8") as log:
        log.write(json.dumps({"sessionId":"debug-session","runId":"project-process","hypothesisId":"I8","location":"ProjectProcess.py:112","message":"Project processing summary","data":{"total":len(json_files),"processed":processed_count,"errors":error_count},"timestamp":int(__import__("time").time()*1000)})+"\n")
    # #endregion

    # Start fresh - clear existing scores for new batch
    # (Scores.json will be rebuilt from scratch with only current batch)
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

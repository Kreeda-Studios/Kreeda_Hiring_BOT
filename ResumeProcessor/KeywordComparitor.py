
#!/usr/bin/env python3
"""
KeywordComparitor.py

Unified comparator:
- Collects *all* JD keywords and resume tokens, normalizes, compares
- Weights applied based on source category (required, preferred, weighted, etc.)
- Avoids missing keywords by centralizing comparison
- Appends results to Scores.json instead of overwriting
"""

import json
import sys
from pathlib import Path

# Output file
OUTPUT_FILE = Path("Ranking/Scores.json")

# Relative dirs
SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
PROCESSED_JSON_DIR = (ROOT_DIR / "ProcessedJson").resolve()
JD_DIR = (ROOT_DIR / "InputThread" / "JD").resolve()

# Skip filename
SKIP_FILENAME = "example_output.json"

# Default weights
DEFAULT_WEIGHTS = {
    "required_skills": 0.18,
    "preferred_skills": 0.08,
    "weighted_keywords": 0.15,
    "experience_keywords": 0.25,
    "domain_relevance": 0.10,
    "technical_depth": 0.10,
    "project_metrics": 0.09,
    "responsibilities": 0.03,
    "education": 0.02,
}

# Experience keyword weights
EXPERIENCE_KEYWORD_WEIGHTS = {
    "lead": 4.0, "led": 4.0, "manager": 4.0, "managed": 4.0, "architect": 4.0,
    "architected": 4.0, "designed": 3.6, "design": 3.6, "owned": 3.6,
    "implemented": 3.2, "built": 3.6, "scaled": 3.4, "scale": 3.4,
    "optimized": 3.2, "deployed": 3.2, "productionized": 3.6,
    "mentored": 2.8, "coach": 2.8, "contributed": 2.4, "contributed to": 2.4,
    "improved": 3.0, "reduced": 3.0, "increased": 3.0, "automated": 3.2,
    "orchestrated": 3.4
}

# Normalizer
def norm(s: str) -> str:
    return s.strip().lower() if isinstance(s, str) else ""


def normalize_name(name: str) -> str:
    """Normalize candidate name consistently across all modules."""
    if not name or not isinstance(name, str):
        return ""
    return " ".join(name.strip().title().split())

# Load JD JSON
def load_jd_json():
    json_files = list(JD_DIR.glob("*.json"))
    if not json_files:
        print(f"❌ No JD JSON found in {JD_DIR}", file=sys.stderr)
        return None
    jd_path = json_files[0]
    with jd_path.open("r", encoding="utf-8") as f:
        jd = json.load(f)
    print(f"ℹ️ Loaded JD JSON: {jd_path}")
    return jd

# Collect JD keywords by category
def collect_jd_keywords(jd: dict):
    return {
        "required_skills": [norm(x) for x in jd.get("required_skills", [])],
        "preferred_skills": [norm(x) for x in jd.get("preferred_skills", [])],
        "weighted_keywords": {norm(k): v for k, v in jd.get("keywords_weighted", {}).items()},
        "domain_tags": [norm(x) for x in jd.get("domain_tags", [])],
        "responsibilities": [norm(x) for x in jd.get("responsibilities", [])],
        "education": [norm(x) for x in jd.get("education_requirements", []) + jd.get("certifications_required", [])],
    }

# Collect resume tokens
def collect_resume_tokens(resume: dict) -> set:
    tokens = set()
    # Handle None canonical_skills
    canonical_skills = resume.get("canonical_skills") or {}
    if isinstance(canonical_skills, dict):
        for cat_vals in canonical_skills.values():
            if isinstance(cat_vals, list):
                tokens.update(norm(v) for v in cat_vals if v)
    
    # Handle None inferred_skills
    inferred_skills = resume.get("inferred_skills") or []
    if isinstance(inferred_skills, list):
        for inf in inferred_skills:
            if isinstance(inf, dict) and inf.get("skill") and inf.get("confidence", 0) >= 0.6:
                tokens.add(norm(inf["skill"]))
    
    # Handle None skill_proficiency
    skill_proficiency = resume.get("skill_proficiency") or []
    if isinstance(skill_proficiency, list):
        for sp in skill_proficiency:
            if isinstance(sp, dict) and sp.get("skill"):
                tokens.add(norm(sp["skill"]))
    
    # Handle None projects
    projects = resume.get("projects") or []
    if isinstance(projects, list):
        for proj in projects:
            if isinstance(proj, dict):
                tech_keywords = proj.get("tech_keywords") or []
                primary_skills = proj.get("primary_skills") or []
                if isinstance(tech_keywords, list):
                    tokens.update(norm(x) for x in tech_keywords)
                if isinstance(primary_skills, list):
                    tokens.update(norm(x) for x in primary_skills)
    
    # Handle None experience_entries
    experience_entries = resume.get("experience_entries") or []
    if isinstance(experience_entries, list):
        for exp in experience_entries:
            if isinstance(exp, dict):
                primary_tech = exp.get("primary_tech") or []
                responsibilities_keywords = exp.get("responsibilities_keywords") or []
                if isinstance(primary_tech, list):
                    tokens.update(norm(x) for x in primary_tech)
                if isinstance(responsibilities_keywords, list):
                    tokens.update(norm(x) for x in responsibilities_keywords)
    for phrase in [resume.get("profile_keywords_line") or "", resume.get("ats_boost_line") or ""]:
        parts = [p.strip() for p in phrase.replace("/", ",").replace(";", ",").split(",") if p.strip()]
        tokens.update(norm(p) for p in parts)
        tokens.update(norm(w) for w in phrase.split())
    tokens.update(norm(x) for x in resume.get("domain_tags", []))
    return tokens

# Keyword overlap score
def score_overlap(jd_list, resume_tokens):
    if not jd_list: return 0.5
    matched = sum(1 for x in jd_list if x in resume_tokens)
    return matched / len(jd_list)

# Weighted keywords
def score_weighted_keywords(jd_kw: dict, resume_tokens: set) -> float:
    if not jd_kw: return 0.5
    matched, total = 0.0, sum(jd_kw.values())
    for kw, w in jd_kw.items():
        if kw in resume_tokens:
            matched += w
    return matched / total if total > 0 else 0.5

# Project metrics
def score_project_metrics(resume: dict) -> float:
    projects = resume.get("projects") or []
    if not projects: return 0.5
    scores = []
    for proj in projects:
        metrics = proj.get("metrics") or {}
        vals = [metrics.get("skill_relevance",0),
                metrics.get("domain_relevance",0),
                metrics.get("execution_quality",0)]
        if vals: scores.append(sum(vals)/len(vals))
    return sum(scores)/len(scores) if scores else 0.5

# Experience keyword score
def score_experience_keywords(resume: dict) -> float:
    text_sources = []
    for exp in resume.get("experience_entries", []):
        text_sources.extend(exp.get("responsibilities_keywords", []))
        text_sources.extend(exp.get("achievements", []))
    text_sources.append(resume.get("profile_keywords_line") or "")
    text_sources.append(resume.get("ats_boost_line") or "")
    joined = " ".join([norm(t) for t in text_sources])
    matched = sum(w for kw, w in EXPERIENCE_KEYWORD_WEIGHTS.items() if kw in joined)
    max_possible = sum(EXPERIENCE_KEYWORD_WEIGHTS.values())
    return matched / max_possible if max_possible > 0 else 0.0

# Main
# def main():
#     if not PROCESSED_JSON_DIR.exists():
#         print(f"❌ ProcessedJson dir not found", file=sys.stderr)
#         sys.exit(1)

#     jd = load_jd_json()
#     if jd is None: sys.exit(1)

#     weights = DEFAULT_WEIGHTS.copy()
#     weights.update(jd.get("weighting", {}))
#     jd_keywords = collect_jd_keywords(jd)

#     resume_files = [p for p in PROCESSED_JSON_DIR.glob("*.json") if p.name != SKIP_FILENAME]
#     if not resume_files:
#         print(f"⚠️ No resumes found", file=sys.stderr); sys.exit(0)

#     results = []
#     for rfile in resume_files:
#         with rfile.open("r", encoding="utf-8") as f: resume = json.load(f)
#         name = resume.get("name") or rfile.stem
#         tokens = collect_resume_tokens(resume)

#         req = score_overlap(jd_keywords["required_skills"], tokens)
#         pref = score_overlap(jd_keywords["preferred_skills"], tokens)
#         weighted_kw = score_weighted_keywords(jd_keywords["weighted_keywords"], tokens)
#         domain = score_overlap(jd_keywords["domain_tags"], tokens)
#         resp = score_overlap(jd_keywords["responsibilities"], tokens)
#         edu = score_overlap(jd_keywords["education"], tokens)
#         exp = score_experience_keywords(resume)
#         proj = score_project_metrics(resume)

#         final = (
#             req*weights["required_skills"] +
#             pref*weights["preferred_skills"] +
#             weighted_kw*weights["weighted_keywords"] +
#             exp*weights["experience_keywords"] +
#             domain*weights["domain_relevance"] +
#             proj*weights["project_metrics"] +
#             resp*weights["responsibilities"] +
#             edu*weights["education"]
#         )

#         results.append({"name": name, "Keyword_Score": round(final,3)})

#     # Merge with existing Scores.json instead of overwrite
#     if OUTPUT_FILE.exists():
#         with OUTPUT_FILE.open("r", encoding="utf-8") as f:
#             try:
#                 existing = json.load(f)
#             except json.JSONDecodeError:
#                 existing = []
#     else:
#         existing = []

#     existing_map = {e["name"]: e for e in existing}

#     for r in results:
#         name = r["name"]
#         if name in existing_map:
#             # ✅ Update only Keyword_Score
#             existing_map[name]["Keyword_Score"] = r["Keyword_Score"]
#         else:
#             # ✅ New entry, keep structure consistent
#             existing_map[name] = {
#                 "name": name,
#                 "project_aggregate": None,
#                 "Keyword_Score": r["Keyword_Score"]
#             }

#     final_results = list(existing_map.values())
#         # 🔹 Normalize Keyword_Score across all candidates (0–1 range)
#     scores = [r.get("Keyword_Score", 0) for r in final_results]
#     if scores:
#         mn, mx = min(scores), max(scores)
#         if mx > mn:  # avoid divide by zero
#             for r in final_results:
#                 r["Keyword_Score"] = round((r["Keyword_Score"] - mn) / (mx - mn), 3)

#     final_results.sort(key=lambda x: x.get("Keyword_Score", 0), reverse=True)

#     print("\n🏆 Top Candidates:")
#     for r in final_results[:10]:
#         print(f"✅ {r['name']} | Keyword_Score={r['Keyword_Score']}")

#     with OUTPUT_FILE.open("w", encoding="utf-8") as f:
#         json.dump(final_results, f, indent=4)
#     print(f"\n📂 Scores merged and written to {OUTPUT_FILE}")

def main():
    if not PROCESSED_JSON_DIR.exists():
        print(f"❌ ProcessedJson dir not found", file=sys.stderr)
        sys.exit(1)

    jd = load_jd_json()
    if jd is None:
        sys.exit(1)

    weights = DEFAULT_WEIGHTS.copy()
    # Update weights from JD, but filter out None values (use defaults instead)
    jd_weighting = jd.get("weighting", {})
    for key, value in jd_weighting.items():
        if value is not None and key in weights:
            weights[key] = value
    jd_keywords = collect_jd_keywords(jd)

    # Only process files in root ProcessedJson directory (exclude FilteredResumes subdirectory)
    resume_files = [
        p for p in PROCESSED_JSON_DIR.glob("*.json") 
        if p.name != SKIP_FILENAME and p.parent == PROCESSED_JSON_DIR
    ]
    if not resume_files:
        print(f"⚠️ No resumes found", file=sys.stderr)
        sys.exit(0)

    # Check for parallel processing
    import os
    from concurrent.futures import ThreadPoolExecutor, as_completed
    
    parallel = os.getenv("ENABLE_PARALLEL", "false").lower() == "true"
    max_workers = int(os.getenv("MAX_WORKERS", "5"))
    
    def process_single_resume(rfile):
        """Process a single resume file and return result."""
        try:
            with rfile.open("r", encoding="utf-8") as f:
                resume = json.load(f)
            raw_name = resume.get("name") or rfile.stem
            name = normalize_name(raw_name)
            candidate_id = resume.get("candidate_id")
            tokens = collect_resume_tokens(resume)

            req = score_overlap(jd_keywords["required_skills"], tokens)
            pref = score_overlap(jd_keywords["preferred_skills"], tokens)
            weighted_kw = score_weighted_keywords(jd_keywords["weighted_keywords"], tokens)
            domain = score_overlap(jd_keywords["domain_tags"], tokens)
            resp = score_overlap(jd_keywords["responsibilities"], tokens)
            edu = score_overlap(jd_keywords["education"], tokens)
            exp = score_experience_keywords(resume)
            proj = score_project_metrics(resume)

            # ✅ Penalty for missing required skills (if less than 50% match, apply penalty)
            required_penalty = 0.0
            if jd_keywords["required_skills"] and req < 0.5:
                # Apply penalty: missing more than 50% of required skills reduces score
                required_penalty = (0.5 - req) * 0.3  # Up to 15% penalty

            # Ensure all weights are floats (not None) - use 0.0 as fallback
            w_req = weights.get("required_skills") or 0.0
            w_pref = weights.get("preferred_skills") or 0.0
            w_weighted = weights.get("weighted_keywords") or 0.0
            w_exp = weights.get("experience_keywords") or 0.0
            w_domain = weights.get("domain_relevance") or 0.0
            w_proj = weights.get("project_metrics") or 0.0
            w_resp = weights.get("responsibilities") or 0.0
            w_edu = weights.get("education") or 0.0
            
            final = (
                req * w_req +
                pref * w_pref +
                weighted_kw * w_weighted +
                exp * w_exp +
                domain * w_domain +
                proj * w_proj +
                resp * w_resp +
                edu * w_edu -
                required_penalty  # Apply penalty
            )
            
            # Ensure score doesn't go negative
            final = max(0.0, final)

            result = {"name": name, "Keyword_Score": round(final, 3)}
            if candidate_id:
                result["candidate_id"] = candidate_id
            return result
        except Exception as e:
            # ⚠️ Bad / irrelevant / corrupted resume → don't crash
            name = normalize_name(rfile.stem)
            print(f"⛔ ERROR processing {name} → {e}")
            return {"name": name, "Keyword_Score": 0.0}

    results = []
    if parallel and len(resume_files) > 1:
        # Parallel processing
        print(f"[INFO] Processing {len(resume_files)} resumes in parallel with {max_workers} workers...")
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single_resume, rfile): rfile for rfile in resume_files}
            
            for future in as_completed(futures):
                rfile = futures[future]
                try:
                    result = future.result()
                    if result:
                        results.append(result)
                except Exception as e:
                    print(f"⚠️ Error processing {rfile.name}: {e}")
    else:
        # Sequential processing
        for rfile in resume_files:
            result = process_single_resume(rfile)
            if result:
                results.append(result)

    # Start fresh - merge with existing scores from ProjectProcess (if any)
    # But only include candidates that exist in current ProcessedJson directory
    existing = []
    if OUTPUT_FILE.exists():
        with OUTPUT_FILE.open("r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    
    # Filter existing to only include candidates that still exist in ProcessedJson
    current_candidate_ids = set()
    current_names = set()
    for rfile in resume_files:
        try:
            with rfile.open("r", encoding="utf-8") as f:
                resume = json.load(f)
                candidate_id = resume.get("candidate_id")
                name = normalize_name(resume.get("name", "") or rfile.stem)
                if candidate_id:
                    current_candidate_ids.add(candidate_id)
                if name:
                    current_names.add(name)
        except Exception:
            continue
    
    # Filter existing entries to only keep current batch candidates
    filtered_existing = []
    for e in existing:
        e_id = e.get("candidate_id")
        e_name = normalize_name(e.get("name", ""))
        if (e_id and e_id in current_candidate_ids) or (e_name and e_name in current_names):
            filtered_existing.append(e)
    
    existing = filtered_existing

    # Build maps: prioritize candidate_id, fallback to normalized name
    existing_map_by_id = {}
    existing_map_by_name = {}
    for e in existing:
        if isinstance(e, dict):
            if e.get("candidate_id"):
                existing_map_by_id[e["candidate_id"]] = e
            if e.get("name"):
                normalized_name = normalize_name(e["name"])
                if normalized_name:
                    existing_map_by_name[normalized_name] = e

    for r in results:
        candidate_id = r.get("candidate_id")
        name = r["name"]
        keyword_score = r["Keyword_Score"]
        
        # Try to merge by candidate_id first (most reliable)
        if candidate_id and candidate_id in existing_map_by_id:
            existing_map_by_id[candidate_id]["Keyword_Score"] = keyword_score
        # Fallback to normalized name
        elif name and name in existing_map_by_name:
            existing_map_by_name[name]["Keyword_Score"] = keyword_score
        else:
            # New entry
            new_entry = {
                "name": name,
                "project_aggregate": None,
                "Keyword_Score": keyword_score
            }
            if candidate_id:
                new_entry["candidate_id"] = candidate_id
                existing_map_by_id[candidate_id] = new_entry
            if name:
                existing_map_by_name[name] = new_entry
    
    # Combine maps, prioritizing candidate_id entries
    final_results = []
    seen_ids = set()
    # First add all entries with candidate_id
    for candidate_id, entry in existing_map_by_id.items():
        if candidate_id not in seen_ids:
            # Ensure Keyword_Score is always set (default to 0.0 if missing)
            if "Keyword_Score" not in entry or entry.get("Keyword_Score") is None:
                entry["Keyword_Score"] = 0.0
            final_results.append(entry)
            seen_ids.add(candidate_id)
    # Then add entries that only exist in name map (for backward compatibility)
    for name, entry in existing_map_by_name.items():
        entry_id = entry.get("candidate_id")
        if not entry_id or entry_id not in seen_ids:
            # Ensure Keyword_Score is always set (default to 0.0 if missing)
            if "Keyword_Score" not in entry or entry.get("Keyword_Score") is None:
                entry["Keyword_Score"] = 0.0
            final_results.append(entry)
            if entry_id:
                seen_ids.add(entry_id)

    # normalize
    scores = [r.get("Keyword_Score", 0.0) for r in final_results]
    mn, mx = min(scores), max(scores)
    if mx > mn:
        for r in final_results:
            r["Keyword_Score"] = round((r.get("Keyword_Score", 0.0) - mn) / (mx - mn), 3)

    final_results.sort(key=lambda x: x.get("Keyword_Score", 0.0), reverse=True)

    print("\n🏆 Top Keyword Matches:")
    for r in final_results[:10]:
        keyword_score = r.get('Keyword_Score', 0.0)
        name = r.get('name', 'Unknown')
        print(f"✔ {name} | Keyword_Score={keyword_score}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=4)
    print(f"\n📂 Scores merged and written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

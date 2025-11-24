
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
    for cat_vals in (resume.get("canonical_skills") or {}).values():
        tokens.update(norm(v) for v in cat_vals if v)
    for inf in resume.get("inferred_skills", []):
        if inf.get("skill") and inf.get("confidence", 0) >= 0.6:
            tokens.add(norm(inf["skill"]))
    for sp in resume.get("skill_proficiency", []):
        if sp.get("skill"):
            tokens.add(norm(sp["skill"]))
    for proj in resume.get("projects", []):
        tokens.update(norm(x) for x in proj.get("tech_keywords", []))
        tokens.update(norm(x) for x in proj.get("primary_skills", []))
    for exp in resume.get("experience_entries", []):
        tokens.update(norm(x) for x in exp.get("primary_tech", []))
        tokens.update(norm(x) for x in exp.get("responsibilities_keywords", []))
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
    weights.update(jd.get("weighting", {}))
    jd_keywords = collect_jd_keywords(jd)

    resume_files = [p for p in PROCESSED_JSON_DIR.glob("*.json") if p.name != SKIP_FILENAME]
    if not resume_files:
        print(f"⚠️ No resumes found", file=sys.stderr)
        sys.exit(0)

    results = []
    for rfile in resume_files:
        try:
            with rfile.open("r", encoding="utf-8") as f:
                resume = json.load(f)
            name = resume.get("name") or rfile.stem
            tokens = collect_resume_tokens(resume)

            req = score_overlap(jd_keywords["required_skills"], tokens)
            pref = score_overlap(jd_keywords["preferred_skills"], tokens)
            weighted_kw = score_weighted_keywords(jd_keywords["weighted_keywords"], tokens)
            domain = score_overlap(jd_keywords["domain_tags"], tokens)
            resp = score_overlap(jd_keywords["responsibilities"], tokens)
            edu = score_overlap(jd_keywords["education"], tokens)
            exp = score_experience_keywords(resume)
            proj = score_project_metrics(resume)

            final = (
                req * weights["required_skills"] +
                pref * weights["preferred_skills"] +
                weighted_kw * weights["weighted_keywords"] +
                exp * weights["experience_keywords"] +
                domain * weights["domain_relevance"] +
                proj * weights["project_metrics"] +
                resp * weights["responsibilities"] +
                edu * weights["education"]
            )

            results.append({"name": name, "Keyword_Score": round(final, 3)})

        except Exception as e:
            # ⚠️ Bad / irrelevant / corrupted resume → don't crash
            name = rfile.stem
            print(f"⛔ ERROR processing {name} → {e}")
            results.append({"name": name, "Keyword_Score": 0.0})
            continue

    # ----------- merging with Scores.json ------------
    if OUTPUT_FILE.exists():
        with OUTPUT_FILE.open("r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    else:
        existing = []

    existing_map = {e.get("name"): e for e in existing if isinstance(e, dict)}

    for r in results:
        name = r["name"]
        if name in existing_map:
            existing_map[name]["Keyword_Score"] = r["Keyword_Score"]
        else:
            existing_map[name] = {
                "name": name,
                "project_aggregate": None,
                "Keyword_Score": r["Keyword_Score"]
            }

    final_results = list(existing_map.values())

    # normalize
    scores = [r.get("Keyword_Score", 0.0) for r in final_results]
    mn, mx = min(scores), max(scores)
    if mx > mn:
        for r in final_results:
            r["Keyword_Score"] = round((r.get("Keyword_Score", 0.0) - mn) / (mx - mn), 3)

    final_results.sort(key=lambda x: x.get("Keyword_Score", 0.0), reverse=True)

    print("\n🏆 Top Keyword Matches:")
    for r in final_results[:10]:
        print(f"✔ {r['name']} | Keyword_Score={r['Keyword_Score']}")

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(final_results, f, indent=4)
    print(f"\n📂 Scores merged and written to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

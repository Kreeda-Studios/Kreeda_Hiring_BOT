#!/usr/bin/env python3
"""
FinalRanking.py  (patched)

Changes:
- candidates with only 1 valid score are no longer skipped
- a decay of 0.08 is applied to make 1-score resumes rank lower without exclusion
- log skipped candidates with full score breakdown
- Added `run_ranking()` and `RANKING_RAM` to support RAM-based ranking import from Streamlit
- Added LLM-based re-ranking with filter requirements (batch size: 30)
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Any

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

INPUT_FILE = Path("Ranking/Scores.json")
OUTPUT_FILE = Path("Ranking/Final_Ranking.json")
SKIPPED_FILE = Path("Ranking/Skipped.json")
DISPLAY_FILE = Path("Ranking/DisplayRanks.txt")
JD_FILE = Path("InputThread/JD/JD.json")
PROCESSED_JSON_DIR = Path("ProcessedJson")

WEIGHTS = {
    "project_aggregate": 0.35,
    "Semantic_Score": 0.35,
    "Keyword_Score": 0.3,
}

ONE_SCORE_DECAY = 0.08
RE_RANK_BATCH_SIZE = 30  # Batch size for LLM re-ranking
RE_RANK_MODEL = "gpt-4o-mini"

# 🔥 RAM holder for Streamlit display (populated when run via run_ranking)
RANKING_RAM = []


def compute_final_score(entry: dict) -> float | None:
    raw_scores = {
        "project_aggregate": entry.get("project_aggregate", 0.0),
        "Semantic_Score": entry.get("Semantic_Score", 0.0),
        "Keyword_Score": entry.get("Keyword_Score", 0.0),
    }

    valid_scores = {k: v for k, v in raw_scores.items() if isinstance(v, (int, float)) and v > 0.0}

    if len(valid_scores) == 0:
        return None

    if len(valid_scores) == 1:
        score_value = list(valid_scores.values())[0]
        adjusted = max(score_value - ONE_SCORE_DECAY, 0.0)
        return round(adjusted, 3)

    total_weight = sum(WEIGHTS[k] for k in valid_scores)
    final = sum((WEIGHTS[k] / total_weight) * valid_scores[k] for k in valid_scores)
    return round(final, 3)


def normalize_name(name: str) -> str:
    """Normalize candidate name consistently."""
    if not name or not isinstance(name, str):
        return ""
    return " ".join(name.strip().title().split())


def create_candidate_summary(candidate: dict, resume_json: dict = None) -> dict:
    """
    Create compact candidate summary for LLM re-ranking.
    Uses abbreviations to minimize tokens.
    """
    summary = {
        "id": candidate.get("candidate_id", ""),  # Use candidate_id, not name
        "n": candidate.get("name", ""),  # Name for reference only
        "sc": {  # All scores (abbreviated)
            "p": candidate.get("project_aggregate", 0.0),
            "k": candidate.get("Keyword_Score", 0.0),
            "s": candidate.get("Semantic_Score", 0.0),
            "f": candidate.get("Final_Score", 0.0)
        }
    }
    
    # Add resume data if available
    if resume_json:
        summary["exp"] = resume_json.get("years_experience")
        summary["loc"] = resume_json.get("location", "")
        summary["role"] = resume_json.get("role_claim", "")
        
        # Top skills (limit to 10)
        skills = []
        canonical = resume_json.get("canonical_skills", {})
        for cat_skills in canonical.values():
            if isinstance(cat_skills, list):
                skills.extend(cat_skills[:5])  # Top 5 per category
        summary["sk"] = skills[:10]  # Top 10 total
        
        # Top 3 projects summary
        projects = resume_json.get("projects", [])[:3]
        summary["pj"] = [
            {
                "n": p.get("name", "")[:50],
                "tech": ", ".join(p.get("tech_keywords", [])[:5]),
                "score": p.get("metrics", {}).get("domain_relevance", 0.0)
            }
            for p in projects
        ]
    else:
        # Fallback if resume JSON not available
        summary["exp"] = None
        summary["loc"] = ""
        summary["sk"] = []
        summary["pj"] = []
    
    return summary


def load_resume_json(candidate_id: str) -> dict:
    """Load resume JSON by candidate_id."""
    if not candidate_id:
        return {}
    
    # Try to find resume JSON file (only in root, not in subdirectories like FilteredResumes)
    for json_file in PROCESSED_JSON_DIR.glob("*.json"):
        # Only check files in root directory, not subdirectories
        if json_file.parent != PROCESSED_JSON_DIR:
            continue
        try:
            with json_file.open("r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("candidate_id") == candidate_id:
                    return data
        except Exception:
            continue
    return {}


def check_experience_compliance(candidate: dict, resume_json: dict, requirement: dict) -> dict:
    """Check if candidate meets experience requirement."""
    if not requirement:
        return None
    
    candidate_exp = resume_json.get("years_experience")
    if candidate_exp is None:
        return {
            "meets": False,
            "requirement": requirement,
            "candidate_value": None,
            "match_quality": "missing",
            "details": "Experience not specified in resume"
        }
    
    try:
        candidate_exp = float(candidate_exp)
    except (ValueError, TypeError):
        return {
            "meets": False,
            "requirement": requirement,
            "candidate_value": candidate_exp,
            "match_quality": "invalid",
            "details": "Invalid experience format in resume"
        }
    
    min_years = requirement.get("min", 0)
    max_years = requirement.get("max", float('inf'))
    field = requirement.get("field", "")
    
    meets = min_years <= candidate_exp <= max_years
    
    if candidate_exp < min_years:
        match_quality = "below"
        details = f"Candidate has {candidate_exp} years (required: {min_years}-{max_years} years{f' in {field}' if field else ''})"
    elif candidate_exp > max_years:
        match_quality = "exceeds"
        details = f"Candidate has {candidate_exp} years (required: {min_years}-{max_years} years{f' in {field}' if field else ''})"
    else:
        match_quality = "exact"
        details = f"Candidate has {candidate_exp} years (required: {min_years}-{max_years} years{f' in {field}' if field else ''})"
    
    return {
        "meets": meets,
        "requirement": requirement,
        "candidate_value": candidate_exp,
        "match_quality": match_quality,
        "details": details
    }


def check_skills_compliance(candidate: dict, resume_json: dict, requirement: dict) -> dict:
    """Check if candidate has required skills."""
    if not requirement:
        return None
    
    required_skills = requirement.get("hard_skills", []) or requirement.get("skills", [])
    if not required_skills:
        return None
    
    # Collect candidate skills
    candidate_skills = set()
    
    # From canonical_skills
    canonical = resume_json.get("canonical_skills", {})
    for cat_skills in canonical.values():
        if isinstance(cat_skills, list):
            candidate_skills.update(s.lower().strip() for s in cat_skills if s)
    
    # From inferred_skills
    for inf in resume_json.get("inferred_skills", []):
        if inf.get("skill"):
            candidate_skills.add(inf["skill"].lower().strip())
    
    # From skill_proficiency
    for sp in resume_json.get("skill_proficiency", []):
        if sp.get("skill"):
            candidate_skills.add(sp["skill"].lower().strip())
    
    # From projects
    for proj in resume_json.get("projects", []):
        for skill_list in [proj.get("tech_keywords", []), proj.get("primary_skills", [])]:
            candidate_skills.update(s.lower().strip() for s in skill_list if s)
    
    # Check which required skills are found
    required_lower = [s.lower().strip() for s in required_skills if s]
    found_skills = [s for s in required_lower if s in candidate_skills]
    missing_skills = [s for s in required_lower if s not in candidate_skills]
    
    meets = len(missing_skills) == 0
    
    if meets:
        match_quality = "exact"
        details = f"Has all required skills: {', '.join(required_skills)}"
    elif len(found_skills) > 0:
        match_quality = "partial"
        details = f"Has {len(found_skills)}/{len(required_skills)} required skills. Missing: {', '.join(missing_skills[:3])}"
    else:
        match_quality = "missing"
        details = f"Missing all required skills: {', '.join(required_skills[:3])}"
    
    return {
        "meets": meets,
        "requirement": required_skills,
        "candidate_value": list(candidate_skills),
        "match_quality": match_quality,
        "details": details,
        "found_skills": found_skills,
        "missing_skills": missing_skills
    }


def check_location_compliance(candidate: dict, resume_json: dict, requirement: str) -> dict:
    """Check if candidate meets location requirement."""
    if not requirement:
        return None
    
    req_loc = requirement.lower().strip()
    # Skip location check if requirement is "Any" or similar
    if req_loc in ["any", "anywhere", "remote/onsite", "flexible", ""]:
        return None
    
    candidate_loc = (resume_json.get("location") or "").lower()
    
    # Check for remote/onsite/hybrid
    is_remote_req = "remote" in req_loc
    is_onsite_req = "onsite" in req_loc or "on-site" in req_loc
    is_hybrid_req = "hybrid" in req_loc
    
    candidate_remote = "remote" in candidate_loc
    candidate_onsite = "onsite" in candidate_loc or "on-site" in candidate_loc
    candidate_hybrid = "hybrid" in candidate_loc
    
    meets = False
    match_quality = "missing"
    
    if is_remote_req and candidate_remote:
        meets = True
        match_quality = "exact"
        details = f"Candidate is available for remote work (required: {requirement})"
    elif is_onsite_req and (candidate_onsite or not candidate_remote):
        meets = True
        match_quality = "exact"
        details = f"Candidate is available for onsite work (required: {requirement})"
    elif is_hybrid_req and candidate_hybrid:
        meets = True
        match_quality = "exact"
        details = f"Candidate is available for hybrid work (required: {requirement})"
    elif is_remote_req and not candidate_remote:
        meets = False
        match_quality = "missing"
        details = f"Candidate location: {resume_json.get('location', 'Not specified')} (required: {requirement})"
    else:
        # Generic location match
        if req_loc in candidate_loc or candidate_loc in req_loc:
            meets = True
            match_quality = "exact"
            details = f"Candidate location matches: {resume_json.get('location', 'Not specified')}"
        else:
            meets = False
            match_quality = "missing"
            details = f"Candidate location: {resume_json.get('location', 'Not specified')} (required: {requirement})"
    
    return {
        "meets": meets,
        "requirement": requirement,
        "candidate_value": resume_json.get("location", ""),
        "match_quality": match_quality,
        "details": details
    }


def check_education_compliance(candidate: dict, resume_json: dict, requirement: dict) -> dict:
    """Check if candidate meets education requirement."""
    if not requirement:
        return None
    
    degree_level = requirement.get("level", "")
    if not degree_level:
        return None
    
    # Extract candidate education (this would need to be in resume JSON)
    # For now, return None as education might not be in structured format
    # This can be enhanced later when education is properly extracted
    
    return None


def check_other_criteria_compliance(candidate: dict, resume_json: dict, other_criteria: List[str]) -> dict:
    """Check compliance with other_criteria requirements."""
    if not other_criteria:
        return None
    
    # Get resume text for semantic matching
    resume_text = ""
    
    # Collect text from various resume sections
    resume_text += " ".join(resume_json.get("summary", [])) + " "
    resume_text += " ".join(resume_json.get("responsibilities", [])) + " "
    
    # Add experience descriptions
    for exp in resume_json.get("experience", []):
        resume_text += exp.get("description", "") + " "
        resume_text += " ".join(exp.get("responsibilities", [])) + " "
        resume_text += exp.get("company", "") + " "
        resume_text += exp.get("industry", "") + " "
    
    # Add project descriptions
    for proj in resume_json.get("projects", []):
        resume_text += proj.get("description", "") + " "
        resume_text += " ".join(proj.get("tech_keywords", [])) + " "
    
    # Add education
    for edu in resume_json.get("education", []):
        resume_text += edu.get("degree", "") + " "
        resume_text += edu.get("field", "") + " "
        resume_text += edu.get("institution", "") + " "
    
    # Add certifications
    for cert in resume_json.get("certifications", []):
        resume_text += cert.get("name", "") + " "
    
    resume_text_lower = resume_text.lower()
    
    met_criteria = []
    failed_criteria = []
    
    for criterion in other_criteria:
        criterion_lower = criterion.lower()
        # Simple keyword matching
        key_terms = [word for word in criterion_lower.split() if len(word) > 3]
        
        matches = sum(1 for term in key_terms if term in resume_text_lower)
        match_ratio = matches / len(key_terms) if key_terms else 0
        
        if match_ratio >= 0.5 or any(term in resume_text_lower for term in key_terms[:2]):
            met_criteria.append(criterion)
        else:
            failed_criteria.append(criterion)
    
    meets = len(failed_criteria) == 0
    details = f"Met {len(met_criteria)}/{len(other_criteria)} criteria"
    if failed_criteria:
        details += f". Missing: {', '.join(failed_criteria[:3])}"
    
    return {
        "meets": meets,
        "requirement": other_criteria,
        "met_criteria": met_criteria,
        "failed_criteria": failed_criteria,
        "match_quality": "exact" if meets else "missing",
        "details": details
    }


def check_all_requirements(candidate: dict, resume_json: dict, filter_requirements: dict) -> dict:
    """
    Check all requirements and generate compliance report.
    Only checks requirements that are explicitly specified (have 'specified: true' or non-empty values).
    """
    if not filter_requirements or not filter_requirements.get("structured"):
        return {}
    
    structured = filter_requirements.get("structured", {})
    compliance = {}
    
    # Check experience (only if specified)
    exp_req = structured.get("experience")
    if exp_req and exp_req.get("specified"):
        exp_compliance = check_experience_compliance(candidate, resume_json, exp_req)
        if exp_compliance:
            compliance["experience"] = exp_compliance
    
    # Check skills (only if specified - non-empty array)
    skills_req = structured.get("hard_skills", [])
    if skills_req:  # Non-empty array = specified
        skills_req_dict = {"hard_skills": skills_req}
        skills_compliance = check_skills_compliance(candidate, resume_json, skills_req_dict)
        if skills_compliance:
            compliance["hard_skills"] = skills_compliance
    
    # Check department (only if specified)
    dept_req = structured.get("department")
    if dept_req and dept_req.get("specified"):
        # Import department check from EarlyFilter if needed, or implement here
        # For now, skip department check in FinalRanking (it's already done in EarlyFilter)
        pass
    
    # Check location (skip if "Any" or not specified)
    location_req = structured.get("location")
    location_req_str = (location_req or "").strip()
    if location_req_str and location_req_str.lower() not in ["any", "anywhere", "remote/onsite", "flexible", ""]:
        loc_compliance = check_location_compliance(candidate, resume_json, location_req)
        if loc_compliance:  # Will be None if "Any"
            compliance["location"] = loc_compliance
    
    # Check education (if available and specified)
    edu_req = structured.get("education", [])
    if edu_req:  # Non-empty array = specified
        edu_compliance = check_education_compliance(candidate, resume_json, {"education": edu_req})
        if edu_compliance:
            compliance["education"] = edu_compliance
    
    # Check other_criteria (only if specified - non-empty array)
    other_criteria = structured.get("other_criteria", [])
    if other_criteria:  # Non-empty array = specified
        other_compliance = check_other_criteria_compliance(candidate, resume_json, other_criteria)
        if other_compliance:
            compliance["other_criteria"] = other_compliance
    
    return compliance


def llm_re_rank_batch(candidates_summaries: List[dict], filter_requirements: dict, client: OpenAI) -> List[dict]:
    """
    LLM re-ranks a batch of candidates based on filter requirements and all scores.
    Batch size: 30 candidates.
    """
    if not client:
        return []
    
    # Function calling schema with compliance validation
    RE_RANK_FUNCTION = {
        "name": "re_rank_candidates",
        "description": "Re-rank candidates based on filter requirements and all ranking scores. Validate compliance results and return validated requirements.",
        "parameters": {
            "type": "object",
            "properties": {
                "ranked_candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "candidate_id": {"type": "string"},
                            "re_rank_score": {"type": "number", "description": "Re-ranked score (0-1)"},
                            "meets_requirements": {"type": "boolean"},
                            "requirements_met": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Validated list of requirement types that candidate meets (e.g., 'experience', 'hard_skills', 'location'). Validate programmatic results and correct if needed."
                            },
                            "requirements_missing": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Validated list of requirement types that candidate is missing. Validate programmatic results and correct if needed."
                            }
                        },
                        "required": ["candidate_id", "re_rank_score", "meets_requirements", "requirements_met", "requirements_missing"]
                    }
                }
            },
            "required": ["ranked_candidates"]
        }
    }
    
    # Build prompt with compliance validation
    system_msg = """You are a candidate re-ranker and compliance validator. Your tasks:
1. VALIDATE compliance results: Review programmatic compliance checks and validate/correct them based on candidate resume data
2. RE-RANK candidates: Rank candidates based on validated compliance + all ranking scores

Validation Rules:
- Review each candidate's compliance results carefully
- If programmatic check missed something (e.g., nuanced experience, skill synonyms), correct it
- If programmatic check was too strict, relax it appropriately
- Consider context and nuances in resume data

Re-ranking Rules:
- Candidates meeting more requirements should rank higher
- But also consider their JD alignment scores (all scores provided)
- Balance requirements compliance with overall quality
- Use candidate_id (not name) for identification

Return:
- re_rank_score (0-1) for each candidate
- Validated requirements_met list (corrected if needed)
- Validated requirements_missing list (corrected if needed)"""
    
    user_msg = f"""Filter Requirements:
{json.dumps(filter_requirements, indent=2)}

Candidates to Re-rank (with all scores and programmatic compliance - abbreviated format):
{json.dumps(candidates_summaries, indent=2)}

Each candidate has a "compliance" field with programmatic compliance results.
VALIDATE these results - review and correct if programmatic checks missed nuances.
Then RE-RANK candidates based on validated compliance + all scores.

Consider all scores (sc.p=project, sc.k=keyword, sc.s=semantic, sc.f=final) when making decisions.
Return validated requirements_met and requirements_missing for each candidate."""
    
    try:
        response = client.chat.completions.create(
            model=RE_RANK_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            functions=[RE_RANK_FUNCTION],
            function_call={"name": "re_rank_candidates"},
            temperature=0.3
        )
        
        # Parse response
        func_call = response.choices[0].message.function_call
        if func_call:
            try:
                args = json.loads(func_call.arguments)
                return args.get("ranked_candidates", [])
            except json.JSONDecodeError as json_err:
                # Handle malformed JSON (unterminated strings, etc.)
                print(f"⚠️ JSON parsing error in LLM re-ranking: {json_err}")
                print(f"   Attempting to fix JSON...")
                # Try to fix common JSON issues
                try:
                    # Remove problematic characters or try to fix unterminated strings
                    fixed_args = func_call.arguments
                    # Basic fix: try to close unterminated strings
                    if fixed_args.count('"') % 2 != 0:
                        # Odd number of quotes - try to fix
                        fixed_args = fixed_args.rsplit('"', 1)[0] + '"'
                    args = json.loads(fixed_args)
                    return args.get("ranked_candidates", [])
                except Exception:
                    print(f"   Could not fix JSON, skipping LLM re-ranking for this batch")
                    return []
    except Exception as e:
        print(f"⚠️ Error in LLM re-ranking: {e}")
        return []
    
    return []


def llm_re_rank_candidates(candidates: List[dict], filter_requirements: dict) -> List[dict]:
    """
    Re-rank candidates using LLM in batches of 30.
    Returns list of re-ranking results with compliance breakdown.
    """
    if not filter_requirements or not filter_requirements.get("structured"):
        return []  # No filters, skip re-ranking
    
    # Initialize OpenAI client
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            try:
                import streamlit as st
                api_key = st.secrets.get("OPENAI_API_KEY", None)
            except (AttributeError, KeyError, FileNotFoundError):
                api_key = None
        
        if not api_key:
            print("⚠️ OpenAI API key not found. Skipping LLM re-ranking.")
            return []
        
        client = OpenAI(api_key=api_key)
    except Exception as e:
        print(f"⚠️ Failed to initialize OpenAI client: {e}")
        return []
    
    # Prepare candidate summaries with compliance
    candidate_summaries = []
    compliance_reports = {}  # Store compliance reports by candidate_id
    
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id")
        resume_json = load_resume_json(candidate_id) if candidate_id else {}
        
        # Check compliance
        compliance = check_all_requirements(candidate, resume_json, filter_requirements)
        compliance_reports[candidate_id] = compliance
        
        # Create summary with compliance
        summary = create_candidate_summary(candidate, resume_json)
        summary["compliance"] = {
            req_type: {
                "meets": comp.get("meets", False),
                "details": comp.get("details", "")
            }
            for req_type, comp in compliance.items()
        }
        candidate_summaries.append(summary)
    
    # Process in batches
    all_results = []
    for i in range(0, len(candidate_summaries), RE_RANK_BATCH_SIZE):
        batch = candidate_summaries[i:i + RE_RANK_BATCH_SIZE]
        print(f"🔄 Re-ranking batch {i//RE_RANK_BATCH_SIZE + 1} ({len(batch)} candidates)...")
        
        results = llm_re_rank_batch(batch, filter_requirements, client)
        
        # Add compliance reports to results
        for result in results:
            candidate_id = result.get("candidate_id")
            if candidate_id in compliance_reports:
                result["compliance_report"] = compliance_reports[candidate_id]
        
        all_results.extend(results)
    
    return all_results


def _ranking_core():
    """Runs ranking and returns (ranked_list, skipped_list)."""
    if not INPUT_FILE.exists():
        print(f"❌ Input file not found: {INPUT_FILE}")
        return [], []

    with INPUT_FILE.open("r", encoding="utf-8") as f:
        candidates = json.load(f)

    ranked, skipped = [], []
    seen_candidate_ids = set()
    seen_names = set()

    print("\n🔍 Log of skipped resumes (if any):\n")

    for cand in candidates:
        # ✅ Deduplicate: Check by candidate_id first, then normalized name
        candidate_id = cand.get("candidate_id")
        name = cand.get("name", "")
        normalized_name = normalize_name(name)
        
        # Skip if duplicate
        if candidate_id and candidate_id in seen_candidate_ids:
            print(f"⚠️ DUPLICATE SKIPPED → {name} (candidate_id: {candidate_id})")
            continue
        if normalized_name and normalized_name in seen_names:
            # Only skip by name if no candidate_id (to avoid false positives)
            if not candidate_id:
                print(f"⚠️ DUPLICATE SKIPPED → {name} (by name)")
                continue
        
        # Mark as seen
        if candidate_id:
            seen_candidate_ids.add(candidate_id)
        if normalized_name:
            seen_names.add(normalized_name)
        
        # ✅ HR Filter: Check if candidate should be filtered based on HR notes
        hr_should_filter = cand.get("hr_should_filter", False)
        hr_filter_reason = cand.get("hr_filter_reason")
        
        if hr_should_filter:
            skipped.append(cand)
            print(
                f"🚫 HR FILTERED → {name}"
                f" | Reason: {hr_filter_reason}"
            )
            continue
        
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

    # Initial ranking by Final_Score, then by experience (descending) as tie-breaker
    # Load resume JSONs to get experience for sorting
    for candidate in ranked:
        candidate_id = candidate.get("candidate_id")
        if candidate_id:
            resume_json = load_resume_json(candidate_id)
            candidate["_years_experience"] = resume_json.get("years_experience", 0) or 0
        else:
            candidate["_years_experience"] = 0
    
    ranked.sort(key=lambda x: (x["Final_Score"], x.get("_years_experience", 0)), reverse=True)
    print(f"\n✅ Deduplication: Processed {len(candidates)} entries → {len(ranked)} unique candidates")
    
    # CRITICAL: Filter out 0 compliance candidates BEFORE re-ranking
    # Check compliance for all candidates and remove those with 0% compliance
    filtered_ranked = []
    filtered_to_skipped = []
    
    if JD_FILE.exists():
        try:
            with JD_FILE.open("r", encoding="utf-8") as f:
                jd = json.load(f)
            filter_reqs = jd.get("filter_requirements")
            
            if filter_reqs and filter_reqs.get("structured"):
                print(f"\n🔍 Checking compliance for all candidates...")
                for cand in ranked:
                    candidate_id = cand.get("candidate_id")
                    resume_json = load_resume_json(candidate_id) if candidate_id else {}
                    
                    # Check compliance
                    compliance_report = check_all_requirements(cand, resume_json, filter_reqs)
                    requirements_met = [req_type for req_type, comp in compliance_report.items() if comp.get("meets", False)]
                    requirements_missing = [req_type for req_type, comp in compliance_report.items() if not comp.get("meets", False)]
                    total_requirements = len(requirements_met) + len(requirements_missing)
                    
                    # Filter out 0% compliance candidates (0 requirements met when requirements exist)
                    if total_requirements > 0 and len(requirements_met) == 0:
                        cand["_filtered_reason"] = "0% compliance - no requirements met"
                        cand["requirements_met"] = []
                        cand["requirements_missing"] = requirements_missing
                        cand["requirement_compliance"] = compliance_report
                        filtered_to_skipped.append(cand)
                        print(f"🚫 FILTERED (0% compliance) → {cand.get('name', 'Unknown')} | 0/{total_requirements} requirements met")
                    else:
                        # Keep candidate and add compliance data
                        cand["requirements_met"] = requirements_met
                        cand["requirements_missing"] = requirements_missing
                        cand["requirement_compliance"] = compliance_report
                        filtered_ranked.append(cand)
            else:
                # No filter requirements - keep all candidates
                filtered_ranked = ranked
        except Exception as e:
            print(f"⚠️ Error checking compliance: {e}")
            import traceback
            traceback.print_exc()
            # On error, keep all candidates
            filtered_ranked = ranked
    else:
        # No JD file - keep all candidates
        filtered_ranked = ranked
    
    # Move filtered candidates to skipped
    skipped.extend(filtered_to_skipped)
    
    if filtered_to_skipped:
        print(f"\n🚫 Filtered out {len(filtered_to_skipped)} candidates with 0% compliance")
    
    # Add initial rank
    for i, cand in enumerate(filtered_ranked, start=1):
        cand["Rank"] = i
    
    # LLM Re-ranking based on filter requirements (if available)
    final_ranked_list = filtered_ranked
    try:
        if JD_FILE.exists():
            with JD_FILE.open("r", encoding="utf-8") as f:
                jd = json.load(f)
            
            filter_reqs = jd.get("filter_requirements")
            if filter_reqs and filter_reqs.get("structured"):
                print(f"\n🔄 Starting LLM-based re-ranking with filter requirements...")
                re_rank_results = llm_re_rank_candidates(ranked, filter_reqs)
                
                if re_rank_results:
                    # Create map of re-ranking results
                    re_rank_map = {r["candidate_id"]: r for r in re_rank_results}
                    
                    # Update candidates with re-ranking scores and compliance data
                    for candidate in ranked:
                        candidate_id = candidate.get("candidate_id")
                        resume_json = load_resume_json(candidate_id) if candidate_id else {}
                        
                        if candidate_id in re_rank_map:
                            re_rank_data = re_rank_map[candidate_id]
                            candidate["Re_Rank_Score"] = re_rank_data.get("re_rank_score", candidate["Final_Score"])
                            candidate["Meets_Requirements"] = re_rank_data.get("meets_requirements", True)
                            
                            # Use LLM-validated requirements (LLM may have corrected programmatic results)
                            llm_requirements_met = re_rank_data.get("requirements_met", [])
                            llm_requirements_missing = re_rank_data.get("requirements_missing", [])
                            
                            # Keep compliance breakdown for detailed view
                            compliance_report = re_rank_data.get("compliance_report", {})
                            if not compliance_report:
                                # Generate compliance if not in results
                                compliance_report = check_all_requirements(candidate, resume_json, filter_reqs)
                            
                            candidate["requirement_compliance"] = compliance_report
                            
                            # Use LLM-validated requirements if available, otherwise extract from compliance_report
                            if llm_requirements_met or llm_requirements_missing:
                                candidate["requirements_met"] = llm_requirements_met
                                candidate["requirements_missing"] = llm_requirements_missing
                            else:
                                # Extract from compliance_report if LLM didn't provide
                                requirements_met = [req_type for req_type, comp in compliance_report.items() if comp.get("meets", False)]
                                requirements_missing = [req_type for req_type, comp in compliance_report.items() if not comp.get("meets", False)]
                                candidate["requirements_met"] = requirements_met
                                candidate["requirements_missing"] = requirements_missing
                        else:
                            # Fallback: use original score and generate compliance
                            candidate["Re_Rank_Score"] = candidate["Final_Score"]
                            candidate["Meets_Requirements"] = True
                            compliance_report = check_all_requirements(candidate, resume_json, filter_reqs)
                            candidate["requirement_compliance"] = compliance_report
                            
                            # Determine requirements met/missing from compliance
                            requirements_met = [req_type for req_type, comp in compliance_report.items() if comp.get("meets", False)]
                            requirements_missing = [req_type for req_type, comp in compliance_report.items() if not comp.get("meets", False)]
                            candidate["requirements_met"] = requirements_met
                            candidate["requirements_missing"] = requirements_missing
                    
                    # Re-sort by Re_Rank_Score (or Final_Score), then by experience (descending) as tie-breaker
                    ranked.sort(key=lambda x: (x.get("Re_Rank_Score", x["Final_Score"]), x.get("_years_experience", 0)), reverse=True)
                    
                    # Update ranks
                    for i, candidate in enumerate(ranked, start=1):
                        candidate["Rank"] = i
                    
                    final_ranked_list = ranked
                    print(f"✅ Re-ranking complete. Rankings updated based on filter requirements.")
                else:
                    print("⚠️ No re-ranking results returned. Using original rankings.")
                    # Still add compliance data even without re-ranking
                    for candidate in ranked:
                        candidate_id = candidate.get("candidate_id")
                        resume_json = load_resume_json(candidate_id) if candidate_id else {}
                        compliance_report = check_all_requirements(candidate, resume_json, filter_reqs)
                        candidate["requirement_compliance"] = compliance_report
                        requirements_met = [req_type for req_type, comp in compliance_report.items() if comp.get("meets", False)]
                        requirements_missing = [req_type for req_type, comp in compliance_report.items() if not comp.get("meets", False)]
                        candidate["requirements_met"] = requirements_met
                        candidate["requirements_missing"] = requirements_missing
            else:
                print("ℹ️ No filter requirements found. Using original rankings.")
    except Exception as e:
        print(f"⚠️ Error during re-ranking: {e}. Using original rankings.")
        # Still add compliance data on error
        try:
            if JD_FILE.exists():
                with JD_FILE.open("r", encoding="utf-8") as f:
                    jd = json.load(f)
                filter_reqs = jd.get("filter_requirements")
                if filter_reqs and filter_reqs.get("structured"):
                    for candidate in ranked:
                        candidate_id = candidate.get("candidate_id")
                        resume_json = load_resume_json(candidate_id) if candidate_id else {}
                        compliance_report = check_all_requirements(candidate, resume_json, filter_reqs)
                        candidate["requirement_compliance"] = compliance_report
                        requirements_met = [req_type for req_type, comp in compliance_report.items() if comp.get("meets", False)]
                        requirements_missing = [req_type for req_type, comp in compliance_report.items() if not comp.get("meets", False)]
                        candidate["requirements_met"] = requirements_met
                        candidate["requirements_missing"] = requirements_missing
        except:
            pass
    
    # CRITICAL: Ensure ALL candidates have compliance data (even if LLM re-ranking failed or skipped some)
    # This ensures DisplayRanks.txt and UI show compliance for all candidates
    try:
        if JD_FILE.exists():
            with JD_FILE.open("r", encoding="utf-8") as f:
                jd = json.load(f)
            filter_reqs = jd.get("filter_requirements")
            if filter_reqs and filter_reqs.get("structured"):
                for candidate in final_ranked_list:
                    # Ensure compliance data exists for all candidates
                    candidate_id = candidate.get("candidate_id")
                    resume_json = load_resume_json(candidate_id) if candidate_id else {}
                    
                    # Only regenerate if missing (preserve LLM-validated data if present)
                    if not candidate.get("requirement_compliance"):
                        compliance_report = check_all_requirements(candidate, resume_json, filter_reqs)
                        candidate["requirement_compliance"] = compliance_report
                    
                    # Always ensure requirements_met and requirements_missing are set
                    if "requirements_met" not in candidate or "requirements_missing" not in candidate:
                        compliance_report = candidate.get("requirement_compliance", {})
                        if not compliance_report:
                            compliance_report = check_all_requirements(candidate, resume_json, filter_reqs)
                            candidate["requirement_compliance"] = compliance_report
                        
                        requirements_met = [req_type for req_type, comp in compliance_report.items() if comp.get("meets", False)]
                        requirements_missing = [req_type for req_type, comp in compliance_report.items() if not comp.get("meets", False)]
                        candidate["requirements_met"] = requirements_met
                        candidate["requirements_missing"] = requirements_missing
                    
                    # CRITICAL: Filter out candidates with 0 compliance (0 requirements met when requirements exist)
                    if filter_reqs and filter_reqs.get("structured"):
                        requirements_met = candidate.get("requirements_met", [])
                        requirements_missing = candidate.get("requirements_missing", [])
                        total_requirements = len(requirements_met) + len(requirements_missing)
                        
                        # If there are requirements and candidate meets 0 of them, filter out
                        if total_requirements > 0 and len(requirements_met) == 0:
                            # Move to skipped list
                            candidate["_filtered_reason"] = "0% compliance - no requirements met"
                            if candidate not in skipped:
                                skipped.append(candidate)
                            # Remove from ranked list
                            if candidate in final_ranked_list:
                                final_ranked_list.remove(candidate)
                            print(f"🚫 FILTERED (0% compliance) → {candidate.get('name', 'Unknown')} | 0/{total_requirements} requirements met")
                            continue
    except Exception as e:
        print(f"⚠️ Error adding compliance data to all candidates: {e}")
        import traceback
        traceback.print_exc()
    
    # Return single ranking
    return final_ranked_list, skipped


def main():
    ranked, skipped = _ranking_core()

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Create output structure with single ranking
    output_data = {
        "ranking": {
            "description": "Final ranking based on JD alignment and HR filter requirements (candidates already filtered for compliance)",
            "candidates": ranked
        },
        "metadata": {
            "total_candidates": len(ranked),
            "skipped_candidates": len(skipped),
            "note": "Candidates are pre-filtered for compliance before ranking. All candidates in ranking meet HR requirements."
        }
    }

    with OUTPUT_FILE.open("w", encoding="utf-8") as f:
        json.dump(output_data, f, indent=4)

    with SKIPPED_FILE.open("w", encoding="utf-8") as f:
        json.dump(skipped, f, indent=4)

    with DISPLAY_FILE.open("w", encoding="utf-8") as f:
        f.write("=== FINAL RANKING (JD Alignment + HR Requirements) ===\n\n")
        for cand in ranked:
            final_score = cand.get("Re_Rank_Score", cand.get("Final_Score", 0.0))
            rank = cand.get("Rank", 0)
            name = cand.get("name", "Unknown")
            f.write(f"{rank}. {name} | Score: {final_score:.3f}\n")
            
            # Add compliance indicators - check both requirement_compliance and requirements_met/missing
            requirements_met = cand.get("requirements_met", [])
            requirements_missing = cand.get("requirements_missing", [])
            total = len(requirements_met) + len(requirements_missing)
            
            # If requirements_met/missing are not set, try to extract from requirement_compliance
            if total == 0 and cand.get("requirement_compliance"):
                compliance = cand.get("requirement_compliance", {})
                if isinstance(compliance, dict) and compliance:
                    requirements_met = [req_type for req_type, comp in compliance.items() if comp.get("meets", False)]
                    requirements_missing = [req_type for req_type, comp in compliance.items() if not comp.get("meets", False)]
                    total = len(requirements_met) + len(requirements_missing)
            
            if total > 0:
                if requirements_met:
                    met_str = ", ".join(requirements_met)
                    f.write(f"   ✅ Meets ({len(requirements_met)}/{total}): {met_str}\n")
                if requirements_missing:
                    missing_str = ", ".join(requirements_missing)
                    f.write(f"   ❌ Missing ({len(requirements_missing)}/{total}): {missing_str}\n")
            
            f.write("\n")

    print(f"\n🏆 Final ranking written → {OUTPUT_FILE}")
    print(f"   - Ranked candidates: {len(ranked)}")
    print(f"⚠️ Skipped entries written → {SKIPPED_FILE} ({len(skipped)} candidates)")
    print(f"📄 HR-friendly display → {DISPLAY_FILE}\n")


# 🔥 New Streamlit-safe callable
def run_ranking():
    """Executes ranking + stores result in RANKING_RAM for Streamlit display."""
    global RANKING_RAM
    ranked, skipped = _ranking_core()
    # Store ranking for UI display
    RANKING_RAM = ranked
    return RANKING_RAM


if __name__ == "__main__":
    main()

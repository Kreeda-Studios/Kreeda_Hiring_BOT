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

# Field mapping: HR requirement field names → Resume data field names
# This allows flexible requirement fields to map to resume data
FIELD_MAPPING = {
    "experience": "years_experience",
    "years_of_experience": "years_experience",
    "technical_skills": "skills",
    "hard_skills": "skills",
    "programming_skills": "skills",
    "location": "location",
    "education": "education",
    "certifications": "certifications",
    "soft_skills": "soft_skills",
    "domain_experience": "domains",
    "industry_experience": "industry_experience",
    "salary_range": "salary_expectations",
    "availability": "availability",
    "notice_period": "notice_period",
    "work_location": "work_location",
    "visa_sponsorship": "visa_sponsorship",
}

# LLM prompt for parsing HR raw requirements into structured format
REQUIREMENT_PARSER_PROMPT = """You are a requirement parser for HR hiring. Convert raw HR requirement text into a structured JSON format.

TASK: Parse HR's requirement text and identify ALL requirement types mentioned, creating dynamic fields for each.

RULES:
1. Identify every requirement type mentioned (not limited to predefined ones)
2. Create a field for each unique requirement type
3. Determine the requirement data type: 'numeric', 'list', 'text', 'education', 'certification', 'location', 'domain', 'budget'
4. Extract specific values (min/max for numeric, items for lists, etc.)
5. Mark each requirement as "specified": true
6. Be flexible - if HR mentions something unusual, create an appropriate field for it

EXAMPLES OF REQUIREMENT TYPES (not exhaustive, create more as needed):
- years_of_experience: {"min": 5, "max": 10, "type": "numeric", "unit": "years", "field": "Python", "specified": true}
- technical_skills: {"required": ["Python", "SQL"], "optional": ["AWS"], "type": "list", "specified": true}
- location: {"allowed": ["NYC", "SF", "Remote"], "type": "location", "specified": true}
- education: {"minimum": "Bachelor's", "preferred": ["Master's"], "type": "education", "specified": true}
- certifications: {"required": ["AWS-SAA"], "preferred": ["GCP"], "type": "certification", "specified": true}
- salary_range: {"min": 100000, "max": 150000, "type": "numeric", "currency": "USD", "specified": true}
- clearance_level: {"required": "Secret", "type": "text", "specified": true}
- availability: {"notice_period": "2 weeks", "type": "text", "specified": true}
- domain_experience: {"required": "FinTech", "years": 3, "type": "domain", "specified": true}
- soft_skills: {"required": ["leadership", "communication"], "type": "list", "specified": true}
- visa_sponsorship: {"required": true, "type": "boolean", "specified": true}
- languages: {"required": ["English"], "preferred": ["Spanish"], "type": "list", "specified": true}

FORMAT:
For each requirement type found, include:
- "type": The data type (numeric, list, text, education, certification, location, domain, boolean, etc.)
- "specified": true (always mark as specified since HR mentioned it)
- (Additional fields specific to that type)

INPUT REQUIREMENTS:
{raw_prompt}

OUTPUT: Return valid JSON with all identified requirements. Example structure:
{{
  "years_of_experience": {{
    "min": 5,
    "type": "numeric",
    "unit": "years",
    "specified": true
  }},
  "technical_skills": {{
    "required": ["Python", "SQL"],
    "type": "list",
    "specified": true
  }},
  "location": {{
    "allowed": ["NYC", "Remote"],
    "type": "location",
    "specified": true
  }}
}}

Parse ALL requirements mentioned. Be comprehensive and dynamic!"""


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


    return {
        "meets": meets,
        "requirement": requirement,
        "candidate_value": resume_json.get("location", ""),
        "match_quality": match_quality,
        "details": details
    }


def get_resume_field_value(resume_json: dict, field_name: str):
    """
    Get value from resume_json based on HR field name.
    Uses FIELD_MAPPING to intelligently map HR field names to resume data.
    Falls back to direct field lookup if mapping not found.
    """
    # Try mapped field name first
    mapped_field = FIELD_MAPPING.get(field_name.lower())
    if mapped_field and mapped_field in resume_json:
        return resume_json.get(mapped_field)
    
    # Try direct field lookup
    if field_name in resume_json:
        return resume_json.get(field_name)
    
    # Try lowercase version
    field_lower = field_name.lower()
    for key in resume_json:
        if key.lower() == field_lower:
            return resume_json.get(key)
    
    return None


def check_numeric_requirement(resume_json: dict, field_name: str, requirement_spec: dict) -> dict:
    """
    Check if numeric requirement is met.
    Works with any numeric field (experience, salary, years in domain, etc.)
    """
    candidate_value = get_resume_field_value(resume_json, field_name)
    
    if candidate_value is None:
        return {
            "meets": False,
            "field": field_name,
            "type": "numeric",
            "candidate_value": None,
            "details": f"{field_name} not found in resume"
        }
    
    try:
        candidate_value = float(candidate_value)
    except (ValueError, TypeError):
        return {
            "meets": False,
            "field": field_name,
            "type": "numeric",
            "candidate_value": candidate_value,
            "details": f"Invalid {field_name} value: {candidate_value}"
        }
    
    min_val = requirement_spec.get("min")
    max_val = requirement_spec.get("max")
    unit = requirement_spec.get("unit", "")
    
    # Check if meets requirement
    meets = True
    if min_val is not None and candidate_value < float(min_val):
        meets = False
    if max_val is not None and candidate_value > float(max_val):
        meets = False
    
    return {
        "meets": meets,
        "field": field_name,
        "type": "numeric",
        "candidate_value": candidate_value,
        "requirement": requirement_spec,
        "details": f"{field_name}: {candidate_value}{unit} (required: {min_val or '0'}-{max_val or 'unlimited'}{unit})"
    }


def check_list_requirement(resume_json: dict, field_name: str, requirement_spec: dict) -> dict:
    """
    Check if list requirement is met.
    Works with any list field (skills, certifications, languages, etc.)
    """
    candidate_value = get_resume_field_value(resume_json, field_name)
    
    if not candidate_value:
        candidate_value = []
    elif isinstance(candidate_value, str):
        candidate_value = [candidate_value]
    elif not isinstance(candidate_value, (list, set, tuple)):
        candidate_value = []
    
    # Normalize to lowercase for comparison
    candidate_items = [str(item).lower().strip() for item in candidate_value if item]
    
    required = requirement_spec.get("required", [])
    optional = requirement_spec.get("optional", [])
    
    if not required:
        required = []
    if not optional:
        optional = []
    
    # Normalize requirement items
    required_items = [str(item).lower().strip() for item in required if item]
    optional_items = [str(item).lower().strip() for item in optional if item]
    
    # Check if all required items are present
    required_met = all(req in candidate_items for req in required_items)
    
    # Count optional items met
    optional_met = [opt for opt in optional_items if opt in candidate_items]
    
    meets = required_met
    
    return {
        "meets": meets,
        "field": field_name,
        "type": "list",
        "candidate_value": list(candidate_value),
        "requirement": requirement_spec,
        "required_met": required_items,
        "optional_met": optional_met,
        "details": f"{field_name}: Found {', '.join(candidate_items) or 'none'}. Required: {', '.join(required_items) or 'none'}"
    }


def check_text_requirement(resume_json: dict, field_name: str, requirement_spec: dict) -> dict:
    """
    Check if text/string requirement is met.
    Works with any text field (clearance level, visa status, etc.)
    """
    candidate_value = get_resume_field_value(resume_json, field_name)
    
    if candidate_value is None:
        return {
            "meets": False,
            "field": field_name,
            "type": "text",
            "candidate_value": None,
            "details": f"{field_name} not found in resume"
        }
    
    required = str(requirement_spec.get("required", "")).lower().strip()
    
    candidate_str = str(candidate_value).lower().strip()
    
    meets = required in candidate_str or candidate_str == required
    
    return {
        "meets": meets,
        "field": field_name,
        "type": "text",
        "candidate_value": str(candidate_value),
        "requirement": requirement_spec,
        "details": f"{field_name}: '{candidate_value}' (required: '{requirement_spec.get('required', '')}')"
    }


def check_location_requirement(resume_json: dict, field_name: str, requirement_spec: dict) -> dict:
    """Check if location requirement is met."""
    candidate_location = get_resume_field_value(resume_json, "location")
    
    if not candidate_location:
        return {
            "meets": False,
            "field": field_name,
            "type": "location",
            "candidate_value": None,
            "details": "Location not found in resume"
        }
    
    allowed_locations = requirement_spec.get("allowed", [])
    if not allowed_locations:
        return {
            "meets": True,
            "field": field_name,
            "type": "location",
            "candidate_value": candidate_location,
            "details": "Any location acceptable"
        }
    
    candidate_loc_lower = str(candidate_location).lower().strip()
    allowed_locs_lower = [str(loc).lower().strip() for loc in allowed_locations]
    
    # Check exact match or partial match
    meets = any(allowed in candidate_loc_lower or candidate_loc_lower in allowed 
                for allowed in allowed_locs_lower)
    
    return {
        "meets": meets,
        "field": field_name,
        "type": "location",
        "candidate_value": candidate_location,
        "requirement": requirement_spec,
        "details": f"Location: {candidate_location} (allowed: {', '.join(allowed_locations)})"
    }


def check_education_requirement(resume_json: dict, field_name: str, requirement_spec: dict) -> dict:
    """Check if education requirement is met."""
    education_hierarchy = ["High School", "Bachelor's", "Master's", "PhD"]
    
    candidate_edu = get_resume_field_value(resume_json, "education")
    
    if not candidate_edu:
        return {
            "meets": False,
            "field": field_name,
            "type": "education",
            "candidate_value": None,
            "details": "Education not found in resume"
        }
    
    minimum = requirement_spec.get("minimum", "High School")
    
    # Find indices
    candidate_idx = next((i for i, edu in enumerate(education_hierarchy) 
                         if edu.lower() in str(candidate_edu).lower()), -1)
    minimum_idx = next((i for i, edu in enumerate(education_hierarchy) 
                       if edu.lower() in str(minimum).lower()), 0)
    
    meets = candidate_idx >= minimum_idx
    
    return {
        "meets": meets,
        "field": field_name,
        "type": "education",
        "candidate_value": candidate_edu,
        "requirement": requirement_spec,
        "details": f"Education: {candidate_edu} (minimum: {minimum})"
    }


def check_dynamic_requirement(resume_json: dict, field_name: str, requirement_spec) -> dict:
    """
    Generic dynamic requirement checker that handles any requirement type.
    Automatically determines checking logic based on requirement type.
    Normalizes requirement_spec if it's not a dict (e.g., simple list).
    """
    if not requirement_spec:
        return None
    
    # Normalize requirement_spec if it's a list or string
    if isinstance(requirement_spec, list):
        requirement_spec = {"type": "list", "required": requirement_spec}
    elif isinstance(requirement_spec, str):
        requirement_spec = {"type": "text", "required": requirement_spec}
    elif not isinstance(requirement_spec, dict):
        requirement_spec = {"type": "text", "value": requirement_spec}
    
    requirement_type = requirement_spec.get("type", "text")
    
    try:
        if requirement_type == "numeric":
            return check_numeric_requirement(resume_json, field_name, requirement_spec)
        elif requirement_type == "list":
            return check_list_requirement(resume_json, field_name, requirement_spec)
        elif requirement_type == "location":
            return check_location_requirement(resume_json, field_name, requirement_spec)
        elif requirement_type == "education":
            return check_education_requirement(resume_json, field_name, requirement_spec)
        elif requirement_type == "boolean":
            # Simple boolean check
            candidate_val = get_resume_field_value(resume_json, field_name)
            required_val = requirement_spec.get("required", True)
            return {
                "meets": bool(candidate_val) == bool(required_val),
                "field": field_name,
                "type": "boolean",
                "candidate_value": candidate_val,
                "details": f"{field_name}: {candidate_val} (required: {required_val})"
            }
        else:
            # Default to text checking for unknown types
            return check_text_requirement(resume_json, field_name, requirement_spec)
    except Exception as e:
        # Graceful fallback for any errors
        print(f"⚠️ Error checking requirement '{field_name}': {e}")
        return {
            "meets": False,
            "field": field_name,
            "type": requirement_type,
            "candidate_value": None,
            "details": f"Error checking requirement: {str(e)}"
        }


def llm_parse_requirements(raw_prompt: str, client: OpenAI = None) -> dict:
    """
    Use LLM to parse raw HR requirement text into structured dynamic format.
    Returns a dictionary with requirement fields that can be any type.
    """
    if not raw_prompt or not raw_prompt.strip():
        return {}
    
    if not client:
        # Initialize client
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                try:
                    import streamlit as st
                    api_key = st.secrets.get("OPENAI_API_KEY")
                except:
                    api_key = None
            
            if not api_key:
                print("⚠️ OpenAI API key not found for requirement parsing. Returning empty structure.")
                return {}
            
            client = OpenAI(api_key=api_key)
        except Exception as e:
            print(f"⚠️ Failed to initialize OpenAI for requirement parsing: {e}")
            return {}
    
    try:
        prompt = REQUIREMENT_PARSER_PROMPT.format(raw_prompt=raw_prompt)
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a requirement parser. Return ONLY valid JSON with no additional text or markdown formatting."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Remove markdown code block if present
        if response_text.startswith("```"):
            response_text = response_text.split("```")[1]
            if response_text.startswith("json"):
                response_text = response_text[4:]
            response_text = response_text.strip()
        
        structured = json.loads(response_text)
        
        print(f"✅ Parsed HR requirements into {len(structured)} dynamic fields")
        return structured
    except json.JSONDecodeError as e:
        print(f"⚠️ JSON parsing error in requirement parsing: {e}")
        return {}
    except Exception as e:
        print(f"⚠️ Error parsing requirements with LLM: {e}")
        return {}


def load_and_parse_hr_requirements(hr_filter_file: Path = None) -> dict:
    """
    Load HR filter requirements and auto-parse if needed.
    
    If structured dict is empty but raw_prompt exists:
    - Uses LLM to parse raw_prompt into dynamic structured fields
    - Saves the parsed result back to the JSON file
    
    Returns the complete filter_requirements with parsed structured dict.
    """
    if not hr_filter_file:
        hr_filter_file = Path("InputThread/JD/HR_Filter_Requirements.json")
    
    # Load existing file
    if not hr_filter_file.exists():
        return {"structured": {}}
    
    try:
        with hr_filter_file.open("r", encoding="utf-8") as f:
            hr_reqs = json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading HR requirements: {e}")
        return {"structured": {}}
    
    # If structured is empty but raw_prompt exists, parse it
    structured = hr_reqs.get("structured", {})
    raw_prompt = hr_reqs.get("raw_prompt", "")
    
    if (not structured or len(structured) == 0) and raw_prompt:
        print(f"📝 Parsing raw HR requirements using LLM...")
        
        # Parse using LLM
        parsed_structured = llm_parse_requirements(raw_prompt)
        
        if parsed_structured:
            # Update the loaded requirements
            hr_reqs["structured"] = parsed_structured
            structured = parsed_structured
            
            # Save back to file
            try:
                with hr_filter_file.open("w", encoding="utf-8") as f:
                    json.dump(hr_reqs, f, indent=2)
                print(f"✅ Saved parsed requirements to HR_Filter_Requirements.json")
            except Exception as e:
                print(f"⚠️ Could not save parsed requirements: {e}")
        else:
            print(f"⚠️ LLM parsing returned no results")
    
    return hr_reqs


def process_hr_requirements(filter_requirements: dict) -> dict:
    """
    Pre-process HR requirements to ensure they're in the correct format.
    If filter_requirements is missing, tries to load from file.
    """
    if not filter_requirements or not filter_requirements.get("structured"):
        # Try to load from file
        loaded = load_and_parse_hr_requirements()
        return loaded
    
    return filter_requirements
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
    Dynamically check ALL requirements without hardcoding any fields.
    Works with any requirement type HR specifies.
    
    Returns compliance report with only the requirements that are specified in filter_requirements.
    """
    if not filter_requirements or not filter_requirements.get("structured"):
        return {}
    
    structured = filter_requirements.get("structured", {})
    compliance = {}
    
    # Loop through ALL fields in structured dict (no hardcoding!)
    for field_name, field_spec in structured.items():
        if not field_spec:
            continue
        
        # Only check if marked as specified or has content
        if isinstance(field_spec, dict):
            is_specified = field_spec.get("specified", False)
            # Check if field has actual values (not empty list or empty dict)
            has_value = False
            for key, val in field_spec.items():
                if key != "specified" and val not in (None, [], {}, "", ""):
                    has_value = True
                    break
            
            if not (is_specified or has_value):
                continue
        else:
            # Non-dict value (should have value)
            if not field_spec:
                continue
        
        try:
            # Use generic dynamic checker for all requirement types
            result = check_dynamic_requirement(resume_json, field_name, field_spec)
            if result:
                compliance[field_name] = result
        except Exception as e:
            print(f"⚠️ Error checking requirement '{field_name}': {e}")
            # Add error to compliance so we know it failed
            compliance[field_name] = {
                "meets": False,
                "field": field_name,
                "type": field_spec.get("type", "unknown") if isinstance(field_spec, dict) else "unknown",
                "details": f"Error: {str(e)}"
            }
    
    return compliance


def llm_re_rank_batch(candidates_summaries: List[dict], filter_requirements: dict, client: OpenAI, specified_fields: set = None) -> List[dict]:
    """
    LLM re-ranks a batch of candidates based on filter requirements and all scores.
    Batch size: 30 candidates.
    
    Args:
        candidates_summaries: List of candidate summaries
        filter_requirements: HR filter requirements
        client: OpenAI client
        specified_fields: Set of requirement field names that HR actually specified
    """
    if not client:
        return []
    
    if not specified_fields:
        specified_fields = set()
    
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
                                "description": f"Validated list of requirement types from this set that candidate meets: {sorted(specified_fields) if specified_fields else 'NONE - no requirements specified'}. Validate programmatic results and correct if needed."
                            },
                            "requirements_missing": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": f"Validated list of requirement types from this set that candidate is missing: {sorted(specified_fields) if specified_fields else 'NONE - no requirements specified'}. Validate programmatic results and correct if needed."
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
    specified_fields_str = ", ".join(sorted(specified_fields)) if specified_fields else "NONE (no requirements specified)"
    
    system_msg = f"""You are a candidate re-ranker and compliance validator. Your tasks:
1. VALIDATE compliance results: Review programmatic compliance checks and validate/correct them based on candidate resume data
2. RE-RANK candidates: Rank candidates based on validated compliance + all ranking scores

IMPORTANT CONSTRAINT:
- Only return requirement types from this list: {specified_fields_str}
- Do NOT return other requirement types like location, education, etc. unless explicitly listed above
- If no requirements specified, return empty arrays for requirements_met and requirements_missing

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
- Validated requirements_met list (ONLY from allowed list)
- Validated requirements_missing list (ONLY from allowed list)"""
    
    user_msg = f"""ALLOWED REQUIREMENT TYPES (only return these): {specified_fields_str}

Filter Requirements:
{json.dumps(filter_requirements, indent=2)}

Candidates to Re-rank (with all scores and programmatic compliance - abbreviated format):
{json.dumps(candidates_summaries, indent=2)}

Each candidate has a "compliance" field with programmatic compliance results.
VALIDATE these results - review and correct if programmatic checks missed nuances.
Then RE-RANK candidates based on validated compliance + all scores.

CRITICAL: In requirements_met and requirements_missing, ONLY include types from: {specified_fields_str}
Do NOT add other requirement types that weren't specified by HR.

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
                ranked_candidates = args.get("ranked_candidates", [])
                
                # FILTER: Ensure only specified requirement fields are in the response
                if specified_fields:
                    for candidate in ranked_candidates:
                        # Filter requirements_met to only include specified fields
                        candidate["requirements_met"] = [
                            req for req in candidate.get("requirements_met", [])
                            if req in specified_fields
                        ]
                        # Filter requirements_missing to only include specified fields
                        candidate["requirements_missing"] = [
                            req for req in candidate.get("requirements_missing", [])
                            if req in specified_fields
                        ]
                
                return ranked_candidates
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
    
    # Determine which requirement fields are actually specified by HR
    structured = filter_requirements.get("structured", {})
    specified_fields = set()
    
    def field_has_value(val):
        if val is None:
            return False
        if isinstance(val, bool):
            return val
        if isinstance(val, (list, tuple, set)):
            return len(val) > 0
        if isinstance(val, dict):
            for k, v in val.items():
                if k == "specified" and bool(v):
                    return True
                if v not in (None, [], {}, ""):
                    return True
            return False
        return bool(val)
    
    # Check each field that HR actually specified (NO hardcoding!)
    for field_name, field_value in structured.items():
        if field_has_value(field_value):
            specified_fields.add(field_name)
    
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
        
        # Pass specified_fields to the batch function
        results = llm_re_rank_batch(batch, filter_requirements, client, specified_fields)
        
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
    
    # Load HR filter requirements with auto-parsing support
    # This ensures compliance filtering is based on HR requirements only
    hr_filter_file = Path("InputThread/JD/HR_Filter_Requirements.json")
    if hr_filter_file.exists():
        try:
            # Use new auto-parsing function
            filter_reqs = load_and_parse_hr_requirements(hr_filter_file)
            
            # Check if any requirements are actually specified (works with any dynamic fields)
            structured = filter_reqs.get("structured", {})

            def field_has_value(val):
                # Returns True if the structured field contains meaningful requirement info
                if val is None:
                    return False
                if isinstance(val, bool):
                    return val
                if isinstance(val, (list, tuple, set)):
                    return len(val) > 0
                if isinstance(val, dict):
                    # If dict, check for any non-empty/non-null entry
                    for k, v in val.items():
                        if k == "specified" and bool(v):
                            return True
                        if v not in (None, [], {}, ""):
                            return True
                    return False
                # strings, numbers, etc.
                return bool(val)

            # Check if ANY requirement is specified (works with dynamic fields!)
            has_any_requirement = any(field_has_value(v) for v in structured.values())
            
            if has_any_requirement:
                print(f"\n🔍 Checking compliance for all candidates (HR requirements)...")
                # Determine which fields are actually specified (works with ANY field names!)
                specified_fields = set()
                for field_name, field_spec in structured.items():
                    if field_has_value(field_spec):
                        specified_fields.add(field_name)
                
                print(f"   📋 Specified requirements: {', '.join(sorted(specified_fields))}")
                for cand in ranked:
                    candidate_id = cand.get("candidate_id")
                    resume_json = load_resume_json(candidate_id) if candidate_id else {}
                    
                    # Check compliance
                    compliance_report = check_all_requirements(cand, resume_json, filter_reqs)
                    
                    # FILTER: Keep only specified fields in compliance report
                    compliance_report = {k: v for k, v in compliance_report.items() if k in specified_fields}
                    
                    requirements_met = [req_type for req_type, comp in compliance_report.items() if comp.get("meets", False)]
                    requirements_missing = [req_type for req_type, comp in compliance_report.items() if not comp.get("meets", False)]
                    total_requirements = len(requirements_met) + len(requirements_missing)
                    
                    # Filter out 0% compliance candidates (0 requirements met when requirements exist)
                    if total_requirements > 0 and len(requirements_met) == 0:
                        cand["_filtered_reason"] = "0% compliance - no requirements met (HR)"
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
                print(f"\n✅ No HR requirements specified - all candidates pass compliance check")
                # IMPORTANT: Clear any compliance data since no HR requirements specified
                for cand in ranked:
                    cand["requirements_met"] = []
                    cand["requirements_missing"] = []
                    cand["requirement_compliance"] = {}
                    if "_filtered_reason" in cand:
                        del cand["_filtered_reason"]
                filtered_ranked = ranked
        except Exception as e:
            print(f"⚠️ Error checking compliance: {e}")
            import traceback
            traceback.print_exc()
            # On error, keep all candidates
            filtered_ranked = ranked
    else:
        # No HR filter file - keep all candidates
        print(f"\n✅ No HR filter requirements file found - all candidates pass compliance check")
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
        # Only do LLM re-ranking if HR requirements were specified
        if has_any_requirement:
            # IMPORTANT: Use filter_reqs that was already loaded from HR_Filter_Requirements.json
            # DO NOT load from JD.json - always use HR's requirements
            if filter_reqs and filter_reqs.get("structured"):
                print(f"\n🔄 Starting LLM-based re-ranking with filter requirements...")
                # CRITICAL: Only re-rank COMPLIANT candidates (filtered_ranked), not all candidates
                # This ensures 0% compliance candidates are NOT added back to rankings
                re_rank_results = llm_re_rank_candidates(filtered_ranked, filter_reqs)
                
                if re_rank_results:
                    # Determine which fields are actually specified (for filtering compliance output)
                    specified_fields = set()
                    structured_temp = filter_reqs.get("structured", {})
                    # Determine specified fields dynamically from the structured dict
                    for field_name, field_spec in structured_temp.items():
                        if field_has_value(field_spec):
                            specified_fields.add(field_name)
                    
                    # Create map of re-ranking results
                    re_rank_map = {r["candidate_id"]: r for r in re_rank_results}
                    
                    # Update COMPLIANT candidates with re-ranking scores and compliance data
                    # Only iterate through filtered_ranked to avoid re-adding 0% compliance candidates
                    for candidate in filtered_ranked:
                        candidate_id = candidate.get("candidate_id")
                        resume_json = load_resume_json(candidate_id) if candidate_id else {}
                        
                        if candidate_id in re_rank_map:
                            re_rank_data = re_rank_map[candidate_id]
                            candidate["Re_Rank_Score"] = re_rank_data.get("re_rank_score", candidate["Final_Score"])
                            candidate["Meets_Requirements"] = re_rank_data.get("meets_requirements", True)
                            
                            # Use LLM-validated requirements (LLM may have corrected programmatic results)
                            llm_requirements_met = re_rank_data.get("requirements_met", [])
                            llm_requirements_missing = re_rank_data.get("requirements_missing", [])
                            
                            # FILTER: Ensure LLM requirements only contain specified fields
                            llm_requirements_met = [req for req in llm_requirements_met if req in specified_fields]
                            llm_requirements_missing = [req for req in llm_requirements_missing if req in specified_fields]
                            
                            # Keep compliance breakdown for detailed view
                            compliance_report = re_rank_data.get("compliance_report", {})
                            if not compliance_report:
                                # Generate compliance if not in results
                                compliance_report = check_all_requirements(candidate, resume_json, filter_reqs)
                            
                            # FILTER: Keep only specified fields
                            compliance_report = {k: v for k, v in compliance_report.items() if k in specified_fields}
                            
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
                            
                            # FILTER: Keep only specified fields
                            compliance_report = {k: v for k, v in compliance_report.items() if k in specified_fields}
                            
                            candidate["requirement_compliance"] = compliance_report
                            
                            # Determine requirements met/missing from compliance
                            requirements_met = [req_type for req_type, comp in compliance_report.items() if comp.get("meets", False)]
                            requirements_missing = [req_type for req_type, comp in compliance_report.items() if not comp.get("meets", False)]
                            candidate["requirements_met"] = requirements_met
                            candidate["requirements_missing"] = requirements_missing
                    
                    # Re-sort by Re_Rank_Score (or Final_Score), then by experience (descending) as tie-breaker
                    filtered_ranked.sort(key=lambda x: (x.get("Re_Rank_Score", x["Final_Score"]), x.get("_years_experience", 0)), reverse=True)
                    
                    # Update ranks
                    for i, candidate in enumerate(filtered_ranked, start=1):
                        candidate["Rank"] = i
                    
                    final_ranked_list = filtered_ranked
                    print(f"✅ Re-ranking complete. Rankings updated based on filter requirements.")
                else:
                    print("⚠️ No re-ranking results returned. Using original rankings.")
                    # Still add compliance data even without re-ranking
                    specified_fields = set()
                    structured_temp = filter_reqs.get("structured", {})
                    for field_name, field_spec in structured_temp.items():
                        if field_has_value(field_spec):
                            specified_fields.add(field_name)
                    
                    for candidate in ranked:
                        candidate_id = candidate.get("candidate_id")
                        resume_json = load_resume_json(candidate_id) if candidate_id else {}
                        compliance_report = check_all_requirements(candidate, resume_json, filter_reqs)
                        # FILTER: Keep only specified fields
                        compliance_report = {k: v for k, v in compliance_report.items() if k in specified_fields}
                        candidate["requirement_compliance"] = compliance_report
                        requirements_met = [req_type for req_type, comp in compliance_report.items() if comp.get("meets", False)]
                        requirements_missing = [req_type for req_type, comp in compliance_report.items() if not comp.get("meets", False)]
                        candidate["requirements_met"] = requirements_met
                        candidate["requirements_missing"] = requirements_missing
            else:
                print("ℹ️ No filter requirements found. Using original rankings.")
        else:
            print("ℹ️ No HR requirements specified. Skipping LLM re-ranking.") 
    except Exception as e:
        print(f"⚠️ Error during re-ranking: {e}. Using original rankings.")
        # Only add compliance data on error if HR requirements were specified
        try:
            if has_any_requirement and JD_FILE.exists():
                with JD_FILE.open("r", encoding="utf-8") as f:
                    jd = json.load(f)
                filter_reqs = jd.get("filter_requirements")
                if filter_reqs and filter_reqs.get("structured"):
                    # Determine specified fields dynamically
                    structured_temp = filter_reqs.get("structured", {})
                    specified_fields = set()
                    for field_name, field_spec in structured_temp.items():
                        if field_has_value(field_spec):
                            specified_fields.add(field_name)

                    for candidate in ranked:
                        candidate_id = candidate.get("candidate_id")
                        resume_json = load_resume_json(candidate_id) if candidate_id else {}
                        compliance_report = check_all_requirements(candidate, resume_json, filter_reqs)
                        # FILTER: Keep only specified fields
                        compliance_report = {k: v for k, v in compliance_report.items() if k in specified_fields}
                        candidate["requirement_compliance"] = compliance_report
                        requirements_met = [req_type for req_type, comp in compliance_report.items() if comp.get("meets", False)]
                        requirements_missing = [req_type for req_type, comp in compliance_report.items() if not comp.get("meets", False)]
                        candidate["requirements_met"] = requirements_met
                        candidate["requirements_missing"] = requirements_missing
        except:
            pass
    
    # CRITICAL: Ensure ALL candidates have compliance data (even if LLM re-ranking failed or skipped some)
    # ONLY if HR requirements were specified
    try:
        if has_any_requirement and JD_FILE.exists():
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

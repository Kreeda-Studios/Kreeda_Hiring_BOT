#!/usr/bin/env python3
"""
EarlyFilter.py

Early filtering based on HR requirements from JD.json filter_requirements.
Filters candidates BEFORE scoring to improve efficiency.
Uses structured requirements extracted by LLM from natural language.

CONFIGURATION:
- FILTER_MODE: "strict" (all skills required) or "flexible" (50% skills threshold)
- SKILL_MATCH_THRESHOLD: Minimum percentage of required skills needed (0.0-1.0)
- ENABLE_SKILL_SYNONYMS: Use synonym matching for skills (RAG, ML, etc.)
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

JD_DIR = Path("InputThread/JD")
PROCESSED_JSON_DIR = Path("ProcessedJson")
SKIPPED_FILE = Path("Ranking/Skipped.json")

# ==================== CONFIGURATION ====================
FILTER_MODE = "flexible"  # "strict" or "flexible"
SKILL_MATCH_THRESHOLD = 0.5  # Require at least 50% of skills (0.0-1.0)
# =======================================================
# Note: Skill normalization is now handled by LLM during JD/Resume parsing
# Skills are normalized to canonical forms, so exact matching should work


def normalize_name(name: str) -> str:
    """Normalize candidate name consistently."""
    if not name:
        return ""
    return re.sub(r'[^\w\s]', '', name.lower().strip())


def check_experience_compliance(resume: dict, exp_req: dict):
    """
    Check if resume meets experience requirement.
    For numerical filters: Only check minimum threshold (don't filter by max).
    Max is used for sorting in ranking, not filtering.
    """
    if not exp_req or not exp_req.get("specified"):
        return True, "No experience requirement"
    
    resume_years = resume.get("years_experience")
    if resume_years is None:
        return False, "Experience not specified in resume"
    
    try:
        resume_years = float(resume_years)
    except (ValueError, TypeError):
        return False, "Invalid experience format in resume"
    
    min_years = exp_req.get("min", 0)
    # NOTE: We don't filter by max_years here - that's handled in ranking (sort descending)
    # Only filter out if below minimum threshold
    
    if resume_years < min_years:
        return False, f"Has {resume_years} years, requires at least {min_years} years"
    
    return True, f"Meets experience requirement ({resume_years} years, min: {min_years})"


def extract_jd_skills_from_domain_tags(domain_tags: List[str]) -> Dict[str, List[str]]:
    """Extract required and preferred skills from JD domain_tags."""
    required_skills = []
    preferred_skills = []
    
    for tag in domain_tags:
        if isinstance(tag, str):
            if tag.startswith("REQ_SKILL:"):
                required_skills.append(tag.replace("REQ_SKILL:", "").strip())
            elif tag.startswith("PREF_SKILL:"):
                preferred_skills.append(tag.replace("PREF_SKILL:", "").strip())
    
    return {
        "required": required_skills,
        "preferred": preferred_skills
    }


def check_skills_compliance(resume: dict, required_skills: List[str]):
    """
    Check if resume has required skills.
    Skills should already be normalized to canonical forms by LLM during parsing.
    """
    if not required_skills:
        return True, "No skills requirement", [], []
    
    # Collect all skills from resume (normalized to lowercase for comparison)
    resume_skills = set()
    resume_text = ""  # For fallback text matching
    
    # From canonical_skills
    canonical = resume.get("canonical_skills", {})
    for cat_skills in canonical.values():
        if isinstance(cat_skills, list):
            resume_skills.update(s.lower().strip() for s in cat_skills if s)
    
    # From inferred_skills
    for inf in resume.get("inferred_skills", []):
        if inf.get("skill"):
            resume_skills.add(inf["skill"].lower().strip())
    
    # From skill_proficiency
    for sp in resume.get("skill_proficiency", []):
        if sp.get("skill"):
            resume_skills.add(sp["skill"].lower().strip())
    
    # From projects
    for proj in resume.get("projects", []):
        for skill_list in [proj.get("tech_keywords", []), proj.get("primary_skills", [])]:
            resume_skills.update(s.lower().strip() for s in skill_list if s)
        # Also collect project descriptions for fallback matching
        if proj.get("description"):
            resume_text += " " + proj.get("description", "").lower()
    
    # From experience descriptions
    for exp in resume.get("experience", []):
        if exp.get("description"):
            resume_text += " " + exp.get("description", "").lower()
    
    # Check which required skills are found (exact match on normalized skills)
    found = []
    missing = []
    
    for req_skill in required_skills:
        req_skill_normalized = req_skill.lower().strip()
        skill_found = False
        
        # Check exact match in skills set (skills should be normalized by LLM)
        if req_skill_normalized in resume_skills:
            skill_found = True
            found.append(req_skill)
        # Fallback: check if skill appears in resume text (for edge cases)
        elif resume_text and len(req_skill_normalized) > 2:
            # Check if skill or its key terms appear in text
            key_terms = req_skill_normalized.split()
            if any(term in resume_text for term in key_terms if len(term) > 3):
                skill_found = True
                found.append(req_skill)
        
        if not skill_found:
            missing.append(req_skill)
    
    # Determine compliance based on filter mode
    total_skills = len(required_skills)
    found_count = len(found)
    match_ratio = found_count / total_skills if total_skills > 0 else 0
    
    if FILTER_MODE == "strict":
        # Strict: require ALL skills
        meets = found_count == total_skills
    else:
        # Flexible: require at least threshold percentage
        meets = match_ratio >= SKILL_MATCH_THRESHOLD
    
    if meets:
        if found_count == total_skills:
            return True, f"Has all required skills: {', '.join(found)}", found, missing
        else:
            return True, f"Has {found_count}/{total_skills} required skills (flexible mode: {int(SKILL_MATCH_THRESHOLD*100)}% threshold). Found: {', '.join(found)}", found, missing
    else:
        return False, f"Has {found_count}/{total_skills} required skills. Missing: {', '.join(missing)}", found, missing


def check_department_compliance(resume: dict, dept_req: dict):
    """
    Check if candidate's department/field of study meets requirement.
    Returns (meets, reason)
    """
    if not dept_req or not dept_req.get("specified"):
        return True, "No department requirement"
    
    # Extract candidate's education departments/fields
    candidate_departments = []
    education_entries = resume.get("education", [])
    
    for edu in education_entries:
        if isinstance(edu, dict):
            field = edu.get("field", "").strip()
            if field:
                candidate_departments.append(field.lower())
        elif isinstance(edu, str):
            # Fallback: try to extract from string
            candidate_departments.append(edu.lower())
    
    if not candidate_departments:
        return False, "Department/field not specified in resume"
    
    # IT departments mapping
    IT_DEPARTMENTS = {
        "computer science", "cs", "cse", "computer engineering", "ce",
        "information technology", "it", "information systems", "is",
        "aids", "artificial intelligence and data science", "ai & ds",
        "electronics and telecommunications", "entc", "ece", "electronics",
        "software engineering", "se", "computer applications", "ca",
        "data science", "ds", "artificial intelligence", "ai", "ml",
        "cyber security", "cybersecurity", "information security"
    }
    
    # Non-IT departments
    NON_IT_DEPARTMENTS = {
        "mechanical", "mechanical engineering", "me",
        "chemical", "chemical engineering", "che",
        "civil", "civil engineering", "ce",
        "electrical", "electrical engineering", "ee",
        "electronics and communication", "ec", "e&c"
    }
    
    category = dept_req.get("category", "").lower()
    allowed = [d.lower().strip() for d in dept_req.get("allowed_departments", [])]
    excluded = [d.lower().strip() for d in dept_req.get("excluded_departments", [])]
    
    # Check if candidate has any matching department
    candidate_has_it = any(dept in IT_DEPARTMENTS or any(it in dept for it in IT_DEPARTMENTS) for dept in candidate_departments)
    candidate_has_non_it = any(dept in NON_IT_DEPARTMENTS or any(nit in dept for nit in NON_IT_DEPARTMENTS) for dept in candidate_departments)
    
    # Check category-based filtering
    if category == "it":
        if not candidate_has_it:
            return False, f"Department not IT-related. Found: {', '.join(candidate_departments[:3])}"
        return True, f"IT department found: {', '.join([d for d in candidate_departments if any(it in d for it in IT_DEPARTMENTS)][:2])}"
    
    elif category == "non-it":
        if not candidate_has_non_it:
            return False, f"Department not Non-IT. Found: {', '.join(candidate_departments[:3])}"
        return True, f"Non-IT department found: {', '.join(candidate_departments[:2])}"
    
    # Check allowed departments
    if allowed:
        matches = [d for d in candidate_departments if any(allowed_dept in d or d in allowed_dept for allowed_dept in allowed)]
        if not matches:
            return False, f"Department not in allowed list. Found: {', '.join(candidate_departments[:3])}, Required: {', '.join(allowed)}"
        return True, f"Department matches: {', '.join(matches[:2])}"
    
    # Check excluded departments
    if excluded:
        matches = [d for d in candidate_departments if any(excluded_dept in d or d in excluded_dept for excluded_dept in excluded)]
        if matches:
            return False, f"Department in excluded list. Found: {', '.join(matches[:2])}, Excluded: {', '.join(excluded)}"
        return True, f"Department not excluded: {', '.join(candidate_departments[:2])}"
    
    # Default: if specified but no specific rules, allow
    return True, f"Department requirement met: {', '.join(candidate_departments[:2])}"


def check_location_compliance(resume: dict, requirement: str):
    """Check if candidate meets location requirement."""
    if not requirement:
        return True, "No location requirement"
    
    req_loc = requirement.lower().strip()
    # Skip location check if requirement is "Any" or similar
    if req_loc in ["any", "anywhere", "remote/onsite", "flexible", ""]:
        return True, "Location requirement is flexible (Any)"
    
    # Handle None location
    location = resume.get("location")
    if not location or not isinstance(location, str):
        return False, "Location not specified in resume"
    candidate_loc = location.lower()
    
    # Check for remote/onsite/hybrid
    is_remote_req = "remote" in req_loc
    is_onsite_req = "onsite" in req_loc or "on-site" in req_loc
    is_hybrid_req = "hybrid" in req_loc
    
    candidate_remote = "remote" in candidate_loc
    candidate_onsite = "onsite" in candidate_loc or "on-site" in candidate_loc
    candidate_hybrid = "hybrid" in candidate_loc
    
    if is_remote_req and candidate_remote:
        return True, f"Candidate is available for remote work"
    elif is_onsite_req and (candidate_onsite or not candidate_remote):
        return True, f"Candidate is available for onsite work"
    elif is_hybrid_req and candidate_hybrid:
        return True, f"Candidate is available for hybrid work"
    elif is_remote_req and not candidate_remote:
        return False, f"Candidate location: {resume.get('location', 'Not specified')} (required: {requirement})"
    else:
        # Generic location match
        if req_loc in candidate_loc or candidate_loc in req_loc:
            return True, f"Location matches: {resume.get('location', 'Not specified')}"
        else:
            return False, f"Candidate location: {resume.get('location', 'Not specified')} (required: {requirement})"


def check_other_criteria_compliance(resume: dict, other_criteria: List[str]):
    """
    Check compliance with other_criteria requirements using semantic matching.
    Returns (is_compliant, met_criteria, failed_criteria)
    """
    if not other_criteria:
        return True, [], []
    
    # Get resume text for semantic matching
    resume_text = ""
    
    # Collect text from various resume sections
    resume_text += " ".join(resume.get("summary", [])) + " "
    resume_text += " ".join(resume.get("responsibilities", [])) + " "
    
    # Add experience descriptions
    for exp in resume.get("experience", []):
        resume_text += exp.get("description", "") + " "
        resume_text += " ".join(exp.get("responsibilities", [])) + " "
        resume_text += exp.get("company", "") + " "
        resume_text += exp.get("industry", "") + " "
    
    # Add project descriptions
    for proj in resume.get("projects", []):
        resume_text += proj.get("description", "") + " "
        resume_text += " ".join(proj.get("tech_keywords", [])) + " "
    
    # Add education
    for edu in resume.get("education", []):
        resume_text += edu.get("degree", "") + " "
        resume_text += edu.get("field", "") + " "
        resume_text += edu.get("institution", "") + " "
    
    # Add certifications
    for cert in resume.get("certifications", []):
        resume_text += cert.get("name", "") + " "
    
    resume_text_lower = resume_text.lower()
    
    met_criteria = []
    failed_criteria = []
    
    for criterion in other_criteria:
        criterion_lower = criterion.lower()
        # Simple keyword matching - can be enhanced with LLM later
        # Check if key terms from criterion appear in resume
        key_terms = [word for word in criterion_lower.split() if len(word) > 3]  # Skip short words
        
        # Check if at least 50% of key terms appear in resume
        matches = sum(1 for term in key_terms if term in resume_text_lower)
        match_ratio = matches / len(key_terms) if key_terms else 0
        
        if match_ratio >= 0.5 or any(term in resume_text_lower for term in key_terms[:2]):  # At least 50% or first 2 key terms
            met_criteria.append(criterion)
        else:
            failed_criteria.append(criterion)
    
    is_compliant = len(failed_criteria) == 0
    return is_compliant, met_criteria, failed_criteria


def extract_experience_from_other_criteria(other_criteria: List[str]) -> Optional[Dict[str, Any]]:
    """Extract experience requirement from other_criteria if not in experience field."""
    if not other_criteria:
        return None
    
    for criterion in other_criteria:
        criterion_lower = criterion.lower()
        # Look for patterns like "1-2 years", "2+ years", "at least 3 years", etc.
        years_match = re.search(r'(\d+)\s*-\s*(\d+)\s*years?', criterion_lower)
        if years_match:
            return {"min": int(years_match.group(1)), "max": int(years_match.group(2))}
        
        min_match = re.search(r'(?:at least|minimum|min)\s*(\d+)\s*years?', criterion_lower)
        if min_match:
            return {"min": int(min_match.group(1)), "max": float('inf')}
        
        max_match = re.search(r'(?:up to|maximum|max)\s*(\d+)\s*years?', criterion_lower)
        if max_match:
            return {"min": 0, "max": int(max_match.group(1))}
        
        exact_match = re.search(r'(\d+)\s*years?', criterion_lower)
        if exact_match:
            years = int(exact_match.group(1))
            return {"min": years - 1, "max": years + 1}  # Allow ±1 year flexibility
    
    return None


def check_all_requirements(resume: dict, filter_requirements: dict) -> Dict[str, Any]:
    """
    Check all HR requirements and determine if candidate should be filtered.
    Only filters on explicitly specified requirements.
    Returns compliance result with should_filter flag and compliance score.
    """
    if not filter_requirements or not filter_requirements.get("structured"):
        return {
            "should_filter": False,
            "filter_reason": None,
            "compliance": {},
            "requirements_met": [],
            "requirements_missing": [],
            "compliance_score": 1.0,
            "specified_requirements_count": 0
        }
    
    structured = filter_requirements.get("structured", {})
    compliance = {}
    requirements_met = []
    requirements_missing = []
    filter_reasons = []
    specified_requirements = []  # Track only specified requirements
    
    # CATEGORICAL FILTERS (strict matching - filter out if doesn't match)
    
    # Check hard_skills (categorical - must match)
    skills_req = structured.get("hard_skills", [])
    if skills_req:  # Non-empty array = specified
        specified_requirements.append("hard_skills")
        required_skills = skills_req
        meets, reason, found, missing = check_skills_compliance(resume, required_skills)
        compliance["hard_skills"] = {
            "meets": meets,
            "requirement": required_skills,
            "found": found,
            "missing": missing,
            "details": reason
        }
        if meets:
            requirements_met.append("hard_skills")
        else:
            # Categorical: filter out if doesn't match
            requirements_missing.append("hard_skills")
            filter_reasons.append(f"Skills: {reason}")
    
    # Check department (categorical - must match)
    dept_req = structured.get("department")
    if dept_req and dept_req.get("specified"):
        specified_requirements.append("department")
        meets, reason = check_department_compliance(resume, dept_req)
        compliance["department"] = {
            "meets": meets,
            "requirement": dept_req,
            "details": reason
        }
        if meets:
            requirements_met.append("department")
        else:
            # Categorical: filter out if doesn't match
            requirements_missing.append("department")
            filter_reasons.append(f"Department: {reason}")
    
    # Check location (categorical - must match, unless "Any")
    location_req = structured.get("location")
    if location_req and isinstance(location_req, str) and location_req.lower().strip() not in ["any", "anywhere", "remote/onsite", "flexible", ""]:
        specified_requirements.append("location")
        meets, reason = check_location_compliance(resume, location_req)
        compliance["location"] = {
            "meets": meets,
            "requirement": location_req,
            "details": reason
        }
        if meets:
            requirements_met.append("location")
        else:
            # Categorical: filter out if doesn't match
            requirements_missing.append("location")
            filter_reasons.append(f"Location: {reason}")
    
    # Check other_criteria (categorical - must match)
    other_criteria = structured.get("other_criteria", [])
    if other_criteria:  # Non-empty array = specified
        specified_requirements.append("other_criteria")
        meets, met_criteria, failed_criteria = check_other_criteria_compliance(resume, other_criteria)
        compliance["other_criteria"] = {
            "meets": meets,
            "requirement": other_criteria,
            "met_criteria": met_criteria,
            "failed_criteria": failed_criteria,
            "details": f"Met: {len(met_criteria)}/{len(other_criteria)} criteria" if other_criteria else "No other criteria"
        }
        if meets:
            requirements_met.append("other_criteria")
        else:
            # Categorical: filter out if doesn't match
            requirements_missing.append("other_criteria")
            filter_reasons.append(f"Other criteria: Missing {', '.join(failed_criteria[:3])}")
    
    # NUMERICAL FILTERS (minimum threshold only - max handled in ranking)
    
    # Check experience (numerical - only check minimum)
    exp_req = structured.get("experience")
    if not exp_req and structured.get("other_criteria"):
        # Try to extract experience from other_criteria
        exp_req = extract_experience_from_other_criteria(structured["other_criteria"])
        if exp_req:
            exp_req["specified"] = True
    
    if exp_req and exp_req.get("specified"):
        specified_requirements.append("experience")
        meets, reason = check_experience_compliance(resume, exp_req)
        compliance["experience"] = {
            "meets": meets,
            "requirement": exp_req,
            "details": reason
        }
        if meets:
            requirements_met.append("experience")
        else:
            # Numerical: filter out if below minimum
            requirements_missing.append("experience")
            filter_reasons.append(f"Experience: {reason}")
    
    # Calculate compliance score (only for specified requirements)
    specified_count = len(specified_requirements)
    if specified_count == 0:
        compliance_score = 1.0  # No requirements = 100% compliant
    else:
        compliance_score = len(requirements_met) / specified_count
    
    # Determine if should filter
    # CRITICAL: 0% compliance ALWAYS filters out, regardless of mode
    should_filter = False
    filter_reason = None
    
    # PRIORITY 1: Always filter out 0% compliance (no requirements met)
    if specified_count > 0 and compliance_score == 0.0:
        should_filter = True
        filter_reason = "; ".join(filter_reasons[:3]) if filter_reasons else "0% compliance - no requirements met"
    # PRIORITY 2: Handle partial compliance based on filter mode
    elif requirements_missing:
        # Partial compliance - keep but mark as partial
        # Only filter if critical categorical requirements are missing
        critical_categorical = ["hard_skills", "department"]
        critical_missing = [r for r in requirements_missing if r in critical_categorical]
        
        if FILTER_MODE == "strict" and critical_missing:
            # Strict mode: filter if any critical categorical requirement is missing
            should_filter = True
            filter_reason = "; ".join(filter_reasons[:3])
        elif FILTER_MODE == "flexible":
            # Flexible mode: only filter if ALL skills missing (0% skills match)
            if "hard_skills" in requirements_missing:
                skills_compliance = compliance.get("hard_skills", {})
                skills_found = skills_compliance.get("found", [])
                if len(skills_found) == 0:  # 0 skills found
                    should_filter = True
                    filter_reason = "; ".join(filter_reasons[:3])
    
    return {
        "should_filter": should_filter,
        "filter_reason": filter_reason,
        "compliance": compliance,
        "requirements_met": requirements_met,
        "requirements_missing": requirements_missing,
        "compliance_score": compliance_score,
        "specified_requirements_count": specified_count
    }


def main():
    """Main function to filter resumes based on HR requirements."""
    # Load HR Filter Requirements (priority) or use empty
    # NOTE: We read from HR_Filter_Requirements.json instead of JD's filter_requirements
    # This ensures only HR-specified requirements are used for compliance
    hr_filter_file = Path("InputThread/JD/HR_Filter_Requirements.json")
    
    if hr_filter_file.exists():
        with hr_filter_file.open("r", encoding="utf-8") as f:
            filter_requirements = json.load(f)
    else:
        filter_requirements = None
    
    # Check if any requirements are actually specified
    if not filter_requirements or not filter_requirements.get("structured"):
        print("ℹ️ No HR filter requirements provided. Skipping early filtering.")
        print("   → All candidates will pass through to ranking/scoring")
        return
    
    structured = filter_requirements.get("structured", {})
    
    # Check if ANY requirement is specified
    has_experience = structured.get("experience") and structured.get("experience", {}).get("specified")
    has_skills = bool(structured.get("hard_skills", []))
    has_department = structured.get("department") and structured.get("department", {}).get("specified")
    has_location = bool(structured.get("location"))
    has_education = bool(structured.get("education", []))
    has_other = bool(structured.get("other_criteria", []))
    
    if not any([has_experience, has_skills, has_department, has_location, has_education, has_other]):
        print("ℹ️ No specific HR requirements specified. Skipping early filtering.")
        print("   → All candidates will pass through to ranking/scoring")
        return
    
    print(f"ℹ️ Found HR filter requirements")
    print(f"   - Source: HR_Filter_Requirements.json (not from JD)")
    exp_req = structured.get("experience", {})
    exp_str = f"{exp_req.get('min', 'N/A')}-{exp_req.get('max', 'N/A')} years" if exp_req and exp_req.get("specified") else "None"
    print(f"   - Experience: {exp_str}")
    print(f"   - Hard Skills: {len(structured.get('hard_skills', []))} skills")
    dept_req = structured.get("department", {})
    dept_str = dept_req.get("category", "None") if dept_req and dept_req.get("specified") else "None"
    print(f"   - Department: {dept_str}")
    print(f"   - Location: {structured.get('location', 'None')}")
    print(f"   - Other Criteria: {len(structured.get('other_criteria', []))} criteria")
    print(f"\n⚙️ Filter Configuration:")
    print(f"   - Mode: {FILTER_MODE}")
    print(f"   - Skill Match Threshold: {int(SKILL_MATCH_THRESHOLD*100)}%")
    print(f"   - Skill Normalization: Handled by LLM during parsing (canonical forms)")
    
    # Process all resumes (only in root directory, exclude FilteredResumes subdirectory)
    resume_files = [
        f for f in PROCESSED_JSON_DIR.glob("*.json")
        if f.parent == PROCESSED_JSON_DIR  # Only root directory files
    ]
    if not resume_files:
        print("⚠️ No resumes found")
        return
    
    filtered_resumes = []
    compliant_resumes = []
    
    print(f"\n🔍 Filtering {len(resume_files)} resumes...\n")
    
    for resume_file in resume_files:
        try:
            with resume_file.open("r", encoding="utf-8") as f:
                resume = json.load(f)
            
            name = resume.get("name", resume_file.stem)
            candidate_id = resume.get("candidate_id")
            
            # Check compliance
            result = check_all_requirements(resume, filter_requirements)
            
            compliance_score = result.get("compliance_score", 1.0)
            specified_count = result.get("specified_requirements_count", 0)
            
            if result["should_filter"]:
                # Add to filtered list
                filtered_resume = {
                    "name": name,
                    "candidate_id": candidate_id,
                    "filter_reason": result["filter_reason"],
                    "requirements_missing": result["requirements_missing"],
                    "compliance": result["compliance"],
                    "compliance_score": compliance_score
                }
                filtered_resumes.append(filtered_resume)
                print(f"🚫 FILTERED → {name} | Compliance: {int(compliance_score*100)}% ({len(result['requirements_met'])}/{specified_count}) | Reason: {result['filter_reason']}")
            else:
                # Keep resume for processing
                compliant_resumes.append(resume_file)
                if result["requirements_missing"]:
                    print(f"⚠️ PARTIAL → {name} | Compliance: {int(compliance_score*100)}% ({len(result['requirements_met'])}/{specified_count}) | Missing: {', '.join(result['requirements_missing'])}")
                else:
                    print(f"✅ COMPLIANT → {name} | Compliance: {int(compliance_score*100)}% ({len(result['requirements_met'])}/{specified_count})")
        
        except Exception as e:
            print(f"⚠️ Error processing {resume_file.name}: {e}")
            # On error, keep resume (don't filter out)
            compliant_resumes.append(resume_file)
            continue
    
    # Save filtered resumes to Skipped.json
    if filtered_resumes:
        SKIPPED_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Load existing skipped if any
        existing_skipped = []
        if SKIPPED_FILE.exists():
            try:
                with SKIPPED_FILE.open("r", encoding="utf-8") as f:
                    existing_skipped = json.load(f)
            except json.JSONDecodeError:
                existing_skipped = []
        
        # Merge with existing
        existing_skipped.extend(filtered_resumes)
        with SKIPPED_FILE.open("w", encoding="utf-8") as f:
            json.dump(existing_skipped, f, indent=2)
        
        print(f"\n📝 Saved {len(filtered_resumes)} filtered resumes to {SKIPPED_FILE}")
    
    # Move filtered resumes to a separate directory or mark them
    # For now, we'll just skip them in subsequent processing
    # Create a marker file or move them to FilteredResumes/ directory
    FILTERED_DIR = PROCESSED_JSON_DIR / "FilteredResumes"
    FILTERED_DIR.mkdir(exist_ok=True)
    
    for resume_file in resume_files:
        if resume_file not in compliant_resumes:
            # Move to filtered directory
            try:
                if resume_file.exists():  # Check if file still exists
                    resume_file.rename(FILTERED_DIR / resume_file.name)
            except Exception as e:
                print(f"⚠️ Could not move {resume_file.name}: {e}")
    
    print(f"\n✅ Early filtering complete!")
    print(f"   - Compliant resumes: {len(compliant_resumes)}")
    print(f"   - Filtered resumes: {len(filtered_resumes)}")
    print(f"   - Filtered resumes moved to: {FILTERED_DIR}")


if __name__ == "__main__":
    main()


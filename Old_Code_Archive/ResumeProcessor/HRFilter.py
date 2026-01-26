#!/usr/bin/env python3
"""
HRFilter.py

Parses HR notes from JD and filters/ranks candidates based on inferred requirements.
- Extracts requirements from HR notes (experience years, skills, etc.)
- Checks resume compliance against HR note criteria
- Calculates HR compliance score
- Identifies candidates that should be filtered out
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

JD_DIR = Path("InputThread/JD")
PROCESSED_JSON_DIR = Path("ProcessedJson")


def extract_hr_notes_from_jd(jd: dict) -> List[Dict[str, Any]]:
    """
    Extract HR notes from JD.json.
    Returns list of parsed HR note dictionaries.
    """
    hr_notes = []
    
    # First, try to get from hr_notes field directly
    if "hr_notes" in jd and isinstance(jd["hr_notes"], list):
        hr_notes.extend(jd["hr_notes"])
    
    # Also parse from domain_tags (HR_NOTE:cat=...;type=...;impact=...;note=...)
    domain_tags = jd.get("domain_tags", [])
    for tag in domain_tags:
        if isinstance(tag, str) and tag.startswith("HR_NOTE:"):
            try:
                # Parse: HR_NOTE:cat=clarity;type=inferred_requirement;impact=0.8;note=...
                parts = tag[8:].split(";")
                note_data = {}
                for part in parts:
                    if "=" in part:
                        key, value = part.split("=", 1)
                        note_data[key.strip()] = value.strip()
                
                # Convert impact to float if possible
                if "impact" in note_data:
                    try:
                        note_data["impact"] = float(note_data["impact"])
                    except ValueError:
                        note_data["impact"] = 0.5
                else:
                    note_data["impact"] = 0.5
                
                hr_notes.append(note_data)
            except Exception as e:
                print(f"⚠️ Error parsing HR note tag: {tag[:50]}... → {e}")
                continue
    
    return hr_notes


def parse_experience_requirement(note_text: str) -> Optional[Dict[str, Any]]:
    """
    Parse experience requirement from HR note text.
    Examples:
    - "Experience should be 2-3 years" → {"min": 2, "max": 3}
    - "Requires 5+ years" → {"min": 5}
    - "2 to 3 years experience" → {"min": 2, "max": 3}
    """
    if not note_text:
        return None
    
    note_lower = note_text.lower()
    
    # Pattern 1: "X-Y years" or "X to Y years"
    range_match = re.search(r'(\d+)\s*[-–—to]+\s*(\d+)\s*years?', note_lower)
    if range_match:
        return {"min": int(range_match.group(1)), "max": int(range_match.group(2))}
    
    # Pattern 2: "X+ years" or "at least X years"
    min_match = re.search(r'(?:at least|minimum|min|more than|over)\s*(\d+)\s*years?', note_lower)
    if min_match:
        return {"min": int(min_match.group(1))}
    
    # Pattern 3: "X years" (exact)
    exact_match = re.search(r'(\d+)\s*years?\s*(?:of|experience|exp)', note_lower)
    if exact_match:
        years = int(exact_match.group(1))
        return {"min": years, "max": years + 2}  # Allow some flexibility
    
    # Pattern 4: "X+ years" (simple)
    plus_match = re.search(r'(\d+)\+\s*years?', note_lower)
    if plus_match:
        return {"min": int(plus_match.group(1))}
    
    return None


def parse_skill_requirement(note_text: str, jd_skills: List[str]) -> List[str]:
    """
    Extract skill requirements from HR note text.
    Matches against JD skills to identify which skills are required.
    """
    if not note_text:
        return []
    
    note_lower = note_text.lower()
    required_skills = []
    
    # Check if note mentions any JD skills
    for skill in jd_skills:
        skill_lower = skill.lower()
        # Check for skill mention in note
        if skill_lower in note_lower or any(word in note_lower for word in skill_lower.split()):
            required_skills.append(skill)
    
    return required_skills


def check_experience_compliance(resume: dict, exp_req: Dict[str, Any]):
    """
    Check if resume meets experience requirement.
    Returns (is_compliant, reason)
    """
    resume_years = resume.get("years_experience")
    if resume_years is None:
        return False, "Experience not specified in resume"
    
    try:
        resume_years = float(resume_years)
    except (ValueError, TypeError):
        return False, "Invalid experience format in resume"
    
    min_years = exp_req.get("min", 0)
    max_years = exp_req.get("max", float('inf'))
    
    if resume_years < min_years:
        return False, f"Resume has {resume_years} years, but requires at least {min_years} years"
    if resume_years > max_years:
        return False, f"Resume has {resume_years} years, but requires at most {max_years} years"
    
    return True, "Experience requirement met"


def check_skill_compliance(resume: dict, required_skills: List[str]):
    """
    Check if resume has required skills.
    Returns (compliance_score, found_skills, missing_skills)
    """
    if not required_skills:
        return 1.0, [], []
    
    # Collect all skills from resume
    resume_skills = set()
    
    # From canonical_skills
    canonical = resume.get("canonical_skills", {})
    for cat_skills in canonical.values():
        if isinstance(cat_skills, list):
            resume_skills.update(s.lower() for s in cat_skills if s)
    
    # From inferred_skills
    for inf in resume.get("inferred_skills", []):
        if inf.get("skill"):
            resume_skills.add(inf["skill"].lower())
    
    # From skill_proficiency
    for sp in resume.get("skill_proficiency", []):
        if sp.get("skill"):
            resume_skills.add(sp["skill"].lower())
    
    # From projects
    for proj in resume.get("projects", []):
        for skill_list in [proj.get("tech_keywords", []), proj.get("primary_skills", [])]:
            resume_skills.update(s.lower() for s in skill_list if s)
    
    # Check which required skills are found
    required_lower = [s.lower() for s in required_skills]
    found = [s for s in required_lower if s in resume_skills]
    missing = [s for s in required_lower if s not in resume_skills]
    
    compliance_score = len(found) / len(required_skills) if required_skills else 1.0
    
    return compliance_score, found, missing


def check_hr_compliance(resume: dict, hr_notes: List[Dict[str, Any]], jd: dict) -> Dict[str, Any]:
    """
    Check resume compliance against all HR notes.
    Returns compliance result dictionary.
    """
    compliance_results = {
        "hr_compliance_score": 1.0,
        "passed_requirements": [],
        "failed_requirements": [],
        "should_filter": False,
        "filter_reason": None
    }
    
    if not hr_notes:
        return compliance_results
    
    # Get JD skills for skill matching
    jd_skills = jd.get("required_skills", []) + jd.get("preferred_skills", [])
    
    total_impact = 0.0
    weighted_score = 0.0
    
    for hr_note in hr_notes:
        note_type = hr_note.get("type", "").lower()
        note_text = hr_note.get("note", "")
        impact = float(hr_note.get("impact", 0.5))
        category = hr_note.get("category", "general")
        
        # Only process inferred_requirement type notes for filtering
        if note_type != "inferred_requirement":
            continue
        
        total_impact += impact
        
        # Check experience requirements
        exp_req = parse_experience_requirement(note_text)
        if exp_req:
            is_compliant, reason = check_experience_compliance(resume, exp_req)
            if is_compliant:
                compliance_results["passed_requirements"].append({
                    "type": "experience",
                    "requirement": exp_req,
                    "note": note_text[:100]
                })
                weighted_score += impact * 1.0
            else:
                compliance_results["failed_requirements"].append({
                    "type": "experience",
                    "requirement": exp_req,
                    "reason": reason,
                    "note": note_text[:100],
                    "impact": impact
                })
                weighted_score += impact * 0.0
                # High impact failures should filter
                if impact >= 0.7:
                    compliance_results["should_filter"] = True
                    compliance_results["filter_reason"] = f"Failed critical experience requirement: {reason}"
        
        # Check skill requirements
        required_skills = parse_skill_requirement(note_text, jd_skills)
        if required_skills:
            skill_score, found, missing = check_skill_compliance(resume, required_skills)
            if skill_score >= 0.5:  # At least 50% of required skills
                compliance_results["passed_requirements"].append({
                    "type": "skills",
                    "required": required_skills,
                    "found": found,
                    "note": note_text[:100]
                })
                weighted_score += impact * skill_score
            else:
                compliance_results["failed_requirements"].append({
                    "type": "skills",
                    "required": required_skills,
                    "missing": missing,
                    "note": note_text[:100],
                    "impact": impact
                })
                weighted_score += impact * skill_score
                # High impact failures should filter
                if impact >= 0.7 and skill_score < 0.3:
                    compliance_results["should_filter"] = True
                    compliance_results["filter_reason"] = f"Missing critical skills: {', '.join(missing[:3])}"
    
    # Calculate final compliance score
    if total_impact > 0:
        compliance_results["hr_compliance_score"] = weighted_score / total_impact
    else:
        compliance_results["hr_compliance_score"] = 1.0  # No requirements = fully compliant
    
    return compliance_results


def main():
    """Main function to process all resumes and add HR compliance scores."""
    # Load JD
    jd_files = list(JD_DIR.glob("*.json"))
    if not jd_files:
        print(f"❌ No JD JSON found in {JD_DIR}")
        return
    
    with jd_files[0].open("r", encoding="utf-8") as f:
        jd = json.load(f)
    
    # Extract HR notes
    hr_notes = extract_hr_notes_from_jd(jd)
    print(f"ℹ️ Found {len(hr_notes)} HR notes in JD")
    
    if not hr_notes:
        print("⚠️ No HR notes found. Skipping HR filtering.")
        return
    
    # Process all resumes
    resume_files = list(PROCESSED_JSON_DIR.glob("*.json"))
    if not resume_files:
        print("⚠️ No resumes found")
        return
    
    results = []
    for resume_file in resume_files:
        try:
            with resume_file.open("r", encoding="utf-8") as f:
                resume = json.load(f)
            
            compliance = check_hr_compliance(resume, hr_notes, jd)
            
            result = {
                "name": resume.get("name", resume_file.stem),
                "hr_compliance_score": compliance["hr_compliance_score"],
                "hr_should_filter": compliance["should_filter"],
                "hr_filter_reason": compliance["filter_reason"],
                "hr_passed_requirements": len(compliance["passed_requirements"]),
                "hr_failed_requirements": len(compliance["failed_requirements"])
            }
            
            if resume.get("candidate_id"):
                result["candidate_id"] = resume["candidate_id"]
            
            results.append(result)
            
        except Exception as e:
            print(f"⚠️ Error processing {resume_file.name}: {e}")
            continue
    
    # Update Scores.json
    scores_file = Path("Ranking/Scores.json")
    if scores_file.exists():
        with scores_file.open("r", encoding="utf-8") as f:
            try:
                existing_scores = json.load(f)
            except json.JSONDecodeError:
                existing_scores = []
    else:
        existing_scores = []
    
    # Build maps for merging
    existing_map_by_id = {}
    existing_map_by_name = {}
    for entry in existing_scores:
        if isinstance(entry, dict):
            if entry.get("candidate_id"):
                existing_map_by_id[entry["candidate_id"]] = entry
            if entry.get("name"):
                existing_map_by_name[entry["name"]] = entry
    
    # Merge HR compliance scores
    for result in results:
        candidate_id = result.get("candidate_id")
        name = result.get("name")
        
        if candidate_id and candidate_id in existing_map_by_id:
            existing_map_by_id[candidate_id].update(result)
        elif name and name in existing_map_by_name:
            existing_map_by_name[name].update(result)
        else:
            # New entry
            new_entry = result.copy()
            if candidate_id:
                existing_map_by_id[candidate_id] = new_entry
            if name:
                existing_map_by_name[name] = new_entry
    
    # Combine results
    final_scores = list(existing_map_by_id.values())
    for name, entry in existing_map_by_name.items():
        if not entry.get("candidate_id") or entry["candidate_id"] not in existing_map_by_id:
            final_scores.append(entry)
    
    # Write back
    scores_file.parent.mkdir(parents=True, exist_ok=True)
    with scores_file.open("w", encoding="utf-8") as f:
        json.dump(final_scores, f, indent=4)
    
    print(f"\n✅ HR compliance scores added to {scores_file}")
    print(f"📊 Processed {len(results)} resumes")


if __name__ == "__main__":
    main()


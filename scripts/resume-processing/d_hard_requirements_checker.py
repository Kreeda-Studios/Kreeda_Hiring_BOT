#!/usr/bin/env python3

"""
Hard Requirements Checker for Resume Analysis

Checks mandatory HR requirements using filter_requirements.mandatory_compliances.structured format.
Returns simple pass/fail based on whether candidate meets ALL mandatory requirements.
"""

from typing import Dict, Any

def check_hard_requirements(resume: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if resume meets ALL mandatory compliance requirements.
    Uses filter_requirements.mandatory_compliances.structured format.
    
    Returns: {
        'success': bool,
        'meets_all_requirements': bool,
        'compliance_score': float,
        'requirements_met': list,
        'requirements_missing': list,
        'filter_reason': str or None,
        'error': str or None
    }
    """
    try:
        # Extract mandatory compliances from JD
        filter_requirements = jd_data.get('filter_requirements', {})
        mandatory_compliances = filter_requirements.get('mandatory_compliances', {})
        
        if not mandatory_compliances:
            # No mandatory requirements
            return {
                'success': True,
                'meets_all_requirements': True,
                'compliance_score': 1.0,
                'requirements_met': [],
                'requirements_missing': [],
                'filter_reason': None,
                'error': None
            }
        
        structured = mandatory_compliances.get('structured', {})
        
        if not structured:
            # No structured requirements
            return {
                'success': True,
                'meets_all_requirements': True,
                'compliance_score': 1.0,
                'requirements_met': [],
                'requirements_missing': [],
                'filter_reason': None,
                'error': None
            }
        
        # Check each requirement
        requirements_met = []
        requirements_missing = []
        filter_reasons = []
        
        def field_has_value(val):
            """Check if a field has a meaningful value."""
            if val is None:
                return False
            if isinstance(val, bool):
                return val
            if isinstance(val, (list, tuple, set)):
                return len(val) > 0
            if isinstance(val, dict):
                if val.get('specified', False):
                    return True
                for k, v in val.items():
                    if k != 'specified' and v not in (None, [], {}, ''):
                        return True
                return False
            return bool(val)
        
        # Check each field in structured requirements
        for field_name, field_spec in structured.items():
            if not field_has_value(field_spec):
                continue  # Skip empty fields
            
            # Check the requirement
            meets_requirement = check_requirement(resume, field_name, field_spec)
            
            if meets_requirement:
                requirements_met.append(field_name)
            else:
                requirements_missing.append(field_name)
                filter_reasons.append(f"{field_name}: requirement not met")
        
        # Calculate compliance
        total_requirements = len(requirements_met) + len(requirements_missing)
        if total_requirements == 0:
            compliance_score = 1.0
            meets_all = True
        else:
            compliance_score = len(requirements_met) / total_requirements
            meets_all = len(requirements_missing) == 0
        
        filter_reason = None
        if not meets_all and filter_reasons:
            filter_reason = '; '.join(filter_reasons[:3])
        
        return {
            'success': True,
            'meets_all_requirements': meets_all,
            'compliance_score': compliance_score,
            'requirements_met': requirements_met,
            'requirements_missing': requirements_missing,
            'filter_reason': filter_reason,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'meets_all_requirements': False,
            'compliance_score': 0.0,
            'requirements_met': [],
            'requirements_missing': [],
            'filter_reason': None,
            'error': f"Hard requirements check failed: {str(e)}"
        }


def check_requirement(resume: Dict[str, Any], field_name: str, field_spec: Any) -> bool:
    """
    Check if resume meets a specific requirement.
    Returns True if requirement is met, False otherwise.
    """
    try:
        # Handle different requirement types
        if field_name == 'experience':
            return check_experience(resume, field_spec)
        elif field_name == 'hard_skills':
            return check_skills(resume, field_spec)
        elif field_name == 'education':
            return check_education(resume, field_spec)
        elif field_name == 'location':
            return check_location(resume, field_spec)
        else:
            # Unknown requirement type - pass by default
            return True
    except Exception:
        return False


def check_experience(resume: Dict[str, Any], spec: Any) -> bool:
    """Check experience requirement."""
    if not isinstance(spec, dict) or not spec.get('specified'):
        return True
    
    min_years = spec.get('min', 0)
    resume_years = resume.get('years_experience', 0)
    
    try:
        resume_years = float(resume_years)
    except (ValueError, TypeError):
        resume_years = 0.0
    
    return resume_years >= min_years


def check_skills(resume: Dict[str, Any], spec: Any) -> bool:
    """Check skills requirement."""
    if not isinstance(spec, dict) or not spec.get('specified'):
        return True
    
    required_skills = spec.get('required', [])
    if not required_skills:
        return True
    
    # Collect resume skills
    resume_skills = set()
    
    # From canonical_skills
    canonical = resume.get('canonical_skills', {})
    for cat_skills in canonical.values():
        if isinstance(cat_skills, list):
            resume_skills.update(s.lower().strip() for s in cat_skills if s)
    
    # From inferred_skills
    for inf in resume.get('inferred_skills', []):
        if inf.get('skill'):
            resume_skills.add(inf['skill'].lower().strip())
    
    # From skill_proficiency
    for sp in resume.get('skill_proficiency', []):
        if sp.get('skill'):
            resume_skills.add(sp['skill'].lower().strip())
    
    # Check if all required skills are present
    for req_skill in required_skills:
        req_normalized = req_skill.lower().strip()
        found = any(req_normalized in skill or skill in req_normalized for skill in resume_skills)
        if not found:
            return False
    
    return True


def check_education(resume: Dict[str, Any], spec: Any) -> bool:
    """Check education requirement."""
    if not isinstance(spec, dict) or not spec.get('specified'):
        return True
    
    required_ed = spec.get('required', '') or spec.get('minimum', '')
    if not required_ed:
        return True
    
    education_entries = resume.get('education', [])
    if not education_entries:
        return False
    
    # Simple check - if any education entry matches
    req_lower = required_ed.lower()
    for edu in education_entries:
        degree = edu.get('degree', '').lower()
        if req_lower in degree or degree in req_lower:
            return True
    
    return False


def check_location(resume: Dict[str, Any], spec: Any) -> bool:
    """Check location requirement."""
    if not isinstance(spec, dict) or not spec.get('specified'):
        return True
    
    required_loc = spec.get('required', '')
    if not required_loc or required_loc.lower() in ['any', 'anywhere', 'flexible']:
        return True
    
    candidate_loc = resume.get('location', '').lower()
    if not candidate_loc:
        return False
    
    required_loc_lower = required_loc.lower()
    
    # Check for remote/onsite/hybrid
    if 'remote' in required_loc_lower and 'remote' in candidate_loc:
        return True
    
    # Check for city/state match
    if required_loc_lower in candidate_loc or candidate_loc in required_loc_lower:
        return True
    
    return False

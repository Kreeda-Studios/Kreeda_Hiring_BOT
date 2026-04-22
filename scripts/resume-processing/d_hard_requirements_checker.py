#!/usr/bin/env python3

"""
Pure LLM-Based Hard Requirements Checker for Resume Analysis
Completely replaces the old rigid string-matching arrays with dynamic semantic compliance verification.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any

# Ensure we can import from common
script_dir = Path(__file__).parent
parent_dir = script_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from openai_client import parse_json_response

def check_hard_requirements(resume: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if resume meets ALL mandatory compliance requirements using LLM Intelligence natively.
    
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
        filter_reqs = jd_data.get('filter_requirements', {}).get('mandatory_compliances', {})
        
        # If there are no mandatory compliances to strictly verify, let them immediately pass
        has_raw = bool(filter_reqs.get('raw_prompt', '').strip())
        has_structured = bool(filter_reqs.get('structured', {}))
        
        if not filter_reqs or (not has_raw and not has_structured):
            return {
                'success': True,
                'meets_all_requirements': True,
                'compliance_score': 1.0,
                'requirements_met': [],
                'requirements_missing': [],
                'filter_reason': None,
                'error': None
            }
            
        system_prompt = (
            "You are an HR Compliance screener. Your ONLY job is to check if the candidate's resume contains evidence of each mandatory requirement. "
            "Use broad semantic matching: treat synonyms, abbreviations, and closely related terms as equivalent "
            "(e.g. 'Gen AI' = 'Generative AI', 'manual testing' + 'automation testing' = 'testing', 'New York' = 'USA'). "
            "PASS the candidate if the skill or concept appears ANYWHERE in their resume — in experience, skills, projects, or certifications. "
            "CRITICAL: You MUST thoroughly scan all JSON fields including `inferred_skills`, `skill_proficiency`, `ats_boost_line`, and `canonical_skills` for evidence! "
            "CRITICAL EXCEPTION: If a requirement has its value or 'required' field as 'Not specified', 'Any', or blank, you MUST automatically PASS that specific requirement without failing the candidate. "
            "FAIL the candidate ONLY if a true mandatory requirement has zero mention or evidence in the entire resume. "
            "Return JSON: "
            "{"
            "   'meets_all_requirements': bool, "
            "   'compliance_score': float (0.0 to 1.0), "
            "   'requirements_met': ['list of met criteria'], "
            "   'requirements_missing': ['list of missing criteria'], "
            "   'filter_reason': 'One-line reason if rejected (e.g. No mention of Python anywhere in resume), or null'"
            "}"
        )
        
        prompt = (
            f"### CANDIDATE RESUME JSON:\n{json.dumps(resume)}\n\n"
            f"### MANDATORY REQUIREMENTS JSON:\n{json.dumps(filter_reqs)}\n\n"
            "Evaluate compliance now."
        )
        
        result = parse_json_response(prompt=prompt, system_prompt=system_prompt, model="gpt-4o-mini")
        
        return {
            'success': True,
            'meets_all_requirements': bool(result.get('meets_all_requirements', True)),
            'compliance_score': float(result.get('compliance_score', 1.0)),
            'requirements_met': result.get('requirements_met', []),
            'requirements_missing': result.get('requirements_missing', []),
            'filter_reason': result.get('filter_reason', None),
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'meets_all_requirements': False,
            'compliance_score': 0.0,
            'requirements_met': [],
            'requirements_missing': [],
            'filter_reason': "LLM engine failed to process validation.",
            'error': f"LLM Hard requirements check failed: {str(e)}"
        }

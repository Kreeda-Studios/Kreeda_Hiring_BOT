#!/usr/bin/env python3

"""
Pure LLM-Based Hard Requirements Checker for Resume Analysis

Compliance source priority:
  1. jd_data["jd_analysis"]["mandatory_compliances"]  → List[str] (LLM-extracted)
  2. jd_data["filter_requirements"]["mandatory_compliances"]["raw_prompt"]  → HR-typed raw text

Filtering ONLY happens when at least one source has content.
If both are empty/missing → everyone passes immediately.
"""

import sys
import json
from pathlib import Path
from typing import Dict, Any, List

script_dir = Path(__file__).parent
parent_dir = script_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from openai_client import parse_json_response


def _collect_mandatory_compliances(jd_data: Dict[str, Any]) -> str:
    """
    Read mandatory compliance raw text from:
        jd_data["filter_requirements"]["mandatory_compliances"]["raw_prompt"]

    Returns the raw HR-typed text, or empty string if not set.
    """
    filter_reqs = jd_data.get("filter_requirements") or {}
    mandatory_block = filter_reqs.get("mandatory_compliances") or {}
    return mandatory_block.get("raw_prompt", "").strip()


def check_hard_requirements(resume: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check if resume meets ALL mandatory compliance requirements.

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
        mandatory_raw = _collect_mandatory_compliances(jd_data)

        # Nothing specified → pass everyone immediately
        if not mandatory_raw:
            return {
                "success": True,
                "meets_all_requirements": True,
                "compliance_score": 1.0,
                "requirements_met": [],
                "requirements_missing": [],
                "filter_reason": None,
                "error": None,
            }

        system_prompt = (
            "You are an HR Compliance screener. Your ONLY job is to check if the candidate's resume "
            "contains evidence of each mandatory requirement listed. "
            "Use broad semantic matching: treat synonyms, abbreviations, and closely related terms as equivalent "
            "(e.g. 'Gen AI' = 'Generative AI', 'manual testing' + 'automation testing' = 'testing'). "
            "PASS the candidate if the skill or concept appears ANYWHERE in their resume — in experience, "
            "skills (provided or inferred), projects, certifications, or achievements. "
            "CRITICAL: Scan ALL JSON fields including `skills.provided`, `skills.inferred`, "
            "`experience.details[].impact`, `projects[].title`, and `certifications`. "
            "CRITICAL EXCEPTION: If a requirement is vague, 'Not specified', or blank, automatically PASS it. "
            "FAIL the candidate ONLY if a true mandatory requirement has zero mention or evidence anywhere. "
            "Return JSON: {"
            "   'meets_all_requirements': bool, "
            "   'compliance_score': float (0.0 to 1.0), "
            "   'requirements_met': ['list of met criteria'], "
            "   'requirements_missing': ['list of missing criteria'], "
            "   'filter_reason': 'Strictly One-line reason if rejected, or null'"
            "}"
        )

        prompt = (
            f"### CANDIDATE RESUME JSON:\n{json.dumps(resume)}\n\n"
            f"### MANDATORY REQUIREMENTS (HR specified — filter strictly on these):\n{mandatory_raw}\n\n"
            "Evaluate compliance now."
        )

        result = parse_json_response(prompt=prompt, system_prompt=system_prompt, model="gpt-4o-mini")

        return {
            "success": True,
            "meets_all_requirements": bool(result.get("meets_all_requirements", True)),
            "compliance_score": float(result.get("compliance_score", 1.0)),
            "requirements_met": result.get("requirements_met", []),
            "requirements_missing": result.get("requirements_missing", []),
            "filter_reason": result.get("filter_reason", None),
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "meets_all_requirements": False,
            "compliance_score": 0.0,
            "requirements_met": [],
            "requirements_missing": [],
            "filter_reason": "LLM engine failed to process validation.",
            "error": f"LLM Hard requirements check failed: {str(e)}",
        }

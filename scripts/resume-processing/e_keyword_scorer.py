#!/usr/bin/env python3

"""
Pure LLM-Based Skill & Compliance Scorer

Scores the resume against:
  - required_skills   (base score 0.0–0.7)
  - preferred_skills  (bonus up to +0.2)
  - soft_compliances  (bonus up to +0.1)

Soft compliance sources (merged):
  1. jd_analysis.soft_compliances          → List[str]  (LLM-extracted)
  2. filter_requirements.soft_compliances.raw_prompt  → HR raw text (fallback)
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


def _collect_soft_compliances(jd_data: Dict[str, Any]) -> str:
    """
    Read soft compliance raw text from:
        jd_data["filter_requirements"]["soft_compliances"]["raw_prompt"]

    Returns the raw HR-typed text, or empty string if not set.
    """
    filter_reqs = jd_data.get("filter_requirements") or {}
    soft_block = filter_reqs.get("soft_compliances") or {}
    return soft_block.get("raw_prompt", "").strip()


def calculate_keyword_scores(resume: Dict[str, Any], jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure LLM-based skill + soft compliance scoring.

    Reads from new JDExtraction schema:
        jd → jd_analysis → skills.required  (List[str])
        jd → jd_analysis → skills.preferred (List[str])
        jd → jd_analysis → soft_compliances (List[str])  ← NEW
        jd → filter_requirements → soft_compliances.raw_prompt  ← NEW fallback
    """
    try:
        # Support both wrapped and flat JD structures
        jd_analysis = jd.get("jd_analysis", jd)

        skills_block = jd_analysis.get("skills", {})
        required_skills  = skills_block.get("required")  or jd_analysis.get("required_skills",  [])
        preferred_skills = skills_block.get("preferred") or jd_analysis.get("preferred_skills", [])

        # Collect soft compliances from all sources
        soft_raw = _collect_soft_compliances(jd)

        has_preferred = bool(preferred_skills)
        has_soft      = bool(soft_raw)

        # Build system prompt dynamically based on what's available
        score_rules = (
            "Scoring rules:\n"
            "1. Base score (0.0–0.7): Fraction of Required Skills the candidate demonstrates.\n"
        )
        if has_preferred:
            score_rules += "2. Preferred Skills bonus (up to +0.2): Each matched preferred skill adds to the score.\n"
        else:
            score_rules += "2. No Preferred Skills provided — skip this bonus, max base score is 1.0.\n"

        if has_soft:
            score_rules += (
                "3. Soft Compliance bonus (up to +0.1): Each matched soft compliance criterion adds a small bonus.\n"
                "   Treat these as nice-to-have signals, NOT mandatory filters.\n"
            )
        else:
            score_rules += "3. No Soft Compliance criteria provided — skip this bonus.\n"

        score_rules += "4. Do NOT penalise for missing preferred or soft criteria.\n"

        system_prompt = (
            "You are a strict technical resume evaluator. Score the candidate solely based on how well "
            "their resume matches the Job Description.\n\n"
            + score_rules +
            "\nReturn ONLY this JSON: {"
            "   'overall_score': float (0.0 to 1.0), "
            "   'matched_required_skills': [list], "
            "   'missing_required_skills': [list], "
            "   'matched_preferred_skills': [list or []], "
            "   'missing_preferred_skills': [list or []], "
            "   'matched_soft_compliances': [list or []], "
            "   'missing_soft_compliances': [list or []], "
            "   'reasoning': 'Concise one-line explanation'"
            "}"
        )

        prompt = (
            f"### CANDIDATE RESUME:\n{json.dumps(resume)}\n\n"
            f"### REQUIRED SKILLS:\n{json.dumps(required_skills)}\n\n"
            f"### PREFERRED SKILLS:\n{json.dumps(preferred_skills) if has_preferred else 'None'}\n\n"
            f"### SOFT COMPLIANCE CRITERIA (HR specified — bonus signal only):\n{soft_raw if has_soft else 'None'}\n\n"
            "Evaluate and return the JSON score."
        )

        result = parse_json_response(prompt=prompt, system_prompt=system_prompt, model="gpt-4o-mini")

        return {
            "success": True,
            "overall_score": float(result.get("overall_score", 0.5)),
            "matched_required_skills":   result.get("matched_required_skills", []),
            "missing_required_skills":   result.get("missing_required_skills", []),
            "matched_preferred_skills":  result.get("matched_preferred_skills", []),
            "missing_preferred_skills":  result.get("missing_preferred_skills", []),
            "matched_soft_compliances":  result.get("matched_soft_compliances", []),
            "missing_soft_compliances":  result.get("missing_soft_compliances", []),
            "reasoning": result.get("reasoning", ""),
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "overall_score": 0.0,
            "error": f"LLM Keyword/Skill scoring failed: {str(e)}",
        }

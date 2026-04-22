#!/usr/bin/env python3

"""
Pure LLM-Based Skill Scorer
Replaces the old regex and iteration keyword lists with an intelligent evaluator focusing explicitly on 'Preferred Skills'.
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

def calculate_keyword_scores(resume: Dict[str, Any], jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pure LLM-based preferred skills and requirement matching score block.
    We name this calculate_keyword_scores so that `main_resume_processor.py` does not break,
    but underneath it mathematically boosts candidates matching preferred skill blocks.
    """
    try:
        jd_analysis = jd.get("jd_analysis", jd)
        preferred_skills = jd_analysis.get("preferred_skills", [])
        required_skills = jd_analysis.get("required_skills", [])
        
        system_prompt = (
            "You are a strict technical resume evaluator. Score the candidate solely based on how well their resume matches the Job Description skills. "
            "Scoring rules: "
            "1. Base score (0.0–0.7): Determined by how many Required Skills the candidate demonstrates. "
            "2. Preferred Skills bonus (up to +0.3): Only apply if Preferred Skills list is non-empty. Each matched preferred skill pushes the score closer to 1.0. "
            "3. If Preferred Skills list is empty, score purely on Required Skills coverage (max score = 1.0). "
            "4. Do not reward skills not mentioned in the JD. Do not penalize missing preferred skills — they are a bonus only. "
            "Return only this JSON: "
            "{"
            "   'overall_score': float (0.0 to 1.0), "
            "   'matched_required_skills': [list of required skills found in resume], "
            "   'missing_required_skills': [list of required skills absent from resume], "
            "   'matched_preferred_skills': [list of preferred skills found in resume, or [] if none provided], "
            "   'missing_preferred_skills': [list of preferred skills absent from resume, or [] if none provided], "
            "   'reasoning': 'Concise explanation of score based on required and preferred skill matches'"
            "}"
        )

        prompt = (
            f"### CANDIDATE RESUME:\n{json.dumps(resume)}\n\n"
            f"### REQUIRED SKILLS:\n{required_skills}\n\n"
            f"### PREFERRED SKILLS:\n{preferred_skills if preferred_skills else 'None — ignore preferred skills, score on required skills only.'}\n\n"
            "Evaluate the resume against the skills above and return the JSON score."
        )
        
        result = parse_json_response(prompt=prompt, system_prompt=system_prompt, model="gpt-4o-mini")
        
        return {
            "success": True,
            "overall_score": float(result.get("overall_score", 0.5)),
            "matched_preferred_skills": result.get("matched_preferred_skills", []),
            "missing_preferred_skills": result.get("missing_preferred_skills", []),
            "reasoning": result.get("reasoning", ""),
            "error": None
        }
        
    except Exception as e:
        return {
            "success": False,
            "overall_score": 0.0,
            "error": f"LLM Keyword/Preferred Skills scoring failed: {str(e)}"
        }

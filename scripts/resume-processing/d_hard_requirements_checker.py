#!/usr/bin/env python3

"""
Two-Phase Hard Requirements Checker for Resume Analysis
========================================================

Phase 1 — Python (deterministic, no LLM):
  - Parses experience range from HR filter text using regex.
  - Computes total experience from pre-structured resume fields (FT months + intern months).
  - Compares arithmetically. Zero possibility of LLM arithmetic errors.

Phase 2 — LLM (label + synonym + compound matching):
  - Runs ONLY if Phase 1 passes.
  - Checks skill keywords extracted from the same HR filter text.
  - Two matching rules:
      Rule 1: Exact label OR direct synonym/abbreviation (e.g. GenAI = Generative AI)
      Rule 2: Compound phrase containment, both directions
              (e.g. resume 'Manual and Automation Testing' covers both
               'Manual Testing' AND 'Automation Testing' requirements)
  - Does NOT do tool-inference (LangChain alone does NOT prove GenAI).
  - Receives only a flat skill list, NOT the full resume JSON.

Data source priority:
  1. jd_data["filter_requirements"]["mandatory_compliances"]["raw_prompt"]
       -> HR-typed text (primary). Parsed into experience range + skill keywords.
  2. jd_data["jd_analysis"]["mandatory_compliances"]
       -> AI-extracted list from JD (fallback when HR text is empty).

If both are empty -> everyone passes immediately.
"""

import re
import sys
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

script_dir = Path(__file__).parent
parent_dir = script_dir.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from openai_client import parse_json_response


# -----------------------------------------------------------------------------
# PHASE 1 HELPERS  --  Pure Python, no LLM
# -----------------------------------------------------------------------------

def _parse_experience_range(text: str) -> Optional[Dict[str, Optional[int]]]:
    """
    Extract a numeric experience range from an HR filter text string.

    Handles all common phrasings:
      "2 months to 1 year"      -> {min_months: 2,  max_months: 12}
      "6 months to 2 years"     -> {min_months: 6,  max_months: 24}
      "2 months to 12 months"   -> {min_months: 2,  max_months: 12}
      "1 year to 3 years"       -> {min_months: 12, max_months: 36}
      "6 to 12 months"          -> {min_months: 6,  max_months: 12}
      "1 to 2 years"            -> {min_months: 12, max_months: 24}

    Returns None if no experience range is found in the text.
    """
    result = None

    # "X months to Y year(s)"
    m = re.search(r'(\d+)\s*months?\s+to\s+(\d+)\s*years?', text, re.IGNORECASE)
    if m:
        result = {"min_months": int(m.group(1)), "max_months": int(m.group(2)) * 12}

    # "X year(s) to Y year(s)"
    if not result:
        m = re.search(r'(\d+)\s*years?\s+to\s+(\d+)\s*years?', text, re.IGNORECASE)
        if m:
            result = {"min_months": int(m.group(1)) * 12, "max_months": int(m.group(2)) * 12}

    # "X months to Y months"
    if not result:
        m = re.search(r'(\d+)\s*months?\s+to\s+(\d+)\s*months?', text, re.IGNORECASE)
        if m:
            result = {"min_months": int(m.group(1)), "max_months": int(m.group(2))}

    # "X to Y months"
    if not result:
        m = re.search(r'(\d+)\s+to\s+(\d+)\s*months?', text, re.IGNORECASE)
        if m:
            result = {"min_months": int(m.group(1)), "max_months": int(m.group(2))}

    # "X to Y years"
    if not result:
        m = re.search(r'(\d+)\s+to\s+(\d+)\s*years?', text, re.IGNORECASE)
        if m:
            result = {"min_months": int(m.group(1)) * 12, "max_months": int(m.group(2)) * 12}

    if result:
        # Determine the type of experience required
        text_lower = text.lower()
        if "internship experience" in text_lower or "intern experience" in text_lower:
            result["exp_type"] = "internship"
        elif "full time experience" in text_lower or "full-time experience" in text_lower:
            result["exp_type"] = "full_time"
        else:
            result["exp_type"] = "total"
        return result

    return None


def _extract_skill_keywords(raw_prompt: str) -> List[str]:
    """
    Remove the experience clause from the HR filter text and return the
    remaining comma-separated items as required skill keywords.

    Example:
      "Total experience(internship+full time): 2 months to 1 year, RAG, GenAI"
      -> ["RAG", "GenAI"]

    If there is no experience clause:
      "RAG, GenAI, LangChain"
      -> ["RAG", "GenAI", "LangChain"]
    """
    # Remove "[Type] experience..." prefix up to the next comma or end of string
    cleaned = re.sub(
        r'(?:total|internship|full\s*-?\s*time)\s+experience[^,]*(?:,|$)',
        '',
        raw_prompt,
        flags=re.IGNORECASE,
    ).strip().strip(',').strip()

    skills = [s.strip() for s in cleaned.split(',') if s.strip()]
    return skills





def _check_experience_python(
    resume: Dict[str, Any],
    exp_range: Dict[str, Optional[int]],
) -> Dict[str, Any]:
    """
    Pure Python experience range check using pre-computed resume fields.
    No LLM, no parsing -- just integer arithmetic.

    Returns:
        {
          'passed': bool,
          'total_months': int,
          'reason': str or None  -- human-readable rejection reason, None if passed
        }
    """
    exp_data = resume.get('experience') or {}
    ft_months = int(exp_data.get('total_full_time_experience') or 0)
    intern_months = int(exp_data.get('total_internship_experience_in_months') or 0)
    
    exp_type = exp_range.get('exp_type', 'total')
    
    if exp_type == 'internship':
        if ft_months > 0:
            return {
                'passed': False,
                'total_months': intern_months,
                'reason': (
                    f"Role is strictly for internship candidates, but candidate has "
                    f"{ft_months} month{'s' if ft_months != 1 else ''} of full-time experience."
                ),
            }
        value_to_check = intern_months
        type_str = "Internship experience"
    elif exp_type == 'full_time':
        value_to_check = ft_months
        type_str = "Full-time experience"
    else:
        value_to_check = ft_months + intern_months
        type_str = "Total experience"

    min_m = exp_range.get('min_months', 0)
    max_m = exp_range.get('max_months')  # None -> no upper limit

    if value_to_check < min_m:
        return {
            'passed': False,
            'total_months': value_to_check,
            'reason': (
                f"{type_str} is {value_to_check} month{'s' if value_to_check != 1 else ''}, "
                f"below the minimum requirement of {min_m} months."
            ),
        }

    if max_m is not None and value_to_check > max_m:
        max_display = (
            f"{max_m // 12} year{'s' if max_m >= 24 else ''}"
            if max_m % 12 == 0
            else f"{max_m} months"
        )
        return {
            'passed': False,
            'total_months': value_to_check,
            'reason': (
                f"{type_str} is {value_to_check} months, "
                f"exceeding the maximum requirement of {max_display}."
            ),
        }

    return {'passed': True, 'total_months': value_to_check, 'reason': None, 'type_str': type_str}


# -----------------------------------------------------------------------------
# PHASE 2 HELPER  --  LLM, skill label + synonym + compound matching
# -----------------------------------------------------------------------------

def _check_skills_llm(
    resume: Dict[str, Any],
    required_skills: List[str],
) -> Dict[str, Any]:
    """
    Ask the LLM whether each required skill is present in the resume using
    two matching rules:

    Rule 1 -- Synonym / abbreviation match:
      The required term OR any well-known synonym/abbreviation of it appears
      in the resume (e.g. 'GenAI' matches 'Generative AI', 'Gen AI').

    Rule 2 -- Compound phrase containment (bidirectional):
      (a) A resume skill phrase CONTAINS the required term as a component.
          e.g. required='Manual Testing', resume='Manual and Automation Testing' -> FOUND
      (b) The required term is a compound whose ALL components are individually
          present across the resume skills.
          e.g. required='Manual and Automation Testing', resume has 'Manual Testing'
          AND 'Automation Testing' separately -> FOUND

    What does NOT count: tool/framework inference. 'LangChain' alone does not
    prove 'GenAI'. Only direct label, synonym, or compound containment counts.

    Sends only a flat, compact skill list -- NOT the full resume JSON.
    """
    skills_data = resume.get('skills') or {}
    provided: List[str] = skills_data.get('provided') or []
    inferred: List[str] = skills_data.get('inferred') or []

    project_titles = [
        p.get('title', '')
        for p in (resume.get('projects') or [])
        if p.get('title')
    ]

    impact_bullets: List[str] = []
    for entry in (resume.get('experience') or {}).get('details') or []:
        impact_bullets.extend(entry.get('impact') or [])
    impact_bullets = impact_bullets[:15]  # hard cap -- keep prompt small

    system_prompt = (
        "You are a strict skill label matcher. Your ONLY task is to check whether "
        "each required skill is present in the candidate's resume data.\n\n"
        "Apply BOTH rules for every required skill:\n\n"
        "RULE 1 -- SYNONYM / ABBREVIATION MATCH:\n"
        "A required skill is FOUND if the resume contains the exact label OR any "
        "well-known synonym or abbreviation of it.\n"
        "Examples:\n"
        "  'GenAI' matches 'Generative AI', 'Gen AI', 'Generative Artificial Intelligence'\n"
        "  'RAG' matches 'Retrieval-Augmented Generation', 'Retrieval Augmented Generation'\n"
        "  'ML' matches 'Machine Learning'\n"
        "  'NLP' matches 'Natural Language Processing'\n"
        "  'CV' matches 'Computer Vision'\n"
        "  'QA' matches 'Quality Assurance'\n"
        "Apply this universally -- if the required term and a resume term refer to "
        "the same concept under a different spelling, abbreviation, or expansion, "
        "it is a MATCH.\n\n"
        "RULE 2 -- COMPOUND PHRASE CONTAINMENT (bidirectional):\n"
        "A required skill is FOUND if:\n"
        "  (a) Any resume skill phrase CONTAINS the required term as a component.\n"
        "      Example: required='Manual Testing', "
        "resume has='Manual and Automation Testing' -> FOUND\n"
        "      Example: required='Automation Testing', "
        "resume has='Manual and Automation Testing' -> FOUND\n"
        "  (b) The required term is itself a compound phrase whose ALL components "
        "are individually present across the resume skills.\n"
        "      Example: required='Manual and Automation Testing', "
        "resume has 'Manual Testing' AND 'Automation Testing' separately -> FOUND\n\n"
        "STRICT BOUNDARY -- what does NOT count as evidence:\n"
        "  - A related tool or framework that merely uses or is built for the skill.\n"
        "    Example: 'LangChain' alone does NOT prove 'GenAI'. "
        "Only a direct label, synonym, or compound containment match counts.\n"
        "  - Domain inference, multi-hop reasoning, or assumption.\n"
        "If neither Rule 1 nor Rule 2 produces a match -> NOT FOUND.\n\n"
        "Return ONLY this JSON:\n"
        "{\n"
        "  \"skills_check\": [\n"
        "    {\"required\": \"<skill name>\", \"found\": true/false, "
        "\"evidence\": \"<exact resume term that matched, or null>\"}\n"
        "  ],\n"
        "  \"all_present\": true/false\n"
        "}"
    )

    user_prompt = (
        f"Check each required skill against the resume data using "
        f"Rule 1 (synonym/abbreviation) and Rule 2 (compound containment).\n\n"
        f"REQUIRED SKILLS:\n{json.dumps(required_skills)}\n\n"
        f"RESUME PROVIDED SKILLS:\n{json.dumps(provided)}\n\n"
        f"RESUME INFERRED SKILLS:\n{json.dumps(inferred)}\n\n"
        f"PROJECT TITLES:\n{json.dumps(project_titles)}\n\n"
        f"EXPERIENCE IMPACT BULLETS (top 15):\n{json.dumps(impact_bullets)}\n\n"
        f"For each required skill: apply Rule 1 first, then Rule 2. Return the JSON."
    )

    return parse_json_response(
        prompt=user_prompt,
        system_prompt=system_prompt,
        model="gpt-4o-mini",
    )


# -----------------------------------------------------------------------------
# FALLBACK HELPER  --  LLM qualitative check against jd_analysis list
# -----------------------------------------------------------------------------

def _check_jd_compliances_llm(
    resume: Dict[str, Any],
    compliances: List[str],
) -> Dict[str, Any]:
    """
    Qualitative LLM check against the AI-extracted mandatory_compliances list
    from jd_analysis. Used only when HR has not typed any filter text.

    Sends a concise resume summary (not full JSON) to keep the prompt manageable.
    """
    exp_data = resume.get('experience') or {}
    skills_data = resume.get('skills') or {}

    resume_summary = {
        "domain": resume.get("domain"),
        "location": (resume.get('profile') or {}).get('location') or "",
        "total_full_time_experience_months": int(exp_data.get('total_full_time_experience') or 0),
        "total_internship_experience_months": int(exp_data.get('total_internship_experience_in_months') or 0),
        "skills_provided": skills_data.get('provided') or [],
        "skills_inferred": skills_data.get('inferred') or [],
        "project_titles": [
            p.get('title', '') for p in (resume.get('projects') or []) if p.get('title')
        ],
        "certifications": resume.get('certifications') or [],
        "education_degrees": [
            (e.get('degree') or '') for e in (resume.get('educations') or [])
        ],
    }

    system_prompt = (
        "You are an HR compliance screener. Evaluate whether the candidate meets "
        "all the mandatory requirements listed.\n"
        "Use synonym and abbreviation matching for skill terms.\n"
        "For experience requirements: use the numeric month fields provided -- "
        "do not re-estimate or infer experience independently. "
        "If a requirement specifies a maximum experience cap (e.g. '0-1 year' -> max 12 months) and the candidate has MORE experience than the maximum, mark them as failing due to OVERQUALIFICATION. "
        "The filter_reason MUST explicitly state 'Candidate has X months of experience, exceeding the maximum requirement of Y', NEVER say 'does not have experience' for candidates who have experience.\n\n"
        "For on-site / work location requirements, apply these rules in order:\n"
        "  1. FAIL: If the resume explicitly mentions 'remote', 'remote only', "
        "'work from home', 'WFH', 'remote preferred', or any similar phrase "
        "indicating the candidate only works remotely.\n"
        "  2. PASS: If the candidate's location field contains the required city "
        "name or is clearly within the same city/metro area "
        "(e.g. 'Pune', 'Pune, Maharashtra', 'Hadapsar, Pune', 'Pune 411032' all "
        "satisfy a requirement for on-site work in Pune).\n"
        "  3. PASS: If the candidate's location field is empty or absent -- "
        "give benefit of the doubt; do NOT reject solely because location is missing.\n"
        "Never reject a candidate for on-site availability unless they have explicitly "
        "stated they work remotely only.\n\n"
        "Return ONLY this JSON:\n"
        "{\n"
        "  \"meets_all_requirements\": true/false,\n"
        "  \"compliance_score\": 0.0-1.0,\n"
        "  \"requirements_met\": [\"...\"],\n"
        "  \"requirements_missing\": [\"...\"],\n"
        "  \"filter_reason\": \"one-line reason if rejected, or null if passed\"\n"
        "}"
    )

    user_prompt = (
        f"MANDATORY REQUIREMENTS:\n{json.dumps(compliances)}\n\n"
        f"CANDIDATE RESUME SUMMARY:\n{json.dumps(resume_summary)}\n\n"
        f"Evaluate compliance and return the JSON."
    )

    return parse_json_response(
        prompt=user_prompt,
        system_prompt=system_prompt,
        model="gpt-4o-mini",
    )


# -----------------------------------------------------------------------------
# PRIVATE RESULT BUILDERS
# -----------------------------------------------------------------------------

def _pass_result(requirements_met: List[str]) -> Dict[str, Any]:
    return {
        "success": True,
        "meets_all_requirements": True,
        "compliance_score": 1.0,
        "requirements_met": requirements_met,
        "requirements_missing": [],
        "filter_reason": None,
        "error": None,
    }


def _fail_result(
    requirements_met: List[str],
    requirements_missing: List[str],
    filter_reason: str,
) -> Dict[str, Any]:
    total = len(requirements_met) + len(requirements_missing)
    score = round(len(requirements_met) / total, 4) if total > 0 else 0.0
    return {
        "success": True,
        "meets_all_requirements": False,
        "compliance_score": score,
        "requirements_met": requirements_met,
        "requirements_missing": requirements_missing,
        "filter_reason": filter_reason,
        "error": None,
    }


# -----------------------------------------------------------------------------
# PUBLIC ENTRY POINT
# -----------------------------------------------------------------------------

def check_hard_requirements(
    resume: Dict[str, Any],
    jd_data: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Two-phase hard requirements check.

    Phase 1 (Python -- deterministic):
      Parses the HR filter text to extract an experience range.
      Computes total experience from resume integer fields.
      Arithmetic comparison: no LLM, no errors.

    Phase 2 (LLM -- label + synonym + compound matching):
      Runs only if Phase 1 passes.
      Checks skill keywords extracted from the same HR filter text.
      Two rules: synonym/abbreviation match + compound phrase containment.
      Does NOT do tool-inference (LangChain alone != GenAI).
      LLM receives only a flat skill list, not the full resume JSON.

    Fallback (LLM -- qualitative):
      If HR filter text is empty, falls back to jd_analysis.mandatory_compliances.
      Sends a compact resume summary (not full JSON).

    Returns:
        {
          'success': bool,
          'meets_all_requirements': bool,
          'compliance_score': float,
          'requirements_met': list[str],
          'requirements_missing': list[str],
          'filter_reason': str or None,
          'error': str or None
        }
    """
    try:
        # -- Read both data sources -----------------------------------------
        filter_reqs = jd_data.get('filter_requirements') or {}
        mandatory_block = filter_reqs.get('mandatory_compliances') or {}
        raw_prompt = (mandatory_block.get('raw_prompt') or '').strip()

        jd_analysis = jd_data.get('jd_analysis') or {}
        jd_compliances: List[str] = jd_analysis.get('mandatory_compliances') or []

        # -- Nothing to filter on -> pass everyone -------------------------
        if not raw_prompt and not jd_compliances:
            return _pass_result([])

        # ==================================================================
        # PRIMARY PATH: HR filter text is present
        # ==================================================================
        if raw_prompt:
            requirements_met: List[str] = []
            requirements_missing: List[str] = []

            # -- Phase 1: Experience range (Python, deterministic) ----------
            exp_range = _parse_experience_range(raw_prompt)

            if exp_range is not None:
                exp_check = _check_experience_python(resume, exp_range)

                if not exp_check['passed']:
                    # Hard fail -- reject immediately, no LLM call needed
                    return _fail_result(
                        requirements_met=[],
                        requirements_missing=[f"{exp_check.get('type_str', 'Experience').split()[0]}: {exp_check['reason']}"],
                        filter_reason=exp_check['reason'],
                    )

                # Experience passed -- record it
                total = exp_check['total_months']
                min_m = exp_range['min_months']
                max_m = exp_range.get('max_months')
                type_str = exp_check.get('type_str', 'Total experience')
                
                max_display = (
                    f"{max_m // 12} year{'s' if max_m >= 24 else ''}"
                    if max_m is not None and max_m % 12 == 0
                    else (f"{max_m} months" if max_m is not None else "no upper limit")
                )
                requirements_met.append(
                    f"{type_str}: {total} months is within the required range "
                    f"({min_m} months - {max_display})"
                )

            # -- Phase 2: Skill keywords (LLM, label + synonym + compound) --
            skill_keywords = _extract_skill_keywords(raw_prompt)

            if skill_keywords:
                skill_result = _check_skills_llm(resume, skill_keywords)
                skills_check: List[Dict] = skill_result.get('skills_check') or []

                for item in skills_check:
                    req_name = item.get('required', '?')
                    if item.get('found'):
                        evidence = item.get('evidence') or 'matched'
                        requirements_met.append(f"{req_name}: found ({evidence})")
                    else:
                        requirements_missing.append(f"{req_name}: no evidence found in resume")

                if requirements_missing:
                    missing_names = [
                        item.get('required', '?')
                        for item in skills_check
                        if not item.get('found')
                    ]
                    return _fail_result(
                        requirements_met=requirements_met,
                        requirements_missing=requirements_missing,
                        filter_reason=f"Missing required skill(s): {', '.join(missing_names)}",
                    )

            # All checks passed
            return _pass_result(requirements_met)

        # ==================================================================
        # FALLBACK PATH: No HR filter text -- use jd_analysis list
        # ==================================================================
        result = _check_jd_compliances_llm(resume, jd_compliances)
        return {
            "success": True,
            "meets_all_requirements": bool(result.get('meets_all_requirements', True)),
            "compliance_score": float(result.get('compliance_score', 1.0)),
            "requirements_met": result.get('requirements_met') or [],
            "requirements_missing": result.get('requirements_missing') or [],
            "filter_reason": result.get('filter_reason') or None,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "meets_all_requirements": False,
            "compliance_score": 0.0,
            "requirements_met": [],
            "requirements_missing": [],
            "filter_reason": "Compliance check engine failed.",
            "error": f"Hard requirements check failed: {str(e)}",
        }

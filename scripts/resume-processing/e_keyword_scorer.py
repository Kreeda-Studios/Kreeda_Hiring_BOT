#!/usr/bin/env python3

"""
Hybrid Skill & Compliance Scorer
==================================
Architecture (deterministic by design):

  ┌─────────────────────────────────────────────────────────┐
  │  LLM (gpt-4o-mini, temperature=0)                       │
  │  Job: ONLY semantic matching — boolean YES/NO per skill  │
  │  Handles: "ReactJS"="React", "ML"="Machine Learning"    │
  │  Output: per-skill matched: true/false lists             │
  └────────────────────────┬────────────────────────────────┘
                           │
                           ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Python (pure math, always deterministic)               │
  │  Job: compute score from boolean match counts           │
  │  Applies discrete bins + fixed bonuses                  │
  │  Output: overall_score float                            │
  └─────────────────────────────────────────────────────────┘

Scoring bins (applied in Python, not by LLM):
  required match %  < 30%  → base 0.0
  required match % 30–50%  → base 0.3
  required match % 51–85%  → base 0.7
  required match %  > 85%  → base 1.0
  preferred bonus: +0.1 if ≥50% preferred matched, else 0.0
  soft compliance bonus: +0.05 if criteria met, else 0.0
  cap: 1.0

Soft compliance sources:
  filter_requirements.soft_compliances.raw_prompt  → HR raw text
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


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _collect_soft_compliances(jd_data: Dict[str, Any]) -> str:
    """
    Read soft compliance raw text from:
        jd_data["filter_requirements"]["soft_compliances"]["raw_prompt"]
    Returns the raw HR-typed text, or empty string if not set.
    """
    filter_reqs = jd_data.get("filter_requirements") or {}
    soft_block  = filter_reqs.get("soft_compliances") or {}
    return soft_block.get("raw_prompt", "").strip()


def _pct_to_base_score(pct: float) -> float:
    """
    Convert required-skill match percentage to a smooth continuous base score.
    Replaces discrete step-function bins with linear continuous scaling (0.00 to 1.00)
    to prevent arbitrary score jumps between match ratios (e.g. 49% vs 51%).
    """
    if pct <= 0.0:
        return 0.0
    return min(1.0, round(float(pct), 4))


# ─────────────────────────────────────────────────────────────────────────────
# SYSTEM PROMPT  (LLM's job is matching, NOT scoring)
# ─────────────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a strict technical resume evaluator.

YOUR ONLY JOB IS SEMANTIC SKILL MATCHING — determine which skills from the provided \
lists are present in the candidate's resume. Use semantic understanding to recognise \
synonyms, abbreviations, and variant spellings as equivalent matches.

Synonym rules (non-exhaustive — apply broadly):
  • ReactJS  ↔  React
  • Node     ↔  Node.js  ↔  NodeJS
  • JS       ↔  JavaScript
  • TS       ↔  TypeScript
  • Postgres ↔  PostgreSQL
  • ML       ↔  Machine Learning
  • DL       ↔  Deep Learning
  • NLP      ↔  Natural Language Processing
  • CV       ↔  Computer Vision
  • k8s      ↔  Kubernetes
  • AWS S3, EC2, Lambda etc. all match "AWS"

DO NOT output a score. Output ONLY the JSON schema below.
For each skill, return:
  "matched": true  — if the resume contains that skill (or a recognised synonym/variant)
  "matched": false — if the resume does not contain that skill
  "matched_as"     — the exact text from the resume that matched, or null if not matched
"""


# ─────────────────────────────────────────────────────────────────────────────
# MAIN FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def calculate_keyword_scores(resume: Dict[str, Any], jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Hybrid LLM + Math keyword scorer.

    LLM step  → semantic skill matching (boolean per skill, temperature=0)
    Math step → deterministic score from match counts + discrete bins

    Reads from JDExtraction schema:
        jd → jd_analysis → skills.required   (List[str])
        jd → jd_analysis → skills.preferred  (List[str])
        jd → filter_requirements → soft_compliances.raw_prompt
    """
    try:
        # ── 1. Collect inputs ────────────────────────────────────────────────
        jd_analysis = jd.get("jd_analysis", jd)

        skills_block     = jd_analysis.get("skills", {})
        required_skills  = skills_block.get("required")  or jd_analysis.get("required_skills",  [])
        preferred_skills = skills_block.get("preferred") or jd_analysis.get("preferred_skills", [])
        
        # Fallback: If JD parser failed to extract explicit required skills but extracted a tech stack,
        # flatten the tech stack and use it as required skills to prevent everyone getting 1.0.
        if not required_skills:
            tech_stack = jd_analysis.get("tech_stack", {})
            for key, items in tech_stack.items():
                if isinstance(items, list):
                    required_skills.extend(items)
        
        soft_raw         = _collect_soft_compliances(jd)

        has_required  = bool(required_skills)
        has_preferred = bool(preferred_skills)
        has_soft      = bool(soft_raw)

        # ── 2. Build user prompt ─────────────────────────────────────────────
        prompt = (
            f"### CANDIDATE RESUME:\n{json.dumps(resume)}\n\n"
            f"### REQUIRED SKILLS TO MATCH:\n"
            f"{json.dumps(required_skills) if has_required else '[]'}\n\n"
            f"### PREFERRED SKILLS TO MATCH:\n"
            f"{json.dumps(preferred_skills) if has_preferred else '[]'}\n\n"
            f"### SOFT COMPLIANCE CRITERIA (HR specified):\n"
            f"{soft_raw if has_soft else 'None'}\n\n"
            "Return ONLY this JSON — no extra keys, no score fields:\n"
            "{\n"
            "  \"required_skill_matches\": [\n"
            "    {\"skill\": \"<jd skill name>\", \"matched\": true/false, "
            "\"matched_as\": \"<exact resume text or null>\"}\n"
            "  ],\n"
            "  \"preferred_skill_matches\": [\n"
            "    {\"skill\": \"<jd skill name>\", \"matched\": true/false, "
            "\"matched_as\": \"<exact resume text or null>\"}\n"
            "  ],\n"
            "  \"soft_compliance_met\": true/false,\n"
            "  \"reasoning\": \"Concise one-line explanation of key matches/misses\"\n"
            "}"
        )

        # ── 3. LLM call (temperature=0 via parse_json_response default) ──────
        result = parse_json_response(
            prompt=prompt,
            system_prompt=_SYSTEM_PROMPT,
            model="gpt-4o-mini",
            temperature=0.0,
        )

        # ── 4. Extract boolean match lists from LLM response ─────────────────
        required_matches  = result.get("required_skill_matches",  [])
        preferred_matches = result.get("preferred_skill_matches", [])
        soft_met          = bool(result.get("soft_compliance_met", False))

        # Flatten to named skill lists
        matched_required  = [m["skill"] for m in required_matches  if m.get("matched")]
        missing_required  = [m["skill"] for m in required_matches  if not m.get("matched")]
        matched_preferred = [m["skill"] for m in preferred_matches if m.get("matched")]
        missing_preferred = [m["skill"] for m in preferred_matches if not m.get("matched")]

        # ── 5. Deterministic score computation (pure Python, no LLM float) ───
        req_total   = len(required_matches)
        req_matched = len(matched_required)

        if req_total == 0:
            # No required skills in JD → candidate qualifies on required dimension
            req_pct    = 1.0
            base_score = 1.0
        else:
            req_pct    = req_matched / req_total
            base_score = _pct_to_base_score(req_pct)

        # Preferred bonus: +0.1 if ≥50% of preferred skills matched
        pref_total = len(matched_preferred) + len(missing_preferred)
        if has_preferred and pref_total > 0:
            preferred_bonus = 0.1 if (len(matched_preferred) / pref_total) >= 0.5 else 0.0
        else:
            preferred_bonus = 0.0

        # Soft compliance bonus: +0.05 if criteria met
        soft_bonus = 0.05 if (has_soft and soft_met) else 0.0

        # Final score, capped at 1.0
        overall_score = min(1.0, base_score + preferred_bonus + soft_bonus)

        # Log calculation summary cleanly
        print(
            f"📊 [KEYWORD SCORER] Required skills match: {req_matched}/{req_total} "
            f"({req_pct * 100:.1f}%) ➔ Base Score: {base_score:.3f} | "
            f"Pref Bonus: {preferred_bonus:.2f} | Soft Bonus: {soft_bonus:.2f} ➔ Overall: {overall_score:.3f}"
        )

        # ── 6. Return structured result ───────────────────────────────────────
        return {
            "success":              True,
            "overall_score":        round(overall_score, 3),
            # Score breakdown (useful for debugging)
            "score_breakdown": {
                "req_match_pct":    round(req_pct, 3),
                "req_matched":      req_matched,
                "req_total":        req_total,
                "base_score":       base_score,
                "preferred_bonus":  preferred_bonus,
                "soft_bonus":       soft_bonus,
            },
            # Skill lists
            "matched_required_skills":  matched_required,
            "missing_required_skills":  missing_required,
            "matched_preferred_skills": matched_preferred,
            "missing_preferred_skills": missing_preferred,
            "matched_soft_compliances": (["soft_compliance"] if (has_soft and soft_met) else []),
            "missing_soft_compliances": ([] if (has_soft and soft_met) else (["soft_compliance"] if has_soft else [])),
            "reasoning":            result.get("reasoning", ""),
            "error":                None,
        }

    except Exception as e:
        return {
            "success":       False,
            "overall_score": 0.0,
            "error":         f"LLM Keyword/Skill scoring failed: {str(e)}",
        }

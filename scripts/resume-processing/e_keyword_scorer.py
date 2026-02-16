#!/usr/bin/env python3
"""
Keyword Scorer (Modular Version)

Supports new structured resume/JD format
while preserving exact old KeywordComparitor logic.
"""

from typing import Dict, Any, Set

# ============================================================================
# CONFIGURATION
# ============================================================================

EXPERIENCE_KEYWORD_WEIGHTS = {
    "lead": 4.0, "led": 4.0, "manager": 4.0, "managed": 4.0, "architect": 4.0,
    "architected": 4.0, "designed": 3.6, "design": 3.6, "owned": 3.6,
    "implemented": 3.2, "built": 3.6, "scaled": 3.4, "scale": 3.4,
    "optimized": 3.2, "deployed": 3.2, "productionized": 3.6,
    "mentored": 2.8, "coach": 2.8, "contributed": 2.4, "contributed to": 2.4,
    "improved": 3.0, "reduced": 3.0, "increased": 3.0, "automated": 3.2,
    "orchestrated": 3.4
}

DEFAULT_WEIGHTS = {
    "required_skills": 0.18,
    "preferred_skills": 0.08,
    "weighted_keywords": 0.15,
    "experience_keywords": 0.25,
    "domain_relevance": 0.10,
    "technical_depth": 0.10,  # legacy (not used directly)
    "project_metrics": 0.09,
    "responsibilities": 0.03,
    "education": 0.02,
}

# ============================================================================
# UTILITIES
# ============================================================================

def norm(s: str) -> str:
    return s.strip().lower() if isinstance(s, str) else ""


# ============================================================================
# JD KEYWORD EXTRACTION (Supports New JD Format)
# ============================================================================

def collect_jd_keywords(jd: Dict[str, Any]) -> Dict[str, Any]:
    jd_analysis = jd.get("jd_analysis", jd)

    return {
        "required_skills": [norm(x) for x in jd_analysis.get("required_skills", [])],
        "preferred_skills": [norm(x) for x in jd_analysis.get("preferred_skills", [])],
        "weighted_keywords": {
            norm(k): float(v)
            for k, v in jd_analysis.get("keywords_weighted", {}).items()
        },
        "domain_tags": [norm(x) for x in jd_analysis.get("domain_tags", [])],
        "responsibilities": [norm(x) for x in jd_analysis.get("responsibilities", [])],
        "education": [
            norm(x)
            for x in jd_analysis.get("education", [])
        ],
    }


# ============================================================================
# RESUME TOKEN EXTRACTION (Old Behavior Preserved)
# ============================================================================

def collect_resume_tokens(resume: Dict[str, Any]) -> Set[str]:
    tokens = set()

    canonical_skills = resume.get("canonical_skills") or {}
    if isinstance(canonical_skills, dict):
        for values in canonical_skills.values():
            if isinstance(values, list):
                tokens.update(norm(v) for v in values if v)

    inferred_skills = resume.get("inferred_skills") or []
    for inf in inferred_skills:
        if isinstance(inf, dict) and inf.get("confidence", 0) >= 0.6:
            if inf.get("skill"):
                tokens.add(norm(inf["skill"]))

    skill_proficiency = resume.get("skill_proficiency") or []
    for sp in skill_proficiency:
        if isinstance(sp, dict) and sp.get("skill"):
            tokens.add(norm(sp["skill"]))

    projects = resume.get("projects") or []
    for proj in projects:
        if isinstance(proj, dict):
            tokens.update(norm(x) for x in proj.get("tech_keywords", []) if x)
            tokens.update(norm(x) for x in proj.get("primary_skills", []) if x)

    experience_entries = resume.get("experience_entries") or []
    for exp in experience_entries:
        if isinstance(exp, dict):
            tokens.update(norm(x) for x in exp.get("primary_tech", []) if x)
            tokens.update(norm(x) for x in exp.get("responsibilities_keywords", []) if x)

    # OLD tokenization behavior for profile & ATS lines
    for phrase in [
        resume.get("profile_keywords_line") or "",
        resume.get("ats_boost_line") or ""
    ]:
        parts = [
            p.strip()
            for p in phrase.replace("/", ",").replace(";", ",").split(",")
            if p.strip()
        ]
        tokens.update(norm(p) for p in parts)
        tokens.update(norm(w) for w in phrase.split())

    tokens.update(norm(x) for x in resume.get("domain_tags", []) if x)

    return tokens


# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def score_overlap(jd_list, resume_tokens):
    if not jd_list:
        return 0.5
    matched = sum(1 for x in jd_list if x in resume_tokens)
    return matched / len(jd_list)


def score_weighted_keywords(jd_kw: dict, resume_tokens: set) -> float:
    if not jd_kw:
        return 0.5
    matched = sum(w for kw, w in jd_kw.items() if kw in resume_tokens)
    total = sum(jd_kw.values())
    return matched / total if total > 0 else 0.5


def score_project_metrics(resume: Dict[str, Any]) -> float:
    projects = resume.get("projects") or []
    if not projects:
        return 0.5  # old neutral behavior

    scores = []

    for proj in projects:
        if not isinstance(proj, dict):
            continue

        # Support both new and old format
        metrics = proj.get("metrics")
        if isinstance(metrics, dict):
            vals = [
                metrics.get("skill_relevance", 0),
                metrics.get("domain_relevance", 0),
                metrics.get("execution_quality", 0),
            ]
        else:
            vals = [
                proj.get("skill_relevance", 0),
                proj.get("domain_relevance", 0),
                proj.get("execution_quality", 0),
            ]

        scores.append(sum(vals) / len(vals))

    return sum(scores) / len(scores) if scores else 0.5


def score_experience_keywords(resume: Dict[str, Any]) -> float:
    text_sources = []

    for exp in resume.get("experience_entries", []):
        text_sources.extend(exp.get("responsibilities_keywords", []))
        text_sources.extend(exp.get("achievements", []))

    # OLD behavior: include profile & ATS lines
    text_sources.append(resume.get("profile_keywords_line") or "")
    text_sources.append(resume.get("ats_boost_line") or "")

    joined = " ".join(norm(t) for t in text_sources)

    matched = sum(
        weight for kw, weight in EXPERIENCE_KEYWORD_WEIGHTS.items()
        if kw in joined
    )

    max_possible = sum(EXPERIENCE_KEYWORD_WEIGHTS.values())

    return matched / max_possible if max_possible > 0 else 0.0


# ============================================================================
# MAIN SCORING FUNCTION
# ============================================================================

def calculate_keyword_scores(resume: Dict[str, Any], jd: Dict[str, Any]) -> Dict[str, Any]:
    try:
        jd_keywords = collect_jd_keywords(jd)
        resume_tokens = collect_resume_tokens(resume)

        # Support JD custom weighting (old behavior)
        weights = DEFAULT_WEIGHTS.copy()
        jd_weighting = jd.get("weighting", {})
        for key, value in jd_weighting.items():
            if value is not None and key in weights:
                weights[key] = float(value)

        category_scores = {
            "required_skills": score_overlap(jd_keywords["required_skills"], resume_tokens),
            "preferred_skills": score_overlap(jd_keywords["preferred_skills"], resume_tokens),
            "weighted_keywords": score_weighted_keywords(jd_keywords["weighted_keywords"], resume_tokens),
            "experience_keywords": score_experience_keywords(resume),
            "domain_relevance": score_overlap(jd_keywords["domain_tags"], resume_tokens),
            "project_metrics": score_project_metrics(resume),
            "responsibilities": score_overlap(jd_keywords["responsibilities"], resume_tokens),
            "education": score_overlap(jd_keywords["education"], resume_tokens),
        }

        # Required skill penalty (old behavior)
        required_penalty = 0.0
        req_score = category_scores["required_skills"]
        if jd_keywords["required_skills"] and req_score < 0.5:
            required_penalty = (0.5 - req_score) * 0.3

        final = (
            category_scores["required_skills"] * weights["required_skills"] +
            category_scores["preferred_skills"] * weights["preferred_skills"] +
            category_scores["weighted_keywords"] * weights["weighted_keywords"] +
            category_scores["experience_keywords"] * weights["experience_keywords"] +
            category_scores["domain_relevance"] * weights["domain_relevance"] +
            category_scores["project_metrics"] * weights["project_metrics"] +
            category_scores["responsibilities"] * weights["responsibilities"] +
            category_scores["education"] * weights["education"]
            - required_penalty
        )

        final = max(0.0, final)

        return {
            "success": True,
            "overall_score": round(final, 3),
            "category_scores": {k: round(v, 3) for k, v in category_scores.items()},
            "weights_used": weights,
            "penalty_applied": round(required_penalty, 3),
            "error": None
        }

    except Exception as e:
        return {
            "success": False,
            "overall_score": 0.0,
            "category_scores": {},
            "error": f"Keyword scoring failed: {str(e)}"
        }

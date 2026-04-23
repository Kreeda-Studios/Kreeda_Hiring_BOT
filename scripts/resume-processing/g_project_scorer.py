#!/usr/bin/env python3
"""
Project Scorer for Resume Analysis

Calculates project aggregate scores from metric_ai fields provided by the AI parser.
Updated to use the new ResumeExtraction schema (project.metric_ai instead of project.metrics).
"""

from typing import Dict, Any

# ── Metric weights for the new metric_ai schema ───────────────────────────────
# impact is already 0.0–1.0.
# difficulty, complexity, domain_relevance are 1–10 integers → normalised /10.
METRIC_WEIGHTS = {
    "impact":           0.40,
    "difficulty":       0.20,
    "complexity":       0.20,
    "domain_relevance": 0.20,
}


# ============================================================================
# CORE SCORING LOGIC
# ============================================================================

def calculate_weighted_score(metric_ai: Dict[str, float]) -> float:
    """
    Calculate weighted score from a project's metric_ai block.

    Args:
        metric_ai: dict with keys: impact (0-1), difficulty (1-10),
                   complexity (1-10), domain_relevance (1-10)

    Returns:
        Float between 0 and 1 representing weighted project score
    """
    if not metric_ai:
        return 0.0

    raw = {
        "impact":           float(metric_ai.get("impact", 0.0)),
        # Normalise 1-10 scale to 0-1
        "difficulty":       float(metric_ai.get("difficulty", 0)) / 10.0,
        "complexity":       float(metric_ai.get("complexity", 0)) / 10.0,
        "domain_relevance": float(metric_ai.get("domain_relevance", 0)) / 10.0,
    }

    total_score  = 0.0
    total_weight = 0.0
    for metric, weight in METRIC_WEIGHTS.items():
        total_score  += raw.get(metric, 0.0) * weight
        total_weight += weight

    return round(total_score / total_weight, 3) if total_weight > 0 else 0.0


# ============================================================================
# MAIN SCORING FUNCTION
# ============================================================================

def calculate_project_scores(resume: Dict[str, Any], jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate project aggregate score by averaging weighted scores of all projects.

    Reads from new ResumeExtraction schema:
        resume → projects[].metric_ai   (was: projects[].metrics)
        resume → projects[].title       (was: projects[].name)

    Args:
        resume: Resume document with projects field
        jd:     Job description document (unused, kept for API compatibility)

    Returns:
        Dictionary with:
            - success: bool
            - overall_score: float (0-1, average of all project weighted scores)
            - project_scores: list of individual project scores
            - error: str or None
    """
    try:
        projects = resume.get("projects", [])

        if not projects:
            return {
                "success": True,
                "overall_score": 0.0,
                "project_scores": [],
                "error": None,
            }

        project_results = []
        for i, project in enumerate(projects):
            metric_ai      = project.get("metric_ai", {})
            weighted_score = calculate_weighted_score(metric_ai)

            project_results.append({
                "project_index":  i,
                "project_name":   project.get("title", f"Project {i + 1}"),  # new field: title
                "weighted_score": weighted_score,
                "metrics":        metric_ai,
            })

        project_scores = [p["weighted_score"] for p in project_results]
        overall_score  = round(sum(project_scores) / len(project_scores), 3) if project_scores else 0.0

        return {
            "success": True,
            "overall_score": overall_score,
            "project_scores": project_results,
            "error": None,
        }

    except Exception as e:
        return {
            "success": False,
            "overall_score": 0.0,
            "project_scores": [],
            "error": f"Project scoring failed: {str(e)}",
        }

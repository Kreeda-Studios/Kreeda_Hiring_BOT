#!/usr/bin/env python3
"""
Project Scorer for Resume Analysis

Calculates project aggregate scores by averaging weighted metrics.
Matches old ProjectProcess.py logic exactly - expects AI parser to provide
project metrics, does not calculate them manually.
"""

from typing import Dict, Any

# Metric weights for weighted average (equal weights from old system)
METRIC_WEIGHTS = {
    "difficulty": 0.142857,
    "novelty": 0.142857,
    "skill_relevance": 0.142857,
    "complexity": 0.142857,
    "technical_depth": 0.142857,
    "domain_relevance": 0.142857,
    "execution_quality": 0.142857
}


# ============================================================================
# CORE SCORING LOGIC
# ============================================================================

def calculate_weighted_score(metrics: Dict[str, float]) -> float:
    """
    Calculate weighted average of project metrics.
    
    Args:
        metrics: Dictionary with metric values (difficulty, novelty, skill_relevance,
                 complexity, technical_depth, domain_relevance, execution_quality)
    
    Returns:
        Float between 0 and 1 representing weighted project score
    """
    total_score = 0.0
    total_weight = 0.0
    
    for metric, weight in METRIC_WEIGHTS.items():
        if metric in metrics:
            total_score += metrics[metric] * weight
            total_weight += weight
    
    return round(total_score / total_weight, 3) if total_weight > 0 else 0.0


# ============================================================================
# MAIN SCORING FUNCTION
# ============================================================================

def calculate_project_scores(resume: Dict[str, Any], jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate project aggregate score by averaging weighted scores of all projects.
    Matches old ProjectProcess.py logic exactly.
    
    Args:
        resume: Resume document with projects field containing metrics
        jd: Job description document (unused, kept for API compatibility)
    
    Returns:
        Dictionary with:
            - success: bool
            - overall_score: float (0-1, average of all project weighted scores)
            - project_scores: list of individual project scores
            - error: str or None
    """
    try:
        projects = resume.get('projects', [])
        
        if not projects:
            return {
                'success': True,
                'overall_score': 0.0,
                'project_scores': [],
                'error': None
            }
        
        # Calculate weighted score for each project using AI parser metrics
        project_results = []
        for i, project in enumerate(projects):
            metrics = project.get('metrics', {})
            weighted_score = calculate_weighted_score(metrics)
            
            project_results.append({
                'project_index': i,
                'project_name': project.get('name', f'Project {i+1}'),
                'weighted_score': weighted_score,
                'metrics': metrics
            })
        
        # Calculate overall score as average of all project scores
        project_scores = [p['weighted_score'] for p in project_results]
        overall_score = round(sum(project_scores) / len(project_scores), 3) if project_scores else 0.0
        
        return {
            'success': True,
            'overall_score': overall_score,
            'project_scores': project_results,
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'overall_score': 0.0,
            'project_scores': [],
            'error': f"Project scoring failed: {str(e)}"
        }

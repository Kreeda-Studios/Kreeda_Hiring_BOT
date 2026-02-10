#!/usr/bin/env python3

"""
Composite Scorer for Resume Analysis

Combines 3 scoring components into final score using weighted average.
Based on FinalRanking.py logic from the existing codebase.
"""

from typing import Dict, Any

# Score weights from old code
WEIGHTS = {
    "project_aggregate": 0.35,
    "Semantic_Score": 0.35,
    "Keyword_Score": 0.3,
}

ONE_SCORE_DECAY = 0.08  # Decay penalty when only 1 score available


def calculate_composite_score(
    project_score_result: Dict[str, Any],
    keyword_score_result: Dict[str, Any],
    semantic_score_result: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate final composite score from 3 components using weighted average.
    Logic from FinalRanking.py compute_final_score().
    """
    try:
        # Extract scores
        raw_scores = {
            "project_aggregate": project_score_result.get('overall_score'),
            "Semantic_Score": semantic_score_result.get('overall_semantic_score'),
            "Keyword_Score": keyword_score_result.get('overall_score'),
        }
        
        # Include scores that are numeric (including 0.0) and not None
        valid_scores = {k: v for k, v in raw_scores.items() if isinstance(v, (int, float)) and v is not None}
        
        if len(valid_scores) == 0:
            return {
                'success': False,
                'final_score': 0.0,
                'error': 'No valid scores available'
            }
        
        # If only one score is available, apply decay penalty
        decay = 0.0
        if len(valid_scores) == 1:
            decay = ONE_SCORE_DECAY
        
        # Calculate weighted average using all available scores
        total_weight = sum(WEIGHTS[k] for k in valid_scores)
        if total_weight == 0:
            return {
                'success': False,
                'final_score': 0.0,
                'error': 'Total weight is zero'
            }
        
        final = sum((WEIGHTS[k] / total_weight) * valid_scores[k] for k in valid_scores)
        
        # Apply decay penalty if applicable
        final = final - decay
        
        # Ensure score is between 0 and 1
        final = max(0.0, min(1.0, final))
        
        return {
            'success': True,
            'final_score': round(final, 3),
            'component_scores': {
                'project_aggregate': raw_scores.get('project_aggregate'),
                'Semantic_Score': raw_scores.get('Semantic_Score'),
                'Keyword_Score': raw_scores.get('Keyword_Score')
            },
            'weights_used': {k: WEIGHTS[k] for k in valid_scores},
            'valid_scores_count': len(valid_scores),
            'decay_applied': decay
        }
        
    except Exception as e:
        return {
            'success': False,
            'final_score': 0.0,
            'error': f"Composite scoring failed: {str(e)}"
        }
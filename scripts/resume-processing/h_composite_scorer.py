#!/usr/bin/env python3

"""
Composite Scorer for Resume Analysis

Combines all scoring components into final ranking scores.
Based on FinalRanking.py logic from the existing codebase.
"""

from typing import Dict, Any, List, Tuple, Optional

def calculate_experience_weight(experience: List[Dict[str, Any]], min_experience_years: float = 0.0) -> float:
    """Calculate experience-based weight factor"""
    try:
        if not experience:
            return 0.1  # Minimal weight for no experience
        
        # Calculate total experience in years
        total_experience = 0.0
        
        for exp in experience:
            # Try to get duration_years first, then calculate from dates
            if exp.get('duration_years'):
                total_experience += float(exp['duration_years'])
            elif exp.get('start_date') and exp.get('end_date'):
                # Simple year calculation if dates available
                try:
                    start_year = int(exp['start_date'][:4])
                    end_year = int(exp['end_date'][:4]) if exp['end_date'] != 'Present' else 2024
                    duration = max(0, end_year - start_year)
                    total_experience += duration
                except (ValueError, TypeError):
                    # Fallback to 1 year if parsing fails
                    total_experience += 1.0
            else:
                # Default to 1 year per job if no duration info
                total_experience += 1.0
        
        # Calculate experience weight
        if total_experience >= min_experience_years:
            # Full weight for meeting minimum requirements
            return 1.0
        elif total_experience >= min_experience_years * 0.5:
            # Partial weight for having some relevant experience
            return 0.5 + (total_experience / min_experience_years) * 0.5
        else:
            # Lower weight for insufficient experience
            return 0.2 + (total_experience / max(min_experience_years, 1.0)) * 0.3
    
    except Exception:
        return 0.5  # Default weight if calculation fails

def calculate_education_weight(education: List[Dict[str, Any]], required_education: Optional[str] = None) -> float:
    """Calculate education-based weight factor"""
    try:
        if not education:
            return 0.3  # Some weight for missing education data
        
        # Education level scoring
        education_scores = {
            'phd': 1.0, 'doctorate': 1.0, 'doctoral': 1.0,
            'masters': 0.9, 'master': 0.9, 'msc': 0.9, 'mba': 0.9,
            'bachelors': 0.7, 'bachelor': 0.7, 'bsc': 0.7, 'btech': 0.7, 'be': 0.7,
            'diploma': 0.5, 'associate': 0.5,
            'certificate': 0.3, 'certification': 0.3
        }
        
        best_education_score = 0.0
        
        for edu in education:
            degree = edu.get('degree', '').lower()
            
            # Find best matching education level
            for edu_level, score in education_scores.items():
                if edu_level in degree:
                    best_education_score = max(best_education_score, score)
                    break
            
            # Check for field relevance if required_education specified
            if required_education and best_education_score > 0:
                field = edu.get('field_of_study', '').lower()
                required_lower = required_education.lower()
                
                # Boost score for relevant field
                relevant_fields = ['computer', 'software', 'engineering', 'technology', 'science']
                if any(field_term in field or field_term in required_lower for field_term in relevant_fields):
                    best_education_score = min(1.0, best_education_score * 1.1)
        
        return max(0.3, best_education_score)  # Minimum 0.3 weight
    
    except Exception:
        return 0.5  # Default weight

def normalize_score_component(score: float, weight: float = 1.0, min_threshold: float = 0.0) -> float:
    """Normalize individual score component"""
    try:
        # Ensure score is within bounds
        normalized = max(0.0, min(1.0, score))
        
        # Apply weight
        weighted = normalized * weight
        
        # Apply minimum threshold if specified
        if min_threshold > 0 and normalized > 0:
            weighted = max(min_threshold, weighted)
        
        return weighted
    
    except Exception:
        return 0.0

def calculate_composite_score(
    hard_requirements_result: Dict[str, Any],
    project_score_result: Dict[str, Any],
    keyword_score_result: Dict[str, Any],
    semantic_score_result: Dict[str, Any],
    resume_data: Dict[str, Any],
    jd_requirements: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate final composite score from all components
    """
    try:
        # Extract individual scores
        hard_req_passed = hard_requirements_result.get('all_requirements_met', False)
        hard_req_score = hard_requirements_result.get('overall_compliance_score', 0.0)
        
        project_score = project_score_result.get('overall_score', 0.0)
        keyword_score = keyword_score_result.get('overall_score', 0.0)
        semantic_score = semantic_score_result.get('overall_semantic_score', 0.0)
        
        # Calculate dynamic weights based on experience and education
        experience_weight = calculate_experience_weight(
            resume_data.get('experience', []),
            jd_requirements.get('minimum_experience_years', 0.0)
        )
        
        education_weight = calculate_education_weight(
            resume_data.get('education', []),
            jd_requirements.get('required_education')
        )
        
        # Base component weights (before dynamic adjustment)
        base_weights = {
            'hard_requirements': 0.25,  # Must-have compliance
            'keyword_matching': 0.25,   # Skill keyword matching
            'semantic_similarity': 0.20, # Semantic understanding
            'project_relevance': 0.15,   # Project quality/relevance
            'experience_bonus': 0.10,    # Experience bonus
            'education_bonus': 0.05      # Education bonus
        }
        
        # Hard requirements gate - if not passed, heavily penalize
        if not hard_req_passed:
            penalty_factor = 0.3  # 70% penalty for failing hard requirements
        else:
            penalty_factor = 1.0
        
        # Calculate component scores with normalization
        component_scores = {
            'hard_requirements': normalize_score_component(hard_req_score, base_weights['hard_requirements']),
            'keyword_matching': normalize_score_component(keyword_score, base_weights['keyword_matching']),
            'semantic_similarity': normalize_score_component(semantic_score, base_weights['semantic_similarity']),
            'project_relevance': normalize_score_component(project_score, base_weights['project_relevance']),
            'experience_bonus': normalize_score_component(experience_weight, base_weights['experience_bonus']),
            'education_bonus': normalize_score_component(education_weight, base_weights['education_bonus'])
        }
        
        # Calculate raw composite score
        raw_score = sum(component_scores.values())
        
        # Apply hard requirements penalty
        final_score = raw_score * penalty_factor
        
        # Calculate percentile ranking factors
        skill_coverage = keyword_score_result.get('keyword_analysis', {}).get('coverage_percentage', 0.0) / 100.0
        semantic_strength = semantic_score
        
        # Experience and education multipliers
        experience_multiplier = min(1.2, 1.0 + (experience_weight - 0.5) * 0.4)
        education_multiplier = min(1.1, 1.0 + (education_weight - 0.5) * 0.2)
        
        # Apply multipliers to final score
        enhanced_score = final_score * experience_multiplier * education_multiplier
        
        # Ensure final score doesn't exceed 1.0
        capped_score = min(1.0, enhanced_score)
        
        # Calculate ranking tier
        if capped_score >= 0.85:
            ranking_tier = 'Excellent'
        elif capped_score >= 0.70:
            ranking_tier = 'Good'
        elif capped_score >= 0.55:
            ranking_tier = 'Average'
        elif capped_score >= 0.40:
            ranking_tier = 'Below Average'
        else:
            ranking_tier = 'Poor'
        
        # Generate detailed breakdown
        score_breakdown = {
            'raw_component_scores': component_scores,
            'raw_total': raw_score,
            'hard_requirements_penalty': penalty_factor,
            'experience_multiplier': experience_multiplier,
            'education_multiplier': education_multiplier,
            'enhanced_score': enhanced_score,
            'final_capped_score': capped_score
        }
        
        # Calculate confidence score
        confidence_factors = [
            hard_req_score if hard_req_passed else 0.2,  # Confidence in requirements compliance
            skill_coverage,  # Confidence in skill match
            semantic_strength,  # Confidence in semantic match
            min(1.0, experience_weight),  # Confidence in experience
            min(1.0, education_weight)  # Confidence in education
        ]
        
        confidence_score = sum(confidence_factors) / len(confidence_factors)
        
        return {
            'success': True,
            'final_score': round(capped_score, 3),
            'ranking_tier': ranking_tier,
            'confidence_score': round(confidence_score, 3),
            'hard_requirements_passed': hard_req_passed,
            'component_scores': {
                'hard_requirements': round(component_scores['hard_requirements'], 3),
                'keyword_matching': round(component_scores['keyword_matching'], 3),
                'semantic_similarity': round(component_scores['semantic_similarity'], 3),
                'project_relevance': round(component_scores['project_relevance'], 3),
                'experience_factor': round(experience_weight, 3),
                'education_factor': round(education_weight, 3)
            },
            'weights_applied': base_weights,
            'multipliers': {
                'hard_requirements_penalty': penalty_factor,
                'experience_multiplier': experience_multiplier,
                'education_multiplier': education_multiplier
            },
            'score_breakdown': score_breakdown,
            'ranking_factors': {
                'skill_coverage_percentage': round(skill_coverage * 100, 1),
                'semantic_strength': round(semantic_strength, 3),
                'experience_years_estimated': sum(exp.get('duration_years', 1) for exp in resume_data.get('experience', [])),
                'education_level': education_weight
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'final_score': 0.0,
            'ranking_tier': 'Error',
            'error': f"Composite scoring failed: {str(e)}"
        }

def calculate_ranking_position(candidate_score: float, all_candidate_scores: List[float]) -> Dict[str, Any]:
    """Calculate ranking position and percentile for a candidate"""
    try:
        if not all_candidate_scores:
            return {
                'rank_position': 1,
                'total_candidates': 1,
                'percentile': 100.0,
                'rank_category': 'Only Candidate'
            }
        
        # Sort scores in descending order
        sorted_scores = sorted(all_candidate_scores, reverse=True)
        
        # Find position of current candidate's score
        rank_position = 1
        for i, score in enumerate(sorted_scores):
            if candidate_score >= score:
                rank_position = i + 1
                break
        
        total_candidates = len(sorted_scores)
        
        # Calculate percentile (higher is better)
        percentile = ((total_candidates - rank_position + 1) / total_candidates) * 100
        
        # Determine rank category
        if percentile >= 90:
            rank_category = 'Top 10%'
        elif percentile >= 75:
            rank_category = 'Top 25%'
        elif percentile >= 50:
            rank_category = 'Top 50%'
        elif percentile >= 25:
            rank_category = 'Bottom 50%'
        else:
            rank_category = 'Bottom 25%'
        
        return {
            'rank_position': rank_position,
            'total_candidates': total_candidates,
            'percentile': round(percentile, 1),
            'rank_category': rank_category,
            'score_distribution': {
                'highest_score': max(sorted_scores),
                'lowest_score': min(sorted_scores),
                'median_score': sorted_scores[len(sorted_scores) // 2],
                'candidate_score': candidate_score
            }
        }
        
    except Exception as e:
        return {
            'rank_position': 1,
            'total_candidates': 1,
            'percentile': 0.0,
            'error': f"Ranking calculation failed: {str(e)}"
        }
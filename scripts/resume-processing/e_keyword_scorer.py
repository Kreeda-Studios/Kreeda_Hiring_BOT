#!/usr/bin/env python3
"""
Keyword Scorer for Resume Analysis

Calculates keyword matching scores by comparing resume tokens with JD keywords.
Matches old KeywordComparitor.py logic exactly.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Set

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

# ============================================================================
# CONFIGURATION
# ============================================================================

# Experience action verb weights for leadership/impact assessment
EXPERIENCE_KEYWORD_WEIGHTS = {
    "lead": 4.0, "led": 4.0, "manager": 4.0, "managed": 4.0, "architect": 4.0,
    "architected": 4.0, "designed": 3.6, "design": 3.6, "owned": 3.6,
    "implemented": 3.2, "built": 3.6, "scaled": 3.4, "scale": 3.4,
    "optimized": 3.2, "deployed": 3.2, "productionized": 3.6,
    "mentored": 2.8, "coach": 2.8, "contributed": 2.4, "contributed to": 2.4,
    "improved": 3.0, "reduced": 3.0, "increased": 3.0, "automated": 3.2,
    "orchestrated": 3.4
}

# Default category weights
DEFAULT_WEIGHTS = {
    "required_skills": 0.18,
    "preferred_skills": 0.08,
    "weighted_keywords": 0.15,
    "experience_keywords": 0.25,
    "domain_relevance": 0.10,
    "technical_depth": 0.10,
    "project_metrics": 0.09,
    "responsibilities": 0.03,
    "education": 0.02,
}


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def norm(s: str) -> str:
    """Normalize string to lowercase and strip whitespace"""
    return s.strip().lower() if isinstance(s, str) else ""


# ============================================================================
# JD KEYWORD EXTRACTION
# ============================================================================

def collect_jd_keywords(jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract keywords from JD analysis.
    
    Args:
        jd: Job description document with jd_analysis field
        
    Returns:
        Dictionary with categorized keyword sets and weighted_keywords dict
    """
    jd_analysis = jd.get('jd_analysis', {})
    
    result = {
        'required_skills': {norm(s) for s in jd_analysis.get('required_skills', []) if s and len(s.strip()) > 1},
        'preferred_skills': {norm(s) for s in jd_analysis.get('preferred_skills', []) if s and len(s.strip()) > 1},
        'domain_tags': {norm(s) for s in jd_analysis.get('domain_tags', []) if s and len(s.strip()) > 1},
        'responsibilities': {norm(s) for s in jd_analysis.get('responsibilities', []) if s and len(s.strip()) > 1},
        'education': {norm(s) for s in jd_analysis.get('education', []) if s and len(s.strip()) > 1},
        'weighted_keywords': {
            norm(k): float(v) for k, v in jd_analysis.get('keywords_weighted', {}).items() 
            if k and len(k.strip()) > 1
        }
    }
    
    print(f"\n🔍 JD KEYWORDS DEBUG:")
    print(f"  Required skills count: {len(result['required_skills'])}")
    print(f"  Required skills: {list(result['required_skills'])[:10]}")
    print(f"  Preferred skills count: {len(result['preferred_skills'])}")
    print(f"  Weighted keywords count: {len(result['weighted_keywords'])}")
    print(f"  Domain tags count: {len(result['domain_tags'])}")
    
    return result


# ============================================================================
# RESUME TOKEN EXTRACTION
# ============================================================================

def collect_resume_tokens(resume: Dict[str, Any]) -> Set[str]:
    """
    Extract all relevant tokens from resume for keyword matching.
    Matches old KeywordComparitor.py extraction logic exactly.
    
    Args:
        resume: Resume document with AI parser output fields
        
    Returns:
        Set of normalized tokens from resume
    """
    tokens = set()
    
    # 1. Canonical skills (all categories: languages, frameworks, tools, databases, etc.)
    canonical_skills = resume.get('canonical_skills', {})
    for category, skills in canonical_skills.items():
        if isinstance(skills, list):
            for skill in skills:
                if skill and len(skill.strip()) > 1:
                    tokens.add(norm(skill))
    
    # 2. Inferred skills (only high confidence >= 0.6)
    for skill_obj in resume.get('inferred_skills', []):
        if skill_obj.get('confidence', 0) >= 0.6:
            skill = skill_obj.get('skill')
            if skill and len(skill.strip()) > 1:
                tokens.add(norm(skill))
    
    # 3. Skill proficiency
    for skill_obj in resume.get('skill_proficiency', []):
        skill = skill_obj.get('skill')
        if skill and len(skill.strip()) > 1:
            tokens.add(norm(skill))
    
    # 4. Projects - tech_keywords and primary_skills
    for project in resume.get('projects', []):
        # Tech keywords
        for keyword in project.get('tech_keywords', []):
            if keyword and len(keyword.strip()) > 1:
                tokens.add(norm(keyword))
        
        # Primary skills
        for skill in project.get('primary_skills', []):
            if skill and len(skill.strip()) > 1:
                tokens.add(norm(skill))
    
    # 5. Experience entries - primary_tech and responsibilities_keywords
    for exp in resume.get('experience_entries', []):
        # Primary tech
        for tech in exp.get('primary_tech', []):
            if tech and len(tech.strip()) > 1:
                tokens.add(norm(tech))
        
        # Responsibilities keywords
        for keyword in exp.get('responsibilities_keywords', []):
            if keyword and len(keyword.strip()) > 1:
                tokens.add(norm(keyword))
    
    # 6. Profile and ATS lines (split by common delimiters)
    profile_line = resume.get('profile_keywords_line', '')
    if profile_line:
        for token in profile_line.replace(',', ' ').replace(';', ' ').split():
            token = token.strip()
            if token and len(token) > 1:
                tokens.add(norm(token))
    
    ats_line = resume.get('ats_boost_line', '')
    if ats_line:
        for token in ats_line.replace(',', ' ').replace(';', ' ').split():
            token = token.strip()
            if token and len(token) > 1:
                tokens.add(norm(token))
    
    # 7. Domain tags
    for tag in resume.get('domain_tags', []):
        if tag and len(tag.strip()) > 1:
            tokens.add(norm(tag))
    
    print(f"\n📄 RESUME TOKENS DEBUG:")
    print(f"  Total unique tokens: {len(tokens)}")
    print(f"  Sample tokens (first 20): {list(tokens)[:20]}")
    print(f"  Canonical skills categories: {list(canonical_skills.keys())}")
    print(f"  Inferred skills count: {len(resume.get('inferred_skills', []))}")
    print(f"  Projects count: {len(resume.get('projects', []))}")
    print(f"  Experience entries count: {len(resume.get('experience_entries', []))}")
    
    return tokens


# ============================================================================
# SCORING FUNCTIONS
# ============================================================================

def score_overlap(jd_list: Set[str], resume_tokens: Set[str]) -> float:
    """
    Calculate overlap score as percentage of JD keywords found in resume.
    
    Args:
        jd_list: Set of keywords from JD
        resume_tokens: Set of tokens from resume
        
    Returns:
        Float between 0 and 1 representing match percentage
    """
    if not jd_list:
        return 0.5  # Neutral score if no JD requirements
    
    matched = jd_list.intersection(resume_tokens)
    score = len(matched) / len(jd_list)
    
    print(f"    Overlap: {len(matched)}/{len(jd_list)} = {score:.3f}")
    if matched:
        print(f"    Matched: {list(matched)[:5]}")
    
    return score


def score_weighted_keywords(jd_kw: Dict[str, float], resume_tokens: Set[str]) -> float:
    """
    Calculate weighted keyword score.
    
    Args:
        jd_kw: Dictionary of {keyword: weight} from JD
        resume_tokens: Set of tokens from resume
        
    Returns:
        Float between 0 and 1 representing weighted match percentage
    """
    if not jd_kw:
        return 0.5  # Neutral score if no weighted keywords
    
    matched_weight = sum(weight for keyword, weight in jd_kw.items() if keyword in resume_tokens)
    total_weight = sum(jd_kw.values())
    
    score = matched_weight / total_weight if total_weight > 0 else 0.5
    
    matched_kws = [kw for kw in jd_kw if kw in resume_tokens]
    print(f"    Weighted: {len(matched_kws)}/{len(jd_kw)} keywords, {matched_weight:.2f}/{total_weight:.2f} weight = {score:.3f}")
    if matched_kws:
        print(f"    Matched weighted: {matched_kws[:5]}")
    
    return score


def score_project_metrics(resume: Dict[str, Any]) -> float:
    """
    Average project quality metrics from resume.
    
    Args:
        resume: Resume document with projects field
        
    Returns:
        Float between 0 and 1 representing average project quality
    """
    projects = resume.get('projects', [])
    if not projects:
        return 0.0
    
    metric_sums = {'skill_relevance': 0.0, 'domain_relevance': 0.0, 'execution_quality': 0.0}
    
    for project in projects:
        metric_sums['skill_relevance'] += project.get('skill_relevance', 0.0)
        metric_sums['domain_relevance'] += project.get('domain_relevance', 0.0)
        metric_sums['execution_quality'] += project.get('execution_quality', 0.0)
    
    avg_skill = metric_sums['skill_relevance'] / len(projects)
    avg_domain = metric_sums['domain_relevance'] / len(projects)
    avg_execution = metric_sums['execution_quality'] / len(projects)
    
    return (avg_skill + avg_domain + avg_execution) / 3.0


def score_experience_keywords(resume: Dict[str, Any]) -> float:
    """
    Score based on leadership/impact action verbs in experience entries.
    
    Args:
        resume: Resume document with experience_entries field
        
    Returns:
        Float between 0 and 1 representing experience keyword match
    """
    experience_entries = resume.get('experience_entries', [])
    if not experience_entries:
        return 0.0
    
    # Collect all experience text
    text_parts = []
    for exp in experience_entries:
        text_parts.extend(exp.get('responsibilities_keywords', []))
        text_parts.extend(exp.get('achievements', []))
    
    joined_text = " ".join([str(t).lower() for t in text_parts if t])
    
    # Calculate weighted score
    matched_weight = sum(weight for keyword, weight in EXPERIENCE_KEYWORD_WEIGHTS.items() if keyword in joined_text)
    max_weight = sum(EXPERIENCE_KEYWORD_WEIGHTS.values())
    
    return matched_weight / max_weight if max_weight > 0 else 0.0


# ============================================================================
# MAIN SCORING FUNCTION
# ============================================================================

def calculate_keyword_scores(resume: Dict[str, Any], jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate comprehensive keyword matching scores between resume and JD.
    Matches old KeywordComparitor.py logic exactly.
    
    Args:
        resume: Resume document with AI parser output
        jd: Job description document with jd_analysis field
        
    Returns:
        Dictionary with:
            - success: bool
            - overall_score: float (0-1, weighted aggregate)
            - category_scores: dict with individual category scores
            - error: str or None
    """
    try:
        # Extract keywords and tokens
        jd_keywords = collect_jd_keywords(jd)
        resume_tokens = collect_resume_tokens(resume)
        
        # Use default weights only (ignore custom weights from JD to avoid normalization issues)
        weights = DEFAULT_WEIGHTS.copy()
        
        print(f"\n⚖️  WEIGHTS DEBUG:")
        print(f"  Using default weights (sum: {sum(DEFAULT_WEIGHTS.values()):.3f})")
        
        # Calculate individual category scores
        category_scores = {
            'required_skills': score_overlap(jd_keywords['required_skills'], resume_tokens),
            'preferred_skills': score_overlap(jd_keywords['preferred_skills'], resume_tokens),
            'weighted_keywords': score_weighted_keywords(jd_keywords['weighted_keywords'], resume_tokens),
            'experience_keywords': score_experience_keywords(resume),
            'domain_relevance': score_overlap(jd_keywords['domain_tags'], resume_tokens),
            'project_metrics': score_project_metrics(resume),
            'responsibilities': score_overlap(jd_keywords['responsibilities'], resume_tokens),
            'education': score_overlap(jd_keywords['education'], resume_tokens),
        }
        
        print(f"\n📊 CATEGORY SCORES DEBUG:")
        for cat, score in category_scores.items():
            weight = weights.get(cat, 0.0)
            contribution = score * weight
            print(f"  {cat}: {score:.3f} × {weight:.3f} = {contribution:.3f}")
        
        # Calculate weighted overall score
        overall_score = sum(
            category_scores[category] * weights.get(category, 0.0)
            for category in category_scores
        )
        
        # Normalize by total weight
        total_weight = sum(weights.get(cat, 0.0) for cat in category_scores)
        if total_weight > 0:
            overall_score = overall_score / total_weight
        
        print(f"\n✅ FINAL KEYWORD SCORE: {overall_score:.3f} (total_weight: {total_weight:.3f})")
        
        return {
            'success': True,
            'overall_score': round(overall_score, 3),
            'category_scores': {k: round(v, 3) for k, v in category_scores.items()},
            'weights_used': {k: round(v, 3) for k, v in weights.items()},
            'keyword_analysis': {
                'jd_required_skills_count': len(jd_keywords['required_skills']),
                'jd_weighted_keywords_count': len(jd_keywords['weighted_keywords']),
                'resume_tokens_count': len(resume_tokens),
            },
            'error': None
        }
        
    except Exception as e:
        return {
            'success': False,
            'overall_score': 0.0,
            'category_scores': {},
            'error': f"Keyword scoring failed: {str(e)}"
        }

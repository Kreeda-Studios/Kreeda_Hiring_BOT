#!/usr/bin/env python3

"""
Keyword Scorer for Resume Analysis

Calculates keyword matching scores using logic from KeywordComparitor.py
in the existing codebase with exact matching algorithms.
"""

import re
from typing import Dict, Any, List, Set, Tuple
from collections import defaultdict

# Experience action verb weights (from Old_Code_Archive/ResumeProcessor/KeywordComparitor.py)
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

def normalize_keyword(keyword: str) -> str:
    """Normalize keywords for consistent matching"""
    if not keyword:
        return ""
    
    # Convert to lowercase and strip
    normalized = keyword.lower().strip()
    
    # Remove special characters except alphanumeric and spaces
    normalized = re.sub(r'[^a-z0-9\s]', ' ', normalized)
    
    # Normalize common technology variations
    tech_normalizations = {
        'javascript': 'javascript', 'js': 'javascript',
        'typescript': 'typescript', 'ts': 'typescript', 
        'python': 'python', 'py': 'python',
        'react js': 'react', 'reactjs': 'react', 'react.js': 'react',
        'node js': 'nodejs', 'node.js': 'nodejs',
        'c plus plus': 'cpp', 'c++': 'cpp',
        'c sharp': 'csharp', 'c#': 'csharp',
        'machine learning': 'machine learning', 'ml': 'machine learning',
        'artificial intelligence': 'artificial intelligence', 'ai': 'artificial intelligence',
        'amazon web services': 'aws', 'aws': 'aws',
        'google cloud platform': 'gcp', 'gcp': 'gcp'
    }
    
    return tech_normalizations.get(normalized, normalized)

def extract_resume_keywords(resume: Dict[str, Any]) -> Set[str]:
    """Extract all keywords from resume with normalization"""
    keywords = set()
    
    # From skills arrays
    for skill in resume.get('skills', []):
        if skill and len(skill.strip()) > 1:
            keywords.add(normalize_keyword(skill))
    
    # From canonical skills
    canonical_skills = resume.get('canonical_skills', {})
    for category, skills in canonical_skills.items():
        if isinstance(skills, list):
            for skill in skills:
                if skill and len(skill.strip()) > 1:
                    keywords.add(normalize_keyword(skill))
    
    # From inferred skills
    for skill_obj in resume.get('inferred_skills', []):
        if skill_obj.get('skill'):
            keywords.add(normalize_keyword(skill_obj['skill']))
    
    # From skill proficiency
    for skill_obj in resume.get('skill_proficiency', []):
        if skill_obj.get('skill'):
            keywords.add(normalize_keyword(skill_obj['skill']))
    
    # From projects
    for project in resume.get('projects', []):
        # Technologies
        for tech in project.get('technologies', []):
            if tech and len(tech.strip()) > 1:
                keywords.add(normalize_keyword(tech))
        
        # Tech keywords
        for keyword in project.get('tech_keywords', []):
            if keyword and len(keyword.strip()) > 1:
                keywords.add(normalize_keyword(keyword))
        
        # Primary skills
        for skill in project.get('primary_skills', []):
            if skill and len(skill.strip()) > 1:
                keywords.add(normalize_keyword(skill))
    
    # From experience descriptions (extract common tech terms)
    tech_pattern = re.compile(r'\b(python|java|javascript|react|angular|vue|node|django|flask|spring|mysql|mongodb|postgresql|aws|azure|docker|kubernetes|git|jenkins)\b', re.IGNORECASE)
    
    for exp in resume.get('experience', []):
        description = exp.get('description', '') + ' ' + ' '.join(exp.get('responsibilities', []))
        tech_matches = tech_pattern.findall(description)
        for match in tech_matches:
            keywords.add(normalize_keyword(match))
    
    # From keywords_flat if available
    for keyword in resume.get('keywords_flat', []):
        if keyword and len(keyword.strip()) > 1:
            keywords.add(normalize_keyword(keyword))
    
    return keywords

def score_weighted_keywords(jd_weighted_keywords: Dict[str, float], resume_tokens: Set[str]) -> float:
    """Score using weighted keywords from JD (if available)"""
    if not jd_weighted_keywords:
        return 0.5
    
    matched_weight = 0.0
    total_weight = sum(jd_weighted_keywords.values())
    
    for keyword, weight in jd_weighted_keywords.items():
        normalized_kw = normalize_keyword(keyword)
        if normalized_kw in resume_tokens:
            matched_weight += weight
    
    return matched_weight / total_weight if total_weight > 0 else 0.5

def score_experience_keywords(resume: Dict[str, Any]) -> float:
    """Score based on leadership/experience action verbs in resume"""
    text_sources = []
    
    # Collect text from experience entries
    for exp in resume.get('experience', []):
        text_sources.extend(exp.get('responsibilities', []))
        text_sources.append(exp.get('description', ''))
        if exp.get('achievements'):
            text_sources.extend(exp['achievements'])
    
    # Join all text sources
    joined_text = " ".join([str(t).lower() for t in text_sources if t])
    
    # Calculate weighted score based on presence of keywords
    matched_weight = 0.0
    for keyword, weight in EXPERIENCE_KEYWORD_WEIGHTS.items():
        if keyword in joined_text:
            matched_weight += weight
    
    max_possible = sum(EXPERIENCE_KEYWORD_WEIGHTS.values())
    return matched_weight / max_possible if max_possible > 0 else 0.0

def extract_jd_keywords(jd_data: Dict[str, Any]) -> Dict[str, Set[str]]:
    """Extract keywords from JD with categorization"""
    jd_analysis = jd_data.get('jd_analysis', {})
    
    keyword_categories = {
        'required_skills': set(),
        'preferred_skills': set(),
        'tools_tech': set(),
        'soft_skills': set(),
        'weighted_keywords': {},
        'all_keywords': set()
    }
    
    # Required skills
    for skill in jd_analysis.get('required_skills', []):
        if skill and len(skill.strip()) > 1:
            normalized = normalize_keyword(skill)
            keyword_categories['required_skills'].add(normalized)
            keyword_categories['all_keywords'].add(normalized)
    
    # Preferred skills
    for skill in jd_analysis.get('preferred_skills', []):
        if skill and len(skill.strip()) > 1:
            normalized = normalize_keyword(skill)
            keyword_categories['preferred_skills'].add(normalized)
            keyword_categories['all_keywords'].add(normalized)
    
    # Tools and tech
    for tech in jd_analysis.get('tools_tech', []):
        if tech and len(tech.strip()) > 1:
            normalized = normalize_keyword(tech)
            keyword_categories['tools_tech'].add(normalized)
            keyword_categories['all_keywords'].add(normalized)
    
    # Soft skills
    for skill in jd_analysis.get('soft_skills', []):
        if skill and len(skill.strip()) > 1:
            normalized = normalize_keyword(skill)
            keyword_categories['soft_skills'].add(normalized)
            keyword_categories['all_keywords'].add(normalized)
    
    # From keywords_flat if available
    for keyword in jd_analysis.get('keywords_flat', []):
        if keyword and len(keyword.strip()) > 1:
            normalized = normalize_keyword(keyword)
            keyword_categories['all_keywords'].add(normalized)
    
    # Extract weighted keywords if available
    keywords_weighted = jd_analysis.get('keywords_weighted', {})
    if isinstance(keywords_weighted, dict):
        for keyword, weight in keywords_weighted.items():
            if keyword and len(keyword.strip()) > 1:
                normalized = normalize_keyword(keyword)
                keyword_categories['weighted_keywords'][normalized] = weight
                keyword_categories['all_keywords'].add(normalized)
    
    return keyword_categories

def calculate_exact_matches(resume_keywords: Set[str], jd_keywords: Set[str]) -> Dict[str, Any]:
    """Calculate exact keyword matches"""
    matches = resume_keywords.intersection(jd_keywords)
    
    if not jd_keywords:
        match_percentage = 0.0
    else:
        match_percentage = len(matches) / len(jd_keywords) * 100
    
    return {
        'matches': list(matches),
        'match_count': len(matches),
        'total_jd_keywords': len(jd_keywords),
        'total_resume_keywords': len(resume_keywords),
        'match_percentage': round(match_percentage, 2)
    }

def calculate_fuzzy_matches(resume_keywords: Set[str], jd_keywords: Set[str]) -> Dict[str, Any]:
    """Calculate fuzzy/partial keyword matches"""
    fuzzy_matches = set()
    match_details = []
    
    for jd_keyword in jd_keywords:
        for resume_keyword in resume_keywords:
            # Skip if exact match (already counted)
            if jd_keyword == resume_keyword:
                continue
            
            # Check for partial matches
            similarity = 0.0
            match_type = None
            
            # Substring matching (both directions)
            if jd_keyword in resume_keyword or resume_keyword in jd_keyword:
                # Calculate similarity based on length ratio
                min_len = min(len(jd_keyword), len(resume_keyword))
                max_len = max(len(jd_keyword), len(resume_keyword))
                similarity = min_len / max_len
                match_type = 'substring'
            
            # Word overlap matching for multi-word terms
            elif ' ' in jd_keyword or ' ' in resume_keyword:
                jd_words = set(jd_keyword.split())
                resume_words = set(resume_keyword.split())
                common_words = jd_words.intersection(resume_words)
                
                if common_words and len(common_words) > 0:
                    similarity = len(common_words) / max(len(jd_words), len(resume_words))
                    match_type = 'word_overlap'
            
            # Consider it a fuzzy match if similarity is high enough
            if similarity >= 0.6:  # Threshold for fuzzy matching
                fuzzy_matches.add(jd_keyword)
                match_details.append({
                    'jd_keyword': jd_keyword,
                    'resume_keyword': resume_keyword,
                    'similarity': similarity,
                    'match_type': match_type
                })
                break  # Only count first good match for each JD keyword
    
    return {
        'fuzzy_matches': list(fuzzy_matches),
        'fuzzy_count': len(fuzzy_matches),
        'match_details': match_details
    }

def calculate_weighted_score(exact_matches: Dict[str, Any], fuzzy_matches: Dict[str, Any], 
                           category_weights: Dict[str, float]) -> float:
    """Calculate weighted keyword score with exact and fuzzy matches"""
    # Weights for different match types
    exact_weight = 1.0
    fuzzy_weight = 0.6
    
    # Calculate base score
    exact_score = exact_matches['match_count'] * exact_weight
    fuzzy_score = fuzzy_matches['fuzzy_count'] * fuzzy_weight
    
    total_possible = exact_matches['total_jd_keywords']
    
    if total_possible == 0:
        return 0.0
    
    # Normalize to 0-1 scale
    raw_score = (exact_score + fuzzy_score) / total_possible
    
    # Cap at 1.0
    return min(raw_score, 1.0)

def calculate_keyword_scores(resume: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to calculate keyword matching scores
    Returns: {
        'success': bool,
        'overall_score': float,
        'category_scores': dict,
        'exact_matches': dict,
        'fuzzy_matches': dict,
        'keyword_analysis': dict,
        'error': str or None
    }
    """
    try:
        # Extract keywords
        resume_keywords = extract_resume_keywords(resume)
        jd_keyword_categories = extract_jd_keywords(jd_data)
        
        # Get custom weights from JD or use defaults
        jd_analysis = jd_data.get('jd_analysis', {})
        custom_weights = jd_analysis.get('weighting', {})
        category_weights = DEFAULT_WEIGHTS.copy()
        category_weights.update(custom_weights)
        
        # Add experience keyword score
        experience_score = score_experience_keywords(resume)
        
        # Add weighted keyword score if available
        weighted_kw_score = 0.5
        if jd_keyword_categories.get('weighted_keywords'):
            weighted_kw_score = score_weighted_keywords(
                jd_keyword_categories['weighted_keywords'],
                resume_keywords
            )
        
        # Calculate scores for each category
        category_scores = {}
        all_exact_matches = set()
        all_fuzzy_matches = set()
        
        for category, jd_keywords in jd_keyword_categories.items():
            if category == 'all_keywords':  # Skip this meta category
                continue
                
            if not jd_keywords:  # Skip empty categories
                category_scores[category] = {
                    'score': 0.0,
                    'exact_matches': {'match_count': 0, 'match_percentage': 0.0, 'total_jd_keywords': 0},
                    'fuzzy_matches': {'fuzzy_count': 0}
                }
                continue
            
            # Calculate exact matches
            exact_results = calculate_exact_matches(resume_keywords, jd_keywords)
            
            # Calculate fuzzy matches
            fuzzy_results = calculate_fuzzy_matches(resume_keywords, jd_keywords)
            
            # Calculate weighted score for this category
            category_score = calculate_weighted_score(exact_results, fuzzy_results, category_weights)
            
            category_scores[category] = {
                'score': category_score,
                'exact_matches': exact_results,
                'fuzzy_matches': fuzzy_results,
                'weight': category_weights.get(category, 0.0)
            }
            
            # Collect all matches for overall analysis
            all_exact_matches.update(exact_results['matches'])
            all_fuzzy_matches.update(fuzzy_results['fuzzy_matches'])
        
        # Calculate overall weighted score
        overall_score = 0.0
        total_weight = 0.0
        
        for category, results in category_scores.items():
            weight = category_weights.get(category, 0.0)
            total_jd_keywords = results['exact_matches'].get('total_jd_keywords', 0)
            if weight > 0 and total_jd_keywords > 0:
                category_contribution = results['score'] * weight
                overall_score += category_contribution
                total_weight += weight
        
        # Add experience keyword score
        exp_weight = category_weights.get('experience_keywords', 0.0)
        if exp_weight > 0:
            exp_contribution = experience_score * exp_weight
            overall_score += exp_contribution
            total_weight += exp_weight
        
        # Add weighted keyword score
        weighted_kw_weight = category_weights.get('weighted_keywords', 0.0)
        if weighted_kw_weight > 0:
            weighted_contribution = weighted_kw_score * weighted_kw_weight
            overall_score += weighted_contribution
            total_weight += weighted_kw_weight
        
        # Normalize overall score
        if total_weight > 0:
            overall_score = overall_score / total_weight
        
        # Generate keyword analysis summary
        keyword_analysis = {
            'total_resume_keywords': len(resume_keywords),
            'total_jd_keywords': len(jd_keyword_categories['all_keywords']),
            'total_exact_matches': len(all_exact_matches),
            'total_fuzzy_matches': len(all_fuzzy_matches),
            'coverage_percentage': (len(all_exact_matches) + len(all_fuzzy_matches)) / max(len(jd_keyword_categories['all_keywords']), 1) * 100,
            'keyword_density': len(all_exact_matches) / max(len(resume_keywords), 1) * 100
        }
        
        return {
            'success': True,
            'overall_score': round(overall_score, 3),
            'category_scores': category_scores,
            'experience_keyword_score': round(experience_score, 3),
            'weighted_keyword_score': round(weighted_kw_score, 3),
            'exact_matches': {
                'all_matches': list(all_exact_matches),
                'count': len(all_exact_matches)
            },
            'fuzzy_matches': {
                'all_matches': list(all_fuzzy_matches), 
                'count': len(all_fuzzy_matches)
            },
            'keyword_analysis': keyword_analysis
        }
        
    except Exception as e:
        return {
            'success': False,
            'overall_score': 0.0,
            'error': f"Keyword scoring failed: {str(e)}"
        }
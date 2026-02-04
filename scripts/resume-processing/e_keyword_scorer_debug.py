#!/usr/bin/env python3
"""
Simple Keyword Scorer - Debug Version
"""

import re
from typing import Dict, Any, Set

def normalize_keyword(keyword: str) -> str:
    """Normalize keywords for consistent matching"""
    if not keyword:
        return ""
    return keyword.lower().strip()

def extract_resume_keywords(resume: Dict[str, Any]) -> Set[str]:
    """Extract keywords from resume"""
    keywords = set()
    
    # From skills arrays
    for skill in resume.get('skills', []):
        if skill and len(skill.strip()) > 1:
            keywords.add(normalize_keyword(skill))
    
    print(f"DEBUG: Found {len(keywords)} resume keywords: {list(keywords)[:10]}")
    return keywords

def extract_jd_keywords(jd_data: Dict[str, Any]) -> Set[str]:
    """Extract keywords from JD"""
    print(f"DEBUG: JD data keys: {list(jd_data.keys()) if jd_data else 'None'}")
    
    jd_analysis = jd_data.get('jd_analysis', {})
    print(f"DEBUG: JD analysis keys: {list(jd_analysis.keys()) if jd_analysis else 'None'}")
    
    keywords = set()
    
    # Required skills
    required_skills = jd_analysis.get('required_skills', [])
    print(f"DEBUG: Required skills: {required_skills}")
    for skill in required_skills:
        if skill and len(skill.strip()) > 1:
            keywords.add(normalize_keyword(skill))
    
    # Preferred skills
    preferred_skills = jd_analysis.get('preferred_skills', [])
    print(f"DEBUG: Preferred skills: {preferred_skills}")
    for skill in preferred_skills:
        if skill and len(skill.strip()) > 1:
            keywords.add(normalize_keyword(skill))
    
    # Tools and tech
    tools_tech = jd_analysis.get('tools_tech', [])
    print(f"DEBUG: Tools tech: {tools_tech}")
    for tech in tools_tech:
        if tech and len(tech.strip()) > 1:
            keywords.add(normalize_keyword(tech))
    
    print(f"DEBUG: Found {len(keywords)} JD keywords: {list(keywords)[:10]}")
    return keywords

def calculate_keyword_scores(resume: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
    """Simple keyword scoring with debug output"""
    try:
        print("DEBUG: Starting keyword scoring...")
        
        # Extract keywords
        resume_keywords = extract_resume_keywords(resume)
        jd_keywords = extract_jd_keywords(jd_data)
        
        if not resume_keywords:
            print("DEBUG: No resume keywords found!")
            return {'success': True, 'overall_score': 0.0, 'error': 'No resume keywords'}
        
        if not jd_keywords:
            print("DEBUG: No JD keywords found!")
            return {'success': True, 'overall_score': 0.0, 'error': 'No JD keywords'}
        
        # Calculate matches
        matches = resume_keywords.intersection(jd_keywords)
        print(f"DEBUG: Matches found: {matches}")
        
        # Simple score calculation
        score = len(matches) / len(jd_keywords) if jd_keywords else 0.0
        
        print(f"DEBUG: Final score: {score} ({len(matches)}/{len(jd_keywords)})")
        
        return {
            'success': True,
            'overall_score': score,
            'matches': list(matches),
            'resume_keyword_count': len(resume_keywords),
            'jd_keyword_count': len(jd_keywords),
            'match_count': len(matches)
        }
        
    except Exception as e:
        print(f"DEBUG: Error in keyword scoring: {e}")
        return {
            'success': False,
            'overall_score': 0.0,
            'error': str(e)
        }
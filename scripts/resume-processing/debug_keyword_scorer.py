#!/usr/bin/env python3

"""
DEBUG VERSION: Keyword Scorer for Resume Analysis
"""

from e_keyword_scorer import extract_jd_keywords, extract_resume_keywords, calculate_keyword_scores

def debug_keyword_scorer(resume: dict, jd_data: dict):
    """Debug the keyword scoring process"""
    
    print("=== KEYWORD SCORER DEBUG ===")
    print(f"JD Data type: {type(jd_data)}")
    print(f"JD Data is None: {jd_data is None}")
    
    if jd_data:
        print(f"JD Data keys: {list(jd_data.keys())}")
        
        jd_analysis = jd_data.get('jd_analysis', {})
        print(f"JD Analysis keys: {list(jd_analysis.keys())}")
        
        # Check specific fields
        required_skills = jd_analysis.get('required_skills', [])
        preferred_skills = jd_analysis.get('preferred_skills', [])
        tools_tech = jd_analysis.get('tools_tech', [])
        
        print(f"Required skills: {required_skills}")
        print(f"Preferred skills: {preferred_skills}")
        print(f"Tools & Tech: {tools_tech}")
    else:
        print("JD Data is empty or None!")
        return {'success': False, 'overall_score': 0.0, 'error': 'No JD data provided'}
        
    # Try to calculate normally
    result = calculate_keyword_scores(resume, jd_data)
    print(f"Final result: {result}")
    
    return result

if __name__ == "__main__":
    # This will be called during resume processing
    pass
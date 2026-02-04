#!/usr/bin/env python3
"""
Simple Semantic Scorer - Debug Version
"""

import numpy as np
from typing import Dict, Any

def calculate_semantic_scores(resume_embeddings: Dict[str, Any], jd_embeddings: Dict[str, Any]) -> Dict[str, Any]:
    """Simple semantic scoring with debug output"""
    try:
        print("DEBUG: Starting semantic scoring...")
        print(f"DEBUG: Resume embeddings type: {type(resume_embeddings)}")
        print(f"DEBUG: Resume embeddings keys: {list(resume_embeddings.keys()) if resume_embeddings else 'None'}")
        print(f"DEBUG: JD embeddings type: {type(jd_embeddings)}")
        print(f"DEBUG: JD embeddings keys: {list(jd_embeddings.keys()) if jd_embeddings else 'None'}")
        
        # Check if jd_embeddings is actually the full jd_data
        if jd_embeddings and 'embeddings' in jd_embeddings:
            print("DEBUG: Found 'embeddings' key in JD data")
            actual_jd_embeddings = jd_embeddings.get('embeddings', {})
            print(f"DEBUG: Actual JD embeddings keys: {list(actual_jd_embeddings.keys()) if actual_jd_embeddings else 'None'}")
        
        if not resume_embeddings or not jd_embeddings:
            print("DEBUG: Missing embeddings!")
            return {
                'success': True,
                'overall_semantic_score': 0.0,
                'error': 'Missing embeddings'
            }
        
        # Simple calculation - just return 0.7 for now to test
        score = 0.7
        
        print(f"DEBUG: Semantic score: {score}")
        
        return {
            'success': True,
            'overall_semantic_score': score,
            'section_scores': {'skills': 0.7, 'projects': 0.7}
        }
        
    except Exception as e:
        print(f"DEBUG: Error in semantic scoring: {e}")
        return {
            'success': False,
            'overall_semantic_score': 0.0,
            'error': str(e)
        }
#!/usr/bin/env python3
"""
Semantic Scorer for Resume Analysis

Calculates semantic similarity scores using embeddings and cosine similarity.
Matches old SemanticComparitor.py 6-section scoring logic exactly.
"""

import numpy as np
from typing import Dict, Any, Tuple, List

# Constants from old system - exact values
TAU_COV = 0.65        # Coverage threshold (original from SemanticComparitor.py)
TAU_RESUME = 0.55     # Resume density threshold (original from SemanticComparitor.py)
SECTION_COMB = (0.5, 0.4, 0.1)  # (coverage, depth, density) weights

# Section weights for overall score
SECTION_WEIGHTS = {
    "skills": 0.30,
    "projects": 0.25,
    "responsibilities": 0.20,
    "profile": 0.10,
    "education": 0.05,
    "overall": 0.10
}


# ============================================================================
# CORE SCORING FUNCTIONS
# ============================================================================

def cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Calculate cosine similarity matrix between two sets of embeddings"""
    return np.matmul(a, b.T)


def compute_section_score(jd_embeddings: np.ndarray, resume_embeddings: np.ndarray) -> Tuple[float, float, float, List]:
    """
    Compute section score using EXACT SemanticComparitor.py algorithm.
    
    Args:
        jd_embeddings: JD embeddings for this section (2D array)
        resume_embeddings: Resume embeddings for this section (2D array)
    
    Returns:
        Tuple of (section_score, coverage, depth, matches)
        - section_score: Combined score using SECTION_COMB weights
        - coverage: Fraction of JD sentences well-matched (>= TAU_COV)
        - depth: Average max similarity across JD sentences
        - matches: List of (jd_idx, resume_idx, similarity) tuples
    """
    # Handle empty cases
    if jd_embeddings.size == 0:
        return 0.5, 0.0, 0.0, []  # Keep 0.5 for empty JD sections as requested
    if resume_embeddings.size == 0:
        return 0.0, 0.0, 0.0, []
    
    # Compute cosine similarity matrix: jd_sentences × resume_sentences
    C = cosine_sim(jd_embeddings, resume_embeddings)
    
    # Coverage: fraction of JD sentences with strong match (>= TAU_COV)
    max_j = C.max(axis=1)
    coverage = float((max_j >= TAU_COV).sum()) / len(max_j)
    
    # Depth: average best match across JD sentences
    depth = float(max_j.mean())
    
    # Density: fraction of resume sentences well-utilized (>= TAU_RESUME)
    max_r = C.max(axis=0)
    density = float((max_r >= TAU_RESUME).sum()) / max(1, len(max_r))
    
    # Combined section score
    section_score = SECTION_COMB[0] * coverage + SECTION_COMB[1] * depth + SECTION_COMB[2] * density
    
    # Best matches for each JD sentence
    matches = [
        (j, int(C[j].argmax()), float(C[j].max()))
        for j in range(C.shape[0])
    ]
    
    return section_score, coverage, depth, matches


# ============================================================================
# MAIN SCORING FUNCTION
# ============================================================================

def calculate_semantic_scores(resume_embeddings: Dict[str, Any], jd_embeddings: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate semantic similarity scores using 6-section algorithm.
    Matches old SemanticComparitor.py logic exactly.
    
    Args:
        resume_embeddings: Dict with section keys (profile, skills, projects, 
                          responsibilities, education, overall) containing 2D numpy arrays (N × 1536)
        jd_embeddings: Dict from Job.embeddings with fields like profile_embedding,
                      skills_embedding containing 2D arrays as lists (M × 1536) from MongoDB
    
    Returns:
        Dictionary with:
            - success: bool
            - overall_semantic_score: float (0-1, weighted aggregate)
            - section_scores: dict with individual section scores
            - section_details: dict with coverage/depth metrics per section
            - error: str or None
    """
    try:
        # Convert JD embeddings from MongoDB 2D lists to numpy 2D arrays
        jd_section_embeddings = {}
        for section in SECTION_WEIGHTS.keys():
            # MongoDB stores as: profile_embedding, skills_embedding, etc.
            jd_key = f'{section}_embedding'
            
            if jd_key in jd_embeddings and jd_embeddings[jd_key]:
                emb_data = jd_embeddings[jd_key]
                
                # Expect 2D list: [[emb1], [emb2], ...] where each emb is 1536 floats
                if isinstance(emb_data, list) and len(emb_data) > 0:
                    # Validate it's 2D
                    if not isinstance(emb_data[0], list):
                        raise ValueError(f"JD {section}_embedding is 1D (expected 2D). Got: {type(emb_data[0])}. First item sample: {emb_data[0][:5] if len(emb_data[0]) > 0 else 'empty'}")
                    
                    # Convert 2D list to numpy 2D array
                    jd_section_embeddings[section] = np.array(emb_data, dtype=np.float32)
                else:
                    jd_section_embeddings[section] = np.zeros((0, 1536), dtype=np.float32)
            else:
                jd_section_embeddings[section] = np.zeros((0, 1536), dtype=np.float32)
        
        # Calculate section scores
        section_scores = {}
        section_details = {}
        
        print(f"\n🔍 SEMANTIC SCORING DEBUG:")
        
        for section in SECTION_WEIGHTS.keys():
            jd_emb = jd_section_embeddings.get(section, np.zeros((0, 1536), dtype=np.float32))
            resume_emb = resume_embeddings.get(section, np.zeros((0, 1536), dtype=np.float32))
            
            print(f"  📊 {section.upper()}:")
            print(f"    JD embeddings: {jd_emb.shape[0]} sentences")
            print(f"    Resume embeddings: {resume_emb.shape[0]} sentences")
            
            # Validate both are 2D arrays
            if jd_emb.ndim != 2:
                raise ValueError(f"JD {section} embedding is {jd_emb.ndim}D (expected 2D). Shape: {jd_emb.shape}")
            if resume_emb.ndim != 2:
                raise ValueError(f"Resume {section} embedding is {resume_emb.ndim}D (expected 2D). Shape: {resume_emb.shape}")
            
            # Compute section score using old archive algorithm
            sec_score, coverage, depth, matches = compute_section_score(jd_emb, resume_emb)
            
            print(f"    Score: {sec_score:.3f} (coverage: {coverage:.3f}, depth: {depth:.3f})")
            print(f"    Weight: {SECTION_WEIGHTS[section]} → Contribution: {sec_score * SECTION_WEIGHTS[section]:.3f}")
            
            section_scores[section] = sec_score
            section_details[section] = {
                'score': sec_score,
                'coverage': coverage,
                'depth': depth,
                'jd_sentences': jd_emb.shape[0],
                'resume_sentences': resume_emb.shape[0],
                'match_count': len(matches)
            }
        
        # Calculate weighted overall score
        overall_score = sum(
            section_scores[section] * weight
            for section, weight in SECTION_WEIGHTS.items()
        )
        
        return {
            'success': True,
            'overall_semantic_score': round(overall_score, 3),
            'section_scores': {k: round(v, 3) for k, v in section_scores.items()},
            'section_details': section_details,
            'error': None
        }
        
    except Exception as e:
        import traceback
        return {
            'success': False,
            'overall_semantic_score': 0.0,
            'section_scores': {},
            'section_details': {},
            'error': f"Semantic scoring failed: {str(e)}\n{traceback.format_exc()}"
        }

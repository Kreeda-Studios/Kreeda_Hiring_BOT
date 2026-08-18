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

def calculate_semantic_scores(
    resume_embeddings: Dict[str, Any],
    jd_embeddings: Dict[str, Any],
    resume_texts: Dict[str, List[str]] = None,
    parsed_resume: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Calculate semantic similarity scores using 6-section algorithm and extract verbatim evidence sentences.
    
    Args:
        resume_embeddings: Dict with section keys containing 2D numpy arrays (N × 1536)
        jd_embeddings: Dict from Job.embeddings with section arrays
        resume_texts: Optional dict mapping section names to original resume sentence strings
        parsed_resume: Optional parsed resume JSON dictionary for structured fallbacks
    """
    try:
        # Convert JD embeddings from MongoDB 2D lists to numpy 2D arrays
        jd_section_embeddings = {}
        for section in SECTION_WEIGHTS.keys():
            jd_key = f'{section}_embedding'
            
            if jd_key in jd_embeddings and jd_embeddings[jd_key]:
                emb_data = jd_embeddings[jd_key]
                if isinstance(emb_data, list) and len(emb_data) > 0:
                    if not isinstance(emb_data[0], list):
                        raise ValueError(f"JD {section}_embedding is 1D (expected 2D). Got: {type(emb_data[0])}")
                    jd_section_embeddings[section] = np.array(emb_data, dtype=np.float32)
                else:
                    jd_section_embeddings[section] = np.zeros((0, 1536), dtype=np.float32)
            else:
                jd_section_embeddings[section] = np.zeros((0, 1536), dtype=np.float32)
        
        # Calculate section scores and extract verbatim evidence
        section_scores = {}
        section_details = {}
        evidence_dict = {}
        
        print(f"\n🔍 SEMANTIC SCORING DEBUG:")
        
        for section in SECTION_WEIGHTS.keys():
            jd_emb = jd_section_embeddings.get(section, np.zeros((0, 1536), dtype=np.float32))
            resume_emb = resume_embeddings.get(section, np.zeros((0, 1536), dtype=np.float32))
            
            print(f"  📊 {section.upper()}:")
            print(f"    JD embeddings: {jd_emb.shape[0]} sentences")
            print(f"    Resume embeddings: {resume_emb.shape[0]} sentences")
            
            if jd_emb.ndim != 2:
                raise ValueError(f"JD {section} embedding is {jd_emb.ndim}D (expected 2D). Shape: {jd_emb.shape}")
            if resume_emb.ndim != 2:
                raise ValueError(f"Resume {section} embedding is {resume_emb.ndim}D (expected 2D). Shape: {resume_emb.shape}")
            
            sec_score, coverage, depth, matches = compute_section_score(jd_emb, resume_emb)
            
            # Extract verbatim candidate sentence evidence
            top_evidence = []
            seen_quotes = set()
            if resume_texts and section in resume_texts and resume_texts[section]:
                sec_sentences = resume_texts[section]
                strong_matches = sorted([m for m in matches if m[2] >= 0.30], key=lambda x: x[2], reverse=True)
                if not strong_matches and matches:
                    strong_matches = sorted(matches, key=lambda x: x[2], reverse=True)
                for _, r_idx, sim in strong_matches:
                    if 0 <= r_idx < len(sec_sentences):
                        quote = sec_sentences[r_idx].strip()
                        if quote and len(quote) > 5 and quote not in seen_quotes:
                            seen_quotes.add(quote)
                            top_evidence.append(quote)
                            if len(top_evidence) >= 3:
                                break

            # Structured Project Title Fallback: If section is projects & no sentence quotes found, pull title from parsed_resume
            if section == 'projects' and not top_evidence and parsed_resume and isinstance(parsed_resume.get('projects'), list):
                for prj in parsed_resume['projects']:
                    title = prj.get('title') or prj.get('name')
                    if title:
                        p_str = f"Project: {title.strip()}"
                        if p_str not in seen_quotes:
                            seen_quotes.add(p_str)
                            top_evidence.append(p_str)
                            if len(top_evidence) >= 2:
                                break

            evidence_dict[section] = top_evidence
            print(f"    Score: {sec_score:.3f} (coverage: {coverage:.3f}, depth: {depth:.3f}) | Evidence quotes: {len(top_evidence)}")
            print(f"    Weight: {SECTION_WEIGHTS[section]} → Contribution: {sec_score * SECTION_WEIGHTS[section]:.3f}")
            
            section_scores[section] = sec_score
            section_details[section] = {
                'score': sec_score,
                'coverage': coverage,
                'depth': depth,
                'jd_sentences': jd_emb.shape[0],
                'resume_sentences': resume_emb.shape[0],
                'match_count': len(matches),
                'top_evidence': top_evidence
            }
        
        # Calculate weighted overall score
        overall_score = sum(
            section_scores[section] * weight
            for section, weight in SECTION_WEIGHTS.items()
        )
        
        sec_scores_dict = {k: round(v, 3) for k, v in section_scores.items()}
        sec_scores_dict['experience'] = sec_scores_dict.get('responsibilities', 0.0)
        
        # Attach evidence dictionary (skills, projects, responsibilities, experience, education)
        evidence_dict['experience'] = evidence_dict.get('responsibilities', [])
        sec_scores_dict['evidence'] = evidence_dict

        return {
            'success': True,
            'overall_semantic_score': round(overall_score, 3),
            'section_scores': sec_scores_dict,
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

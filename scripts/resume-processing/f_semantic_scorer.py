#!/usr/bin/env python3

"""
Semantic Scorer for Resume Analysis

Calculates semantic similarity scores using OpenAI embeddings.
Exact match with old archive SemanticComparitor.py scoring logic.
"""

import numpy as np
from typing import Dict, Any, List, Tuple

# Constants from old archive - exact match
TAU_COV = 0.65
TAU_RESUME = 0.55
SECTION_COMB = (0.5, 0.4, 0.1)
SECTION_WEIGHTS = {
    "skills": 0.30, 
    "projects": 0.25, 
    "responsibilities": 0.20,
    "profile": 0.10, 
    "education": 0.05, 
    "overall": 0.10
}

def cosine_sim(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Cosine similarity - exact match with old archive"""
    return np.matmul(a, b.T)

def compute_section_score(jd_embeddings: np.ndarray, resume_embeddings: np.ndarray) -> Tuple[float, float, float, List]:
    """Compute section score - exact match with old archive"""
    if jd_embeddings.size == 0: 
        return 0.5, 0, 0, []
    if resume_embeddings.size == 0: 
        return 0, 0, 0, []
    
    C = cosine_sim(jd_embeddings, resume_embeddings)
    max_j = C.max(axis=1)
    cov = float((max_j >= TAU_COV).sum()) / len(max_j)
    depth = float(max_j.mean())
    max_r = C.max(axis=0)
    dens = float((max_r >= TAU_RESUME).sum()) / max(1, len(max_r))
    sec = SECTION_COMB[0] * cov + SECTION_COMB[1] * depth + SECTION_COMB[2] * dens
    matches = [(j, int(C[j].argmax()), float(C[j].max())) for j in range(C.shape[0])]
    return sec, cov, depth, matches

def calculate_experience_similarity(resume_embeddings: Dict[str, Any], jd_embeddings: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate experience-based semantic similarity"""
    try:
        resume_experiences = resume_embeddings.get('experience_embeddings', [])
        jd_responsibilities = jd_embeddings.get('responsibility_embeddings', {})
        
        if not resume_experiences or not jd_responsibilities:
            return {
                'average_similarity': 0.0,
                'best_match_score': 0.0,
                'experience_matches': []
            }
        
        # Get JD responsibility embedding (combine all responsibilities)
        jd_resp_embedding = jd_responsibilities.get('combined_embedding', [])
        if not jd_resp_embedding:
            return {
                'average_similarity': 0.0,
                'best_match_score': 0.0,
                'experience_matches': []
            }
        
        experience_similarities = []
        experience_matches = []
        
        # Compare each resume experience with JD responsibilities
        for exp in resume_experiences:
            exp_embedding = exp.get('embedding', [])
            if not exp_embedding:
                continue
            
            similarity = calculate_cosine_similarity(exp_embedding, jd_resp_embedding)
            
            experience_similarities.append(similarity)
            experience_matches.append({
                'company': exp.get('company', ''),
                'title': exp.get('title', ''),
                'similarity': similarity,
                'index': exp.get('index', 0)
            })
        
        # Calculate metrics
        avg_similarity = sum(experience_similarities) / len(experience_similarities) if experience_similarities else 0.0
        best_match = max(experience_similarities) if experience_similarities else 0.0
        
        # Sort matches by similarity
        experience_matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        return {
            'average_similarity': avg_similarity,
            'best_match_score': best_match,
            'experience_matches': experience_matches,
            'experiences_analyzed': len(experience_similarities)
        }
        
    except Exception as e:
        return {
            'average_similarity': 0.0,
            'error': f"Experience similarity calculation failed: {str(e)}"
        }

def calculate_project_similarity(resume_embeddings: Dict[str, Any], jd_embeddings: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate project-based semantic similarity"""
    try:
        resume_projects = resume_embeddings.get('project_embeddings', [])
        jd_embedding = jd_embeddings.get('jd_embedding', [])
        
        if not resume_projects or not jd_embedding:
            return {
                'average_similarity': 0.0,
                'best_project_score': 0.0,
                'project_matches': []
            }
        
        project_similarities = []
        project_matches = []
        
        # Compare each project with overall JD
        for proj in resume_projects:
            proj_embedding = proj.get('embedding', [])
            if not proj_embedding:
                continue
            
            similarity = calculate_cosine_similarity(proj_embedding, jd_embedding)
            
            project_similarities.append(similarity)
            project_matches.append({
                'name': proj.get('name', ''),
                'similarity': similarity,
                'technologies': proj.get('technologies', []),
                'index': proj.get('index', 0)
            })
        
        # Calculate metrics
        avg_similarity = sum(project_similarities) / len(project_similarities) if project_similarities else 0.0
        best_project = max(project_similarities) if project_similarities else 0.0
        
        # Sort matches by similarity
        project_matches.sort(key=lambda x: x['similarity'], reverse=True)
        
        return {
            'average_similarity': avg_similarity,
            'best_project_score': best_project,
            'project_matches': project_matches,
            'projects_analyzed': len(project_similarities)
        }
        
    except Exception as e:
        return {
            'average_similarity': 0.0,
            'error': f"Project similarity calculation failed: {str(e)}"
        }

def calculate_semantic_scores(resume_section_embeddings: Dict[str, Any], jd_embeddings_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to calculate semantic similarity scores using old archive algorithm
    Uses 6-section scoring with proper weights and compute_section_score function
    
    Args:
        resume_section_embeddings: Dict with keys: profile, skills, projects, responsibilities, education, overall (numpy arrays)
        jd_embeddings_data: Dict from job.embeddings containing profile_embedding, skills_embedding, etc. (lists)
    
    Returns: {
        'success': bool,
        'overall_semantic_score': float,
        'section_scores': dict,
        'semantic_breakdown': dict,
        'error': str or None
    }
    """
    try:
        # Check if JD embeddings are nested under 'embeddings' key
        if 'embeddings' in jd_embeddings_data:
            jd_embeddings_source = jd_embeddings_data['embeddings']
        else:
            jd_embeddings_source = jd_embeddings_data
        
        # Convert JD embeddings from lists to numpy arrays
        jd_section_embeddings = {}
        for section in ['profile', 'skills', 'projects', 'responsibilities', 'education', 'overall']:
            jd_key = f'{section}_embedding'
            if jd_key in jd_embeddings_source and jd_embeddings_source[jd_key]:
                emb_data = jd_embeddings_source[jd_key]
                # Check if it's a 2D array [[emb1], [emb2]] or single 1D array [emb]
                if isinstance(emb_data, list) and len(emb_data) > 0:
                    if isinstance(emb_data[0], list):
                        # Already 2D: [[emb1], [emb2], ...]
                        jd_section_embeddings[section] = np.array(emb_data, dtype=np.float32)
                    else:
                        # 1D array, wrap in 2D: [emb] -> [[emb]]
                        jd_section_embeddings[section] = np.array([emb_data], dtype=np.float32)
                else:
                    jd_section_embeddings[section] = np.zeros((0, 1536), dtype=np.float32)
            else:
                # Empty embedding
                jd_section_embeddings[section] = np.zeros((0, 1536), dtype=np.float32)
        
        # Calculate section scores using old archive algorithm
        section_scores = {}
        section_details = {}
        
        for section in SECTION_WEIGHTS.keys():
            jd_emb = jd_section_embeddings.get(section, np.zeros((0, 1536), dtype=np.float32))
            resume_emb = resume_section_embeddings.get(section, np.zeros((0, 1536), dtype=np.float32))
            
            # Use old archive's compute_section_score function
            sec_score, coverage, depth, matches = compute_section_score(jd_emb, resume_emb)
            
            section_scores[section] = sec_score
            section_details[section] = {
                'score': sec_score,
                'coverage': coverage,
                'depth': depth,
                'match_count': len(matches)
            }
        
        # Calculate weighted overall semantic score (old archive formula)
        raw_score = sum(
            section_scores[section] * weight
            for section, weight in SECTION_WEIGHTS.items()
        )
        
        # Create semantic breakdown
        semantic_breakdown = {
            'section_weights': SECTION_WEIGHTS,
            'section_scores': section_scores,
            'section_details': section_details,
            'weighted_components': {
                f'{section}_weighted': section_scores[section] * weight
                for section, weight in SECTION_WEIGHTS.items()
            },
            'raw_score': raw_score,
            'algorithm': 'old_archive_6_section'
        }
        
        return {
            'success': True,
            'overall_semantic_score': round(raw_score, 3),
            'section_scores': section_scores,
            'semantic_breakdown': semantic_breakdown
        }
        
    except Exception as e:
        import traceback
        return {
            'success': False,
            'overall_semantic_score': 0.0,
            'error': f"Semantic scoring failed: {str(e)}\n{traceback.format_exc()}"
        }
  #!/usr/bin/env python3
"""
AI Embedding Generation for Job Descriptions

Generates 6 section-specific embeddings for semantic matching with resumes.
Each section produces a 2D array of embeddings: [[emb1], [emb2], ...] where each
item in the section gets its own embedding vector for fine-grained matching.

SECTION FIELD MAPPINGS:
========================

1. PROFILE (Role identity)
   - role_title (sentence split)
   - embedding_hints.overall_embed (sentence split)

2. SKILLS (Technical requirements)
   - required_skills (list items)
   - preferred_skills (list items)
   - keywords_flat (fallback if no skills)

3. PROJECTS (Project expectations)
   - embedding_hints.projects_embed (sentence split)

4. RESPONSIBILITIES (Daily duties)
   - responsibilities[] (each item sentence split)

5. EDUCATION (Qualifications)
   - certifications_required[] (list items)
   - education_requirements[] (list items)

6. OVERALL (Complete summary)
   - embedding_hints.overall_embed (sentence split)

OUTPUT FORMAT:
==============
Returns 2D arrays for compatibility with matrix-based semantic scoring.
Example: profile_embedding = [[vec1], [vec2], [vec3]]

Each embedding vector is 1536 dimensions (text-embedding-3-small)
"""

import os
import sys
import time
from typing import Dict, Any, List
from pathlib import Path

# Add parent directory to path for OpenAI client import
sys.path.append(str(Path(__file__).parent.parent))

try:
    from openai_client import create_embedding_async
except ImportError:
    #print("❌ Failed to import OpenAI client")
    sys.exit(1)


# -----------------------
# Text Processing Utilities
# -----------------------
def norm(s): 
    """Normalize and trim string"""
    return s.strip() if isinstance(s, str) else ""

def sentence_split(text: str) -> List[str]:
    """
    Split text into sentences for individual embedding generation.
    Only includes sentences with 3+ words for meaningful content.
    """
    if not text: return []
    text = text.replace("\n", " ")
    parts = []
    start = 0
    for i, ch in enumerate(text):
        if ch in ".!?":
            seg = text[start:i+1].strip()
            if seg: parts.append(seg)
            start = i+1
    tail = text[start:].strip()
    if tail: parts.append(tail)
    return [p for p in parts if len(p.split()) >= 3]

def safe_list(x): 
    """Safely extract list from value"""
    return x if isinstance(x, list) else []


# -----------------------
# Embedding Generation
# -----------------------
async def generate_section_embeddings(texts: List[str], section_name: str) -> Dict[str, Any]:
    """
    Generate embeddings for multiple text items in a section.
    Creates one embedding vector per text item for fine-grained semantic matching.
    
    Args:
        texts: List of strings to embed (e.g., ["skill1", "skill2", "skill3"])
        section_name: Section identifier for logging
    
    Returns:
        dict: {
            'success': bool,
            'embeddings': [[emb1], [emb2], ...],  # 2D array
            'dimension': int (1536),
            'count': int
        }
    """
    try:
        if not texts or len(texts) == 0:
            return {
                'success': True,
                'embeddings': [],
                'dimension': 1536,
                'section': section_name,
                'count': 0
            }
        
        # Generate one embedding per text item to create 2D array
        embeddings = []
        for text in texts:
            if text and text.strip():
                emb = await create_embedding_async(text.strip())  # Returns 1D: [f1, f2, ..., f1536]
                embeddings.append(emb)  # Append to create 2D: [[f1, f2, ..., f1536], [f1, f2, ...]]
        
        return {
            'success': True,
            'embeddings': embeddings,
            'dimension': len(embeddings[0]) if embeddings else 1536,  # Get dimension from first embedding
            'section': section_name,
            'count': len(embeddings)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"{section_name} embeddings failed: {str(e)}"
        }


# -----------------------
# Section Extraction from JD
# -----------------------
def extract_sections_from_jd(jd: dict) -> Dict[str, List[str]]:
    """
    Extract text content from JD fields and organize into 6 semantic sections.
    Each section returns a list of strings (not a single concatenated string).
    
    Returns:
        dict: {
            'profile': [str, str, ...],
            'skills': [str, str, ...],
            'projects': [str, str, ...],
            'responsibilities': [str, str, ...],
            'education': [str, str, ...],
            'overall': [str, str, ...]
        }
    """
    sections = {k: [] for k in ["profile","skills","projects","responsibilities","education","overall"]}

    # PROFILE: Role title and high-level summary
    if jd.get("role_title"): 
        sections["profile"] += sentence_split(jd["role_title"])
    if jd.get("embedding_hints", {}).get("overall_embed"):
        sections["overall"] += sentence_split(jd["embedding_hints"]["overall_embed"])
    
    # RESPONSIBILITIES: Job duties (each responsibility broken into sentences)
    if jd.get("responsibilities"):
        for r in jd["responsibilities"]: 
            sections["responsibilities"] += sentence_split(r)
    
    # SKILLS: Required and preferred technical skills
    if jd.get("required_skills"):
        sections["skills"] += [norm(x) for x in jd["required_skills"]]
    if jd.get("preferred_skills"):
        sections["skills"] += [norm(x) for x in jd["preferred_skills"]]
    
    # PROJECTS: Project-related expectations
    if jd.get("embedding_hints", {}).get("projects_embed"):
        sections["projects"] += sentence_split(jd["embedding_hints"]["projects_embed"])
    
    # EDUCATION: Certifications and degree requirements
    if jd.get("certifications_required"):
        sections["education"] += [norm(x) for x in jd["certifications_required"]]
    if jd.get("education_requirements"):
        sections["education"] += [norm(x) for x in jd["education_requirements"]]
    
    # Fallback: If skills section is empty, use keywords_flat
    if jd.get("keywords_flat") and not sections["skills"]:
        sections["skills"] += [norm(x) for x in jd["keywords_flat"]]

    # Deduplicate items within each section while preserving order
    for k in sections:
        dedup, out = set(), []
        for s in sections[k]:
            key = s.lower().strip()
            if key not in dedup:
                dedup.add(key)
                out.append(s)
        sections[k] = out

    return sections


async def generate_and_format_embeddings(parsed_jd: dict) -> Dict:
    """
    Generate embeddings and format for database storage (API-ready payload).
    
    Args:
        parsed_jd: Parsed JD data from AI parser
        
    Returns:
        dict: {
            'success': bool,
            'embeddings_payload': {
                'embeddings': {
                    'embedding_model': 'text-embedding-3-small',
                    'embedding_dimension': 1536,
                    'profile_embedding': [[emb1], [emb2], ...],
                    'skills_embedding': [[emb1], [emb2], ...],
                    'projects_embedding': [[emb1], [emb2], ...],
                    'responsibilities_embedding': [[emb1], [emb2], ...],
                    'education_embedding': [[emb1], [emb2], ...],
                    'overall_embedding': [[emb1], [emb2], ...]
                }
            },
            'stats': {
                'sections_generated': int,
                'total_sections': 6,
                'model': str,
                'dimension': int
            },
            'error': str or None
        }
    """
    result = await process_jd_embeddings(parsed_jd)
    
    if not result.get('success'):
        return {
            'success': False,
            'embeddings_payload': None,
            'stats': {
                'sections_generated': 0,
                'total_sections': 6,
                'model': None,
                'dimension': None
            },
            'error': result.get('error', 'Embedding generation failed')
        }
    
    embeddings_payload = {
        'embeddings': {
            'embedding_model': result.get('embedding_model', 'text-embedding-3-small'),
            'embedding_dimension': result.get('embedding_dimension', 1536),
            'profile_embedding': result.get('profile_embedding'),
            'skills_embedding': result.get('skills_embedding'),
            'projects_embedding': result.get('projects_embedding'),
            'responsibilities_embedding': result.get('responsibilities_embedding'),
            'education_embedding': result.get('education_embedding'),
            'overall_embedding': result.get('overall_embedding')
        }
    }
    
    sections_count = result.get('sections_generated', 6)
    
    return {
        'success': True,
        'embeddings_payload': embeddings_payload,
        'stats': {
            'sections_generated': sections_count,
            'total_sections': 6,
            'model': result.get('embedding_model', 'text-embedding-3-small'),
            'dimension': result.get('embedding_dimension', 1536)
        },
        'error': None
    }


# -----------------------
# Main Processing Functions
# -----------------------
async def process_jd_embeddings(parsed_jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate embeddings for all 6 JD sections.
    Each section produces a 2D array for matrix-based semantic scoring.
    
    Args:
        parsed_jd: Parsed JD data from AI parser
    
    Returns:
        dict: {
            'success': bool,
            'profile_embedding': [[emb1], [emb2], ...],
            'skills_embedding': [[emb1], [emb2], ...],
            'projects_embedding': [[emb1], [emb2], ...],
            'responsibilities_embedding': [[emb1], [emb2], ...],
            'education_embedding': [[emb1], [emb2], ...],
            'overall_embedding': [[emb1], [emb2], ...],
            'embedding_model': 'text-embedding-3-small',
            'embedding_dimension': 1536,
            'sections_generated': int,
            'processing_time': float
        }
    """
    try:
        start_time = time.time()
        
        # Extract text content organized by section
        sections = extract_sections_from_jd(parsed_jd)
        
        # Generate embeddings for each section
        results = {}
        section_names = ['profile', 'skills', 'projects', 'responsibilities', 'education', 'overall']
        
        for section in section_names:
            texts = sections.get(section, [])
            result = await generate_section_embeddings(texts, section)
            
            if not result['success']:
                # Use empty array as fallback (won't break scoring)
                results[f'{section}_embedding'] = []
            else:
                results[f'{section}_embedding'] = result['embeddings']
        
        processing_time = time.time() - start_time
        
        # Count successful sections (non-empty embeddings)
        successful_embeddings = sum(1 for k, v in results.items() if v and len(v) > 0)
        
        if successful_embeddings == 0:
            return {
                'success': False,
                'error': 'All section embeddings failed to generate'
            }
        
        return {
            'success': True,
            **results,
            'embedding_model': 'text-embedding-3-small',
            'embedding_dimension': 1536,
            'sections_generated': successful_embeddings,
            'processing_time': processing_time
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"JD embeddings processing failed: {str(e)}"
        }

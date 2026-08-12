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
    from openai_client import create_embeddings_batch_async
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
    Generate embeddings for multiple text items in a section in batch.
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
        
        # Clean up and filter out empty texts
        cleaned_texts = [text.strip() for text in texts if text and text.strip()]
        
        if not cleaned_texts:
            return {
                'success': True,
                'embeddings': [],
                'dimension': 1536,
                'section': section_name,
                'count': 0
            }
        
        # Generate embeddings in a single batch API call
        embeddings = await create_embeddings_batch_async(cleaned_texts)
        
        return {
            'success': True,
            'embeddings': embeddings,
            'dimension': len(embeddings[0]) if embeddings else 1536,
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
    Maps from the new JDExtraction schema (b_ai_jd_parser.py).

    New field paths:
      - job_profile.role / job_profile.domain  → profile
      - skills.required / skills.preferred + tech_stack.*  → skills
      - tech_stack (frameworks, ai_techniques, libraries) → projects (proxy)
      - responsibilities                         → responsibilities
      - education_requirements.degrees/fields + certifications → education
      - combined summary                         → overall

    Returns:
        dict: {
            'profile': [str, ...],
            'skills': [str, ...],
            'projects': [str, ...],
            'responsibilities': [str, ...],
            'education': [str, ...],
            'overall': [str, ...]
        }
    """
    sections = {k: [] for k in ["profile", "skills", "projects", "responsibilities", "education", "overall"]}

    # ── PROFILE: role + domain ──────────────────────────────────────────────
    job_profile = jd.get("job_profile") or {}
    role = job_profile.get("role")
    domain = job_profile.get("domain")
    if role:
        sections["profile"] += sentence_split(role)
    if domain:
        sections["profile"].append(norm(domain))

    # ── SKILLS: required + preferred + flattened tech_stack ───────────────
    skills = jd.get("skills") or {}
    for s in safe_list(skills.get("required")):
        sections["skills"].append(norm(s))
    for s in safe_list(skills.get("preferred")):
        sections["skills"].append(norm(s))

    tech_stack = jd.get("tech_stack") or {}
    for bucket in ("languages", "frameworks", "libraries", "databases", "cloud", "tools", "ai_techniques"):
        for item in safe_list(tech_stack.get(bucket)):
            sections["skills"].append(norm(item))

    # ── PROJECTS: use ai_techniques + frameworks as project-context proxy ──
    for item in safe_list(tech_stack.get("ai_techniques")):
        sections["projects"].append(norm(item))
    for item in safe_list(tech_stack.get("frameworks")):
        sections["projects"].append(norm(item))
    for item in safe_list(tech_stack.get("libraries")):
        sections["projects"].append(norm(item))

    # ── RESPONSIBILITIES: raw responsibility strings ────────────────────────
    for r in safe_list(jd.get("responsibilities")):
        sections["responsibilities"] += sentence_split(r)

    # ── EDUCATION: degrees + fields + certifications ────────────────────────
    edu_req = jd.get("education_requirements") or {}
    for d in safe_list(edu_req.get("degrees")):
        sections["education"].append(norm(d))
    for f in safe_list(edu_req.get("fields")):
        sections["education"].append(norm(f))
    for c in safe_list(jd.get("certifications")):
        sections["education"].append(norm(c))

    # ── OVERALL: role + required skills + top responsibilities ─────────────
    if role:
        sections["overall"].append(norm(role))
    for s in safe_list(skills.get("required"))[:20]:
        sections["overall"].append(norm(s))
    for r in safe_list(jd.get("responsibilities"))[:10]:
        sections["overall"] += sentence_split(r)

    # Deduplicate within each section while preserving order
    for k in sections:
        dedup, out = set(), []
        for s in sections[k]:
            key = s.lower().strip()
            if key and key not in dedup:
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
        
        # Generate embeddings for all sections in a single batch call
        results = {}
        section_names = ['profile', 'skills', 'projects', 'responsibilities', 'education', 'overall']
        
        flat_texts = []
        section_slices = {}
        
        for section in section_names:
            texts = sections.get(section, [])
            cleaned_texts = [t.strip() for t in texts if t and t.strip()]
            if cleaned_texts:
                start_idx = len(flat_texts)
                flat_texts.extend(cleaned_texts)
                end_idx = len(flat_texts)
                section_slices[section] = (start_idx, end_idx)
            else:
                section_slices[section] = None
        
        # Generate embeddings in one batch API call
        if flat_texts:
            print(f"📊 [EMBEDDING BATCHING] Flattened 6 Job Description sections into {len(flat_texts)} total strings. Sending 1 single API call to OpenAI.")
            flat_embeddings = await create_embeddings_batch_async(flat_texts)
            print(f"✅ [EMBEDDING BATCHING] Successfully generated {len(flat_embeddings)} embeddings in a single API call.")
        else:
            flat_embeddings = []
            
        for section in section_names:
            slice_info = section_slices.get(section)
            if slice_info is not None and flat_embeddings:
                start, end = slice_info
                results[f'{section}_embedding'] = flat_embeddings[start:end]
            else:
                results[f'{section}_embedding'] = []
        
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

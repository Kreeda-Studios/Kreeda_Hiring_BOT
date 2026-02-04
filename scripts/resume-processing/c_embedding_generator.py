#!/usr/bin/env python3
"""
Embedding Generator for Resumes

Generates vector embeddings for resume content using OpenAI embeddings.
Exact match with old archive SemanticComparitor.py logic.
"""

import os
import time
import random
import hashlib
import pickle
from pathlib import Path
from typing import Dict, Any, List, Optional
import numpy as np

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# Model configuration - exact match with old archive
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
EMBED_BATCH = 128
EMBED_RETRIES = 5
BACKOFF_BASE = 1.4
MAX_SENT = 200

# Cache for embeddings
EMBED_CACHE_PATH = Path(__file__).parent / ".semantic_embed_cache.pkl"

class EmbedCache:
    """Embedding cache - exact match with old archive"""
    def __init__(self, path: Path):
        self.path = path
        self._cache = {}
        if path.exists():
            try:
                self._cache = pickle.load(open(path, "rb"))
            except Exception:
                self._cache = {}

    def _key(self, text: str):
        return hashlib.sha256(f"{EMBEDDING_MODEL}||{text}".encode()).hexdigest()

    def get(self, text: str):
        return self._cache.get(self._key(text))

    def set(self, text: str, vec):
        self._cache[self._key(text)] = vec
        if len(self._cache) % 100 == 0:
            try:
                pickle.dump(self._cache, open(self.path, "wb"))
            except Exception:
                pass

    def close(self):
        try:
            pickle.dump(self._cache, open(self.path, "wb"))
        except Exception:
            pass

def get_openai_client():
    """Initialize OpenAI client"""
    if OpenAI is None:
        raise ImportError("openai library not installed. Run: pip install openai")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    return OpenAI(api_key=api_key)

def _embed_batch(client, texts: List[str]) -> List[List[float]]:
    """Generate embeddings for batch - exact match with old archive"""
    for attempt in range(1, EMBED_RETRIES + 1):
        try:
            res = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
            return [d.embedding for d in res.data]
        except Exception as e:
            if attempt == EMBED_RETRIES:
                raise RuntimeError(f"OpenAI embeddings failed: {e}")
            time.sleep((BACKOFF_BASE ** attempt) + random.random())

def embed_texts(cache: EmbedCache, client, texts: List[str]) -> np.ndarray:
    """Embed texts with caching - exact match with old archive"""
    if not texts: 
        return np.zeros((0, EMBEDDING_DIMENSION), dtype=np.float32)

    vecs = [None] * len(texts)
    todo, todo_i = [], []

    for i, t in enumerate(texts):
        c = cache.get(t)
        if c is None:
            todo.append(t)
            todo_i.append(i)
        else:
            vecs[i] = np.array(c, dtype=np.float32)

    for i in range(0, len(todo), EMBED_BATCH):
        batch = todo[i:i+EMBED_BATCH]
        emb = _embed_batch(client, batch)
        for j, vec in enumerate(emb):
            idx = todo_i[i+j]
            arr = np.array(vec, dtype=np.float32)
            n = np.linalg.norm(arr)
            if n > 0: 
                arr = arr / n
            vecs[idx] = arr
            cache.set(batch[j], arr.tolist())

    d = EMBEDDING_DIMENSION
    for i, v in enumerate(vecs):
        if v is None: 
            vecs[i] = np.zeros((d,), dtype=np.float32)

    M = np.vstack(vecs)
    M /= np.linalg.norm(M, axis=1, keepdims=True).clip(min=1e-9)
    return M.astype(np.float32)

def sentence_split(text: str) -> List[str]:
    """Split text into sentences - exact match with old archive"""
    if not text: 
        return []
    text = text.replace("\n", " ")
    parts = []
    start = 0
    for i, ch in enumerate(text):
        if ch in ".!?":
            seg = text[start:i+1].strip()
            if seg: 
                parts.append(seg)
            start = i+1
    tail = text[start:].strip()
    if tail: 
        parts.append(tail)
    return [p for p in parts if len(p.split()) >= 3]

def safe_list(x): 
    """Safe list conversion - exact match with old archive"""
    return x if isinstance(x, list) else []

def norm(s): 
    """Normalize text - exact match with old archive"""
    return s.strip()

def extract_sections_from_resume(resume: dict) -> Dict[str, List[str]]:
    """Extract resume sections - updated for new AI parser field names"""
    sections = {k: [] for k in ["profile","skills","projects","responsibilities","education","overall"]}

    # Profile - use summary instead of profile_keywords_line
    summary = resume.get("summary")
    if summary:
        if isinstance(summary, list):
            for s in summary:
                if s:
                    sections["profile"] += sentence_split(s)
        elif isinstance(summary, str):
            sections["profile"] += sentence_split(summary)

    # Skills - canonical and inferred (same structure)
    canonical = resume.get("canonical_skills") or {}
    for vals in canonical.values():
        if isinstance(vals, list):
            sections["skills"] += [norm(v) for v in vals if v]

    for inf in safe_list(resume.get("inferred_skills")):
        if inf.get("skill") and inf.get("confidence",0) >= 0.6:
            sections["skills"].append(norm(inf["skill"]))

    # Projects - use description instead of approach
    for proj in safe_list(resume.get("projects")):
        if proj.get("name"): 
            sections["projects"] += sentence_split(proj["name"])
        if proj.get("description"):  # Changed from 'approach'
            sections["projects"] += sentence_split(proj["description"])
        if proj.get("tech_keywords"): 
            sections["projects"] += [norm(x) for x in proj["tech_keywords"]]
        if proj.get("primary_skills"):  # Also use primary_skills
            sections["projects"] += [norm(x) for x in safe_list(proj["primary_skills"])]

    # Experience/Responsibilities - use experience instead of experience_entries
    for exp in safe_list(resume.get("experience")):  # Changed from 'experience_entries'
        if exp.get("description"):  # Use description instead of responsibilities_keywords
            sections["responsibilities"] += sentence_split(exp["description"])

    # Education (same structure)
    for e in safe_list(resume.get("education")):
        if isinstance(e, dict):
            # New structure: education is list of objects
            if e.get("degree"):
                sections["education"] += sentence_split(e["degree"])
            if e.get("field"):
                sections["education"] += sentence_split(e["field"])
            if e.get("institution"):
                sections["education"] += sentence_split(e["institution"])
        elif isinstance(e, str): 
            sections["education"] += sentence_split(e)

    # Overall section - combine key fields
    overall = []
    
    # Add summary to overall
    summary = resume.get("summary")
    if summary:
        if isinstance(summary, list):
            overall.extend(summary)
        elif isinstance(summary, str):
            overall.append(summary)
    
    # Add project descriptions to overall
    for proj in safe_list(resume.get("projects")):
        if proj.get("description"): 
            overall.append(proj["description"])
    
    # Add experience descriptions to overall
    for exp in safe_list(resume.get("experience")):
        if exp.get("description"):
            overall.append(exp["description"])
    
    # Convert overall to sentences
    sections["overall"] = [s for text in overall for s in sentence_split(text)]

    # Truncate sections to MAX_SENT
    for k in sections:
        if len(sections[k]) > MAX_SENT: 
            sections[k] = sections[k][:MAX_SENT]
    
    return sections

def generate_resume_embeddings(parsed_resume: Dict[str, Any]) -> Dict[str, Any]:
    """Generate resume embeddings using OpenAI - exact match with old archive"""
    try:
        client = get_openai_client()
        cache = EmbedCache(EMBED_CACHE_PATH)
        
        # Extract sections exactly like old archive
        resume_sections = extract_sections_from_resume(parsed_resume)
        
        # Generate embeddings for each section
        section_embeddings = {}
        section_texts = {}
        
        for section_name, section_texts_list in resume_sections.items():
            if section_texts_list:
                section_embeddings[section_name] = embed_texts(cache, client, section_texts_list)
                section_texts[section_name] = section_texts_list
            else:
                section_embeddings[section_name] = np.zeros((0, EMBEDDING_DIMENSION), dtype=np.float32)
                section_texts[section_name] = []
        
        cache.close()
        
        return {
            'success': True,
            'resume_sections': resume_sections,
            'section_embeddings': section_embeddings,
            'section_texts': section_texts,
            'model_used': EMBEDDING_MODEL,
            'dimension': EMBEDDING_DIMENSION
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Resume embedding generation failed: {str(e)}"
        }

def generate_skill_embeddings(parsed_resume: Dict[str, Any]) -> Dict[str, Any]:
    """Generate embeddings for different skill categories"""
    try:
        model = get_embedding_model()
        
        skill_embeddings = {}
        canonical_skills = parsed_resume.get('canonical_skills', {})
        
        # Generate embeddings for each skill category
        for category, skills in canonical_skills.items():
            if isinstance(skills, list) and skills:
                # Combine skills into text
                skills_text = ' '.join(skills)
                embedding = model.encode(skills_text, convert_to_tensor=False)
                skill_embeddings[category] = {
                    'embedding': embedding.tolist(),
                    'skills': skills,
                    'text': skills_text
                }
        
        # Generate embedding for all skills combined
        all_skills = parsed_resume.get('skills', [])
        if all_skills:
            all_skills_text = ' '.join(all_skills)
            embedding = model.encode(all_skills_text, convert_to_tensor=False)
            skill_embeddings['all_skills'] = {
                'embedding': embedding.tolist(),
                'skills': all_skills,
                'text': all_skills_text
            }
        
        return {
            'success': True,
            'skill_embeddings': skill_embeddings,
            'categories_processed': len(skill_embeddings)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Skill embedding generation failed: {str(e)}"
        }

def process_resume_embeddings(parsed_resume: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to generate all resume embeddings
    Returns: {
        'success': bool,
        'resume_embedding': list,
        'skill_embeddings': dict,
        'metadata': dict,
        'error': str or None
    }
    """
    try:
        start_time = time.time()
        
        # Generate main resume embedding
        resume_result = generate_resume_embeddings(parsed_resume)
        if not resume_result['success']:
            return resume_result
        
        # Generate skill embeddings
        skill_result = generate_skill_embeddings(parsed_resume)
        if not skill_result['success']:
            return skill_result
        
        total_time = time.time() - start_time
        
        return {
            'success': True,
            'resume_embedding': resume_result['resume_embedding'],
            'skill_embeddings': skill_result['skill_embeddings'],
            'metadata': {
                'model_used': EMBEDDING_MODEL,
                'embedding_dimension': EMBEDDING_DIMENSION,
                'total_processing_time': total_time,
                'resume_embedding_time': resume_result.get('processing_time', 0),
                'skill_categories': skill_result.get('categories_processed', 0)
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Resume embedding processing failed: {str(e)}"
        }
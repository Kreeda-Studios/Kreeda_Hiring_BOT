#!/usr/bin/env python3
"""
Resume Embedding Generator

Generates vector embeddings for resume sections using OpenAI text-embedding-3-small.
Matches old system logic for semantic scoring compatibility.
"""

import sys
import time
import random
import hashlib
import pickle
from pathlib import Path
from typing import Dict, Any, List
import numpy as np

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from openai_client import get_async_openai_client
import asyncio

# ============================================================================
# CONFIGURATION
# ============================================================================

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536
EMBED_BATCH = 128
EMBED_RETRIES = 5
BACKOFF_BASE = 1.4
MAX_SENT = 200

EMBED_CACHE_PATH = Path(__file__).parent / ".semantic_embed_cache.pkl"


# ============================================================================
# EMBEDDING CACHE
# ============================================================================

class EmbedCache:
    """Persistent cache for embeddings to avoid redundant API calls"""
    
    def __init__(self, path: Path):
        self.path = path
        self._cache = {}
        if path.exists():
            try:
                with open(path, "rb") as f:
                    self._cache = pickle.load(f)
            except Exception:
                self._cache = {}

    def _key(self, text: str) -> str:
        """Generate cache key from text and model name"""
        return hashlib.sha256(f"{EMBEDDING_MODEL}||{text}".encode()).hexdigest()

    def get(self, text: str):
        """Retrieve cached embedding for text"""
        return self._cache.get(self._key(text))

    def set(self, text: str, vec):
        """Store embedding in cache"""
        self._cache[self._key(text)] = vec
        if len(self._cache) % 100 == 0:
            self._save()

    def close(self):
        """Persist cache to disk"""
        self._save()
    
    def _save(self):
        """Internal save method"""
        try:
            with open(self.path, "wb") as f:
                pickle.dump(self._cache, f)
        except Exception:
            pass


# ============================================================================
# EMBEDDING GENERATION
# ============================================================================

async def _embed_batch(client, texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a batch of texts with retry logic
    
    Args:
        client: OpenAI client instance
        texts: List of text strings to embed
        
    Returns:
        List of embedding vectors
    """
    for attempt in range(1, EMBED_RETRIES + 1):
        try:
            response = await client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
            return [d.embedding for d in response.data]
        except Exception as e:
            if attempt == EMBED_RETRIES:
                raise RuntimeError(f"OpenAI embeddings failed after {EMBED_RETRIES} attempts: {e}")
            await asyncio.sleep((BACKOFF_BASE ** attempt) + random.random())


async def embed_texts(cache: EmbedCache, client, texts: List[str]) -> np.ndarray:
    """
    Generate embeddings for texts with caching and normalization
    
    Args:
        cache: Embedding cache instance
        client: OpenAI client instance
        texts: List of text strings to embed
        
    Returns:
        Normalized embedding matrix (N x EMBEDDING_DIMENSION)
    """
    if not texts:
        return np.zeros((0, EMBEDDING_DIMENSION), dtype=np.float32)

    vecs = [None] * len(texts)
    todo, todo_i = [], []

    # Check cache for existing embeddings
    for i, text in enumerate(texts):
        cached = cache.get(text)
        if cached is None:
            todo.append(text)
            todo_i.append(i)
        else:
            vecs[i] = np.array(cached, dtype=np.float32)

    # Generate embeddings for uncached texts in batches
    for i in range(0, len(todo), EMBED_BATCH):
        batch = todo[i:i + EMBED_BATCH]
        embeddings = await _embed_batch(client, batch)
        
        for j, vec in enumerate(embeddings):
            idx = todo_i[i + j]
            arr = np.array(vec, dtype=np.float32)
            norm = np.linalg.norm(arr)
            if norm > 0:
                arr = arr / norm
            vecs[idx] = arr
            cache.set(batch[j], arr.tolist())

    # Fill any missing vectors with zeros
    for i, v in enumerate(vecs):
        if v is None:
            vecs[i] = np.zeros(EMBEDDING_DIMENSION, dtype=np.float32)

    # Stack and normalize
    M = np.vstack(vecs)
    M /= np.linalg.norm(M, axis=1, keepdims=True).clip(min=1e-9)
    return M.astype(np.float32)


# ============================================================================
# TEXT PROCESSING UTILITIES
# ============================================================================

def sentence_split(text: str) -> List[str]:
    """
    Split text into sentences on punctuation marks
    
    Args:
        text: Input text string
        
    Returns:
        List of sentences with at least 3 words each
    """
    if not text:
        return []
    
    text = text.replace("\n", " ")
    parts = []
    start = 0
    
    for i, ch in enumerate(text):
        if ch in ".!?":
            seg = text[start:i + 1].strip()
            if seg:
                parts.append(seg)
            start = i + 1
    
    tail = text[start:].strip()
    if tail:
        parts.append(tail)
    
    return [p for p in parts if len(p.split()) >= 3]


def safe_list(x):
    """Convert to list if not already a list, otherwise return empty list"""
    return x if isinstance(x, list) else []


def norm(s):
    """Normalize string by stripping whitespace"""
    return s.strip() if isinstance(s, str) else ""


# ============================================================================
# RESUME SECTION EXTRACTION
# ============================================================================

def extract_sections_from_resume(resume: dict) -> Dict[str, List[str]]:
    """
    Extract text sections from parsed resume for embedding generation
    
    Field mappings match AI parser schema:
    - profile_keywords_line → profile section
    - canonical_skills + inferred_skills → skills section
    - projects.approach + projects.tech_keywords → projects section
    - experience_entries.responsibilities_keywords + achievements → responsibilities section
    - education → education section
    - Combined fields → overall section
    
    Args:
        resume: Parsed resume dictionary from AI parser
        
    Returns:
        Dictionary with 6 section keys, each containing list of text strings
    """
    sections = {k: [] for k in ["profile", "skills", "projects", "responsibilities", "education", "overall"]}

    # Profile section
    profile_line = resume.get("profile_keywords_line")
    if profile_line:
        sections["profile"] += sentence_split(profile_line)

    # Skills section: canonical + inferred (confidence >= 0.6)
    canonical = resume.get("canonical_skills") or {}
    for skill_list in canonical.values():
        if isinstance(skill_list, list):
            sections["skills"] += [norm(v) for v in skill_list if v]

    for inferred in safe_list(resume.get("inferred_skills")):
        if inferred.get("skill") and inferred.get("confidence", 0) >= 0.6:
            sections["skills"].append(norm(inferred["skill"]))

    # Projects section: name + approach + tech_keywords
    for proj in safe_list(resume.get("projects")):
        if proj.get("name"):
            sections["projects"] += sentence_split(proj["name"])
        if proj.get("approach"):
            sections["projects"] += sentence_split(proj["approach"])
        if proj.get("tech_keywords"):
            sections["projects"] += [norm(x) for x in proj["tech_keywords"]]

    # Responsibilities section: responsibilities + achievements + primary_tech
    for exp in safe_list(resume.get("experience_entries")):
        for resp in safe_list(exp.get("responsibilities_keywords")):
            if resp:
                sections["responsibilities"] += sentence_split(resp)
        for ach in safe_list(exp.get("achievements")):
            if ach:
                sections["responsibilities"] += sentence_split(ach)
        for tech in safe_list(exp.get("primary_tech")):
            if tech:
                sections["responsibilities"].append(norm(tech))

    # Education section: string entries only
    for edu in safe_list(resume.get("education")):
        if isinstance(edu, str):
            sections["education"] += sentence_split(edu)

    # Fallback: use ats_boost_line for empty education
    ats = resume.get("ats_boost_line") or ""
    if ats and not sections["education"]:
        parts = [x.strip() for x in ats.split(",") if x.strip()]
        sections["education"] += parts[:20]

    # Overall section: comprehensive combination
    overall_parts = []
    if resume.get("profile_keywords_line"):
        overall_parts.append(resume["profile_keywords_line"])
    for proj in safe_list(resume.get("projects")):
        if proj.get("approach"):
            overall_parts.append(proj["approach"])
    for exp in safe_list(resume.get("experience_entries")):
        if exp.get("responsibilities_keywords"):
            overall_parts += exp["responsibilities_keywords"]
    if ats:
        overall_parts.append(ats)
    sections["overall"] = [s for part in overall_parts for s in sentence_split(part)]

    # Truncate all sections to MAX_SENT
    for key in sections:
        if len(sections[key]) > MAX_SENT:
            sections[key] = sections[key][:MAX_SENT]

    return sections


# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def generate_resume_embeddings(parsed_resume: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate embeddings for all resume sections
    
    Args:
        parsed_resume: Parsed resume dictionary from AI parser
        
    Returns:
        Dictionary containing:
        - success: bool
        - section_embeddings: dict with 6 section keys, each with embedding matrix
        - section_texts: dict with original text lists per section
        - model_used: str
        - dimension: int
        - error: str (if success=False)
    """
    try:
        client = get_async_openai_client()
        cache = EmbedCache(EMBED_CACHE_PATH)

        resume_sections = extract_sections_from_resume(parsed_resume)

        section_embeddings = {}
        section_texts = {}

        for section_name, text_list in resume_sections.items():
            if text_list:
                section_embeddings[section_name] = await embed_texts(cache, client, text_list)
                section_texts[section_name] = text_list
            else:
                section_embeddings[section_name] = np.zeros((0, EMBEDDING_DIMENSION), dtype=np.float32)
                section_texts[section_name] = []

        cache.close()

        return {
            'success': True,
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
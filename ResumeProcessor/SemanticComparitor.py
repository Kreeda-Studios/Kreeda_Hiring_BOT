#!/usr/bin/env python3
"""
SemanticComparitor.py (updated to use OpenAI embeddings)

Behavior preserved:
- Reads JD JSON from InputThread/JD/*.json (first found)
- Reads resume JSONs from ../ProcessedJson
- Computes section-level semantic matching, aggregates into Semantic_Score (0..1)
- Merges Semantic_Score into Ranking/Scores.json
- Prints / logs top results (keeps same output structure)

Embedding change:
- Replaced sentence-transformers with OpenAI embeddings (text-embedding-3-small by default)
- Added cache (pickle) to avoid re-embedding identical strings
- Batch requests and exponential backoff retries
"""
import json
import sys
import os
import hashlib
import pickle
import tempfile
import time
import random
from pathlib import Path
from typing import List, Dict, Tuple
from tqdm import tqdm
import streamlit as st

import numpy as np

# Attempt to import openai. If missing, error out with a helpful message.
try:
    import openai
except Exception as e:
    print("❌ The 'openai' package is required for this updated script. Please `pip install openai`.", file=sys.stderr)
    raise

# -----------------------
# Config / Paths
# -----------------------
EMBEDDING_MODEL = "text-embedding-3-small"  # smaller, faster, lower-cost good default. Change if needed.
EMBED_BATCH = 128
EMBED_RETRIES = 5
EMBED_BACKOFF_BASE = 1.2

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent  # assumes repo layout unchanged
PROCESSED_JSON_DIR = (ROOT_DIR / "ProcessedJson").resolve()
JD_DIR = (ROOT_DIR / "InputThread" / "JD").resolve()
SCORES_FILE = Path("Ranking/Scores.json")

# Local embedding cache file (pickle-backed dict) to avoid re-embedding text repeatedly
EMBED_CACHE_PATH = SCRIPT_DIR / ".semantic_embed_cache.pkl"

# Thresholds & weights (same as before)
TAU_COV = 0.65      # JD sentence coverage threshold
TAU_RESUME = 0.55   # resume-side threshold
SECTION_COMB = (0.5, 0.4, 0.1)  # (coverage, depth, density)

SECTION_WEIGHTS = {
    "skills": 0.30,
    "projects": 0.25,
    "responsibilities": 0.20,
    "profile": 0.10,
    "education": 0.05,
    "overall": 0.10
}

MAX_SENT_PER_SECTION = 200  # safety cap

# -----------------------
# Utilities: embed cache
# -----------------------
class EmbedCache:
    def __init__(self, path: Path):
        self.path = path
        self._cache = {}
        if path.exists():
            try:
                with path.open("rb") as f:
                    self._cache = pickle.load(f)
            except Exception:
                self._cache = {}

    def _key(self, text: str, model: str) -> str:
        key_raw = f"{model}||{text}"
        return hashlib.sha256(key_raw.encode("utf-8")).hexdigest()

    def get(self, text: str, model: str):
        k = self._key(text, model)
        v = self._cache.get(k)
        if v is None:
            return None
        # restore numpy array (stored as list or array)
        arr = np.asarray(v, dtype=np.float32)
        # normalize defensively
        norm = np.linalg.norm(arr)
        if norm > 0:
            return (arr / norm).astype(np.float32)
        return arr.astype(np.float32)

    def set(self, text: str, model: str, vector: np.ndarray):
        k = self._key(text, model)
        # store as list to be robust across pickle versions
        self._cache[k] = vector.astype(np.float32).tolist()
        # occasional flush (every 1000 entries)
        if len(self._cache) % 1000 == 0:
            self.flush()

    def flush(self):
        tmp = tempfile.NamedTemporaryFile(delete=False)
        try:
            with open(tmp.name, "wb") as f:
                pickle.dump(self._cache, f, protocol=pickle.HIGHEST_PROTOCOL)
            os.replace(tmp.name, self.path)
        except Exception:
            pass

    def close(self):
        try:
            with self.path.open("wb") as f:
                pickle.dump(self._cache, f, protocol=pickle.HIGHEST_PROTOCOL)
        except Exception:
            pass

# -----------------------
# Helpers: text processing
# -----------------------
def norm(s: str) -> str:
    return s.strip()

def sentence_split(text: str) -> List[str]:
    if not text:
        return []
    text = text.replace("\r\n", " ").replace("\n", " ")
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
    parts = [p for p in parts if len(p.split()) >= 3]
    return parts

def safe_list_extract(x):
    return x if isinstance(x, list) else []

# -----------------------
# Section extractor
# (kept identical to original logic)
# -----------------------
def extract_sections_from_resume(resume: dict) -> Dict[str, List[str]]:
    sections = {
        "profile": [],
        "skills": [],
        "projects": [],
        "responsibilities": [],
        "education": [],
        "overall": []
    }

    p = resume.get("profile_keywords_line") or ""
    if p:
        sections["profile"].extend(sentence_split(p))

    canonical = resume.get("canonical_skills") or {}
    skills_tokens = []
    for vals in canonical.values():
        if isinstance(vals, list):
            skills_tokens.extend([norm(t) for t in vals if t])
    for inf in safe_list_extract(resume.get("inferred_skills") or []):
        if inf.get("skill") and inf.get("confidence", 0) >= 0.6:
            skills_tokens.append(norm(inf.get("skill")))
    sections["skills"].extend(skills_tokens)

    for proj in safe_list_extract(resume.get("projects") or []):
        name = proj.get("name") or ""
        approach = proj.get("approach") or ""
        tk = proj.get("tech_keywords") or []
        if name:
            sections["projects"].extend(sentence_split(name))
        if approach:
            sections["projects"].extend(sentence_split(approach))
        if tk:
            sections["projects"].extend([norm(x) for x in tk if x])

    for exp in safe_list_extract(resume.get("experience_entries") or []):
        for r in safe_list_extract(exp.get("responsibilities_keywords") or []):
            if r:
                sections["responsibilities"].extend(sentence_split(r))
        for a in safe_list_extract(exp.get("achievements") or []):
            if a:
                sections["responsibilities"].extend(sentence_split(a))
        for t in safe_list_extract(exp.get("primary_tech") or []):
            if t:
                sections["responsibilities"].append(norm(t))

    edu = resume.get("education") or []
    for e in safe_list_extract(edu):
        if isinstance(e, str) and e.strip():
            sections["education"].extend(sentence_split(e))

    ats = resume.get("ats_boost_line") or ""
    if ats and not sections["education"]:
        parts = [p.strip() for p in ats.split(",") if p.strip()]
        sections["education"].extend(parts[:20])

    overall_parts = []
    if resume.get("profile_keywords_line"):
        overall_parts.append(resume.get("profile_keywords_line"))
    for proj in safe_list_extract(resume.get("projects") or []):
        if proj.get("approach"):
            overall_parts.append(proj.get("approach"))
    for exp in safe_list_extract(resume.get("experience_entries") or []):
        if exp.get("responsibilities_keywords"):
            overall_parts.extend([r for r in exp.get("responsibilities_keywords") if r])
    if ats:
        overall_parts.append(ats)
    sections["overall"].extend([s for p in overall_parts for s in sentence_split(p)])

    for k in sections:
        if len(sections[k]) > MAX_SENT_PER_SECTION:
            sections[k] = sections[k][:MAX_SENT_PER_SECTION]

    return sections

# -----------------------
# JD extractor (unchanged)
# -----------------------
def extract_sections_from_jd(jd: dict) -> Dict[str, List[str]]:
    sections = {
        "profile": [],
        "skills": [],
        "projects": [],
        "responsibilities": [],
        "education": [],
        "overall": []
    }

    profile_texts = []
    if jd.get("role_title"):
        profile_texts.append(jd.get("role_title"))
    if jd.get("embedding_hints", {}) and jd["embedding_hints"].get("overall_embed"):
        profile_texts.append(jd["embedding_hints"]["overall_embed"])
    if jd.get("responsibilities"):
        for r in jd.get("responsibilities"):
            if isinstance(r, str):
                sections["responsibilities"].extend(sentence_split(r))
    if jd.get("required_skills"):
        sections["skills"].extend([norm(x) for x in jd.get("required_skills")])
    if jd.get("preferred_skills"):
        sections["skills"].extend([norm(x) for x in jd.get("preferred_skills")])
    if jd.get("embedding_hints", {}).get("projects_embed"):
        sections["projects"].extend(sentence_split(jd["embedding_hints"]["projects_embed"]))
    if jd.get("certifications_required"):
        sections["education"].extend([norm(x) for x in jd.get("certifications_required")])
    if jd.get("education_requirements"):
        sections["education"].extend([norm(x) for x in jd.get("education_requirements")])
    if jd.get("embedding_hints", {}).get("overall_embed"):
        sections["overall"].extend(sentence_split(jd["embedding_hints"]["overall_embed"]))
    if not sections["skills"] and jd.get("keywords_flat"):
        sections["skills"].extend([norm(x) for x in jd.get("keywords_flat")])
    if jd.get("role_title"):
        sections["profile"].extend(sentence_split(jd.get("role_title")))
    if jd.get("alt_titles"):
        sections["profile"].extend([norm(x) for x in jd.get("alt_titles") if isinstance(x, str)])

    for k in sections:
        seen = set()
        out = []
        for s in sections[k]:
            if not s: continue
            key = s.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(s)
        sections[k] = out

    return sections

# -----------------------
# Embedding helpers (OpenAI)
# -----------------------
def _openai_embed_texts(batch_texts: List[str], model: str) -> List[List[float]]:
    """
    Call OpenAI Embeddings API for a list of texts. Implements retry/backoff.
    Returns list of embedding vectors (list of floats) in same order.
    """
    attempt = 0
    while True:
        try:
            resp = openai.Embedding.create(model=model, input=batch_texts)
            # response.data is a list with 'embedding' field
            embeddings = [d["embedding"] for d in resp["data"]]
            return embeddings
        except Exception as e:
            attempt += 1
            if attempt > EMBED_RETRIES:
                raise RuntimeError(f"OpenAI Embeddings failed after {EMBED_RETRIES} tries: {e}")
            backoff = (EMBED_BACKOFF_BASE ** attempt) + random.random()
            time.sleep(backoff)

def embed_texts(cache: EmbedCache, texts: List[str]) -> np.ndarray:
    """
    Returns (n_texts, dim) normalized embeddings using OpenAI, using cache where possible.
    """
    if not texts:
        return np.zeros((0, 1536), dtype=np.float32)  # fallback shape; will be resized as needed

    vectors = [None] * len(texts)
    to_embed = []
    to_embed_idx = []
    for i, t in enumerate(texts):
        t_norm = t.strip()
        v = cache.get(t_norm, EMBEDDING_MODEL)
        if v is None:
            to_embed.append(t_norm)
            to_embed_idx.append(i)
        else:
            vectors[i] = v

    if to_embed:
        # batch up
        for i in range(0, len(to_embed), EMBED_BATCH):
            batch = to_embed[i:i+EMBED_BATCH]
            emb_lists = _openai_embed_texts(batch, EMBEDDING_MODEL)
            for j, emb in enumerate(emb_lists):
                idx = to_embed_idx[i + j]
                arr = np.asarray(emb, dtype=np.float32)
                # normalize
                norm = np.linalg.norm(arr)
                if norm > 0:
                    arr = arr / norm
                vectors[idx] = arr
                cache.set(batch[j], EMBEDDING_MODEL, arr)

    # if any remaining None (shouldn't happen), set zero vector with detected dim
    dims = [v.shape[0] for v in vectors if v is not None]
    if dims:
        d = dims[0]
    else:
        # as safe fallback use 1536
        d = 1536
    for i, v in enumerate(vectors):
        if v is None:
            vectors[i] = np.zeros((d,), dtype=np.float32)

    arr = np.vstack(vectors).astype(np.float32)
    # ensure normalization (should be normalized already)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    arr = arr / norms
    return arr

def cosine_sim_matrix(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    """Compute cosine similarity matrix between a (m x d) and b (n x d) -> m x n"""
    # both assumed normalized rows
    if a.size == 0 or b.size == 0:
        return np.zeros((a.shape[0], b.shape[0]), dtype=np.float32)
    return np.matmul(a, b.T)

# -----------------------
# Section scoring (unchanged)
# -----------------------
def compute_section_score(jd_emb: np.ndarray, resume_emb: np.ndarray) -> Tuple[float, float, float, List[Tuple[int, int, float]]]:
    if jd_emb.shape[0] == 0:
        return 0.5, 0.0, 0.0, []
    if resume_emb.shape[0] == 0:
        return 0.0, 0.0, 0.0, []

    C = cosine_sim_matrix(jd_emb, resume_emb)  # (m x n)
    max_per_jd = C.max(axis=1)  # best resume sim per jd sentence
    coverage = float((max_per_jd >= TAU_COV).sum()) / max(1, len(max_per_jd))
    depth = float(max_per_jd.mean())
    max_per_resume = C.max(axis=0)
    density = float((max_per_resume >= TAU_RESUME).sum()) / max(1, resume_emb.shape[0])

    alpha, beta, gamma = SECTION_COMB
    section_score = alpha * coverage + beta * depth + gamma * density

    matches = []
    for j_idx in range(C.shape[0]):
        r_idx = int(C[j_idx].argmax())
        matches.append((j_idx, r_idx, float(C[j_idx, r_idx])))

    return section_score, coverage, depth, matches

# -----------------------
# Main flow (preserved)
# -----------------------
def main():
    # sanity checks
    if not PROCESSED_JSON_DIR.exists():
        print(f"❌ ProcessedJson dir not found: {PROCESSED_JSON_DIR}", file=sys.stderr)
        sys.exit(1)

    # load JD
    jd_files = list(JD_DIR.glob("*.json"))
    if not jd_files:
        print(f"❌ No JD JSON found in {JD_DIR}. Run JDGpt.py first.", file=sys.stderr)
        sys.exit(1)
    jd_path = jd_files[0]
    with jd_path.open("r", encoding="utf-8") as f:
        jd = json.load(f)

    jd_sections = extract_sections_from_jd(jd)

    # gather resume files
    resume_files = sorted([p for p in PROCESSED_JSON_DIR.glob("*.json")])
    if not resume_files:
        print("⚠️ No resume JSON files found. Exiting.", file=sys.stderr)
        sys.exit(0)

    # Configure openai from environment if available
    openai_api_key = st.secrets.get("OPENAI_API_KEY")
    if not openai_api_key:
        # If user uses AzureOpenAI or different config, OpenAI client may still work if env is set appropriately.
        print("⚠️ OPENAI_API_KEY not found in environment. OpenAI embeddings may fail.", file=sys.stderr)
    else:
        openai.api_key = openai_api_key

    cache = EmbedCache(EMBED_CACHE_PATH)

    # Pre-embed JD section sentences once
    jd_embeds = {}
    jd_texts = {}
    for sec, sents in jd_sections.items():
        jd_texts[sec] = [norm(s) for s in sents]
        if jd_texts[sec]:
            jd_embeds[sec] = embed_texts(cache, jd_texts[sec])
        else:
            jd_embeds[sec] = np.zeros((0, 1536), dtype=np.float32)

    # load existing scores
    if SCORES_FILE.exists():
        try:
            with SCORES_FILE.open("r", encoding="utf-8") as f:
                existing_scores = json.load(f)
        except Exception:
            existing_scores = []
    else:
        existing_scores = []

    existing_map = {e.get("name"): e for e in existing_scores if isinstance(e, dict)}

    candidate_results = []
    # iterate resumes streaming to avoid memory spikes
    for rpath in tqdm(resume_files, desc="Resumes"):
        try:
            with rpath.open("r", encoding="utf-8") as f:
                resume = json.load(f)
        except Exception as e:
            print(f"⚠️ Failed to load {rpath}: {e}", file=sys.stderr)
            continue

        raw_name = resume.get("name") or rpath.stem
        name = " ".join(raw_name.strip().title().split())

        sections = extract_sections_from_resume(resume)

        # per-section embeddings for resume
        sec_emb = {}
        sec_texts = {}
        for sec in jd_sections.keys():
            texts = sections.get(sec) or []
            texts = [t for t in texts if t and isinstance(t, str)]
            sec_texts[sec] = texts
            if texts:
                sec_emb[sec] = embed_texts(cache, texts)
            else:
                sec_emb[sec] = np.zeros((0, 1536), dtype=np.float32)

        # compute section scores & explainability top matches
        section_scores = {}
        section_matches = {}
        for sec in jd_sections.keys():
            jd_e = jd_embeds.get(sec)
            resume_e = sec_emb.get(sec)
            s_score, coverage, depth, matches = compute_section_score(jd_e, resume_e)
            section_scores[sec] = {
                "score": round(float(s_score), 3),
                "coverage": round(float(coverage), 3),
                "depth": round(float(depth), 3)
            }
            top_matches = []
            for j_idx, r_idx, sim in matches:
                jd_txt = jd_texts.get(sec, [])[j_idx] if jd_texts.get(sec) and j_idx < len(jd_texts[sec]) else ""
                res_txt = sec_texts.get(sec, [])[r_idx] if sec_texts.get(sec) and r_idx < len(sec_texts[sec]) else ""
                top_matches.append({"jd": jd_txt, "resume": res_txt, "sim": round(sim, 3)})
            section_matches[sec] = top_matches[:5]

        # aggregate raw score
        raw = 0.0
        for sec, w in SECTION_WEIGHTS.items():
            sec_score = section_scores.get(sec, {}).get("score", 0.5)
            raw += sec_score * w
        raw = float(raw)

        candidate_results.append({
            "name": name,
            "raw_score": raw,
            "section_scores": section_scores,
            "section_matches": section_matches,
            "project_aggregate": existing_map.get(name, {}).get("project_aggregate")
        })

    # persist cache
    cache.close()

    # Normalize raw scores to 0..1 with min-max to produce Semantic_Score
    raws = [c["raw_score"] for c in candidate_results]
    if raws:
        mn, mx = min(raws), max(raws)
        if mx > mn:
            for c in candidate_results:
                c["Semantic_Score"] = round((c["raw_score"] - mn) / (mx - mn), 3)
        else:
            for c in candidate_results:
                c["Semantic_Score"] = round(1.0, 3)
    else:
        print("⚠️ No candidates processed.", file=sys.stderr)
        sys.exit(0)

    # Print top 10 for logging (keeps parity with original)
    for c in sorted(candidate_results, key=lambda x: x["Semantic_Score"], reverse=True)[:10]:
        name = c["name"]
        sem = c["Semantic_Score"]
        proj = c.get("project_aggregate")
        keyword = existing_map.get(name, {}).get("Keyword_Score")
        print(f"✅ {name} | Semantic_Score={sem} | Keyword_Score={keyword} | project_aggregate={proj}")

    # Merge into SCORES_FILE: update existing entries or append new ones
    out_map = {e.get("name"): e for e in existing_scores if isinstance(e, dict)}
    for c in candidate_results:
        name = c["name"]
        sem = c["Semantic_Score"]
        if name in out_map:
            out_map[name]["Semantic_Score"] = sem
        else:
            out_map[name] = {
                "name": name,
                "project_aggregate": c.get("project_aggregate"),
                "Keyword_Score": out_map.get(name, {}).get("Keyword_Score"),
                "Semantic_Score": sem
            }

    # write atomically
    tmp_file = SCORES_FILE.with_suffix(".tmp")
    try:
        with tmp_file.open("w", encoding="utf-8") as f:
            json.dump(list(out_map.values()), f, indent=4)
        os.replace(tmp_file, SCORES_FILE)
        print(f"\n📂 Semantic scores written to {SCORES_FILE}")
    except Exception as e:
        print(f"❌ Failed to write scores: {e}", file=sys.stderr)
        if tmp_file.exists():
            try:
                tmp_file.unlink()
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()

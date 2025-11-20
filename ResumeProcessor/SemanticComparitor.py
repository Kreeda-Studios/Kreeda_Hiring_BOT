#!/usr/bin/env python3
"""
SemanticComparitor.py — OpenAI embeddings upgrade (drop-in replacement)

This script is 100% pipeline-compatible:
- same inputs, same outputs, same JSON fields
- same flow, scoring & file paths
- only embedding engine changed to OpenAI text-embedding-3-small
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
import numpy as np

from openai import OpenAI   # NEW API
client = None               # created in main()

# -----------------------
# Config / Paths (unchanged)
# -----------------------
EMBEDDING_MODEL = "text-embedding-3-small"
EMBED_BATCH = 128
EMBED_RETRIES = 5
BACKOFF_BASE = 1.4

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DIR = SCRIPT_DIR.parent
PROCESSED_JSON_DIR = (ROOT_DIR / "ProcessedJson").resolve()
JD_DIR = (ROOT_DIR / "InputThread" / "JD").resolve()
SCORES_FILE = Path("Ranking/Scores.json")
EMBED_CACHE_PATH = SCRIPT_DIR / ".semantic_embed_cache.pkl"

TAU_COV = 0.65
TAU_RESUME = 0.55
SECTION_COMB = (0.5, 0.4, 0.1)
SECTION_WEIGHTS = {
    "skills": 0.30, "projects": 0.25, "responsibilities": 0.20,
    "profile": 0.10, "education": 0.05, "overall": 0.10
}
MAX_SENT = 200

# -----------------------
# Cache
# -----------------------
class EmbedCache:
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
        if len(self._cache) % 1000 == 0:
            pickle.dump(self._cache, open(self.path, "wb"))

    def close(self):
        pickle.dump(self._cache, open(self.path, "wb"))

# -----------------------
# Text helpers
# -----------------------
def norm(s): return s.strip()

def sentence_split(text: str):
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

def safe_list(x): return x if isinstance(x, list) else []

# -----------------------
# JSON → sections (unchanged)
# -----------------------
def extract_sections_from_resume(resume: dict) -> Dict[str, List[str]]:
    sections = {k: [] for k in ["profile","skills","projects","responsibilities","education","overall"]}

    p = resume.get("profile_keywords_line")
    if p: sections["profile"] += sentence_split(p)

    canonical = resume.get("canonical_skills") or {}
    for vals in canonical.values():
        if isinstance(vals, list):
            sections["skills"] += [norm(v) for v in vals if v]

    for inf in safe_list(resume.get("inferred_skills")):
        if inf.get("skill") and inf.get("confidence",0) >= 0.6:
            sections["skills"].append(norm(inf["skill"]))

    for proj in safe_list(resume.get("projects")):
        if proj.get("name"): sections["projects"] += sentence_split(proj["name"])
        if proj.get("approach"): sections["projects"] += sentence_split(proj["approach"])
        if proj.get("tech_keywords"): sections["projects"] += [norm(x) for x in proj["tech_keywords"]]

    for exp in safe_list(resume.get("experience_entries")):
        for r in safe_list(exp.get("responsibilities_keywords")):
            if r: sections["responsibilities"] += sentence_split(r)
        for a in safe_list(exp.get("achievements")):
            if a: sections["responsibilities"] += sentence_split(a)
        for t in safe_list(exp.get("primary_tech")):
            if t: sections["responsibilities"].append(norm(t))

    for e in safe_list(resume.get("education")):
        if isinstance(e, str): sections["education"] += sentence_split(e)

    ats = resume.get("ats_boost_line") or ""
    if ats and not sections["education"]:
        parts = [x.strip() for x in ats.split(",") if x.strip()]
        sections["education"] += parts[:20]

    overall = []
    if resume.get("profile_keywords_line"): overall.append(resume["profile_keywords_line"])
    for proj in safe_list(resume.get("projects")):
        if proj.get("approach"): overall.append(proj["approach"])
    for exp in safe_list(resume.get("experience_entries")):
        if exp.get("responsibilities_keywords"):
            overall += exp["responsibilities_keywords"]
    if ats: overall.append(ats)
    sections["overall"] = [s for p in overall for s in sentence_split(p)]

    for k in sections:
        if len(sections[k]) > MAX_SENT: sections[k] = sections[k][:MAX_SENT]
    return sections

def extract_sections_from_jd(jd: dict):
    sections = {k: [] for k in ["profile","skills","projects","responsibilities","education","overall"]}

    if jd.get("role_title"): sections["profile"] += sentence_split(jd["role_title"])
    if jd.get("embedding_hints", {}).get("overall_embed"):
        sections["overall"] += sentence_split(jd["embedding_hints"]["overall_embed"])
    if jd.get("responsibilities"):
        for r in jd["responsibilities"]: sections["responsibilities"] += sentence_split(r)
    if jd.get("required_skills"):
        sections["skills"] += [norm(x) for x in jd["required_skills"]]
    if jd.get("preferred_skills"):
        sections["skills"] += [norm(x) for x in jd["preferred_skills"]]
    if jd.get("embedding_hints", {}).get("projects_embed"):
        sections["projects"] += sentence_split(jd["embedding_hints"]["projects_embed"])
    if jd.get("certifications_required"):
        sections["education"] += [norm(x) for x in jd["certifications_required"]]
    if jd.get("education_requirements"):
        sections["education"] += [norm(x) for x in jd["education_requirements"]]
    if jd.get("keywords_flat") and not sections["skills"]:
        sections["skills"] += [norm(x) for x in jd["keywords_flat"]]

    for k in sections:
        dedup, out = set(), []
        for s in sections[k]:
            key = s.lower().strip()
            if key not in dedup:
                dedup.add(key)
                out.append(s)
        sections[k] = out

    return sections

# -----------------------
# OpenAI embeddings (new)
# -----------------------
def _embed_batch(texts: List[str]) -> List[List[float]]:
    for attempt in range(1, EMBED_RETRIES + 1):
        try:
            res = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
            return [d.embedding for d in res.data]
        except Exception as e:
            if attempt == EMBED_RETRIES:
                raise RuntimeError(f"OpenAI embeddings failed: {e}")
            time.sleep((BACKOFF_BASE ** attempt) + random.random())

def embed_texts(cache: EmbedCache, texts: List[str]) -> np.ndarray:
    if not texts: return np.zeros((0,1536),dtype=np.float32)

    vecs = [None] * len(texts)
    todo, todo_i = [], []

    for i,t in enumerate(texts):
        c = cache.get(t)
        if c is None:
            todo.append(t); todo_i.append(i)
        else:
            vecs[i] = np.array(c,dtype=np.float32)

    for i in range(0,len(todo),EMBED_BATCH):
        batch = todo[i:i+EMBED_BATCH]
        emb = _embed_batch(batch)
        for j,vec in enumerate(emb):
            idx = todo_i[i+j]
            arr = np.array(vec,dtype=np.float32)
            n = np.linalg.norm(arr)
            if n>0: arr = arr/n
            vecs[idx] = arr
            cache.set(batch[j], arr.tolist())

    d = vecs[0].shape[0]
    for i,v in enumerate(vecs):
        if v is None: vecs[i] = np.zeros((d,),dtype=np.float32)

    M = np.vstack(vecs)
    M /= np.linalg.norm(M,axis=1,keepdims=True).clip(min=1e-9)
    return M.astype(np.float32)

# -----------------------
# Scoring
# -----------------------
def cosine_sim(a,b): return np.matmul(a,b.T)

def compute_section_score(jd, resume):
    if jd.size==0: return 0.5,0,0,[]
    if resume.size==0: return 0,0,0,[]
    C = cosine_sim(jd,resume)
    max_j = C.max(axis=1)
    cov = float((max_j>=TAU_COV).sum()) / len(max_j)
    depth = float(max_j.mean())
    max_r = C.max(axis=0)
    dens = float((max_r>=TAU_RESUME).sum()) / max(1,len(max_r))
    sec = SECTION_COMB[0]*cov + SECTION_COMB[1]*depth + SECTION_COMB[2]*dens
    matches = [(j,int(C[j].argmax()),float(C[j].max())) for j in range(C.shape[0])]
    return sec,cov,depth,matches

# -----------------------
# Main (drop-in)
# -----------------------
def main():
    global client
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if not PROCESSED_JSON_DIR.exists():
        print("❌ No ProcessedJson folder", file=sys.stderr); sys.exit(1)

    jd_files = list(JD_DIR.glob("*.json"))
    if not jd_files:
        print("❌ No JD JSON found", file=sys.stderr); sys.exit(1)
    jd = json.load(open(jd_files[0],"r",encoding="utf-8"))
    jd_secs = extract_sections_from_jd(jd)

    resumes = sorted(PROCESSED_JSON_DIR.glob("*.json"))
    if not resumes:
        print("⚠️ No resumes found"); sys.exit(0)

    cache = EmbedCache(EMBED_CACHE_PATH)

    jd_emb = {}; jd_txt = {}
    for sec,txts in jd_secs.items():
        jd_txt[sec] = txts
        jd_emb[sec] = embed_texts(cache, txts) if txts else np.zeros((0,1536),dtype=np.float32)

    existing = json.load(open(SCORES_FILE)) if SCORES_FILE.exists() else []
    existing_map = {e.get("name"):e for e in existing}

    out = []
    for r in tqdm(resumes, desc="Resumes"):
        resume = json.load(open(r,"r",encoding="utf-8"))
        raw_name = resume.get("name") or r.stem
        name = " ".join(raw_name.strip().title().split())
        secs = extract_sections_from_resume(resume)

        sec_emb, sec_txt = {}, {}
        for sec in jd_secs.keys():
            arr = secs.get(sec,[])
            sec_txt[sec] = arr
            sec_emb[sec] = embed_texts(cache,arr) if arr else np.zeros((0,1536),dtype=np.float32)

        sec_scores = {}; sec_matches = {}
        total = 0.0
        for sec,w in SECTION_WEIGHTS.items():
            s,c,d,m = compute_section_score(jd_emb[sec],sec_emb[sec])
            total += s*w
            sec_scores[sec] = {"score":round(s,3),"coverage":round(c,3),"depth":round(d,3)}
            sec_matches[sec] = m[:5]

        out.append({
            "name": name,
            "raw": total,
            "project_aggregate": existing_map.get(name,{}).get("project_aggregate"),
            "Keyword_Score": existing_map.get(name,{}).get("Keyword_Score"),
            "_internal": sec_scores
        })

    cache.close()

    raws = [x["raw"] for x in out]
    mn,mx = min(raws),max(raws)
    for x in out:
        x["Semantic_Score"] = 1.0 if mx==mn else round((x["raw"]-mn)/(mx-mn),3)

    out_map = {e.get("name"):e for e in existing}
    for x in out:
        nm = x["name"]
        if nm not in out_map: out_map[nm] = {"name":nm}
        out_map[nm]["Semantic_Score"] = x["Semantic_Score"]
        if x.get("project_aggregate") is not None:
            out_map[nm]["project_aggregate"] = x["project_aggregate"]
        if x.get("Keyword_Score") is not None:
            out_map[nm]["Keyword_Score"] = x["Keyword_Score"]

    tmp = SCORES_FILE.with_suffix(".tmp")
    json.dump(list(out_map.values()), open(tmp,"w",encoding="utf-8"), indent=4)
    os.replace(tmp,SCORES_FILE)

    print("📂 Semantic scores written →", SCORES_FILE)


if __name__ == "__main__":
    main()

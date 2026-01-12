# #!/usr/bin/env python3
# """
# SemanticComparitor.py — OpenAI embeddings upgrade (drop-in replacement)

# This script is 100% pipeline-compatible:
# - same inputs, same outputs, same JSON fields
# - same flow, scoring & file paths
# - only embedding engine changed to OpenAI text-embedding-3-small
# """

# import json
# import sys
# import os
# import hashlib
# import pickle
# import tempfile
# import time
# import random
# from pathlib import Path
# from typing import List, Dict, Tuple
# from tqdm import tqdm
# import numpy as np
# from openai import OpenAI   # NEW API
# client = None               # created in main()

# # -----------------------
# # Config / Paths (unchanged)
# # -----------------------
# EMBEDDING_MODEL = "text-embedding-3-small"
# EMBED_BATCH = 128
# EMBED_RETRIES = 5
# BACKOFF_BASE = 1.4

# SCRIPT_DIR = Path(__file__).resolve().parent
# ROOT_DIR = SCRIPT_DIR.parent
# PROCESSED_JSON_DIR = (ROOT_DIR / "ProcessedJson").resolve()
# JD_DIR = (ROOT_DIR / "InputThread" / "JD").resolve()
# SCORES_FILE = Path("Ranking/Scores.json")
# EMBED_CACHE_PATH = SCRIPT_DIR / ".semantic_embed_cache.pkl"

# TAU_COV = 0.65
# TAU_RESUME = 0.55
# SECTION_COMB = (0.5, 0.4, 0.1)
# SECTION_WEIGHTS = {
#     "skills": 0.30, "projects": 0.25, "responsibilities": 0.20,
#     "profile": 0.10, "education": 0.05, "overall": 0.10
# }
# MAX_SENT = 200

# # -----------------------
# # Cache
# # -----------------------
# class EmbedCache:
#     def __init__(self, path: Path):
#         self.path = path
#         self._cache = {}
#         if path.exists():
#             try:
#                 self._cache = pickle.load(open(path, "rb"))
#             except Exception:
#                 self._cache = {}

#     def _key(self, text: str):
#         return hashlib.sha256(f"{EMBEDDING_MODEL}||{text}".encode()).hexdigest()

#     def get(self, text: str):
#         return self._cache.get(self._key(text))

#     def set(self, text: str, vec):
#         self._cache[self._key(text)] = vec
#         # Write cache more frequently for better performance (every 100 items instead of 1000)
#         if len(self._cache) % 100 == 0:
#             try:
#                 pickle.dump(self._cache, open(self.path, "wb"))
#             except Exception:
#                 pass  # Non-critical, continue processing

#     def close(self):
#         pickle.dump(self._cache, open(self.path, "wb"))

# # -----------------------
# # Text helpers
# # -----------------------
# def norm(s): return s.strip()

# def normalize_name(name: str) -> str:
#     """Normalize candidate name consistently across all modules."""
#     if not name or not isinstance(name, str):
#         return ""
#     return " ".join(name.strip().title().split())

# def sentence_split(text: str):
#     if not text: return []
#     text = text.replace("\n", " ")
#     parts = []
#     start = 0
#     for i, ch in enumerate(text):
#         if ch in ".!?":
#             seg = text[start:i+1].strip()
#             if seg: parts.append(seg)
#             start = i+1
#     tail = text[start:].strip()
#     if tail: parts.append(tail)
#     return [p for p in parts if len(p.split()) >= 3]

# def safe_list(x): return x if isinstance(x, list) else []

# # -----------------------
# # JSON → sections (unchanged)
# # -----------------------
# def extract_sections_from_resume(resume: dict) -> Dict[str, List[str]]:
#     sections = {k: [] for k in ["profile","skills","projects","responsibilities","education","overall"]}

#     p = resume.get("profile_keywords_line")
#     if p: sections["profile"] += sentence_split(p)

#     canonical = resume.get("canonical_skills") or {}
#     for vals in canonical.values():
#         if isinstance(vals, list):
#             sections["skills"] += [norm(v) for v in vals if v]

#     for inf in safe_list(resume.get("inferred_skills")):
#         if inf.get("skill") and inf.get("confidence",0) >= 0.6:
#             sections["skills"].append(norm(inf["skill"]))

#     for proj in safe_list(resume.get("projects")):
#         if proj.get("name"): sections["projects"] += sentence_split(proj["name"])
#         if proj.get("approach"): sections["projects"] += sentence_split(proj["approach"])
#         if proj.get("tech_keywords"): sections["projects"] += [norm(x) for x in proj["tech_keywords"]]

#     for exp in safe_list(resume.get("experience_entries")):
#         for r in safe_list(exp.get("responsibilities_keywords")):
#             if r: sections["responsibilities"] += sentence_split(r)
#         for a in safe_list(exp.get("achievements")):
#             if a: sections["responsibilities"] += sentence_split(a)
#         for t in safe_list(exp.get("primary_tech")):
#             if t: sections["responsibilities"].append(norm(t))

#     for e in safe_list(resume.get("education")):
#         if isinstance(e, str): sections["education"] += sentence_split(e)

#     ats = resume.get("ats_boost_line") or ""
#     if ats and not sections["education"]:
#         parts = [x.strip() for x in ats.split(",") if x.strip()]
#         sections["education"] += parts[:20]

#     overall = []
#     if resume.get("profile_keywords_line"): overall.append(resume["profile_keywords_line"])
#     for proj in safe_list(resume.get("projects")):
#         if proj.get("approach"): overall.append(proj["approach"])
#     for exp in safe_list(resume.get("experience_entries")):
#         if exp.get("responsibilities_keywords"):
#             overall += exp["responsibilities_keywords"]
#     if ats: overall.append(ats)
#     sections["overall"] = [s for p in overall for s in sentence_split(p)]

#     for k in sections:
#         if len(sections[k]) > MAX_SENT: sections[k] = sections[k][:MAX_SENT]
#     return sections

# def extract_sections_from_jd(jd: dict):
#     sections = {k: [] for k in ["profile","skills","projects","responsibilities","education","overall"]}

#     if jd.get("role_title"): sections["profile"] += sentence_split(jd["role_title"])
#     if jd.get("embedding_hints", {}).get("overall_embed"):
#         sections["overall"] += sentence_split(jd["embedding_hints"]["overall_embed"])
#     if jd.get("responsibilities"):
#         for r in jd["responsibilities"]: sections["responsibilities"] += sentence_split(r)
#     if jd.get("required_skills"):
#         sections["skills"] += [norm(x) for x in jd["required_skills"]]
#     if jd.get("preferred_skills"):
#         sections["skills"] += [norm(x) for x in jd["preferred_skills"]]
#     if jd.get("embedding_hints", {}).get("projects_embed"):
#         sections["projects"] += sentence_split(jd["embedding_hints"]["projects_embed"])
#     if jd.get("certifications_required"):
#         sections["education"] += [norm(x) for x in jd["certifications_required"]]
#     if jd.get("education_requirements"):
#         sections["education"] += [norm(x) for x in jd["education_requirements"]]
#     if jd.get("keywords_flat") and not sections["skills"]:
#         sections["skills"] += [norm(x) for x in jd["keywords_flat"]]

#     for k in sections:
#         dedup, out = set(), []
#         for s in sections[k]:
#             key = s.lower().strip()
#             if key not in dedup:
#                 dedup.add(key)
#                 out.append(s)
#         sections[k] = out

#     return sections

# # -----------------------
# # OpenAI embeddings (new)
# # -----------------------
# def _embed_batch(texts: List[str]) -> List[List[float]]:
#     for attempt in range(1, EMBED_RETRIES + 1):
#         try:
#             res = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
#             return [d.embedding for d in res.data]
#         except Exception as e:
#             if attempt == EMBED_RETRIES:
#                 raise RuntimeError(f"OpenAI embeddings failed: {e}")
#             time.sleep((BACKOFF_BASE ** attempt) + random.random())

# def embed_texts(cache: EmbedCache, texts: List[str]) -> np.ndarray:
#     if not texts: return np.zeros((0,1536),dtype=np.float32)

#     vecs = [None] * len(texts)
#     todo, todo_i = [], []

#     for i,t in enumerate(texts):
#         c = cache.get(t)
#         if c is None:
#             todo.append(t); todo_i.append(i)
#         else:
#             vecs[i] = np.array(c,dtype=np.float32)

#     for i in range(0,len(todo),EMBED_BATCH):
#         batch = todo[i:i+EMBED_BATCH]
#         emb = _embed_batch(batch)
#         for j,vec in enumerate(emb):
#             idx = todo_i[i+j]
#             arr = np.array(vec,dtype=np.float32)
#             n = np.linalg.norm(arr)
#             if n>0: arr = arr/n
#             vecs[idx] = arr
#             cache.set(batch[j], arr.tolist())

#     d = vecs[0].shape[0]
#     for i,v in enumerate(vecs):
#         if v is None: vecs[i] = np.zeros((d,),dtype=np.float32)

#     M = np.vstack(vecs)
#     M /= np.linalg.norm(M,axis=1,keepdims=True).clip(min=1e-9)
#     return M.astype(np.float32)

# # -----------------------
# # Scoring
# # -----------------------
# def cosine_sim(a,b): return np.matmul(a,b.T)

# def compute_section_score(jd, resume):
#     if jd.size==0: return 0.5,0,0,[]
#     if resume.size==0: return 0,0,0,[]
#     C = cosine_sim(jd,resume)
#     max_j = C.max(axis=1)
#     cov = float((max_j>=TAU_COV).sum()) / len(max_j)
#     depth = float(max_j.mean())
#     max_r = C.max(axis=0)
#     dens = float((max_r>=TAU_RESUME).sum()) / max(1,len(max_r))
#     sec = SECTION_COMB[0]*cov + SECTION_COMB[1]*depth + SECTION_COMB[2]*dens
#     matches = [(j,int(C[j].argmax()),float(C[j].max())) for j in range(C.shape[0])]
#     return sec,cov,depth,matches

# # -----------------------
# # Main (drop-in)
# # -----------------------
# def main():
#     global client
#     client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

#     if not PROCESSED_JSON_DIR.exists():
#         print("❌ No ProcessedJson folder", file=sys.stderr); sys.exit(1)

#     jd_files = list(JD_DIR.glob("*.json"))
#     if not jd_files:
#         print("❌ No JD JSON found", file=sys.stderr); sys.exit(1)
#     jd = json.load(open(jd_files[0],"r",encoding="utf-8"))
#     jd_secs = extract_sections_from_jd(jd)

#     # Only process files in root ProcessedJson directory (exclude FilteredResumes subdirectory)
#     resumes = sorted([
#         p for p in PROCESSED_JSON_DIR.glob("*.json")
#         if p.parent == PROCESSED_JSON_DIR
#     ])
#     if not resumes:
#         print("⚠️ No resumes found"); sys.exit(0)

#     cache = EmbedCache(EMBED_CACHE_PATH)

#     jd_emb = {}; jd_txt = {}
#     for sec,txts in jd_secs.items():
#         jd_txt[sec] = txts
#         jd_emb[sec] = embed_texts(cache, txts) if txts else np.zeros((0,1536),dtype=np.float32)

#     # Load existing scores, but filter to only current batch candidates
#     existing = json.load(open(SCORES_FILE)) if SCORES_FILE.exists() else []
    
#     # Get current batch candidate IDs and names
#     current_candidate_ids = set()
#     current_names = set()
#     for r in resumes:
#         try:
#             resume = json.load(open(r,"r",encoding="utf-8"))
#             candidate_id = resume.get("candidate_id")
#             name = normalize_name(resume.get("name") or r.stem)
#             if candidate_id:
#                 current_candidate_ids.add(candidate_id)
#             if name:
#                 current_names.add(name)
#         except Exception:
#             continue
    
#     # Filter existing to only include current batch candidates
#     filtered_existing = []
#     for e in existing:
#         if isinstance(e, dict):
#             e_id = e.get("candidate_id")
#             e_name = normalize_name(e.get("name", ""))
#             if (e_id and e_id in current_candidate_ids) or (e_name and e_name in current_names):
#                 filtered_existing.append(e)
    
#     existing = filtered_existing
    
#     # Build maps: prioritize candidate_id, fallback to normalized name
#     existing_map_by_id = {}
#     existing_map_by_name = {}
#     for e in existing:
#         if isinstance(e, dict):
#             if e.get("candidate_id"):
#                 existing_map_by_id[e["candidate_id"]] = e
#             if e.get("name"):
#                 normalized_name = normalize_name(e["name"])
#                 if normalized_name:
#                     existing_map_by_name[normalized_name] = e

#     # Check for parallel processing
#     parallel = os.getenv("ENABLE_PARALLEL", "false").lower() == "true"
#     max_workers = int(os.getenv("MAX_WORKERS", "5"))
    
#     def process_single_resume(r):
#         """Process a single resume and return result."""
#         resume = json.load(open(r,"r",encoding="utf-8"))
#         raw_name = resume.get("name") or r.stem
#         name = normalize_name(raw_name)
#         candidate_id = resume.get("candidate_id")
#         secs = extract_sections_from_resume(resume)

#         sec_emb, sec_txt = {}, {}
#         for sec in jd_secs.keys():
#             arr = secs.get(sec,[])
#             sec_txt[sec] = arr
#             sec_emb[sec] = embed_texts(cache,arr) if arr else np.zeros((0,1536),dtype=np.float32)

#         sec_scores = {}; sec_matches = {}
#         total = 0.0
#         for sec,w in SECTION_WEIGHTS.items():
#             s,c,d,m = compute_section_score(jd_emb[sec],sec_emb[sec])
#             total += s*w
#             sec_scores[sec] = {"score":round(s,3),"coverage":round(c,3),"depth":round(d,3)}
#             sec_matches[sec] = m[:5]

#         # Get existing scores - try candidate_id first, then normalized name
#         existing_entry = None
#         if candidate_id and candidate_id in existing_map_by_id:
#             existing_entry = existing_map_by_id[candidate_id]
#         elif name and name in existing_map_by_name:
#             existing_entry = existing_map_by_name[name]
        
#         return {
#             "name": name,
#             "candidate_id": candidate_id,
#             "raw": total,
#             "project_aggregate": existing_entry.get("project_aggregate") if existing_entry else None,
#             "Keyword_Score": existing_entry.get("Keyword_Score") if existing_entry else None,
#             "_internal": sec_scores
#         }
    
#     out = []
#     if parallel and len(resumes) > 1:
#         # Parallel processing for resume scoring (embeddings are already batched)
#         print(f"[INFO] Processing {len(resumes)} resumes in parallel with {max_workers} workers...")
#         from concurrent.futures import ThreadPoolExecutor, as_completed
        
#         with ThreadPoolExecutor(max_workers=max_workers) as executor:
#             futures = {executor.submit(process_single_resume, r): r for r in resumes}
            
#             for future in tqdm(as_completed(futures), total=len(resumes), desc="Resumes"):
#                 r = futures[future]
#                 try:
#                     result = future.result()
#                     if result:
#                         out.append(result)
#                 except Exception as e:
#                     print(f"⚠️ Error processing {r.name}: {e}")
#     else:
#         # Sequential processing
#         for r in tqdm(resumes, desc="Resumes"):
#             try:
#                 result = process_single_resume(r)
#                 if result:
#                     out.append(result)
#             except Exception as e:
#                 print(f"⚠️ Error processing {r.name}: {e}")

#     cache.close()

#     raws = [x["raw"] for x in out]
#     mn,mx = min(raws),max(raws)
#     for x in out:
#         x["Semantic_Score"] = 1.0 if mx==mn else round((x["raw"]-mn)/(mx-mn),3)

#     # Build output map - prioritize candidate_id, fallback to normalized name
#     out_map_by_id = existing_map_by_id.copy()
#     out_map_by_name = existing_map_by_name.copy()
    
#     for x in out:
#         candidate_id = x.get("candidate_id")
#         nm = x["name"]
#         semantic_score = x["Semantic_Score"]
        
#         # Try to update by candidate_id first (most reliable)
#         if candidate_id:
#             if candidate_id not in out_map_by_id:
#                 out_map_by_id[candidate_id] = {"name": nm, "candidate_id": candidate_id}
#             out_map_by_id[candidate_id]["Semantic_Score"] = semantic_score
#             if x.get("project_aggregate") is not None:
#                 out_map_by_id[candidate_id]["project_aggregate"] = x["project_aggregate"]
#             if x.get("Keyword_Score") is not None:
#                 out_map_by_id[candidate_id]["Keyword_Score"] = x["Keyword_Score"]
        
#         # Also update by name for backward compatibility
#         if nm:
#             if nm not in out_map_by_name:
#                 out_map_by_name[nm] = {"name": nm}
#                 if candidate_id:
#                     out_map_by_name[nm]["candidate_id"] = candidate_id
#             out_map_by_name[nm]["Semantic_Score"] = semantic_score
#             if x.get("project_aggregate") is not None:
#                 out_map_by_name[nm]["project_aggregate"] = x["project_aggregate"]
#             if x.get("Keyword_Score") is not None:
#                 out_map_by_name[nm]["Keyword_Score"] = x["Keyword_Score"]
    
#     # Combine maps, prioritizing candidate_id entries
#     final_results = []
#     seen_ids = set()
#     # First add all entries with candidate_id
#     for candidate_id, entry in out_map_by_id.items():
#         if candidate_id not in seen_ids:
#             final_results.append(entry)
#             seen_ids.add(candidate_id)
#     # Then add entries that only exist in name map (for backward compatibility)
#     for name, entry in out_map_by_name.items():
#         entry_id = entry.get("candidate_id")
#         if not entry_id or entry_id not in seen_ids:
#             final_results.append(entry)
#             if entry_id:
#                 seen_ids.add(entry_id)
    
#     tmp = SCORES_FILE.with_suffix(".tmp")
    
#     json.dump(final_results, open(tmp,"w",encoding="utf-8"), indent=4)
#     os.replace(tmp,SCORES_FILE)

#     print("📂 Semantic scores written →", SCORES_FILE)


# if __name__ == "__main__":
#     main()
#!/usr/bin/env python3
"""
SemanticComparitor.py — OpenAI embeddings upgrade (drop-in replacement)

Enhanced JD extraction:
- Checks many JD fields (description, summary, overview, job_description, etc.)
- If still empty, flatten all string fields in the JD JSON and use that as a fallback
- Keeps safe normalization and diagnostics so you don't get everyone as 1.0
"""

import json
import sys
import os
import hashlib
import pickle
import time
import random
from pathlib import Path
from typing import List, Dict, Any
from tqdm import tqdm
import numpy as np

try:
    from openai import OpenAI   # NEW API
except Exception:
    OpenAI = None

client = None               # created in main()

# -----------------------
# Config / Paths (unchanged)
# -----------------------
EMBEDDING_MODEL = "text-embedding-3-small"
EMBED_BATCH = 256
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
EMBED_DIM = 1536  # matches text-embedding-3-small

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

# -----------------------
# Text helpers
# -----------------------
def norm(s): return s.strip() if isinstance(s, str) else ""

def normalize_name(name: str) -> str:
    if not name or not isinstance(name, str):
        return ""
    return " ".join(name.strip().title().split())

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
# JSON → sections (resume)
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

# -----------------------
# JSON → sections (JD) — enhanced
# -----------------------
def _collect_strings(obj: Any, out: List[str], depth=0):
    """Recursively collect string values from nested JD JSON (limit depth to avoid extremely deep traversal)."""
    if depth > 10:
        return
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, list):
        for v in obj:
            _collect_strings(v, out, depth+1)
    elif isinstance(obj, dict):
        for v in obj.values():
            _collect_strings(v, out, depth+1)

def extract_sections_from_jd(jd: dict):
    sections = {k: [] for k in ["profile","skills","projects","responsibilities","education","overall"]}

    # Known fields (original)
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

    # Additional common fields to attempt
    for key in ("description", "job_description", "summary", "overview", "role_summary", "responsibilities_text", "requirements"):
        if jd.get(key):
            sections["overall"] += sentence_split(jd[key])

    # If some fields are lists/dicts of blocks
    if jd.get("sections") and isinstance(jd["sections"], list):
        for s in jd["sections"]:
            if isinstance(s, dict):
                if s.get("title"): sections["profile"] += sentence_split(s.get("title"))
                if s.get("content"): sections["overall"] += sentence_split(s.get("content"))

    # Deduplicate per section
    for k in sections:
        dedup, out = set(), []
        for s in sections[k]:
            key = s.lower().strip()
            if key not in dedup:
                dedup.add(key)
                out.append(s)
        sections[k] = out

    # If all sections are empty, flatten the JD JSON and use that as fallback for overall
    all_empty = all(len(v) == 0 for v in sections.values())
    if all_empty:
        flattened = []
        _collect_strings(jd, flattened)
        joined = " ".join([s.strip() for s in flattened if isinstance(s, str) and s.strip()])
        if joined:
            # Use sentence split on the flattened text but cap to MAX_SENT
            sections["overall"] = sentence_split(joined)[:MAX_SENT]
    # Final trim
    for k in sections:
        if len(sections[k]) > MAX_SENT:
            sections[k] = sections[k][:MAX_SENT]
    return sections

# -----------------------
# OpenAI embeddings (unchanged)
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
    if not texts: return np.zeros((0, EMBED_DIM), dtype=np.float32)

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

    d = EMBED_DIM
    for i,v in enumerate(vecs):
        if v is None: vecs[i] = np.zeros((d,),dtype=np.float32)

    M = np.vstack(vecs) if vecs else np.zeros((0, d), dtype=np.float32)
    norms = np.linalg.norm(M,axis=1,keepdims=True).clip(min=1e-9)
    M = M / norms
    return M.astype(np.float32)

# -----------------------
# Scoring helpers (unchanged)
# -----------------------
def cosine_sim(a,b):
    if a.size == 0 or b.size == 0:
        return np.zeros((a.shape[0], b.shape[0]), dtype=np.float32)
    return np.matmul(a,b.T)

def compute_section_score(jd, resume):
    if jd.size==0:
        # If JD has no vectors for this section, return a neutral fallback
        return 0.5,0,0,[]
    if resume.size==0:
        return 0,0,0,[]
    C = cosine_sim(jd,resume)
    if C.size == 0:
        return 0.0,0,0,[]
    max_j = C.max(axis=1)
    cov = float((max_j>=TAU_COV).sum()) / len(max_j)
    depth = float(max_j.mean())
    max_r = C.max(axis=0) if C.size else np.array([])
    dens = float((max_r>=TAU_RESUME).sum()) / max(1,len(max_r))
    sec = SECTION_COMB[0]*cov + SECTION_COMB[1]*depth + SECTION_COMB[2]*dens
    matches = [(j,int(C[j].argmax()),float(C[j].max())) for j in range(C.shape[0])]
    return sec,cov,depth,matches

# -----------------------
# Main
# -----------------------
def main():
    global client
    if OpenAI is None:
        print("❌ openai package not available. Install 'openai' python package that provides OpenAI class.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    if not PROCESSED_JSON_DIR.exists():
        print("❌ No ProcessedJson folder", file=sys.stderr); sys.exit(1)

    jd_files = list(JD_DIR.glob("*.json"))
    if not jd_files:
        print("❌ No JD JSON found", file=sys.stderr); sys.exit(1)
    jd = json.load(open(jd_files[0],"r",encoding="utf-8"))
    jd_secs = extract_sections_from_jd(jd)

    # Only process files in root ProcessedJson directory (exclude FilteredResumes subdirectory)
    resumes = sorted([
        p for p in PROCESSED_JSON_DIR.glob("*.json")
        if p.parent == PROCESSED_JSON_DIR
    ])
    if not resumes:
        print("⚠️ No resumes found"); sys.exit(0)

    cache = EmbedCache(EMBED_CACHE_PATH)

    jd_emb = {}; jd_txt = {}
    for sec,txts in jd_secs.items():
        jd_txt[sec] = txts
        jd_emb[sec] = embed_texts(cache, txts) if txts else np.zeros((0,EMBED_DIM),dtype=np.float32)

    # Diagnostic: show JD section counts and embedding rows
    total_jd_vectors = sum(int(arr.shape[0]) for arr in jd_emb.values())
    for sec, arr in jd_emb.items():
        print(f"[JD] section '{sec}': {len(jd_txt.get(sec,[]))} texts -> emb rows {arr.shape[0]}")
    print(f"[JD] total embedding rows across sections: {total_jd_vectors}")

    # If JD provides no embeddings at all, attempt to rebuild using a more aggressive fallback (flattened JD)
    if total_jd_vectors == 0:
        print("⚠️ JD sections empty — trying aggressive fallback (flatten all string fields in JD JSON).", file=sys.stderr)
        # rebuild jd_secs by forcing flatten fallback
        flattened = []
        _collect_strings(jd, flattened)
        joined = " ".join([s.strip() for s in flattened if isinstance(s, str) and s.strip()])
        if joined:
            fallback_sents = sentence_split(joined)[:MAX_SENT]
            jd_secs["overall"] = fallback_sents
            jd_txt["overall"] = fallback_sents
            jd_emb["overall"] = embed_texts(cache, fallback_sents) if fallback_sents else np.zeros((0,EMBED_DIM),dtype=np.float32)
            total_jd_vectors = int(jd_emb["overall"].shape[0])
            print(f"[JD-FALLBACK] overall texts: {len(fallback_sents)} -> emb rows {total_jd_vectors}")
        else:
            print("❌ Aggressive fallback failed — no textual JD content found. Proceeding with neutral behavior.", file=sys.stderr)

    # If still zero, warn but continue (safe normalization later prevents all 1.0 scores)
    if total_jd_vectors == 0:
        print("⚠️ No JD embeddings found after fallback. Scores may not be discriminative. Continuing with neutral fallbacks.", file=sys.stderr)

    # Load existing scores, but filter to only current batch candidates
    existing = json.load(open(SCORES_FILE)) if SCORES_FILE.exists() else []
    
    current_candidate_ids = set()
    current_names = set()
    for r in resumes:
        try:
            resume = json.load(open(r,"r",encoding="utf-8"))
            candidate_id = resume.get("candidate_id")
            name = normalize_name(resume.get("name") or r.stem)
            if candidate_id:
                current_candidate_ids.add(candidate_id)
            if name:
                current_names.add(name)
        except Exception:
            continue
    
    filtered_existing = []
    for e in existing:
        if isinstance(e, dict):
            e_id = e.get("candidate_id")
            e_name = normalize_name(e.get("name", ""))
            if (e_id and e_id in current_candidate_ids) or (e_name and e_name in current_names):
                filtered_existing.append(e)
    
    existing = filtered_existing
    
    existing_map_by_id = {}
    existing_map_by_name = {}
    for e in existing:
        if isinstance(e, dict):
            if e.get("candidate_id"):
                existing_map_by_id[e["candidate_id"]] = e
            if e.get("name"):
                normalized_name = normalize_name(e["name"])
                if normalized_name:
                    existing_map_by_name[normalized_name] = e

    parallel = os.getenv("ENABLE_PARALLEL", "false").lower() == "true"
    max_workers = int(os.getenv("MAX_WORKERS", "5"))
    
    def process_single_resume(r):
        resume = json.load(open(r,"r",encoding="utf-8"))
        raw_name = resume.get("name") or r.stem
        name = normalize_name(raw_name)
        candidate_id = resume.get("candidate_id")
        secs = extract_sections_from_resume(resume)

        sec_emb, sec_txt = {}, {}
        for sec in jd_secs.keys():
            arr = secs.get(sec,[])
            sec_txt[sec] = arr
            sec_emb[sec] = embed_texts(cache,arr) if arr else np.zeros((0,EMBED_DIM),dtype=np.float32)

        sec_scores = {}; sec_matches = {}
        total = 0.0
        for sec,w in SECTION_WEIGHTS.items():
            s,c,d,m = compute_section_score(jd_emb.get(sec, np.zeros((0,EMBED_DIM),dtype=np.float32)), sec_emb[sec])
            total += s*w
            sec_scores[sec] = {"score":round(s,3),"coverage":round(c,3),"depth":round(d,3)}
            sec_matches[sec] = m[:5]

        existing_entry = None
        if candidate_id and candidate_id in existing_map_by_id:
            existing_entry = existing_map_by_id[candidate_id]
        elif name and name in existing_map_by_name:
            existing_entry = existing_map_by_name[name]
        
        return {
            "name": name,
            "candidate_id": candidate_id,
            "raw": total,
            "project_aggregate": existing_entry.get("project_aggregate") if existing_entry else None,
            "Keyword_Score": existing_entry.get("Keyword_Score") if existing_entry else None,
            "_internal": sec_scores
        }
    
    out = []
    if parallel and len(resumes) > 1:
        print(f"[INFO] Processing {len(resumes)} resumes in parallel with {max_workers} workers...")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_single_resume, r): r for r in resumes}
            for future in tqdm(as_completed(futures), total=len(resumes), desc="Resumes"):
                r = futures[future]
                try:
                    result = future.result()
                    if result:
                        out.append(result)
                except Exception as e:
                    print(f"⚠️ Error processing {r.name}: {e}")
    else:
        for r in tqdm(resumes, desc="Resumes"):
            try:
                result = process_single_resume(r)
                if result:
                    out.append(result)
            except Exception as e:
                print(f"⚠️ Error processing {r.name}: {e}")

    cache.close()

    if not out:
        print(" No processed resumes produced any output. Exiting.", file=sys.stderr)
        sys.exit(0)

    raws = [x["raw"] for x in out]
    mn, mx = min(raws), max(raws)
    print("raws sample (first 10):", raws[:10], "mn,mx =", mn, mx)

    if mx == mn:
        print(f"⚠️ All raw scores identical (mn==mx=={mn}). Cannot min-max normalize.", file=sys.stderr)
        for x in out:
            candidate_id = x.get("candidate_id")
            prev = None
            if candidate_id and candidate_id in existing_map_by_id:
                prev = existing_map_by_id[candidate_id].get("Semantic_Score")
            elif x.get("name") and x["name"] in existing_map_by_name:
                prev = existing_map_by_name[x["name"]].get("Semantic_Score")

            if prev is not None:
                x["Semantic_Score"] = prev
            else:
                x["Semantic_Score"] = round(0.5, 3)
    else:
        for x in out:
            x["Semantic_Score"] = round((x["raw"] - mn) / (mx - mn), 3)

    out_map_by_id = existing_map_by_id.copy()
    out_map_by_name = existing_map_by_name.copy()
    
    for x in out:
        candidate_id = x.get("candidate_id")
        nm = x["name"]
        semantic_score = x["Semantic_Score"]
        
        if candidate_id:
            if candidate_id not in out_map_by_id:
                out_map_by_id[candidate_id] = {"name": nm, "candidate_id": candidate_id}
            out_map_by_id[candidate_id]["Semantic_Score"] = semantic_score
            if x.get("project_aggregate") is not None:
                out_map_by_id[candidate_id]["project_aggregate"] = x["project_aggregate"]
            if x.get("Keyword_Score") is not None:
                out_map_by_id[candidate_id]["Keyword_Score"] = x["Keyword_Score"]
        
        if nm:
            if nm not in out_map_by_name:
                out_map_by_name[nm] = {"name": nm}
                if candidate_id:
                    out_map_by_name[nm]["candidate_id"] = candidate_id
            out_map_by_name[nm]["Semantic_Score"] = semantic_score
            if x.get("project_aggregate") is not None:
                out_map_by_name[nm]["project_aggregate"] = x["project_aggregate"]
            if x.get("Keyword_Score") is not None:
                out_map_by_name[nm]["Keyword_Score"] = x["Keyword_Score"]
    
    final_results = []
    seen_ids = set()
    for candidate_id, entry in out_map_by_id.items():
        if candidate_id not in seen_ids:
            final_results.append(entry)
            seen_ids.add(candidate_id)
    for name, entry in out_map_by_name.items():
        entry_id = entry.get("candidate_id")
        if not entry_id or entry_id not in seen_ids:
            final_results.append(entry)
            if entry_id:
                seen_ids.add(entry_id)
    
    tmp = SCORES_FILE.with_suffix(".tmp")
    json.dump(final_results, open(tmp,"w",encoding="utf-8"), indent=4)
    os.replace(tmp,SCORES_FILE)

    print("📂 Semantic scores written →", SCORES_FILE)


if __name__ == "__main__":
    main()

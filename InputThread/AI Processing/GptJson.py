#!/usr/bin/env python3
"""
Rich Resume TXT -> Normalized JSON converter
- General-purpose (AI/ML, Fullstack, Testing, DB modeling, Cloud, Solution Arch, Sales, etc.)
- Uses OpenAI function-calling for consistent structured output.
- No retries, no fallback parsing: if the model does not return the function-call JSON, the file is skipped and logged.
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load from your .env file
load_dotenv(".env")


# ---------------------------
# PATHS & CONFIG
# ---------------------------
JD_JSON = "InputThread/JD/JD.json"
INPUT_DIR = "Processed-TXT"
OUTPUT_DIR = "ProcessedJson"
LOG_FILE = "processing_errors.log1"
# Try .env first, fallback to Streamlit secrets (for Streamlit Cloud compatibility)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
    except (AttributeError, KeyError, FileNotFoundError):
        OPENAI_API_KEY = None
MODEL_NAME = "gpt-4o-mini"   # inexpensive model that supports function calling
MAX_RESPONSE_TOKENS = 2500
# ---------------------------




import os
import json
import logging
import time
import uuid
import hashlib
from pathlib import Path
from typing import Dict, Any, List
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.validation import validate_resume, validate_resume_file, ResumeSchema
from utils.retry import retry_api_call, openai_circuit_breaker
from utils.cache import resume_cache, get_resume_cache_key
from utils.common import (
    extract_function_call, 
    safe_json_load, 
    safe_json_save, 
    extract_jd_skills_from_domain_tags,
    canonicalize_string_list,
    canonicalize_skills_block
)

try:
    from openai import OpenAI
except Exception:
    raise RuntimeError("Install the OpenAI Python SDK (>=1.0.0): pip install openai") from None

# Validate API key
if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY not found! Please set it in:\n"
        "  For local development: Create .env file with OPENAI_API_KEY=your_key_here\n"
        "  For Streamlit Cloud: Go to Manage App -> Settings -> Secrets (UI)\n"
        "Get your API key from: https://platform.openai.com/api-keys"
    )

# Setup OpenAI client (new API)
client = OpenAI(api_key=OPENAI_API_KEY)

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# Retrieve Domain Tags (with caching)
def load_domain_tags():
    """Load domain tags from JD.json with caching."""
    jd_path = Path(JD_JSON)
    if not jd_path.exists():
        return []
    
    cache_key = get_resume_cache_key(jd_path)  # Reuse cache key function
    cached = resume_cache.get(cache_key)
    if cached:
        return cached.get("domain_tags", [])
    
    jd_data = safe_json_load(jd_path, {})
    domain_tags = jd_data.get("domain_tags", [])
    
    # Cache the result
    resume_cache.set(cache_key, {"domain_tags": domain_tags})
    return domain_tags

# Load JD domain tags once
domain_tags = load_domain_tags()


# ---------------------------
# Function-calling JSON schema (detailed)
# ---------------------------
PARSE_FUNCTION = {
    "name": "parse_resume_detailed",
    "description": "Return a richly-structured JSON resume for ATS and LLM ranking. Include canonical skills, inferred skills with provenance & confidence, projects, experiences, domain tags (AIML, Fullstack, Cloud, DB, Testing, Sales, Solution Arch, etc.), minimal filler, and embedding hint strings.",
    "parameters": {
        "type": "object",
        "properties": {
            "candidate_id": {"type": "string"},
            "name": {"type": "string"},
            "role_claim": {"type": "string"},
            "years_experience": {"type": "number"},
            "location": {"type": "string"},
            "contact": {
                "type": "object",
                "properties": {
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "profile": {"type": "string"}
                }
            },
            "domain_tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "High-level role areas e.g., AIML, Fullstack, Testing, DB Modeling, Cloud, Solution Arch, Sales"
            },
            "profile_keywords_line": {"type": "string"},
            "canonical_skills": {
                "type": "object",
                "properties": {
                    "programming": {"type": "array", "items": {"type": "string"}},
                    "ml_ai": {"type": "array", "items": {"type": "string"}},
                    "frontend": {"type": "array", "items": {"type": "string"}},
                    "backend": {"type": "array", "items": {"type": "string"}},
                    "testing": {"type": "array", "items": {"type": "string"}},
                    "databases": {"type": "array", "items": {"type": "string"}},
                    "cloud": {"type": "array", "items": {"type":"string"}},
                    "infra": {"type": "array", "items": {"type":"string"}},
                    "devtools": {"type": "array", "items": {"type":"string"}},
                    "methodologies": {"type": "array", "items": {"type":"string"}}
                }
            },
            "inferred_skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill": {"type": "string"},
                        "confidence": {"type": "number"},
                        "provenance": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            "skill_proficiency": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill": {"type":"string"},
                        "level": {"type":"string"},
                        "years_last_used": {"type":"integer"},
                        "provenance": {"type":"array", "items": {"type":"string"}}
                    }
                }
            },
            "projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "duration_start": {"type": "string"},
                        "duration_end": {"type": "string"},
                        "role": {"type": "string"},
                        "domain": {"type": "string"},
                        "tech_keywords": {"type": "array", "items": {"type": "string"}},
                        "approach": {"type": "string"},
                        "impact_metrics": {"type": "object"},
                        "primary_skills": {"type": "array", "items": {"type": "string"}},
                        "metrics": {
                            "type": "object",
                            "properties": {
                                "difficulty": {"type": "number", "description": "Rating 0–1"},
                                "novelty": {"type": "number", "description": "Rating 0–1"},
                                "skill_relevance": {"type": "number", "description": "Rating 0–1"},
                                "complexity": {"type": "number", "description": "Rating 0–1"},
                                "technical_depth": {"type": "number", "description": "Rating 0–1"},
                                "domain_relevance": {"type": "number", "description": "Rating 0–1"},
                                "execution_quality": {"type": "number", "description": "Rating 0–1"}
                            },
                            "required": [
                                "difficulty", "novelty", "skill_relevance", "complexity",
                                "technical_depth", "domain_relevance", "execution_quality"
                            ]
                        }
                    }
                }
            },
            # "projects": {
            #     "type": "array",
            #     "items": {
            #         "type": "object",
            #         "properties": {
            #             "name": {"type": "string"},
            #             "duration_start": {"type": "string"},
            #             "duration_end": {"type": "string"},
            #             "role": {"type": "string"},
            #             "domain": {"type": "string"},
            #             "tech_keywords": {"type": "array", "items": {"type": "string"}},
            #             "approach": {"type": "string"},
            #             "impact_metrics": {"type": "object"},
            #             "primary_skills": {"type": "array", "items": {"type": "string"}},
            #             "provenance_spans": {"type":"array", "items":{"type":"object", "properties":{"start": {"type":"integer"},"end":{"type":"integer"},"text":{"type":"string"}}}}
            #         }
            #     }
            # },
            "experience_entries": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company": {"type":"string"},
                        "title": {"type":"string"},
                        "period_start": {"type":"string"},
                        "period_end": {"type":"string"},
                        "responsibilities_keywords": {"type":"array", "items":{"type":"string"}},
                        "achievements": {"type":"array", "items":{"type":"string"}},
                        "primary_tech": {"type":"array", "items":{"type":"string"}},
                        "provenance_spans": {"type":"array", "items":{"type":"object", "properties":{"start":{"type":"integer"},"end":{"type":"integer"},"text":{"type":"string"}}}}
                    }
                }
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "degree": {"type": "string", "description": "Degree level (e.g., B.Tech, M.Tech, B.E., M.S., Ph.D.)"},
                        "field": {"type": "string", "description": "Field of study/department (e.g., Computer Science, Mechanical Engineering, IT, CE, AIDS, ENTC)"},
                        "institution": {"type": "string", "description": "University/College name"},
                        "year": {"type": "string", "description": "Graduation year or period"}
                    }
                },
                "description": "Education entries with degree, field/department, institution, and year"
            },
            "ats_boost_line": {"type":"string"},
            "embedding_hints": {
                "type": "object",
                "properties": {
                    "profile_embed": {"type":"string"},
                    "projects_embed": {"type":"string"},
                    "skills_embed": {"type":"string"}
                }
            },
            "explainability": {
                "type":"object",
                "properties": {
                    "top_matched_sentences": {"type":"array", "items":{"type":"string"}},
                    "top_matched_keywords": {"type":"array", "items":{"type":"string"}}
                }
            },
            "meta": {
                "type":"object",
                "properties": {
                    "raw_text_length": {"type":"integer"},
                    "keyword_occurrences": {"type":"object"},
                    "last_updated": {"type":"string"}
                }
            }
        },
        "required": ["candidate_id", "name", "profile_keywords_line", "canonical_skills", "ats_boost_line"]
    }
}


# ---------------------------
# Helpers
# ---------------------------
def normalize_name(name: str) -> str:
    """Normalize candidate name consistently across all modules."""
    if not name or not isinstance(name, str):
        return ""
    return " ".join(name.strip().title().split())


def generate_deterministic_candidate_id(email: str, phone: str, name: str, filename: str) -> str:
    """
    Generate a deterministic candidate_id based on contact info and name.
    Same person = same ID regardless of filename.
    """
    # Normalize inputs
    email = (email or "").strip().lower()
    phone = (phone or "").strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    name = normalize_name(name or "")
    filename_base = Path(filename).stem
    
    # Create hash from available identifiers
    # Priority: email > phone > normalized_name > filename
    if email:
        identifier = f"email:{email}"
    elif phone:
        identifier = f"phone:{phone}"
    elif name:
        identifier = f"name:{name}"
    else:
        # Fallback to filename hash if no contact info
        identifier = f"file:{filename_base}"
    
    # Generate deterministic hash (first 12 chars of SHA256)
    hash_id = hashlib.sha256(identifier.encode('utf-8')).hexdigest()[:12]
    
    # Include readable prefix for debugging
    if email:
        prefix = email.split("@")[0][:8] if "@" in email else "cand"
    elif name:
        prefix = name.replace(" ", "")[:8].lower()
    else:
        prefix = filename_base[:8]
    
    return f"{prefix}_{hash_id}"


def generate_candidate_id(filename: str) -> str:
    """Legacy function - generates temporary ID before parsing. Will be replaced after parsing."""
    base = Path(filename).stem
    return f"{base}_{uuid.uuid4().hex[:8]}"


# Canonicalization functions moved to utils.common to avoid duplication


# ---------------------------
# Core processing
# ---------------------------
def process_resume_file(path: str) -> Dict[str, Any]:
    filename = os.path.basename(path)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    candidate_id = generate_candidate_id(filename)

    # sYSTEM MESSAGE WITH DOMAIN TAGS FOR BETTER METRICS
    # system_msg = {
    #     "role": "system",
    #     "content": (
    #         "You are a structured resume parser and judge. The caller will provide raw resume text. "
    #         f"\n\nIMPORTANT: The Job Description domain tags are: {domain_tags}. "
    #         "Return EXACTLY one function call to 'parse_resume_detailed' with JSON arguments that match the schema. "
    #         "Minimize filler language; produce concise canonical tokens. "
    #         "Include provenance spans (character offsets) for extracted projects/skills when found in the text. "
    #         "If a value cannot be determined, return empty string, empty list or empty object. "
    #         "Deduce keywords specific to the domain from indirect entries (Projects, Skills, Experience). "
    #         "IMPORTANT for Projects field except for the dates, STRICTLY do not leave any field blank." 
    #         "IMPORTANT Have project metrics on each project"
    #         "Strictly mention role, domain, and most relevant technical keywords. "
    #         f"IMPORTANT Strictly judge and score projects/skills higher if they align strictly with these domains : {domain_tags}, and score projects unrelated or in irrelevant domains low. Only relevant projects should score higher, Judge with high Strictness"
    #         "The complete resume is to be judged with consistent strictness and projects require technical depth and explain understanding, basic projects or projects below the required level of technical depth are scored low."
    #     )
    # }

    # Extract JD skills from domain_tags for normalization reference (using shared utility)
    jd_skills = extract_jd_skills_from_domain_tags(domain_tags)
    jd_required_skills = jd_skills["required"]
    jd_preferred_skills = jd_skills["preferred"]
    
    # Truncate domain_tags for prompt (keep first 20 to save tokens)
    domain_tags_preview = domain_tags[:20] if len(domain_tags) > 20 else domain_tags
    domain_tags_str = str(domain_tags_preview) + ("..." if len(domain_tags) > 20 else "")
    
    system_msg = {
        "role": "system",
        "content": (
            "Parse resume into structured JSON. Return EXACTLY ONE function call to `parse_resume_detailed`.\n\n"
            
            f"JD CONTEXT: {domain_tags_str}\n"
            "This contains JD domain, seniority, required/preferred skills, and HR priorities.\n\n"
            
            "SKILL NORMALIZATION (CRITICAL):\n"
            "• Match JD skill format. If JD requires 'RAG' and resume has 'Retrieval Augmented Generation', extract as 'RAG'\n"
            "• If JD requires 'ML' and resume has 'Machine Learning', extract as 'Machine Learning' (use JD's canonical form)\n"
            "• Use JD required_skills as normalization reference (check REQ_SKILL: tags in domain_tags)\n"
            "• Normalize all skills to match JD format for consistent filtering\n"
            + (f"• JD Required Skills (normalize to these forms): {', '.join(jd_required_skills[:10])}\n" if jd_required_skills else "") +
            "\n"
            
            "SCORING (use domain_tags as benchmark):\n"
            "• High alignment with domain_tags → HIGH scores\n"
            "• Low alignment / basic projects → LOW scores\n"
            "• Experience below JD seniority → LOW scores\n"
            "• Production-grade work → HIGH; toy projects → LOW\n"
            "• Architecture/scaling work → very HIGH\n\n"
            
            "EXPERIENCE CALCULATION (CRITICAL):\n"
            "• Calculate years_experience from experience_entries dates\n"
            "• Handle overlapping periods, internships, part-time correctly\n"
            "• Sum all relevant work experience (exclude internships if not relevant)\n"
            "• Use current date or latest period_end as reference\n"
            "• Return as number (e.g., 2.5 for 2 years 6 months)\n\n"
            
            "EDUCATION EXTRACTION:\n"
            "• Extract degree, field/department, institution, year from education section\n"
            "• Field should be specific: 'Computer Science', 'Mechanical Engineering', 'IT', 'CE', 'AIDS', 'ENTC'\n"
            "• Map abbreviations: CS→Computer Science, CE→Computer Engineering, IT→Information Technology\n"
            "• Include all degrees (B.Tech, M.Tech, etc.)\n\n"
            
            "REQUIREMENTS:\n"
            "1. Fill all project fields (except dates)\n"
            "2. Include provenance spans\n"
            "3. Normalize skills to JD format (see above)\n"
            "4. Calculate years_experience accurately from dates\n"
            "5. Extract education with field/department\n"
            "6. No hallucinations - only extract what's present\n"
            "7. Use canonical tokens\n\n"
            
            "Return ONLY the function call. See schema for field descriptions."
        )
    }


    user_msg = {
        "role": "user",
        "content": f"CandidateID: {candidate_id}\n\nRawResumeText:\n```\n{raw_text}\n```"
    }

    # API call with retry and circuit breaker
    @retry_api_call(max_attempts=3, initial_wait=1.0, max_wait=10.0)
    def call_openai_api():
        return openai_circuit_breaker.call(
            client.chat.completions.create,
            model=MODEL_NAME,
            messages=[system_msg, user_msg],
            functions=[PARSE_FUNCTION],
            function_call="auto",
            temperature=0.0,
            max_tokens=MAX_RESPONSE_TOKENS
        )
    
    resp = call_openai_api()
    
    # Extract function call using shared utility
    parsed = extract_function_call(resp)

    # Generate deterministic candidate_id based on extracted contact info
    contact = parsed.get("contact", {})
    email = contact.get("email", "") if isinstance(contact, dict) else ""
    phone = contact.get("phone", "") if isinstance(contact, dict) else ""
    name = parsed.get("name", "")
    
    # Replace temporary candidate_id with deterministic one
    deterministic_id = generate_deterministic_candidate_id(email, phone, name, filename)
    parsed["candidate_id"] = deterministic_id
    
    # Normalize name for consistency
    if name:
        parsed["name"] = normalize_name(name)
    
    parsed.setdefault("meta", {})
    parsed["meta"].setdefault("raw_text_length", len(raw_text))
    parsed["meta"].setdefault("last_updated", time.strftime("%Y-%m-%d"))

    parsed["canonical_skills"] = canonicalize_skills_block(parsed.get("canonical_skills", {}))

    for proj in parsed.get("projects", []):
        proj["tech_keywords"] = canonicalize_string_list(proj.get("tech_keywords", []))
        proj["primary_skills"] = canonicalize_string_list(proj.get("primary_skills", []))

    for exp in parsed.get("experience_entries", []):
        exp["primary_tech"] = canonicalize_string_list(exp.get("primary_tech", []))
        exp["responsibilities_keywords"] = canonicalize_string_list(exp.get("responsibilities_keywords", []))

    boost_tokens = set()
    for cat_list in parsed.get("canonical_skills", {}).values():
        boost_tokens.update([tok.lower() for tok in cat_list])
    for sp in parsed.get("skill_proficiency", []):
        if sp.get("skill"):
            boost_tokens.add(sp["skill"].lower())
    for iskill in parsed.get("inferred_skills", []):
        if iskill.get("skill"):
            boost_tokens.add(iskill["skill"].lower())
    parsed["ats_boost_line"] = ", ".join(sorted(boost_tokens))

    parsed.setdefault("embedding_hints", {
        "profile_embed": parsed.get("profile_keywords_line", ""),
        "projects_embed": " | ".join([p.get("name","") + ": " + p.get("approach","") for p in parsed.get("projects", [])[:2]]),
        "skills_embed": ", ".join(list(boost_tokens)[:10])
    })

    parsed.setdefault("explainability", {"top_matched_sentences": [], "top_matched_keywords": []})

    # Validate parsed data
    try:
        validated = validate_resume(parsed, Path(path))
        return validated.model_dump()  # Convert Pydantic model back to dict
    except Exception as e:
        logging.error(f"Validation failed for {path}: {e}")
        # Return unvalidated data but log warning
        print(f"⚠️ Validation warning for {path}: {e}")
        return parsed


# ---------------------------
# Data normalization
# ---------------------------
# Data normalization function to auto-fix validation issues
def normalize_resume_data(parsed: dict) -> dict:
    """
    Normalize resume data to fix common validation issues:
    - Convert string achievements to list
    - Round float years to int
    - Handle list.strip() errors
    """
    try:
        # Fix experience_entries achievements (string -> list)
        if "experience_entries" in parsed and isinstance(parsed["experience_entries"], list):
            for exp in parsed["experience_entries"]:
                if "achievements" in exp:
                    achievements = exp["achievements"]
                    if isinstance(achievements, str):
                        # Convert string to list
                        if achievements.strip():
                            exp["achievements"] = [achievements.strip()]
                        else:
                            exp["achievements"] = []
                    elif not isinstance(achievements, list):
                        exp["achievements"] = []
        
        # Fix skill_proficiency years_last_used (float -> int)
        if "skill_proficiency" in parsed and isinstance(parsed["skill_proficiency"], list):
            for skill in parsed["skill_proficiency"]:
                if "years_last_used" in skill:
                    years = skill["years_last_used"]
                    if isinstance(years, float):
                        skill["years_last_used"] = int(round(years))
                    elif not isinstance(years, int):
                        skill["years_last_used"] = 0
        
        # Fix any string fields that should be strings but got lists
        # Handle list.strip() errors by ensuring strings are strings
        if "ats_boost_line" in parsed and isinstance(parsed["ats_boost_line"], list):
            parsed["ats_boost_line"] = " ".join(str(x) for x in parsed["ats_boost_line"])
        
        if "profile_keywords_line" in parsed and isinstance(parsed["profile_keywords_line"], list):
            parsed["profile_keywords_line"] = " ".join(str(x) for x in parsed["profile_keywords_line"])
            
    except Exception as e:
        # If normalization fails, log but continue with original data
        logging.warning(f"Warning: Data normalization failed: {e}")
    
    return parsed


# ---------------------------
# Batch processing
# ---------------------------
# Optimized function with caching and parallel processing support
def process_single_resume(in_path: str, output_dir: str, existing_candidate_ids: set) -> tuple[bool, str]:
    """
    Process a single resume file with caching.
    
    Returns:
        (success: bool, message: str)
    """
    in_path_obj = Path(in_path)
    out_path = Path(output_dir) / f"{in_path_obj.stem}.json"
    
    # Check cache first
    cache_key = get_resume_cache_key(in_path_obj)
    cached_result = resume_cache.get(cache_key)
    if cached_result:
        # Check if output file exists and is valid
        if out_path.exists():
            try:
                validate_resume_file(out_path)
                return True, f"Skipped (cached): {in_path_obj.name}"
            except Exception:
                pass  # Cache invalid, reprocess
    
    # Skip if output file already exists
    if out_path.exists():
        try:
            validate_resume_file(out_path)
            return True, f"Skipped (exists): {in_path_obj.name}"
        except Exception:
            pass  # File invalid, reprocess
    
    try:
        parsed = process_resume_file(in_path)
        
        # Handle AttributeError: 'list' object has no attribute 'strip'
        # This can happen if LLM returns wrong data type
        if not isinstance(parsed, dict):
            return False, f"ERROR: Invalid data type returned from LLM: {type(parsed)}"
        
        candidate_id = parsed.get("candidate_id")
        
        # Skip if duplicate candidate (only if candidate_id is not None and not empty)
        # IMPORTANT: Only skip if we're certain it's a duplicate from the CURRENT batch
        # If candidate_id is None or empty, process it (might be a new candidate)
        if candidate_id and candidate_id.strip():
            if candidate_id in existing_candidate_ids:
                # #region agent log
                with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                    log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson","hypothesisId":"I3","location":"GptJson.py:608","message":"Duplicate candidate detected","data":{"candidate_id":candidate_id,"file":in_path_obj.name,"existing_count":len(existing_candidate_ids)},"timestamp":int(time.time()*1000)})+"\n")
                # #endregion
                return True, f"Skipped (duplicate): {in_path_obj.name} -> {candidate_id}"
            existing_candidate_ids.add(candidate_id)
            # #region agent log
            with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson","hypothesisId":"I3","location":"GptJson.py:614","message":"New candidate_id added","data":{"candidate_id":candidate_id,"file":in_path_obj.name},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
        else:
            # #region agent log
            with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson","hypothesisId":"I3","location":"GptJson.py:617","message":"Processing resume without candidate_id","data":{"file":in_path_obj.name,"candidate_id":candidate_id},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
        # Note: If candidate_id is None, we still process it (might be a new candidate without ID)
        
        # Auto-fix validation issues: normalize data types
        parsed = normalize_resume_data(parsed)
        
        # Map PDF path to candidate_id for download feature
        # Look for corresponding PDF in Uploaded_Resumes directory
        from pathlib import Path as PathLib
        uploaded_resumes_dir = PathLib("Uploaded_Resumes")
        pdf_mapping_file = uploaded_resumes_dir / "pdf_mapping.json"
        
        # Load existing mapping
        pdf_mapping = {}
        if pdf_mapping_file.exists():
            try:
                with open(pdf_mapping_file, "r", encoding="utf-8") as f:
                    pdf_mapping = json.load(f)
            except Exception:
                pdf_mapping = {}
        
        # Try to find matching PDF
        # CRITICAL: Prioritize candidate name (from content) over filename matching
        # Filenames can be wrong (e.g., "Ankit_Chaware.pdf" but content is "Aditya Kulkarni")
        resume_name = in_path_obj.stem
        candidate_name = parsed.get("name", "")
        
        # Normalize names for better matching
        def normalize_for_matching(text):
            """Normalize text for fuzzy matching"""
            if not text:
                return ""
            return "".join(c.lower() for c in text if c.isalnum() or c in (" ", "_", "-"))
        
        normalized_resume_name = normalize_for_matching(resume_name)
        normalized_candidate_name = normalize_for_matching(candidate_name)
        
        matching_pdf = None
        if uploaded_resumes_dir.exists():
            pdf_files = list(uploaded_resumes_dir.glob("*.pdf"))
            # #region agent log
            with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"I2","location":"GptJson.py:636","message":"Starting PDF matching","data":{"resume_name":resume_name,"candidate_name":candidate_name,"candidate_id":candidate_id,"total_pdfs":len(pdf_files)},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            
            # Strategy 1: Match by candidate name FIRST (most reliable - from actual resume content)
            # This handles cases where filename is wrong but content has correct name
            if candidate_name and len(normalized_candidate_name) > 3:
                candidate_words = [w for w in normalized_candidate_name.split() if len(w) > 2]
                if candidate_words:
                    for pdf_file in pdf_files:
                        pdf_stem = pdf_file.stem
                        pdf_normalized = normalize_for_matching(pdf_stem)
                        # Check if candidate name words appear in PDF filename
                        matches = sum(1 for word in candidate_words if word in pdf_normalized)
                        if matches >= min(2, len(candidate_words)):  # At least 2 words or all words if less than 2
                            matching_pdf = pdf_file
                            # #region agent log
                            with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                                log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"I2","location":"GptJson.py:650","message":"PDF matched by candidate name (PRIORITY)","data":{"pdf":pdf_file.name,"candidate_name":candidate_name,"matches":matches},"timestamp":int(time.time()*1000)})+"\n")
                            # #endregion
                            break
            
            # Strategy 2: Exact stem match (filename matching - less reliable)
            if not matching_pdf:
                for pdf_file in pdf_files:
                    pdf_stem = pdf_file.stem
                    if pdf_stem == resume_name:
                        matching_pdf = pdf_file
                        # #region agent log
                        with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                            log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"I2","location":"GptJson.py:660","message":"PDF matched by exact stem (filename)","data":{"pdf":pdf_file.name,"resume_name":resume_name},"timestamp":int(time.time()*1000)})+"\n")
                        # #endregion
                        break
            
            # Strategy 3: Fuzzy stem match (filename matching - less reliable)
            if not matching_pdf:
                for pdf_file in pdf_files:
                    pdf_stem = pdf_file.stem
                    pdf_normalized = normalize_for_matching(pdf_stem)
                    if (normalized_resume_name in pdf_normalized or pdf_normalized in normalized_resume_name) and len(normalized_resume_name) > 3:
                        matching_pdf = pdf_file
                        # #region agent log
                        with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                            log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"I2","location":"GptJson.py:671","message":"PDF matched by fuzzy stem (filename)","data":{"pdf":pdf_file.name,"resume_name":resume_name},"timestamp":int(time.time()*1000)})+"\n")
                        # #endregion
                        break
        
        # Strategy 4: Find unmapped PDFs (last resort - only if we have candidate_id)
        # This ensures we map candidate_id even if filename/name matching fails
        if not matching_pdf and candidate_id and uploaded_resumes_dir.exists():
            mapped_pdf_paths = set(pdf_mapping.values())
            pdf_files = list(uploaded_resumes_dir.glob("*.pdf"))
            unmapped_pdfs = [pdf for pdf in pdf_files if str(pdf.resolve()) not in mapped_pdf_paths]
            if unmapped_pdfs:
                # Use the first unmapped PDF as fallback
                matching_pdf = unmapped_pdfs[0]
                # #region agent log
                with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                    log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"I2","location":"GptJson.py:688","message":"PDF matched by fallback (unmapped)","data":{"pdf":matching_pdf.name,"candidate_id":candidate_id},"timestamp":int(time.time()*1000)})+"\n")
                # #endregion
        
        # Update mapping with candidate_id and name
        # CRITICAL: Always prioritize candidate_id and actual candidate name (from content) over filename
        if matching_pdf:
            pdf_path_str = str(matching_pdf.resolve())
            
            # Map by candidate_id (MOST RELIABLE - generated from actual resume content, not filename)
            # This is the primary mapping key that should always be used
            if candidate_id:
                pdf_mapping[candidate_id] = pdf_path_str
                # #region agent log
                with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                    log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"I2","location":"GptJson.py:695","message":"Mapping PDF by candidate_id","data":{"candidate_id":candidate_id,"pdf":matching_pdf.name,"candidate_name":candidate_name},"timestamp":int(time.time()*1000)})+"\n")
                # #endregion
            
            # Map by candidate name using the SAME normalization as main.py
            # This MUST match main.py's normalize_name function exactly
            def normalize_name_for_mapping(name: str) -> str:
                """Normalize name to match main.py's normalize_name function EXACTLY"""
                if not name:
                    return ""
                import unicodedata
                name = unicodedata.normalize("NFKD", name)
                name = "".join(c for c in name if not unicodedata.combining(c))
                # Match main.py's normalize_name: lowercase, replace spaces/hyphens with underscores, remove dots, strip underscores
                return (
                    name.lower()
                    .replace(" ", "_")
                    .replace("-", "_")
                    .replace(".", "")
                    .strip("_")
                )
            
            # Map by actual candidate name (from content) - SECOND PRIORITY
            if candidate_name:
                # Use normalized name (matches main.py's normalize_name)
                norm_name = normalize_name_for_mapping(candidate_name)
                if norm_name:
                    pdf_mapping[norm_name] = pdf_path_str
                # Also map by various name formats for backward compatibility
                pdf_mapping[candidate_name.strip().title()] = pdf_path_str
                pdf_mapping[candidate_name] = pdf_path_str
                pdf_mapping[candidate_name.replace(" ", "_")] = pdf_path_str
                pdf_mapping[candidate_name.replace(" ", "-")] = pdf_path_str
                # Map by lowercase version too
                pdf_mapping[candidate_name.lower()] = pdf_path_str
            
            # Map by filename as fallback only (THIRD PRIORITY - least reliable)
            # Keep filename mapping for backward compatibility, but it's not the primary method
            pdf_mapping[resume_name] = pdf_path_str
            if matching_pdf.name not in pdf_mapping:
                pdf_mapping[matching_pdf.name] = pdf_path_str
            # Also map by PDF stem (normalized) as fallback
            pdf_stem_norm = normalize_name_for_mapping(matching_pdf.stem)
            if pdf_stem_norm:
                pdf_mapping[pdf_stem_norm] = pdf_path_str
        elif candidate_id:
            # Even if no PDF match found, try to map candidate_id to any available PDF
            # This ensures candidate_id is in the mapping for later lookup
            if uploaded_resumes_dir.exists():
                pdf_files = list(uploaded_resumes_dir.glob("*.pdf"))
                mapped_pdf_paths = set(pdf_mapping.values())
                
                # Normalize name function (same as above - MUST match main.py exactly)
                def normalize_name_for_mapping(name: str) -> str:
                    """Normalize name to match main.py's normalize_name function EXACTLY"""
                    if not name:
                        return ""
                    import unicodedata
                    name = unicodedata.normalize("NFKD", name)
                    name = "".join(c for c in name if not unicodedata.combining(c))
                    # Match main.py's normalize_name: lowercase, replace spaces/hyphens with underscores, remove dots, strip underscores
                    return (
                        name.lower()
                        .replace(" ", "_")
                        .replace("-", "_")
                        .replace(".", "")
                        .strip("_")
                    )
                
                # Find any unmapped PDF
                unmapped_found = False
                for pdf_file in pdf_files:
                    pdf_path_str = str(pdf_file.resolve())
                    if pdf_path_str not in mapped_pdf_paths:
                        # Map candidate_id to this PDF as fallback
                        pdf_mapping[candidate_id] = pdf_path_str
                        if candidate_name:
                            norm_name = normalize_name_for_mapping(candidate_name)
                            if norm_name:
                                pdf_mapping[norm_name] = pdf_path_str
                            pdf_mapping[candidate_name.strip().title()] = pdf_path_str
                            pdf_mapping[candidate_name] = pdf_path_str
                        pdf_mapping[resume_name] = pdf_path_str
                        unmapped_found = True
                        # #region agent log
                        with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                            log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"I2","location":"GptJson.py:720","message":"PDF mapped by fallback (unmapped PDF)","data":{"pdf":pdf_file.name,"candidate_id":candidate_id},"timestamp":int(time.time()*1000)})+"\n")
                        # #endregion
                        break
                
                if not unmapped_found and pdf_files:
                    # No unmapped PDFs found - try to use any PDF (last resort)
                    pdf_file = pdf_files[0]
                    pdf_path_str = str(pdf_file.resolve())
                    pdf_mapping[candidate_id] = pdf_path_str
                    if candidate_name:
                        norm_name = normalize_name_for_mapping(candidate_name)
                        if norm_name:
                            pdf_mapping[norm_name] = pdf_path_str
                        pdf_mapping[candidate_name.strip().title()] = pdf_path_str
                        pdf_mapping[candidate_name] = pdf_path_str
                    pdf_mapping[resume_name] = pdf_path_str
                    # #region agent log
                    with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                        log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"I2","location":"GptJson.py:735","message":"PDF mapped by last resort (any PDF)","data":{"pdf":pdf_file.name,"candidate_id":candidate_id},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                elif not pdf_files:
                    # #region agent log
                    with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                        log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"I2","location":"GptJson.py:740","message":"No PDFs available for mapping","data":{"candidate_id":candidate_id,"uploaded_dir":str(uploaded_resumes_dir)},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
        
        # Save mapping (even if no match found, we may have added candidate_id mapping)
        if candidate_id or matching_pdf:
            try:
                pdf_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                # #region agent log
                with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                    log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"B","location":"GptJson.py:696","message":"Saving PDF mapping","data":{"candidate_id":candidate_id,"candidate_name":candidate_name,"resume_name":resume_name,"matching_pdf":str(matching_pdf) if matching_pdf else None,"mapping_keys":list(pdf_mapping.keys())[:10]},"timestamp":int(time.time()*1000)})+"\n")
                # #endregion
                with open(pdf_mapping_file, "w", encoding="utf-8") as f:
                    json.dump(pdf_mapping, f, indent=2)
                # #region agent log
                with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                    log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"B","location":"GptJson.py:702","message":"PDF mapping saved successfully","data":{"file":str(pdf_mapping_file),"size":len(json.dumps(pdf_mapping))},"timestamp":int(time.time()*1000)})+"\n")
                # #endregion
            except Exception as e:
                # #region agent log
                with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                    log.write(json.dumps({"sessionId":"debug-session","runId":"pdf-mapping","hypothesisId":"B","location":"GptJson.py:705","message":"Error saving PDF mapping","data":{"error":str(e)},"timestamp":int(time.time()*1000)})+"\n")
                # #endregion
                pass  # Non-critical, continue processing
        
        # Save with validation
        safe_json_save(parsed, out_path)
        
        # Cache the result
        resume_cache.set(cache_key, parsed)
        
        return True, f"OK: {out_path.name} (candidate_id: {candidate_id})"
        
    except Exception as e:
        err_msg = f"Failed to process {in_path_obj.name}: {repr(e)}"
        logging.error(err_msg)
        
        # Log failed resume to Skipped.json
        try:
            from datetime import datetime
            skipped_file = Path("Ranking/Skipped.json")
            skipped_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Try to extract any available info from the file
            failed_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "name": in_path_obj.stem,
                "candidate_id": None,
                "reason": f"Processing failed: {str(e)}",
                "file": in_path_obj.name
            }
            
            # #region agent log
            with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson-error","hypothesisId":"F","location":"GptJson.py:710","message":"Logging failed resume to Skipped.json","data":{"file":in_path_obj.name,"skipped_file":str(skipped_file),"exists":skipped_file.exists()},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            
            # Load existing skipped entries
            existing_skipped = []
            if skipped_file.exists():
                try:
                    with open(skipped_file, "r", encoding="utf-8") as f:
                        existing_skipped = json.load(f)
                        if not isinstance(existing_skipped, list):
                            existing_skipped = []
                    # #region agent log
                    with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                        log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson-error","hypothesisId":"F","location":"GptJson.py:720","message":"Loaded existing skipped entries","data":{"count":len(existing_skipped)},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                except Exception as load_err:
                    # #region agent log
                    with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                        log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson-error","hypothesisId":"F","location":"GptJson.py:723","message":"Error loading skipped entries","data":{"error":str(load_err)},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
                    existing_skipped = []
            
            # Add failed entry
            existing_skipped.append(failed_entry)
            
            # Save back
            with open(skipped_file, "w", encoding="utf-8") as f:
                json.dump(existing_skipped, f, indent=2)
            # #region agent log
            with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson-error","hypothesisId":"F","location":"GptJson.py:732","message":"Successfully wrote failed resume to Skipped.json","data":{"total_entries":len(existing_skipped)},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
        except Exception as log_error:
            # #region agent log
            with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson-error","hypothesisId":"F","location":"GptJson.py:735","message":"Error logging to Skipped.json","data":{"error":str(log_error)},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion
            # Don't fail if logging to Skipped.json fails
            logging.warning(f"Could not log to Skipped.json: {log_error}")
        
        return False, f"ERROR: {err_msg}"


def process_all(input_dir: str, output_dir: str, parallel: bool = True, max_workers: int = 5, only_files: list = None):
    """
    Process all resumes with optional parallel processing.
    
    Args:
        input_dir: Input directory with .txt files
        output_dir: Output directory for .json files
        parallel: Whether to use parallel processing
        max_workers: Number of parallel workers (if parallel=True)
        only_files: Optional list of specific filenames to process (if None, processes all)
    """
    all_files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith(".txt")])
    
    # Filter to only process specified files if provided
    if only_files:
        files = [f for f in all_files if f in only_files]
        if not files:
            print(f"[INFO] No matching files found in {input_dir} from the specified list")
            return
        print(f"[INFO] Processing only {len(files)} newly uploaded file(s) out of {len(all_files)} total files")
    else:
        files = all_files
    
    if not files:
        print(f"[INFO] No .txt files found in {input_dir}")
        return

    # Build map of existing candidate_ids
    # NOTE: ProcessedJson should be cleared before this runs, so this should be empty
    # But we check anyway to handle edge cases
    existing_candidate_ids = set()
    output_path = Path(output_dir)
    if output_path.exists():
        existing_files = list(output_path.glob("*.json"))
        # #region agent log
        with open(".cursor/debug.log", "a", encoding="utf-8") as log:
            log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson","hypothesisId":"I1","location":"GptJson.py:819","message":"Checking existing ProcessedJson files","data":{"existing_count":len(existing_files),"output_dir":output_dir},"timestamp":int(time.time()*1000)})+"\n")
        # #endregion
        for existing_json in existing_files:
            try:
                existing_data = safe_json_load(existing_json, {})
                if isinstance(existing_data, dict) and "candidate_id" in existing_data:
                    candidate_id = existing_data["candidate_id"]
                    existing_candidate_ids.add(candidate_id)
                    # #region agent log
                    with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                        log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson","hypothesisId":"I1","location":"GptJson.py:825","message":"Found existing candidate_id","data":{"candidate_id":candidate_id,"file":existing_json.name},"timestamp":int(time.time()*1000)})+"\n")
                    # #endregion
            except Exception:
                continue
        
        if existing_candidate_ids:
            print(f"[WARNING] Found {len(existing_candidate_ids)} existing candidate_id(s) in ProcessedJson. These will be skipped if duplicates are found.")
            # #region agent log
            with open(".cursor/debug.log", "a", encoding="utf-8") as log:
                log.write(json.dumps({"sessionId":"debug-session","runId":"gptjson","hypothesisId":"I1","location":"GptJson.py:832","message":"Existing candidate_ids found","data":{"count":len(existing_candidate_ids)},"timestamp":int(time.time()*1000)})+"\n")
            # #endregion

    print(f"[INFO] Processing {len(files)} files from {input_dir} -> {output_dir}")
    if parallel:
        print(f"[INFO] Using parallel processing with {max_workers} workers")
        from concurrent.futures import ThreadPoolExecutor, as_completed
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(process_single_resume, 
                               os.path.join(input_dir, fname), 
                               output_dir, 
                               existing_candidate_ids): fname 
                for fname in files
            }
            
            completed = 0
            for future in as_completed(futures):
                fname = futures[future]
                completed += 1
                try:
                    success, message = future.result(timeout=300)  # 5 minute timeout per file
                    status = "✅" if success else "❌"
                    print(f"[{completed}/{len(files)}] {status} {message}")
                except Exception as e:
                    print(f"[{completed}/{len(files)}] ❌ ERROR processing {fname}: {e}")
                    import traceback
                    traceback.print_exc()
        
        print(f"[INFO] Parallel processing completed: {completed}/{len(files)} files processed")
    else:
        # Sequential processing (original behavior)
        for i, fname in enumerate(files, start=1):
            in_path = os.path.join(input_dir, fname)
            success, message = process_single_resume(in_path, output_dir, existing_candidate_ids)
            status = "✅" if success else "❌"
            print(f"[{i}/{len(files)}] {status} {message}")
    
    # Post-processing: Ensure all candidate_ids are mapped to PDFs (non-blocking, fast)
    try:
        print(f"\n[INFO] Post-processing: Ensuring all candidate_ids are mapped to PDFs...")
        uploaded_resumes_dir = Path("Uploaded_Resumes")
        pdf_mapping_file = uploaded_resumes_dir / "pdf_mapping.json"
        
        # Load final mapping
        final_pdf_mapping = {}
        if pdf_mapping_file.exists():
            try:
                with open(pdf_mapping_file, "r", encoding="utf-8") as f:
                    final_pdf_mapping = json.load(f)
            except Exception:
                final_pdf_mapping = {}
        
        # Get all processed JSON files and their candidate_ids (only from current batch)
        output_path = Path(output_dir)
        unmapped_candidate_ids = []
        if output_path.exists():
            # Only check files that were just processed (match the input files)
            processed_stems = {Path(f).stem for f in files}
            for json_file in output_path.glob("*.json"):
                if json_file.name == "example_output.json":
                    continue
                # Only process files that match our input files
                if json_file.stem not in processed_stems:
                    continue
                try:
                    data = safe_json_load(json_file, {})
                    candidate_id = data.get("candidate_id")
                    candidate_name = data.get("name", "")
                    if candidate_id and candidate_id not in final_pdf_mapping:
                        unmapped_candidate_ids.append((candidate_id, candidate_name, json_file.stem))
                except Exception:
                    continue
        
        # Try to map unmapped candidate_ids to available PDFs (limit to avoid long processing)
        if unmapped_candidate_ids and uploaded_resumes_dir.exists() and len(unmapped_candidate_ids) <= 1000:
            pdf_files = list(uploaded_resumes_dir.glob("*.pdf"))
            if len(pdf_files) <= 10000:  # Limit PDF count to avoid performance issues
                mapped_pdf_paths = set(final_pdf_mapping.values())
                unmapped_pdfs = [pdf for pdf in pdf_files if str(pdf.resolve()) not in mapped_pdf_paths]
                
                def normalize_name_for_mapping(name: str) -> str:
                    """Normalize name to match main.py's normalize_name function EXACTLY"""
                    if not name:
                        return ""
                    import unicodedata
                    name = unicodedata.normalize("NFKD", name)
                    name = "".join(c for c in name if not unicodedata.combining(c))
                    return (
                        name.lower()
                        .replace(" ", "_")
                        .replace("-", "_")
                        .replace(".", "")
                        .strip("_")
                    )
                
                mapped_count = 0
                # Limit processing to avoid blocking
                max_to_process = min(100, len(unmapped_candidate_ids))
                for candidate_id, candidate_name, resume_stem in unmapped_candidate_ids[:max_to_process]:
                    # Try to find matching PDF
                    matching_pdf = None
                    norm_name = normalize_name_for_mapping(candidate_name) if candidate_name else ""
                    
                    # Try matching by name (limit search)
                    if norm_name and len(unmapped_pdfs) <= 1000:
                        for pdf in unmapped_pdfs[:500]:  # Limit search
                            pdf_stem_norm = normalize_name_for_mapping(pdf.stem)
                            if pdf_stem_norm == norm_name:
                                matching_pdf = pdf
                                break
                    
                    # If no match, use first unmapped PDF
                    if not matching_pdf and unmapped_pdfs:
                        matching_pdf = unmapped_pdfs.pop(0)
                    
                    if matching_pdf:
                        pdf_path_str = str(matching_pdf.resolve())
                        final_pdf_mapping[candidate_id] = pdf_path_str
                        if norm_name:
                            final_pdf_mapping[norm_name] = pdf_path_str
                        if candidate_name:
                            final_pdf_mapping[candidate_name.strip().title()] = pdf_path_str
                        final_pdf_mapping[resume_stem] = pdf_path_str
                        mapped_count += 1
                        # Remove from unmapped list if it was there
                        if matching_pdf in unmapped_pdfs:
                            unmapped_pdfs.remove(matching_pdf)
                
                # Save updated mapping
                if mapped_count > 0:
                    try:
                        pdf_mapping_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(pdf_mapping_file, "w", encoding="utf-8") as f:
                            json.dump(final_pdf_mapping, f, indent=2)
                        print(f"[INFO] Post-processed: Mapped {mapped_count} additional candidate_id(s) to PDFs")
                    except Exception as e:
                        print(f"[WARNING] Could not save post-processed PDF mapping: {e}")
        elif unmapped_candidate_ids:
            print(f"[INFO] Post-processing skipped: Too many files to process ({len(unmapped_candidate_ids)} unmapped)")
    except Exception as e:
        # Don't let post-processing block the main process
        print(f"[WARNING] Post-processing PDF mapping failed (non-critical): {e}")
        import traceback
        traceback.print_exc()


# ---------------------------
# Example JSON writer
# ---------------------------
def write_example(output_dir: str):
    # example = {
    #     "candidate_id": "example_0001",
    #     "name": "Jane Doe",
    #     "role_claim": "Fullstack Engineer / Solution Architect",
    #     "years_experience": 6,
    #     "location": "Bengaluru, India",
    #     "contact": {"email": "jane@example.com", "phone": "+91-XXXXXXXXXX", "profile": "https://linkedin.example/jane"},
    #     "domain_tags": ["Fullstack", "Solution Architecture", "Cloud"],
    #     "profile_keywords_line": "Fullstack Engineer - 6 Yrs - React, Node.js - AWS - Microservices",
    #     "canonical_skills": {"programming": ["Python"], "frontend": ["React"], "backend": ["Node.js"], "cloud": ["AWS"], "databases": ["PostgreSQL"], "infra": [], "devtools": [], "methodologies": []},
    #     "inferred_skills": [],
    #     "skill_proficiency": [],
    #     "projects": [],
    #     "experience_entries": [],
    #     "ats_boost_line": "python, react, node.js, aws, postgresql",
    #     "embedding_hints": {"profile_embed": "Fullstack Engineer|React|Node.js|AWS", "projects_embed": "", "skills_embed": "python,react,node.js"},
    #     "explainability": {"top_matched_sentences": [], "top_matched_keywords": []},
    #     "meta": {"raw_text_length": 2500, "keyword_occurrences": {}, "last_updated": time.strftime("%Y-%m-%d")}
    # }

    out_path = Path(output_dir) / "example_output.json"
    # with open(out_path, "w", encoding="utf-8") as fx:
    #     json.dump(example, fx, indent=2, ensure_ascii=False)
    print(f"[INFO] Example JSON written to {out_path}")


# ---------------------------
# Entrypoint
# ---------------------------
if __name__ == "__main__":
    import argparse
    import os
    
    # Check for parallel flag from environment or command line
    parallel_env = os.getenv("ENABLE_PARALLEL", "false").lower() == "true"
    workers_env = int(os.getenv("MAX_WORKERS", "5"))
    
    # Check for list of files to process (from session state or environment)
    only_files = None
    try:
        import streamlit as st
        if hasattr(st, 'session_state') and 'newly_uploaded_files' in st.session_state:
            only_files = st.session_state.newly_uploaded_files
    except Exception:
        pass
    
    # Also check environment variable as fallback
    if not only_files:
        only_files_env = os.getenv("ONLY_PROCESS_FILES", "")
        if only_files_env:
            only_files = [f.strip() for f in only_files_env.split(",") if f.strip()]
    
    parser = argparse.ArgumentParser(description="Process resumes with optional parallel processing")
    parser.add_argument("--parallel", action="store_true", default=parallel_env, help="Enable parallel processing")
    parser.add_argument("--workers", type=int, default=workers_env, help="Number of parallel workers")
    parser.add_argument("--only-files", nargs="+", default=only_files, help="Only process these specific files")
    args = parser.parse_args()
    
    process_all(INPUT_DIR, OUTPUT_DIR, parallel=args.parallel, max_workers=args.workers, only_files=args.only_files)
    print("[DONE] Processing finished.")


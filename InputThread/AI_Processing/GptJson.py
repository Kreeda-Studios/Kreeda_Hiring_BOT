#!/usr/bin/env python3
"""
Rich Resume TXT -> Normalized JSON converter
- General-purpose (AI/ML, Fullstack, Testing, DB modeling, Cloud, Solution Arch, Sales, etc.)
- Uses OpenAI function-calling for consistent structured output.
- No retries, no fallback parsing: if the model does not return the function-call JSON, the file is skipped and logged.
"""

import os
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
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-4.1-nano"   # inexpensive model that supports function calling
MAX_RESPONSE_TOKENS = 2500
# ---------------------------




import os
import json
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Any, List

try:
    from openai import OpenAI
except Exception:
    raise RuntimeError("Install the OpenAI Python SDK (>=1.0.0): pip install openai") from None

# Setup OpenAI client (new API)
client = OpenAI(api_key=OPENAI_API_KEY)

Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# Retrive Domain Tags
def load_domain_tags():
    with open(JD_JSON, "r", encoding="utf-8") as f:
        jd_data = json.load(f)
    domain_tags = jd_data.get("domain_tags", [])
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
def generate_candidate_id(filename: str) -> str:
    base = Path(filename).stem
    return f"{base}_{uuid.uuid4().hex[:8]}"


def _canonicalize_token(token: str) -> str:
    return token.strip()


def canonicalize_string_list(arr: List[str]) -> List[str]:
    out = []
    for token in arr or []:
        can = _canonicalize_token(token)
        if can and can not in out:
            out.append(can)
    return out


def canonicalize_skills_block(skills_block: Dict[str, List[str]]) -> Dict[str, List[str]]:
    out = {}
    for cat, arr in (skills_block or {}).items():
        out[cat] = canonicalize_string_list(arr)
    return out


# ---------------------------
# Core processing
# ---------------------------
def process_resume_file(path: str) -> Dict[str, Any]:
    filename = os.path.basename(path)
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    candidate_id = generate_candidate_id(filename)

    # system_msg = {
    #     "role": "system",
    #     "content": (
    #         "You are a structured resume parser. The caller will provide raw resume text. "
    #         "Return EXACTLY one function call to 'parse_resume_detailed' with JSON arguments that match the schema. "
    #         "Minimize filler language; produce concise canonical tokens. "
    #         "Include provenance spans (character offsets) for extracted projects/skills when found in the text. "
    #         "If a value cannot be determined, return empty string, empty list or empty object. "
    #         "Deduce keywords specific to the domain from indirect entries (Projects, Skills, Experience). "
    #         "For Projects except for the dates, do not leave any field blank. "
    #         "Strictly mention role, domain, and most relevant technical keywords."
            
    #     )
    # }

    # sYSTEM MESSAGE WITH DOMAIN TAGS FOR BETTER METRICS
    system_msg = {
        "role": "system",
        "content": (
            "You are a structured resume parser. The caller will provide raw resume text. "
            "Return EXACTLY one function call to 'parse_resume_detailed' with JSON arguments that match the schema. "
            "Minimize filler language; produce concise canonical tokens. "
            "Include provenance spans (character offsets) for extracted projects/skills when found in the text. "
            "If a value cannot be determined, return empty string, empty list or empty object. "
            "Deduce keywords specific to the domain from indirect entries (Projects, Skills, Experience). "
            "IMPORTANT for Projects field except for the dates, STRICTLY do not leave any field blank." 
            "IMPORTANT Have project metrics on each project"
            "Strictly mention role, domain, and most relevant technical keywords. "
            f"\n\nIMPORTANT: The Job Description domain tags are: {domain_tags}. "
            f"Strictly judge and score projects/skills higher if they align strictly with these domains : {domain_tags}, and score projects unrelated or in irrelevant domains low. Only relevant projects should score higher, Judge with high Strictness"
            ""
        )
    }

    user_msg = {
        "role": "user",
        "content": f"CandidateID: {candidate_id}\n\nRawResumeText:\n```\n{raw_text}\n```"
    }

    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[system_msg, user_msg],
        functions=[PARSE_FUNCTION],
        function_call="auto",
        temperature=0.0,
        max_tokens=MAX_RESPONSE_TOKENS
    )

    choice = resp.choices[0]
    msg = choice.message

    func_call = getattr(msg, "function_call", None)
    if not func_call and isinstance(msg, dict):
        func_call = msg.get("function_call")
    if not func_call:
        raise RuntimeError("Model did not return function_call response. Skipping file.")

    args_text = getattr(func_call, "arguments", None) or func_call.get("arguments")
    if not args_text:
        raise RuntimeError("Function call returned but 'arguments' missing. Skipping file.")

    parsed = json.loads(args_text)

    parsed.setdefault("candidate_id", candidate_id)
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

    return parsed


# ---------------------------
# Batch processing
# ---------------------------
# def process_all(input_dir: str, output_dir: str):
#     files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith(".txt")])
#     if not files:
#         print(f"[INFO] No .txt files found in {input_dir}")
#         return

#     print(f"[INFO] Processing {len(files)} files from {input_dir} -> {output_dir}")
#     for i, fname in enumerate(files, start=1):
#         in_path = os.path.join(input_dir, fname)
#         out_path = os.path.join(output_dir, Path(fname).stem + ".json")
#         print(f"[{i}/{len(files)}] {fname}")

#         try:
#             parsed = process_resume_file(in_path)
#             with open(out_path, "w", encoding="utf-8") as wf:
#                 json.dump(parsed, wf, indent=2, ensure_ascii=False)
#             print(f"  [OK] -> {out_path}")

#         except Exception as e:
#             err_msg = f"Failed to process {fname}: {repr(e)}"
#             print(f"  [ERROR] {err_msg}")
#             logging.error(err_msg)


# New function with skipping
def process_all(input_dir: str, output_dir: str):
    files = sorted([f for f in os.listdir(input_dir) if f.lower().endswith(".txt")])
    if not files:
        print(f"[INFO] No .txt files found in {input_dir}")
        return

    print(f"[INFO] Processing {len(files)} files from {input_dir} -> {output_dir}")
    for i, fname in enumerate(files, start=1):
        in_path = os.path.join(input_dir, fname)
        out_path = os.path.join(output_dir, Path(fname).stem + ".json")

        # ✅ Skip if already processed
        if os.path.exists(out_path):
            print(f"[{i}/{len(files)}] {fname} -> Skipped (already processed)")
            continue

        print(f"[{i}/{len(files)}] {fname}")
        try:
            parsed = process_resume_file(in_path)
            with open(out_path, "w", encoding="utf-8") as wf:
                json.dump(parsed, wf, indent=2, ensure_ascii=False)
            print(f"  [OK] -> {out_path}")

        except Exception as e:
            err_msg = f"Failed to process {fname}: {repr(e)}"
            print(f"  [ERROR] {err_msg}")
            logging.error(err_msg)


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
    # print("[START] Rich resume processing")
    # print(f"INPUT_DIR = {INPUT_DIR}")
    # print(f"OUTPUT_DIR = {OUTPUT_DIR}")
    # print(f"MODEL = {MODEL_NAME}")

    # write_example(OUTPUT_DIR)
    process_all(INPUT_DIR, OUTPUT_DIR)
    print("[DONE] Processing finished.")


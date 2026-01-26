# #!/usr/bin/env python3
# """
# JD TXT -> Normalized JSON converter
# - Extracts structured Job Description JSON for comparison with resumes.
# - Designed for keyword and semantic matching: no information loss, all skills + nuances captured.
# - Output is always written to JD.json (overwritten each run).
# """

# import os
# import streamlit as st
# # from dotenv import load_dotenv

# # # Load from your .env file
# # load_dotenv(".env")

# # ---------------------------
# # PATHS & CONFIG
# # ---------------------------
# INPUT_FILE = "InputThread/JD/JD.txt"
# OUTPUT_FILE = "InputThread/JD/JD.json"
# LOG_FILE = "processing_errors.log"
# OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY")
# MODEL_NAME = "gpt-4o-mini"
# MAX_RESPONSE_TOKENS = 2500
# # ---------------------------

# import os
# import json
# import logging
# import time
# from pathlib import Path

# try:
#     from openai import OpenAI
# except Exception:
#     raise RuntimeError("Install the OpenAI Python SDK: pip install openai") from None

# # Setup OpenAI client
# client = OpenAI(api_key=OPENAI_API_KEY)

# Path(os.path.dirname(OUTPUT_FILE)).mkdir(parents=True, exist_ok=True)
# logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# # ---------------------------
# # JSON schema for JD parsing
# # ---------------------------
# PARSE_FUNCTION = {
#     "name": "parse_jd_detailed",
#     "description": "Return an extremely detailed Job Description JSON for ATS + semantic matching. Capture every explicit and implicit requirement, normalize skills, attach provenance, create weighted keywords, and compute HR_Points (+1 per recommendation/extra inferred requirement logged).",
#     "parameters": {
#         "type": "object",
#         "properties": {
#             # --- Core role context ---
#             "role_title": {"type": "string", "description": "Exact job title as written in JD"},
#             "alt_titles": {"type": "array", "items": {"type": "string"}, "description": "Other possible role labels or synonyms"},
#             "seniority_level": {"type": "string", "description": "Explicit or inferred level: Junior, Mid, Senior, Lead, Principal, Staff"},
#             "department": {"type": "string", "description": "Business function / unit e.g., Engineering, Marketing, HR"},
#             "industry": {"type": "string", "description": "Target industry e.g., Finance, Healthcare, SaaS, Manufacturing"},
#             "domain_tags": {
#                 "type": "array",
#                 "items": {"type": "string"},
#                 "description": "High-level buckets e.g., AIML, Fullstack, Cloud, Testing, Sales, Data, Security. Must not skew to one domain; capture all relevant."
#             },

#             # --- Work model & logistics ---
#             "location": {"type": "string", "description": "City / Region / Country if given"},
#             "work_model": {"type": "string", "description": "Remote / Hybrid / Onsite (+days onsite if hybrid)"},
#             "employment_type": {"type": "string", "description": "Full-time, Contract, Internship, Part-time"},
#             "contract": {
#                 "type": "object",
#                 "description": "Capture contract details if explicitly mentioned",
#                 "properties": {
#                     "duration_months": {"type": "integer"},
#                     "extendable": {"type": "boolean"}
#                 }
#             },
#             "start_date_preference": {"type": "string", "description": "Immediate / Within X weeks / Specific date"},
#             "travel_requirement_percent": {"type": "number", "description": "Expected % of travel if stated"},
#             "work_hours": {"type": "string", "description": "General working hours or shift pattern"},
#             "shift_details": {"type": "string", "description": "Day, Night, Rotational"},
#             "visa_sponsorship": {"type": "boolean", "description": "True if JD states sponsorship available"},
#             "clearances_required": {"type": "array", "items": {"type": "string"}, "description": "Background checks, security clearances etc."},

#             # --- Experience & education ---
#             "years_experience_required": {"type": "number", "description": "Minimum total years of professional experience"},
#             "education_requirements": {"type": "array", "items": {"type": "string"}, "description": "Explicitly listed degrees/courses"},
#             "min_degree_level": {"type": "string", "description": "e.g., Bachelors, Masters, PhD, or 'Open'"},
#             "fields_of_study": {"type": "array", "items": {"type": "string"}, "description": "Relevant academic disciplines"},
#             "certifications_required": {"type": "array", "items": {"type": "string"}},
#             "certifications_preferred": {"type": "array", "items": {"type": "string"}},

#             # --- Skills ---
#             "required_skills": {
#                 "type": "array", "items": {"type": "string"},
#                 "description": "Explicit must-have skills mentioned in JD"
#             },
#             "preferred_skills": {
#                 "type": "array", "items": {"type": "string"},
#                 "description": "Optional / good-to-have skills"
#             },
#             "tools_tech": {"type": "array", "items": {"type": "string"}, "description": "technologies, libraries, frameworks, tools (relevant to the domain - go indepth)"},
#             "soft_skills": {"type": "array", "items": {"type": "string"}, "description": "Non-technical skills e.g., communication, leadership"},
#             "languages": {"type": "array", "items": {"type": "string"}, "description": "Spoken or programming languages (disambiguate via context)"},
#             "canonical_skills": {
#                 "type": "object",
#                 "description": "Add categories used in JD for direct ATS scoring compatibility, mention all frameworks, libraries necessary for the programming languages mentioned even if its not in the JD",
#                 "properties": {
#                     "programming": {"type": "array", "items": {"type": "string"}},
#                     "frameworks": {"type": "array", "items": {"type": "string"}},
#                     "libraries": {"type": "array", "items": {"type": "string"}},
#                     "ml_ai": {"type": "array", "items": {"type": "string"}},
#                     "frontend": {"type": "array", "items": {"type": "string"}},
#                     "backend": {"type": "array", "items": {"type": "string"}},
#                     "testing": {"type": "array", "items": {"type": "string"}},
#                     "databases": {"type": "array", "items": {"type": "string"}},
#                     "cloud": {"type": "array", "items": {"type": "string"}},
#                     "infra": {"type": "array", "items": {"type": "string"}},
#                     "devtools": {"type": "array", "items": {"type": "string"}},
#                     "methodologies": {"type": "array", "items": {"type": "string"}}
#                 }
#             },
#             "skill_requirements": {
#                 "type": "array",
#                 "description": "Fine-grained structured skills with level, category, provenance",
#                 "items": {
#                     "type": "object",
#                     "properties": {
#                         "skill": {"type": "string"},
#                         "category": {"type": "string", "description": "e.g., programming, cloud, devtools"},
#                         "priority": {"type": "string", "description": "must-have | good-to-have"},
#                         "level": {"type": "string", "description": "novice | intermediate | advanced | expert"},
#                         "years_min": {"type": "number"},
#                         "versions": {"type": "array", "items": {"type": "string"}},
#                         "related_tools": {"type": "array", "items": {"type": "string"}},
#                         "mandatory": {"type": "boolean"},
#                         "provenance": {"type": "array", "items": {"type": "string"}}
#                     }
#                 }
#             },

#             # --- Duties & outcomes ---
#             "responsibilities": {"type": "array", "items": {"type": "string"}, "description": "Key tasks the role must perform"},
#             "deliverables": {"type": "array", "items": {"type": "string"}, "description": "Expected outputs / goals"},
#             "kpis_okrs": {"type": "array", "items": {"type": "string"}, "description": "Performance indicators if stated"},

#             # --- Team & reporting ---
#             "team_context": {
#                 "type": "object",
#                 "description": "Org context for the role",
#                 "properties": {
#                     "team_size": {"type": "integer"},
#                     "reports_to": {"type": "string"},
#                     "manages_team": {"type": "boolean"},
#                     "direct_reports": {"type": "integer"}
#                 }
#             },

#             # --- Constraints / exclusions / compliance ---
#             "exclusions": {"type": "array", "items": {"type": "string"}, "description": "Disqualifiers or anti-requirements"},
#             "compliance": {"type": "array", "items": {"type": "string"}, "description": "Legal/regulatory compliance needs"},
#             "screening_questions": {"type": "array", "items": {"type": "string"}},

#             # --- Interview process ---
#             "interview_process": {
#                 "type": "object",
#                 "description": "Stages and evaluation focus if listed",
#                 "properties": {
#                     "total_rounds": {"type": "integer"},
#                     "stages": {
#                         "type": "array",
#                         "items": {
#                             "type": "object",
#                             "properties": {
#                                 "name": {"type": "string"},
#                                 "purpose": {"type": "string"},
#                                 "skills_evaluated": {"type": "array", "items": {"type": "string"}}
#                             }
#                         }
#                     },
#                     "assignment_expected": {"type": "boolean"}
#                 }
#             },

#             # --- Compensation & benefits ---
#             "compensation": {
#                 "type": "object",
#                 "description": "Salary and perks if given",
#                 "properties": {
#                     "currency": {"type": "string"},
#                     "salary_min": {"type": "number"},
#                     "salary_max": {"type": "number"},
#                     "period": {"type": "string", "description": "yearly, monthly, hourly"},
#                     "bonus": {"type": "string"},
#                     "equity": {"type": "string"}
#                 }
#             },
#             "benefits": {"type": "array", "items": {"type": "string"}},

#             # --- Keywords for ATS scoring ---
#             "keywords_flat": {
#                 "type": "array", "items": {"type": "string"},
#                 "description": "Deduplicated, canonicalized tokens for exact-match scoring"
#             },
#             "keywords_weighted": {
#                 "type": "object",
#                 "additionalProperties": {"type": "number"},
#                 "description": "Token -> weight (0–1) reflecting importance"
#             },

#             # --- Weighting knobs ---
#             "weighting": {
#                 "type": "object",
#                 "description": "Relative importance across categories. Adjust dynamically per JD.",
#                 "properties": {
#                     "required_skills": {"type": "number"},
#                     "preferred_skills": {"type": "number"},
#                     "responsibilities": {"type": "number"},
#                     "domain_relevance": {"type": "number"},
#                     "technical_depth": {"type": "number"},
#                     "soft_skills": {"type": "number"},
#                     "education": {"type": "number"},
#                     "certifications": {"type": "number"},
#                     "keywords_exact": {"type": "number"},
#                     "keywords_semantic": {"type": "number"}
#                 }
#             },

#             # --- Embedding hints ---
#             "embedding_hints": {
#                 "type": "object",
#                 "properties": {
#                     "skills_embed": {"type": "string"},
#                     "responsibilities_embed": {"type": "string"},
#                     "overall_embed": {"type": "string"},
#                     "negatives_embed": {"type": "string"},
#                     "seniority_embed": {"type": "string"}
#                 }
#             },

#             # --- Explainability ---
#             "explainability": {
#                 "type": "object",
#                 "properties": {
#                     "top_jd_sentences": {"type": "array", "items": {"type": "string"}},
#                     "key_phrases": {"type": "array", "items": {"type": "string"}},
#                     "rationales": {"type": "array", "items": {"type": "string"}}
#                 }
#             },
#             "provenance_spans": {
#                 "type": "array",
#                 "description": "Character offsets of key items in the JD text",
#                 "items": {
#                     "type": "object",
#                     "properties": {
#                         "type": {"type": "string", "description": "e.g., skill, responsibility, exclusion"},
#                         "text": {"type": "string"}
#                     }
#                 }
#             },

#             # --- HR insights ---
#             "hr_points": {"type": "integer", "description": "Count of recommendations/extra inferred requirements"},
#             "hr_notes": {
#                 "type": "array",
#                 "description": "Each item adds +1 to hr_points. Use when JD suggests improvements or when NLP infers extra requirements.",
#                 "items": {
#                     "type": "object",
#                     "properties": {
#                         "category": {"type": "string", "description": "compensation | clarity | security | compliance etc."},
#                         "type": {"type": "string", "description": "recommendation | inferred_requirement"},
#                         "note": {"type": "string"},
#                         "impact": {"type": "number", "description": "0–1 perceived impact on hiring quality"},
#                         "reason": {"type": "string"},
#                         "source_provenance": {"type": "array", "items": {"type": "string"}}
#                     }
#                 }
#             },

#             # --- Meta ---
#             "meta": {
#                 "type": "object",
#                 "properties": {
#                     "jd_version": {"type": "string"},
#                     "raw_text_length": {"type": "integer"},
#                     "last_updated": {"type": "string"},
#                     "sections_detected": {"type": "array", "items": {"type": "string"}}
#                 }
#             }
#         },
#         "required": [
#             "role_title",
#             "required_skills",
#             "responsibilities",
#             "weighting",
#             "keywords_flat",
#             "keywords_weighted",
#             "hr_points",
#             "hr_notes"
#         ]
#     }
# }

# # ---------------------------
# # Core JD processor
# # ---------------------------
# def process_jd_file(in_path: str) -> dict:
#     with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
#         raw_text = f.read()

#     system_msg = {
#         "role": "system",
#         "content": (
#             "You are a meticulous Job Description (JD) parser for ATS + semantic matching. Add all information mentioned directly or indirectly, Make sure all information is captured without exception and if some information or skills are missing which are paramount or necessary but not present in the JD, add them yourself"
#             "The caller will provide raw JD text. Your task: return EXACTLY ONE function call to `parse_jd_detailed` "
#             "with arguments conforming to the provided schema. "
#             "Be exhaustive and precise: DO NOT lose information. Prefer concise, canonical tokens for skills.ADD Missing skills if relevant skills are missing from JD specific to the given domain."
#             "IMPORTANT In given domain add all specific languages (technical) and atleast 5 relevant frameworks , libraries to these languages"
#             "Normalize skills so they align with a resume ontology but do not remove any skills/tools from the JD"
#             "(programming, ml_ai, frontend, backend, testing, databases, cloud, infra, devtools, methodologies). "
#             "Populate fine-grained `skill_requirements` (level, years_min, versions, mandatory, related_tools). "
#             "Extract responsibilities, deliverables, KPIs/OKRs, exclusions, compliance, interview stages, "
#             "compensation if present, and team context. "
#             "Build `keywords_flat` (deduped, canonical tokens) and `keywords_weighted` (token -> importance 0–1). "
#             "Set `weighting` to reflect realistic hiring priorities "
#             "(e.g., required_skills > responsibilities > domain_relevance > technical_depth > preferred_skills > soft_skills; "
#             "adjust if the JD implies otherwise). "
#             "Provide `embedding_hints` to power semantic search (skills_embed, responsibilities_embed, overall_embed, "
#             "negatives_embed, seniority_embed). "
#             "Provide `provenance_spans` with character offsets for key items whenever feasible. "
#             "Provide `explainability` (top_jd_sentences, key_phrases, rationales). "
#             "HR Points rule (MANDATORY): Whenever you identify a recommendation or extra inferred requirement "
#             "(from wording, context, or common hiring practice), append an item to `hr_notes`. "
#             "Set hr_notes[i].type = 'recommendation' (if it improves clarity/completeness) or 'inferred_requirement' "
#             "(if the JD implies it indirectly). "
#             "Include category, note, reason, impact (0–1), and any source_provenance snippets. "
#             "Set `hr_points` = number of items in `hr_notes`. Each item contributes +1. "
#             "Do NOT add points for ordinary extractions. "
#             "IMPORTANT: If something is not stated, DO NOT hallucinate. Use `hr_notes` for recommendations instead of inventing facts. "
#             "If the JD is ambiguous (e.g., hybrid days, version specificity), log clarity recommendations in `hr_notes`. "
#             "Keep text fields concise but complete; avoid filler language. "
#             "Return ONLY the function call to `parse_jd_detailed` with its arguments."
#         )
#     }

#     user_msg = {"role": "user", "content": f"RawJDText:\n```\n{raw_text}\n```"}

#     resp = client.chat.completions.create(
#         model=MODEL_NAME,
#         messages=[system_msg, user_msg],
#         functions=[PARSE_FUNCTION],
#         function_call="auto",
#         temperature=0.0,
#         max_tokens=MAX_RESPONSE_TOKENS
#     )

#     choice = resp.choices[0]
#     msg = choice.message

#     func_call = getattr(msg, "function_call", None)
#     if func_call is None and isinstance(msg, dict):
#         func_call = msg.get("function_call")
#     if not func_call:
#         raise RuntimeError("Model did not return function_call response.")

#     args_text = getattr(func_call, "arguments", None) or func_call.get("arguments")
#     if not args_text:
#         raise RuntimeError("Function call arguments missing.")

#     parsed = json.loads(args_text)
#     parsed.setdefault("meta", {})
#     parsed["meta"].setdefault("raw_text_length", len(raw_text))
#     parsed["meta"].setdefault("last_updated", time.strftime("%Y-%m-%d"))

#     return parsed


# # ---------------------------
# # Entrypoint
# # ---------------------------
# if __name__ == "__main__":
#     print("[START] JD processing")
#     try:
#         jd_json = process_jd_file(INPUT_FILE)
#         with open(OUTPUT_FILE, "w", encoding="utf-8") as wf:
#             json.dump(jd_json, wf, indent=2, ensure_ascii=False)
#         print(f"[OK] JD JSON written -> {OUTPUT_FILE}")
#     except Exception as e:
#         logging.error(f"JD Processing failed: {repr(e)}")
#         print(f"[ERROR] JD processing failed: {e}")


#!/usr/bin/env python3
"""
JD TXT -> Normalized JSON converter
- Extracts structured Job Description JSON for comparison with resumes.
- Designed for keyword and semantic matching: no information loss, all skills + nuances captured.
- Output is always written to JD.json (overwritten each run).
"""

import os
import streamlit as st
from dotenv import load_dotenv

# Load from your .env file
load_dotenv(".env")

# ---------------------------
# PATHS & CONFIG
# ---------------------------
INPUT_FILE = "InputThread/JD/JD.txt"
OUTPUT_FILE = "InputThread/JD/JD.json"
LOG_FILE = "processing_errors.log"
# Try .env first, fallback to Streamlit secrets (for Streamlit Cloud compatibility)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    try:
        OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", None)
    except (AttributeError, KeyError, FileNotFoundError):
        OPENAI_API_KEY = None
MODEL_NAME = "gpt-4o-mini"
MAX_RESPONSE_TOKENS = 2500
# ---------------------------

import os
import json
import logging
import time
from pathlib import Path
import sys

# Add utils to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from utils.validation import validate_jd, JDSchema
from utils.retry import retry_api_call, openai_circuit_breaker
from utils.cache import jd_cache, get_jd_cache_key
from utils.common import extract_function_call, safe_json_load, safe_json_save

try:
    from openai import OpenAI
except Exception:
    raise RuntimeError("Install the OpenAI Python SDK: pip install openai") from None

# Validate API key
if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY not found! Please set it in:\n"
        "  For local development: Create .env file with OPENAI_API_KEY=your_key_here\n"
        "  For Streamlit Cloud: Go to Manage App -> Settings -> Secrets (UI)\n"
        "Get your API key from: https://platform.openai.com/api-keys"
    )

# Setup OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

Path(os.path.dirname(OUTPUT_FILE)).mkdir(parents=True, exist_ok=True)
logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


# ---------------------------
# JSON schema for JD parsing
# ---------------------------
PARSE_FUNCTION = {
    "name": "parse_jd_detailed",
    "description": "Return an extremely detailed Job Description JSON for ATS + semantic matching. Capture every explicit and implicit requirement, normalize skills, attach provenance, create weighted keywords, and compute HR_Points (+1 per recommendation/extra inferred requirement logged).",
    "parameters": {
        "type": "object",
        "properties": {
            # --- Core role context ---
            "role_title": {"type": "string", "description": "Exact job title as written in JD"},
            "alt_titles": {"type": "array", "items": {"type": "string"}, "description": "Other possible role labels or synonyms"},
            "seniority_level": {"type": "string", "description": "Explicit or inferred level: Junior, Mid, Senior, Lead, Principal, Staff"},
            "department": {"type": "string", "description": "Business function / unit e.g., Engineering, Marketing, HR"},
            "industry": {"type": "string", "description": "Target industry e.g., Finance, Healthcare, SaaS, Manufacturing"},
            "domain_tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "High-level buckets e.g., AIML, Fullstack, Cloud, Testing, Sales, Data, Security. Must not skew to one domain; capture all relevant."
            },

            # --- Work model & logistics ---
            "location": {"type": "string", "description": "City / Region / Country if given"},
            "work_model": {"type": "string", "description": "Remote / Hybrid / Onsite (+days onsite if hybrid)"},
            "employment_type": {"type": "string", "description": "Full-time, Contract, Internship, Part-time"},
            "contract": {
                "type": "object",
                "description": "Capture contract details if explicitly mentioned",
                "properties": {
                    "duration_months": {"type": "integer"},
                    "extendable": {"type": "boolean"}
                }
            },
            "start_date_preference": {"type": "string", "description": "Immediate / Within X weeks / Specific date"},
            "travel_requirement_percent": {"type": "number", "description": "Expected % of travel if stated"},
            "work_hours": {"type": "string", "description": "General working hours or shift pattern"},
            "shift_details": {"type": "string", "description": "Day, Night, Rotational"},
            "visa_sponsorship": {"type": "boolean", "description": "True if JD states sponsorship available"},
            "clearances_required": {"type": "array", "items": {"type": "string"}, "description": "Background checks, security clearances etc."},

            # --- Experience & education ---
            "years_experience_required": {"type": "number", "description": "Minimum total years of professional experience"},
            "education_requirements": {"type": "array", "items": {"type": "string"}, "description": "Explicitly listed degrees/courses"},
            "min_degree_level": {"type": "string", "description": "e.g., Bachelors, Masters, PhD, or 'Open'"},
            "fields_of_study": {"type": "array", "items": {"type": "string"}, "description": "Relevant academic disciplines"},
            "certifications_required": {"type": "array", "items": {"type": "string"}},
            "certifications_preferred": {"type": "array", "items": {"type": "string"}},

            # --- Skills ---
            "required_skills": {
                "type": "array", "items": {"type": "string"},
                "description": "Explicit must-have skills mentioned in JD"
            },
            "preferred_skills": {
                "type": "array", "items": {"type": "string"},
                "description": "Optional / good-to-have skills"
            },
            "tools_tech": {"type": "array", "items": {"type": "string"}, "description": "technologies, libraries, frameworks, tools (relevant to the domain - go indepth)"},
            "soft_skills": {"type": "array", "items": {"type": "string"}, "description": "Non-technical skills e.g., communication, leadership"},
            "languages": {"type": "array", "items": {"type": "string"}, "description": "Spoken or programming languages (disambiguate via context)"},
            "canonical_skills": {
                "type": "object",
                "description": "Add categories used in JD for direct ATS scoring compatibility, mention all frameworks, libraries necessary for the programming languages mentioned even if its not in the JD",
                "properties": {
                    "programming": {"type": "array", "items": {"type": "string"}},
                    "frameworks": {"type": "array", "items": {"type": "string"}},
                    "libraries": {"type": "array", "items": {"type": "string"}},
                    "ml_ai": {"type": "array", "items": {"type": "string"}},
                    "frontend": {"type": "array", "items": {"type": "string"}},
                    "backend": {"type": "array", "items": {"type": "string"}},
                    "testing": {"type": "array", "items": {"type": "string"}},
                    "databases": {"type": "array", "items": {"type": "string"}},
                    "cloud": {"type": "array", "items": {"type": "string"}},
                    "infra": {"type": "array", "items": {"type": "string"}},
                    "devtools": {"type": "array", "items": {"type": "string"}},
                    "methodologies": {"type": "array", "items": {"type": "string"}}
                }
            },
            "skill_requirements": {
                "type": "array",
                "description": "Fine-grained structured skills with level, category, provenance",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill": {"type": "string"},
                        "category": {"type": "string", "description": "e.g., programming, cloud, devtools"},
                        "priority": {"type": "string", "description": "must-have | good-to-have"},
                        "level": {"type": "string", "description": "novice | intermediate | advanced | expert"},
                        "years_min": {"type": "number"},
                        "versions": {"type": "array", "items": {"type": "string"}},
                        "related_tools": {"type": "array", "items": {"type": "string"}},
                        "mandatory": {"type": "boolean"},
                        "provenance": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },

            # --- Duties & outcomes ---
            "responsibilities": {"type": "array", "items": {"type": "string"}, "description": "Key tasks the role must perform"},
            "deliverables": {"type": "array", "items": {"type": "string"}, "description": "Expected outputs / goals"},
            "kpis_okrs": {"type": "array", "items": {"type": "string"}, "description": "Performance indicators if stated"},

            # --- Team & reporting ---
            "team_context": {
                "type": "object",
                "description": "Org context for the role",
                "properties": {
                    "team_size": {"type": "integer"},
                    "reports_to": {"type": "string"},
                    "manages_team": {"type": "boolean"},
                    "direct_reports": {"type": "integer"}
                }
            },

            # --- Constraints / exclusions / compliance ---
            "exclusions": {"type": "array", "items": {"type": "string"}, "description": "Disqualifiers or anti-requirements"},
            "compliance": {"type": "array", "items": {"type": "string"}, "description": "Legal/regulatory compliance needs"},
            "screening_questions": {"type": "array", "items": {"type": "string"}},

            # --- Interview process ---
            "interview_process": {
                "type": "object",
                "description": "Stages and evaluation focus if listed",
                "properties": {
                    "total_rounds": {"type": "integer"},
                    "stages": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "purpose": {"type": "string"},
                                "skills_evaluated": {"type": "array", "items": {"type": "string"}}
                            }
                        }
                    },
                    "assignment_expected": {"type": "boolean"}
                }
            },

            # --- Compensation & benefits ---
            "compensation": {
                "type": "object",
                "description": "Salary and perks if given",
                "properties": {
                    "currency": {"type": "string"},
                    "salary_min": {"type": "number"},
                    "salary_max": {"type": "number"},
                    "period": {"type": "string", "description": "yearly, monthly, hourly"},
                    "bonus": {"type": "string"},
                    "equity": {"type": "string"}
                }
            },
            "benefits": {"type": "array", "items": {"type": "string"}},

            # --- Keywords for ATS scoring ---
            "keywords_flat": {
                "type": "array", "items": {"type": "string"},
                "description": "Deduplicated, canonicalized tokens for exact-match scoring"
            },
            "keywords_weighted": {
                "type": "object",
                "additionalProperties": {"type": "number"},
                "description": "Token -> weight (0–1) reflecting importance"
            },

            # --- Weighting knobs ---
            "weighting": {
                "type": "object",
                "description": "Relative importance across categories. Adjust dynamically per JD.",
                "properties": {
                    "required_skills": {"type": "number"},
                    "preferred_skills": {"type": "number"},
                    "responsibilities": {"type": "number"},
                    "domain_relevance": {"type": "number"},
                    "technical_depth": {"type": "number"},
                    "soft_skills": {"type": "number"},
                    "education": {"type": "number"},
                    "certifications": {"type": "number"},
                    "keywords_exact": {"type": "number"},
                    "keywords_semantic": {"type": "number"}
                }
            },

            # --- Embedding hints ---
            "embedding_hints": {
                "type": "object",
                "properties": {
                    "skills_embed": {"type": "string"},
                    "responsibilities_embed": {"type": "string"},
                    "overall_embed": {"type": "string"},
                    "negatives_embed": {"type": "string"},
                    "seniority_embed": {"type": "string"}
                }
            },

            # --- Explainability ---
            "explainability": {
                "type": "object",
                "properties": {
                    "top_jd_sentences": {"type": "array", "items": {"type": "string"}},
                    "key_phrases": {"type": "array", "items": {"type": "string"}},
                    "rationales": {"type": "array", "items": {"type": "string"}}
                }
            },
            "provenance_spans": {
                "type": "array",
                "description": "Character offsets of key items in the JD text",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {"type": "string", "description": "e.g., skill, responsibility, exclusion"},
                        "text": {"type": "string"}
                    }
                }
            },

            # --- HR insights ---
            "hr_points": {"type": "integer", "description": "Count of recommendations/extra inferred requirements"},
            "hr_notes": {
                "type": "array",
                "description": "Each item adds +1 to hr_points. Use when JD suggests improvements or when NLP infers extra requirements.",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string", "description": "compensation | clarity | security | compliance etc."},
                        "type": {"type": "string", "description": "recommendation | inferred_requirement"},
                        "note": {"type": "string"},
                        "impact": {"type": "number", "description": "0–1 perceived impact on hiring quality"},
                        "reason": {"type": "string"},
                        "source_provenance": {"type": "array", "items": {"type": "string"}}
                    }
                }
            },
            
            # --- Filter Requirements (from HR UI) ---
            "filter_requirements": {
                "type": "object",
                "description": "Additional filter requirements from HR (parsed from UI text input). Used for candidate filtering and re-ranking.",
                "properties": {
                    "raw_prompt": {"type": "string", "description": "Original HR prompt text"},
                    "structured": {
                        "type": "object",
                        "description": "Structured requirements extracted from prompt. IMPORTANT: Only include fields that HR explicitly specified. If a requirement is NOT mentioned, set it to null or empty array. Mark each field with 'specified: true' only if HR explicitly mentioned it.",
                        "properties": {
                            "experience": {
                                "type": "object",
                                "description": "Experience requirements. Include ONLY if HR specified experience. Set 'specified: true' if mentioned.",
                                "properties": {
                                    "min": {"type": "number", "description": "Minimum years required"},
                                    "max": {"type": "number", "description": "Maximum years (optional, only if HR specified upper limit)"},
                                    "field": {"type": "string", "description": "Specific field/domain (optional)"},
                                    "specified": {"type": "boolean", "description": "True if HR explicitly mentioned experience requirement"}
                                }
                            },
                            "hard_skills": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Must-have skills. Empty array if not specified. Normalize to canonical forms (e.g., 'Machine Learning' not 'ML')."
                            },
                            "preferred_skills": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Nice-to-have skills. Empty array if not specified."
                            },
                            "department": {
                                "type": "object",
                                "description": "Department/field of study requirements. Include ONLY if HR specified department. Examples: 'IT field only', 'Not Mechanical/Chemical', 'CS, CE, IT, AIDS, ENTC only'.",
                                "properties": {
                                    "category": {"type": "string", "enum": ["IT", "Non-IT", "Specific"], "description": "Category: 'IT' for IT fields only, 'Non-IT' for non-IT fields, 'Specific' for specific departments"},
                                    "allowed_departments": {"type": "array", "items": {"type": "string"}, "description": "Allowed departments (e.g., ['CS', 'CE', 'IT', 'AIDS', 'ENTC'])"},
                                    "excluded_departments": {"type": "array", "items": {"type": "string"}, "description": "Excluded departments (e.g., ['Mechanical', 'Chemical', 'Civil'])"},
                                    "specified": {"type": "boolean", "description": "True if HR explicitly mentioned department requirement"}
                                }
                            },
                            "location": {"type": "string", "description": "Location requirements. Null if not specified. 'Any' or empty string means flexible."},
                            "education": {"type": "array", "items": {"type": "string"}, "description": "Education requirements. Empty array if not specified."},
                            "other_criteria": {"type": "array", "items": {"type": "string"}, "description": "Other filtering criteria that don't fit standard fields. IMPORTANT: Extract ALL requirements mentioned in natural language that are not covered by experience, skills, location, department, or education. Examples: 'Must have worked in fintech', 'Should have startup experience', 'Must be available for night shifts', 'Should have published research papers', 'Must have security clearance', 'Should have experience with specific tools/frameworks not in hard_skills', 'Must have specific certifications', 'Should have worked with specific clients/industries', etc. Be comprehensive - if HR mentions ANY requirement, capture it here as a clear, actionable criterion. Empty array if none."}
                        }
                    },
                    "re_ranking_instructions": {"type": "string", "description": "How to use these requirements for re-ranking candidates"}
                }
            },

            # --- Meta ---
            "meta": {
                "type": "object",
                "properties": {
                    "jd_version": {"type": "string"},
                    "raw_text_length": {"type": "integer"},
                    "last_updated": {"type": "string"},
                    "sections_detected": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "required": [
            "role_title",
            "required_skills",
            "responsibilities",
            "weighting",
            "keywords_flat",
            "keywords_weighted",
            "hr_points",
            "hr_notes"
        ]
    }
}

# ---------------------------
# Core JD processor
# ---------------------------
def process_jd_file(in_path: str, filter_text: str = None) -> dict:
    with open(in_path, "r", encoding="utf-8", errors="ignore") as f:
        raw_text = f.read()

    system_msg = {
        "role": "system",
        "content": (
            "Parse JD into structured JSON. Return EXACTLY ONE function call to `parse_jd_detailed`.\n\n"
            
            "SKILL NORMALIZATION (CRITICAL):\n"
            "• Use canonical forms, NOT abbreviations. Examples: 'ML'→'Machine Learning', 'RAG'→'Retrieval Augmented Generation', 'NLP'→'Natural Language Processing'\n"
            "• Normalize all skills to full names for consistent matching with resumes\n"
            "• If domain-specific skills are missing, add relevant ones (e.g., for AI/ML: add frameworks like TensorFlow, PyTorch)\n"
            "• Map skills to ontology categories: programming, ml_ai, frontend, backend, testing, databases, cloud, infra, devtools, methodologies\n\n"
            
            "REQUIREMENTS:\n"
            "1. Extract ALL information (explicit + implicit)\n"
            "2. Normalize skills to canonical forms (see above)\n"
            "3. Add missing domain-relevant skills if JD is incomplete\n"
            "4. Structure filter_requirements if provided (see below)\n"
            "5. Build keywords_flat (deduped) and keywords_weighted (token→0-1)\n"
            "6. Set weighting: required_skills > responsibilities > domain_relevance > technical_depth > preferred_skills\n"
            "7. Provide embedding_hints, provenance_spans, explainability\n"
            "8. HR notes: Add to hr_notes for recommendations/inferred requirements (type: 'recommendation' or 'inferred_requirement')\n"
            "9. Set hr_points = len(hr_notes). Do NOT hallucinate - use hr_notes for suggestions only\n\n"
            
            + ("FILTER REQUIREMENTS (if provided):\n"
               "Structure HR's additional criteria. CRITICAL: Only extract what HR explicitly mentioned.\n"
               "- experience: {min, max, field, specified: true} - ONLY if HR mentioned experience\n"
               "- hard_skills: [must-have skills] - NORMALIZE to canonical forms. Empty [] if not specified\n"
               "- department: {category, allowed_departments, excluded_departments, specified: true} - ONLY if HR mentioned department/field\n"
               "  Examples: 'IT field only' → category:'IT', 'Not Mechanical/Chemical' → excluded_departments:['Mechanical','Chemical']\n"
               "- location: string or null - null if not specified\n"
               "- education: [requirements] - Empty [] if not specified\n"
               "- other_criteria: [any other requirements - be exhaustive] - Empty [] if none\n"
               "Examples of other_criteria: 'fintech experience', 'night shift availability', 'security clearance'\n"
               "IMPORTANT: Mark 'specified: true' only for fields HR explicitly mentioned. If not mentioned, set to null/empty.\n\n" if filter_text else "") +
            
            "Return ONLY the function call. See schema for field descriptions."
        )
    }

    user_content = f"RawJDText:\n```\n{raw_text}\n```"
    if filter_text and filter_text.strip():
        user_content += f"\n\nFilter Requirements (from HR - parse and structure these):\n```\n{filter_text.strip()}\n```"
    
    user_msg = {"role": "user", "content": user_content}

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
    parsed.setdefault("meta", {})
    parsed["meta"].setdefault("raw_text_length", len(raw_text))
    parsed["meta"].setdefault("last_updated", time.strftime("%Y-%m-%d"))
    
    # Validate parsed JD data
    try:
        validated = validate_jd(parsed, Path(in_path))
        parsed = validated.model_dump()  # Convert back to dict for compatibility
    except Exception as e:
        logging.warning(f"JD validation warning for {in_path}: {e}")
        # Continue with unvalidated data but log warning

    # ---------------------------
    # NEW: enrich domain_tags so resume parser receives explicit seniority/domain/requirements + HR highlights
    # - Keep domain_tags as an array of strings (backwards-compatible).
    # - Add a concise machine-readable JD summary tag (JSON encoded string under a prefix),
    #   then append HR notes and skill tags. This doesn't remove existing domain_tags,
    #   it only augments them with structured info the resume parser can consume.
    # ---------------------------
    try:
        # ensure domain_tags exists and is a list
        existing_tags = parsed.get("domain_tags") if isinstance(parsed.get("domain_tags"), list) else []
        domain_tags = list(existing_tags)

        # seniority: prefer parsed value, otherwise infer from raw_text heuristics
        seniority = parsed.get("seniority_level") or ""
        if not seniority:
            lt = raw_text.lower()
            if "principal" in lt:
                seniority = "Principal"
            elif "lead" in lt and "tech lead" not in lt:
                seniority = "Lead"
            elif "senior" in lt:
                seniority = "Senior"
            elif "mid-level" in lt or "mid level" in lt or "midlevel" in lt:
                seniority = "Mid"
            elif "junior" in lt or "entry level" in lt or "fresher" in lt:
                seniority = "Junior"
            else:
                seniority = parsed.get("meta", {}).get("inferred_seniority", "Unspecified")

        # domain: prefer industry, then department, then empty
        domain = parsed.get("industry") or parsed.get("department") or "Unspecified"

        # build concise summary payload for domain_tags (JSON string) - resume parser can json.loads after detecting prefix
        summary_payload = {
            "role_title": parsed.get("role_title", ""),
            "seniority": seniority,
            "domain": domain,
            "years_experience_required": parsed.get("years_experience_required"),
            "min_degree_level": parsed.get("min_degree_level"),
            "required_skills": parsed.get("required_skills", [])[:50],
            "preferred_skills": parsed.get("preferred_skills", [])[:50],
            "top_tools": parsed.get("tools_tech", [])[:50],
            "confidence_note": "seniority inferred heuristically if not provided",
        }
        # add as a single structured string tag with a fixed prefix so other modules can detect and parse it
        domain_tags.append("JD_SUMMARY:" + json.dumps(summary_payload, ensure_ascii=False))

        # add per-skill tags for direct matching (keeps tokens simple)
        for s in parsed.get("required_skills", [])[:100]:
            if isinstance(s, str) and s.strip():
                domain_tags.append(f"REQ_SKILL:{s.strip()}")

        for s in parsed.get("preferred_skills", [])[:100]:
            if isinstance(s, str) and s.strip():
                domain_tags.append(f"PREF_SKILL:{s.strip()}")

        # include key tool tags
        for t in parsed.get("tools_tech", [])[:100]:
            if isinstance(t, str) and t.strip():
                domain_tags.append(f"TOOL:{t.strip()}")

        # include canonical top-level domain tags if present (e.g., AIML, Fullstack)
        if isinstance(parsed.get("domain_tags"), list):
            for t in parsed.get("domain_tags"):
                if isinstance(t, str) and t.strip():
                    domain_tags.append(f"DOMAIN_TOP:{t.strip()}")

        # Add HR notes as compact tags that keep human-readable content while machine-detectable
        for hr in parsed.get("hr_notes", [])[:200]:
            cat = hr.get("category", "general")
            typ = hr.get("type", "recommendation")
            note = hr.get("note", "")
            impact = hr.get("impact", 0)
            # sanitize and limit length
            note_short = (note.strip()[:240] + "...") if len(note.strip()) > 240 else note.strip()
            # compact HR tag format
            hr_tag = f"HR_NOTE:cat={cat};type={typ};impact={impact};note={note_short}"
            domain_tags.append(hr_tag)

        # add explainability top phrases as tags to influence semantic weighting quickly
        top_phrases = parsed.get("explainability", {}).get("top_jd_sentences", []) if parsed.get("explainability") else []
        for p in top_phrases[:20]:
            if isinstance(p, str) and p.strip():
                domain_tags.append(f"PHRASE:{p.strip()[:200]}")

        # final assignment (dedupe while keeping order)
        seen = set()
        deduped = []
        for t in domain_tags:
            if not isinstance(t, str):
                continue
            key = t.strip().lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(t)
        parsed["domain_tags"] = deduped

        # ensure seniority_level is present for downstream consumers
        parsed["seniority_level"] = seniority

        # if hr_points missing, set to len of hr_notes
        if "hr_points" not in parsed:
            parsed["hr_points"] = len(parsed.get("hr_notes", []))
        
        # Ensure filter_requirements exists (even if empty)
        if "filter_requirements" not in parsed:
            parsed["filter_requirements"] = None

    except Exception as _err:
        # don't fail the whole pipeline on tagging; just log
        logging.exception("Failed to enrich domain_tags: %s", repr(_err))
        # Ensure these fields exist even if enrichment failed
        if "hr_points" not in parsed:
            parsed["hr_points"] = len(parsed.get("hr_notes", []))
        if "filter_requirements" not in parsed:
            parsed["filter_requirements"] = None

    return parsed


# ---------------------------
# Entrypoint
# ---------------------------
if __name__ == "__main__":
    print("[START] JD processing")
    try:
        # Check cache first
        input_path = Path(INPUT_FILE)
        cache_key = get_jd_cache_key(input_path)
        cached = jd_cache.get(cache_key)
        
        # Check if filter requirements file exists
        filter_file = Path("InputThread/JD/Filter_Requirements.txt")
        filter_text = None
        if filter_file.exists():
            try:
                with open(filter_file, "r", encoding="utf-8") as f:
                    filter_text = f.read().strip()
                if filter_text:
                    print(f"[INFO] Found filter requirements: {len(filter_text)} characters")
            except Exception as e:
                logging.warning(f"Failed to read filter file: {e}")
        
        # Use cache if available and no filter changes
        if cached and not filter_text:
            print(f"[INFO] Using cached JD result")
            jd_json = cached
        else:
            jd_json = process_jd_file(INPUT_FILE, filter_text=filter_text)
            # Cache the result (validation already done in process_jd_file)
            jd_cache.set(cache_key, jd_json)
        
        # Save to output file
        if safe_json_save(jd_json, Path(OUTPUT_FILE)):
            print(f"[OK] JD JSON written -> {OUTPUT_FILE}")
        else:
            print(f"[WARNING] Failed to save JD JSON")
    except Exception as e:
        logging.error(f"JD Processing failed: {repr(e)}")
        print(f"[ERROR] JD processing failed: {e}")

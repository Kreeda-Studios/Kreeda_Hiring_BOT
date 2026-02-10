#!/usr/bin/env python3
"""
AI JD Parser - Rebuilt from JDGpt.py

Complete JD parsing logic from Old_Code_Archive/InputThread/AI Processing/JDGpt.py
Adapted for processing pipeline: takes jd_text instead of file path.
"""

import sys
import json
import time
import asyncio
from pathlib import Path
from typing import Dict, Any

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from openai import AsyncOpenAI

MODEL_NAME = "gpt-4o-mini"
MAX_RESPONSE_TOKENS = 2500

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


from openai_client import get_async_openai_client

def get_openai_client():
    """Get async OpenAI client instance"""
    return get_async_openai_client()

client = get_openai_client()

async def process_jd_with_ai(jd_text: str, filter_text: str = None) -> Dict[str, Any]:
    """
    Process JD text with AI parsing.
    
    Args:
        jd_text: Job description text to parse
        filter_text: Optional HR filter requirements text
    
    Returns:
        dict: {'success': bool, 'parsed_data': dict} or {'success': False, 'error': str}
    """
    raw_text = jd_text

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
        )}

    user_content = f"RawJDText:\n```\n{raw_text}\n```"
    user_msg = {"role": "user", "content": user_content}

    # API call with retry and circuit breaker
    async def call_openai_api():
        return await client.chat.completions.create(
            model=MODEL_NAME,
            messages=[system_msg, user_msg],
            functions=[PARSE_FUNCTION],
            function_call="auto",
            temperature=0.0,
            max_tokens=MAX_RESPONSE_TOKENS
        )
    
    try:
        resp = await call_openai_api()
    except Exception as e:
        return {'success': False, 'error': f'API call failed: {str(e)}'}

    
    # Extract function call
    choice = resp.choices[0]
    msg = choice.message
    func_call = getattr(msg, "function_call", None) or (msg if isinstance(msg, dict) else {}).get("function_call")
    if not func_call:
        return {'success': False, 'error': 'No function_call in response'}
    args_text = getattr(func_call, "arguments", None) or func_call.get("arguments")
    if not args_text:
        return {'success': False, 'error': 'No arguments in function_call'}
    try:
        parsed = json.loads(args_text)
    except json.JSONDecodeError as e:
        return {'success': False, 'error': f'JSON decode error: {str(e)}'}
    
    # Add metadata
    parsed.setdefault("meta", {})
    parsed["meta"].setdefault("raw_text_length", len(raw_text))
    parsed["meta"].setdefault("last_updated", time.strftime("%Y-%m-%d"))

    # Enrich domain_tags with structured data for resume parser
    # Adds: JD summary, skill tags, HR notes for better matching
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

    except Exception as _err:
        # Don't fail the whole pipeline on tagging enrichment errors
        # Uncomment for debugging: print(f"Warning: Failed to enrich domain_tags: {_err}")
        # Ensure hr_points exists even if enrichment failed
        if "hr_points" not in parsed:
            parsed["hr_points"] = len(parsed.get("hr_notes", []))

    return {'success': True, 'parsed_data': parsed}


def format_jd_analysis_payload(parsed_jd: dict, filter_requirements: dict = None) -> dict:
    """
    Format parsed JD data into database payload (API-ready)
    
    Args:
        parsed_jd: Parsed JD data from AI
        filter_requirements: Optional validated compliance requirements
        
    Returns:
        dict: Payload ready for API PATCH to /jobs/:id
    """
    jd_analysis = dict(parsed_jd)
    
    
    return {
        'jd_analysis': jd_analysis,
    }

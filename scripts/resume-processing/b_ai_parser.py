#!/usr/bin/env python3
"""
AI Resume Parser using OpenAI GPT

Parses resume text using OpenAI function calling to extract structured data.
Based on the exact schema from Old_Code_Archive parsing logic.
"""

import os
import json
import time
import asyncio
from typing import Dict, Any, List, Optional

try:
    from openai import AsyncOpenAI
except ImportError:
    AsyncOpenAI = None

# OpenAI Configuration
MODEL_NAME = "gpt-4o-mini"
MAX_TOKENS = 4096

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


# System prompt for resume parsing
SYSTEM_PROMPT = """
You are an expert resume parser. Your task is to extract structured information from resume text with high accuracy.

Guidelines:
1. Extract ALL information accurately - don't skip or summarize
2. Normalize skill names (e.g., "js" → "JavaScript", "react.js" → "React")
3. Calculate years_experience by analyzing work history durations
4. Categorize skills into canonical groups (programming languages, frameworks, etc.)
5. Infer additional skills from project descriptions and work experience
6. Extract ALL projects mentioned, including side projects and coursework
7. Parse contact information carefully - extract email, phone, LinkedIn, GitHub
8. Identify responsibilities vs achievements clearly
9. Calculate parsing confidence based on completeness and clarity
10. If information is missing or unclear, use empty strings/arrays rather than null

For years_experience calculation:
- Sum up all professional work experience durations
- Don't count overlapping periods
- Include internships and part-time work proportionally
- Be conservative but fair in estimation

For skill inference:
- Extract skills mentioned in project descriptions
- Infer skills from job responsibilities
- Include both explicit mentions and implied skills
- Assign confidence scores based on evidence strength

Be thorough and accurate - this data will be used for candidate matching.
"""

def extract_jd_skills_from_domain_tags(domain_tags: List[str]) -> Dict[str, List[str]]:
    """
    Extract required and preferred skills from JD domain_tags.
    Matches old GptJson.py utility function.
    
    Args:
        domain_tags: List of domain tag strings
        
    Returns:
        Dictionary with 'required' and 'preferred' skill lists
    """
    required_skills = []
    preferred_skills = []
    
    for tag in domain_tags:
        if isinstance(tag, str):
            if tag.startswith("REQ_SKILL:"):
                required_skills.append(tag.replace("REQ_SKILL:", "").strip())
            elif tag.startswith("PREF_SKILL:"):
                preferred_skills.append(tag.replace("PREF_SKILL:", "").strip())
    
    return {
        "required": required_skills,
        "preferred": preferred_skills
    }


def get_openai_client():
    """Initialize async OpenAI client"""
    if AsyncOpenAI is None:
        raise ImportError("OpenAI library not installed. Run: pip install openai")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    return AsyncOpenAI(api_key=api_key)

async def parse_resume_with_ai(resume_text: str, jd_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse resume using OpenAI function calling with JD context (async).
    Matches old GptJson.py logic with skill normalization and scoring against JD.
    
    Args:
        resume_text: Raw resume text
        jd_data: Job description data with domain_tags, required_skills, etc.
    
    Returns:
        Dict with success, parsed_data, processing_time, tokens_used
    """
    try:
        client = get_openai_client()
        
        start_time = time.time()
        
        # Extract JD context for skill normalization (matching old GptJson.py logic)
        domain_tags = []
        jd_required_skills = []
        jd_preferred_skills = []
        
        if jd_data:
            domain_tags = jd_data.get('domain_tags', [])
            # Extract JD skills from domain_tags for normalization reference (using old system utility)
            jd_skills = extract_jd_skills_from_domain_tags(domain_tags)
            jd_required_skills = jd_skills["required"]
            jd_preferred_skills = jd_skills["preferred"]
            
        # Truncate domain_tags for prompt (keep first 20 to save tokens)
        domain_tags_preview = domain_tags[:20] if len(domain_tags) > 20 else domain_tags
        domain_tags_str = str(domain_tags_preview) + ("..." if len(domain_tags) > 20 else "")
        
        # Build enhanced system prompt with JD context (matching old GptJson.py logic exactly)
        system_prompt_enhanced = (
            "Parse resume into structured JSON. Return EXACTLY ONE function call to `parse_resume`.\n\n"
        )
        
        if jd_data:
            system_prompt_enhanced += (
                f"JD CONTEXT: {domain_tags_str}\n"
                "This contains JD domain, seniority, required/preferred skills, and HR priorities.\n\n"
                
                "SKILL NORMALIZATION (CRITICAL):\n"
                "• Match JD skill format. If JD requires 'RAG' and resume has 'Retrieval Augmented Generation', extract as 'RAG'\n"
                "• If JD requires 'ML' and resume has 'Machine Learning', extract as 'Machine Learning' (use JD's canonical form)\n"
                "• Use JD required_skills as normalization reference (check REQ_SKILL: tags in domain_tags)\n"
                "• Normalize all skills to match JD format for consistent filtering\n"
            )
            
            system_prompt_enhanced += (f"• JD Required Skills (normalize to these forms): {', '.join(jd_required_skills[:10])}\n" if jd_required_skills else "")
            system_prompt_enhanced += "\n"
            
            system_prompt_enhanced += (
                "SCORING (use domain_tags as benchmark):\n"
                "• High alignment with domain_tags → HIGH scores\n"
                "• Low alignment / basic projects → LOW scores\n"
                "• Experience below JD seniority → LOW scores\n"
                "• Production-grade work → HIGH; toy projects → LOW\n"
                "• Architecture/scaling work → very HIGH\n\n"
            )
        
        system_prompt_enhanced += (
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
        
        # Prepare messages (matching old GptJson.py format)
        # Generate temporary candidate_id (will be replaced after parsing)
        candidate_id = f"temp_{int(time.time() * 1000)}"
        
        messages = [
            {"role": "system", "content": system_prompt_enhanced},
            {"role": "user", "content": f"CandidateID: {candidate_id}\n\nRawResumeText:\n```\n{resume_text}\n```"}
        ]
        
        # Make async API call with function calling
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            functions=[PARSE_FUNCTION],
            function_call={"name": "parse_resume_detailed"},
            temperature=0.0,
            max_tokens=MAX_TOKENS
        )
        
        processing_time = time.time() - start_time
        
        # Extract function call result
        message = response.choices[0].message
        
        if message.function_call and message.function_call.name == "parse_resume_detailed":
            try:
                parsed_data = json.loads(message.function_call.arguments)
                
                # Add processing metadata
                if not parsed_data.get('meta'):
                    parsed_data['meta'] = {}
                    
                parsed_data['meta'].update({
                    'ai_processing_time': processing_time,
                    'model_used': MODEL_NAME,
                    'parsing_timestamp': time.time()
                })
                
                return {
                    'success': True,
                    'parsed_data': parsed_data,
                    'processing_time': processing_time,
                    'tokens_used': response.usage.total_tokens if response.usage else 0
                }
                
            except json.JSONDecodeError as e:
                return {
                    'success': False,
                    'error': f"Failed to parse AI response JSON: {str(e)}",
                    'raw_response': message.function_call.arguments
                }
        else:
            return {
                'success': False,
                'error': "AI did not call the parse_resume function",
                'response': message.content
            }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"OpenAI API call failed: {str(e)}"
        }

def validate_parsed_resume(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Validate parsed resume data quality"""
    issues = []
    warnings = []
    score = 1.0
    
    # Required field validation
    required_fields = ['name', 'contact_info', 'experience_entries', 'education', 'skills']
    for field in required_fields:
        if not parsed_data.get(field):
            issues.append(f"Missing required field: {field}")
            score -= 0.2
    
    # Contact info validation
    contact = parsed_data.get('contact_info', {})
    if not contact.get('email'):
        issues.append("Missing email in contact_info")
        score -= 0.1
    
    # Experience validation
    experience = parsed_data.get('experience_entries', [])
    if not experience:
        issues.append("No work experience found")
        score -= 0.2
    else:
        for i, exp in enumerate(experience):
            if not exp.get('company') or not exp.get('title'):
                warnings.append(f"Experience {i+1} missing company or title")
                score -= 0.05
    
    # Skills validation
    skills = parsed_data.get('skills', [])
    if len(skills) < 3:
        warnings.append("Very few skills extracted (< 3)")
        score -= 0.1
    
    # Years experience consistency
    stated_years = parsed_data.get('years_experience')
    calculated_years = parsed_data.get('meta', {}).get('total_experience_calculated')
    
    if stated_years and calculated_years and abs(stated_years - calculated_years) > 2:
        warnings.append(f"Experience mismatch: stated {stated_years} vs calculated {calculated_years}")
        score -= 0.05
    
    return {
        'is_valid': len(issues) == 0 and score >= 0.5,
        'quality_score': max(0.0, score),
        'issues': issues,
        'warnings': warnings,
        'completeness': {
            'has_contact': bool(contact.get('email')),
            'has_experience': len(experience) > 0,
            'has_education': len(parsed_data.get('education', [])) > 0,
            'has_skills': len(skills) > 0,
            'has_projects': len(parsed_data.get('projects', [])) > 0
        }
    }

def enhance_parsed_data(parsed_data: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance parsed data with additional processing (matching old GptJson.py logic)"""
    import hashlib
    enhanced = parsed_data.copy()
    
    # Generate candidate_id if not present (deterministic based on contact info)
    if not enhanced.get('candidate_id'):
        contact = enhanced.get('contact_info', {})
        email = contact.get('email', '') if isinstance(contact, dict) else ''
        phone = contact.get('phone', '') if isinstance(contact, dict) else ''
        name = enhanced.get('name', 'unknown')
        
        # Normalize inputs
        email = (email or "").strip().lower()
        phone = (phone or "").strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        name_normalized = " ".join(name.strip().title().split()) if name else ""
        
        # Create hash from available identifiers
        if email:
            identifier = f"email:{email}"
            prefix = email.split("@")[0][:8] if "@" in email else "cand"
        elif phone:
            identifier = f"phone:{phone}"
            prefix = "cand"
        elif name_normalized:
            identifier = f"name:{name_normalized}"
            prefix = name_normalized.replace(" ", "")[:8].lower()
        else:
            identifier = f"unknown"
            prefix = "cand"
        
        # Generate deterministic hash (first 12 chars of SHA256)
        hash_id = hashlib.sha256(identifier.encode('utf-8')).hexdigest()[:12]
        enhanced['candidate_id'] = f"{prefix}_{hash_id}"
    
    # Normalize years_experience if not calculated
    if not enhanced.get('years_experience'):
        total_years = 0
        for exp in enhanced.get('experience_entries', []):
            # Try to parse period dates
            period_start = exp.get('period_start', '')
            period_end = exp.get('period_end', '')
            
            if period_start and period_end:
                # Try to parse years from dates
                import re
                start_match = re.findall(r'(\d{4})', period_start)
                end_match = re.findall(r'(\d{4})', period_end)
                if start_match and end_match:
                    start_year = int(start_match[0])
                    end_year = int(end_match[0])
                    total_years += max(0, end_year - start_year)
        
        enhanced['years_experience'] = round(total_years, 1)
    
    # Canonicalize skills
    canonical = enhanced.get('canonical_skills', {})
    for cat, skill_list in canonical.items():
        if isinstance(skill_list, list):
            canonical[cat] = sorted(list(set([s.strip() for s in skill_list if s and isinstance(s, str)])))
    
    # Canonicalize project fields
    for proj in enhanced.get('projects', []):
        for field in ['tech_keywords', 'technologies', 'primary_skills']:
            if field in proj and isinstance(proj[field], list):
                proj[field] = sorted(list(set([s.strip() for s in proj[field] if s and isinstance(s, str)])))
    
    # Canonicalize experience_entries fields
    for exp in enhanced.get('experience_entries', []):
        for field in ['primary_tech', 'responsibilities_keywords']:
            if field in exp and isinstance(exp[field], list):
                exp[field] = sorted(list(set([s.strip() for s in exp[field] if s and isinstance(s, str)])))
    
    # Build ATS boost line
    boost_tokens = set()
    for cat_list in canonical.values():
        if isinstance(cat_list, list):
            boost_tokens.update([tok.lower() for tok in cat_list if tok])
    for sp in enhanced.get('skill_proficiency', []):
        if sp.get('skill'):
            boost_tokens.add(sp['skill'].lower())
    for iskill in enhanced.get('inferred_skills', []):
        if iskill.get('skill'):
            boost_tokens.add(iskill['skill'].lower())
    enhanced['ats_boost_line'] = ", ".join(sorted(boost_tokens))
    
    # Build embedding hints
    enhanced.setdefault('embedding_hints', {
        "profile_embed": enhanced.get("profile_keywords_line", ""),
        "projects_embed": " | ".join([p.get("name","") + ": " + p.get("approach","") for p in enhanced.get("projects", [])[:2]]),
        "skills_embed": ", ".join(list(boost_tokens)[:10])
    })
    
    # Initialize explainability
    enhanced.setdefault('explainability', {"top_matched_sentences": [], "top_matched_keywords": []})
    
    # Flatten all skills into keywords_flat if not present
    if not enhanced.get('keywords_flat'):
        all_keywords = set()
        
        # Add skills
        all_keywords.update(enhanced.get('skills', []))
        
        # Add canonical skills
        for skill_list in canonical.values():
            if isinstance(skill_list, list):
                all_keywords.update(skill_list)
        
    # Flatten all skills into keywords_flat if not present
    if not enhanced.get('keywords_flat'):
        all_keywords = set()
        
        # Add skills
        all_keywords.update(enhanced.get('skills', []))
        
        # Add canonical skills
        canonical = enhanced.get('canonical_skills', {})
        for skill_list in canonical.values():
            if isinstance(skill_list, list):
                all_keywords.update(skill_list)
        
        # Add inferred skills
        for skill_obj in enhanced.get('inferred_skills', []):
            if skill_obj.get('skill'):
                all_keywords.add(skill_obj['skill'])
        
        # Add project technologies
        for project in enhanced.get('projects', []):
            all_keywords.update(project.get('technologies', []))
            all_keywords.update(project.get('tech_keywords', []))
        
        enhanced['keywords_flat'] = sorted(list(all_keywords))
    
    # Update meta
    enhanced.setdefault('meta', {})
    enhanced['meta']['last_updated'] = time.strftime("%Y-%m-%d")
    
    return enhanced

def process_resume_content(resume_text: str) -> Dict[str, Any]:
    """
    Main function to parse resume text with AI
    Returns: {
        'success': bool,
        'parsed_data': dict,
        'validation': dict,
        'processing_time': float,
        'tokens_used': int,
        'error': str or None
    }
    """
    try:
        # Parse with AI
        parse_result = parse_resume_with_ai(resume_text)
        
        if not parse_result['success']:
            return parse_result
        
        # Enhance parsed data
        enhanced_data = enhance_parsed_data(parse_result['parsed_data'])
        
        # Validate quality
        validation = validate_parsed_resume(enhanced_data)
        
        return {
            'success': True,
            'parsed_data': enhanced_data,
            'validation': validation,
            'processing_time': parse_result.get('processing_time', 0),
            'tokens_used': parse_result.get('tokens_used', 0)
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Resume parsing failed: {str(e)}"
        }
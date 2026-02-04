#!/usr/bin/env python3
"""
AI Resume Parser using OpenAI GPT

Parses resume text using OpenAI function calling to extract structured data.
Based on the exact schema from Old_Code_Archive parsing logic.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# OpenAI Configuration
MODEL_NAME = "gpt-4o-mini"
MAX_TOKENS = 4096
TEMPERATURE = 0.1

PARSE_RESUME_FUNCTION = {
    "name": "parse_resume",
    "description": "Parse resume content into structured data with comprehensive details",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Full name of the candidate"
            },
            "contact_info": {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Email address"},
                    "phone": {"type": "string", "description": "Phone number"},
                    "address": {"type": "string", "description": "Full address"},
                    "linkedin": {"type": "string", "description": "LinkedIn profile URL"},
                    "github": {"type": "string", "description": "GitHub profile URL"},
                    "portfolio": {"type": "string", "description": "Portfolio website URL"}
                },
                "required": ["email"]
            },
            "location": {
                "type": "string",
                "description": "Current location/city/state"
            },
            "summary": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Professional summary or objective statements"
            },
            "years_experience": {
                "type": "number",
                "description": "Total years of professional experience"
            },
            "experience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company": {"type": "string", "description": "Company/organization name"},
                        "title": {"type": "string", "description": "Job title/position"},
                        "duration": {"type": "string", "description": "Employment duration (e.g., '2020-2023')"},
                        "location": {"type": "string", "description": "Job location"},
                        "description": {"type": "string", "description": "Detailed job description"},
                        "responsibilities": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of key responsibilities"
                        },
                        "achievements": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Notable achievements or accomplishments"
                        },
                        "industry": {"type": "string", "description": "Industry sector"},
                        "years_at_company": {"type": "number", "description": "Years worked at this company"}
                    },
                    "required": ["company", "title", "duration"]
                },
                "description": "Professional work experience"
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "institution": {"type": "string", "description": "Educational institution name"},
                        "degree": {"type": "string", "description": "Degree type (e.g., Bachelor's, Master's)"},
                        "field": {"type": "string", "description": "Field of study/major"},
                        "year": {"type": "string", "description": "Graduation year or duration"},
                        "gpa": {"type": "string", "description": "GPA if mentioned"},
                        "honors": {"type": "string", "description": "Honors, dean's list, etc."}
                    },
                    "required": ["institution", "degree", "field"]
                },
                "description": "Educational background"
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Technical and professional skills"
            },
            "canonical_skills": {
                "type": "object",
                "properties": {
                    "programming_languages": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Programming languages (Python, JavaScript, etc.)"
                    },
                    "frameworks_libraries": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Frameworks and libraries (React, Django, etc.)"
                    },
                    "databases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Database technologies (MySQL, MongoDB, etc.)"
                    },
                    "cloud_platforms": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Cloud platforms (AWS, Azure, GCP)"
                    },
                    "tools_software": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Tools and software (Git, Docker, etc.)"
                    },
                    "soft_skills": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Soft skills (leadership, communication, etc.)"
                    }
                },
                "description": "Skills categorized into canonical groups"
            },
            "inferred_skills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill": {"type": "string", "description": "Skill name"},
                        "source": {"type": "string", "description": "Where skill was inferred from"},
                        "confidence": {"type": "number", "description": "Confidence score (0-1)"}
                    },
                    "required": ["skill", "source", "confidence"]
                },
                "description": "Skills inferred from experience and projects"
            },
            "skill_proficiency": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "skill": {"type": "string", "description": "Skill name"},
                        "level": {"type": "string", "description": "Proficiency level (Beginner/Intermediate/Advanced/Expert)"},
                        "years_experience": {"type": "number", "description": "Years of experience with this skill"}
                    },
                    "required": ["skill", "level"]
                },
                "description": "Skills with proficiency levels"
            },
            "projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Project name"},
                        "description": {"type": "string", "description": "Project description"},
                        "technologies": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Technologies/tools used"
                        },
                        "tech_keywords": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Technical keywords from project"
                        },
                        "primary_skills": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Primary skills demonstrated"
                        },
                        "url": {"type": "string", "description": "Project URL/link"},
                        "duration": {"type": "string", "description": "Project duration"},
                        "role": {"type": "string", "description": "Role in the project"}
                    },
                    "required": ["name", "description"]
                },
                "description": "Personal and professional projects"
            },
            "certifications": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Certification name"},
                        "issuer": {"type": "string", "description": "Issuing organization"},
                        "date": {"type": "string", "description": "Issue/expiry date"},
                        "credential_id": {"type": "string", "description": "Credential ID if available"}
                    },
                    "required": ["name", "issuer"]
                },
                "description": "Professional certifications"
            },
            "languages": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "language": {"type": "string", "description": "Language name"},
                        "proficiency": {"type": "string", "description": "Proficiency level (Native/Fluent/Conversational/Basic)"}
                    },
                    "required": ["language", "proficiency"]
                },
                "description": "Language skills"
            },
            "responsibilities": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Overall key responsibilities across roles"
            },
            "achievements": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Notable achievements and accomplishments"
            },
            "keywords_flat": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Flat list of all relevant keywords from resume"
            },
            "meta": {
                "type": "object",
                "properties": {
                    "resume_version": {"type": "string", "description": "Resume version or format"},
                    "sections_detected": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Resume sections found"
                    },
                    "parsing_confidence": {"type": "number", "description": "Overall parsing confidence (0-1)"},
                    "total_experience_calculated": {"type": "number", "description": "Calculated total experience in years"}
                },
                "description": "Metadata about the parsing process"
            }
        },
        "required": ["name", "contact_info", "experience", "education", "skills"]
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

def get_openai_client():
    """Initialize OpenAI client"""
    if OpenAI is None:
        raise ImportError("OpenAI library not installed. Run: pip install openai")
    
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    return OpenAI(api_key=api_key)

def parse_resume_with_ai(resume_text: str, jd_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse resume using OpenAI function calling with JD context.
    Matches old archive logic with skill normalization and scoring against JD.
    
    Args:
        resume_text: Raw resume text
        jd_data: Job description data with domain_tags, required_skills, etc.
    
    Returns:
        Dict with success, parsed_data, processing_time, tokens_used
    """
    try:
        client = get_openai_client()
        
        start_time = time.time()
        
        # Extract JD context for skill normalization
        domain_tags = []
        jd_required_skills = []
        jd_preferred_skills = []
        
        if jd_data:
            domain_tags = jd_data.get('domain_tags', [])
            # Extract skills from jd_analysis
            jd_analysis = jd_data.get('jd_analysis', {})
            jd_required_skills = jd_analysis.get('required_skills', [])
            jd_preferred_skills = jd_analysis.get('preferred_skills', [])
            
        # Truncate domain_tags for prompt (keep first 20 to save tokens)
        domain_tags_preview = domain_tags[:20] if len(domain_tags) > 20 else domain_tags
        domain_tags_str = str(domain_tags_preview) + ("..." if len(domain_tags) > 20 else "")
        
        # Build enhanced system prompt with JD context (matching old archive logic)
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
                "• Use JD required_skills as normalization reference\n"
                "• Normalize all skills to match JD format for consistent filtering\n"
            )
            
            if jd_required_skills:
                system_prompt_enhanced += f"• JD Required Skills (normalize to these forms): {', '.join(jd_required_skills[:10])}\n"
            
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
            "• Calculate years_experience from experience dates\n"
            "• Handle overlapping periods, internships, part-time correctly\n"
            "• Sum all relevant work experience (exclude internships if not relevant)\n"
            "• Use current date or latest period_end as reference\n"
            "• Return as number (e.g., 2.5 for 2 years 6 months)\n\n"
            
            "EDUCATION EXTRACTION:\n"
            "• Extract degree, field/department, institution, year from education section\n"
            "• Field should be specific: 'Computer Science', 'Mechanical Engineering', 'IT', 'CE', 'AIDS', 'ENTC'\n"
            "• Map abbreviations: CS→Computer Science, CE→Computer Engineering, IT→Information Technology\n"
            "• Include all degrees (B.Tech, M.Tech, etc.)\n\n"
            
            "PROJECT REQUIREMENTS:\n"
            "1. Fill all project fields (except dates may be optional)\n"
            "2. Include tech_keywords and primary_skills for each project\n"
            "3. Normalize skills to JD format (see above)\n"
            "4. Score projects based on JD alignment\n\n"
            
            "REQUIREMENTS:\n"
            "1. Calculate years_experience accurately from dates\n"
            "2. Extract education with field/department\n"
            "3. No hallucinations - only extract what's present\n"
            "4. Use canonical skill names\n"
            "5. Extract ALL skills from experience and projects (inferred_skills)\n"
            "6. Assign confidence scores to inferred skills\n\n"
            
            "Return ONLY the function call with complete structured data."
        )
        
        # Prepare messages
        messages = [
            {"role": "system", "content": system_prompt_enhanced},
            {"role": "user", "content": f"Parse this resume:\n\n{resume_text}"}
        ]
        
        # Make API call with function calling
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            functions=[PARSE_RESUME_FUNCTION],
            function_call={"name": "parse_resume"},
            temperature=TEMPERATURE,
            max_tokens=MAX_TOKENS
        )
        
        processing_time = time.time() - start_time
        
        # Extract function call result
        message = response.choices[0].message
        
        if message.function_call and message.function_call.name == "parse_resume":
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
    required_fields = ['name', 'contact_info', 'experience', 'education', 'skills']
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
    experience = parsed_data.get('experience', [])
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
    """Enhance parsed data with additional processing"""
    enhanced = parsed_data.copy()
    
    # Generate candidate_id if not present
    if not enhanced.get('candidate_id'):
        name = enhanced.get('name', 'unknown')
        email = enhanced.get('contact_info', {}).get('email', '')
        candidate_id = f"{name.replace(' ', '_').lower()}_{hash(email) % 10000}"
        enhanced['candidate_id'] = candidate_id
    
    # Normalize years_experience if not calculated
    if not enhanced.get('years_experience'):
        total_years = 0
        for exp in enhanced.get('experience', []):
            duration = exp.get('duration', '')
            years_at_company = exp.get('years_at_company')
            
            if years_at_company:
                total_years += years_at_company
            else:
                # Try to parse duration string
                import re
                year_match = re.findall(r'(\d{4})', duration)
                if len(year_match) >= 2:
                    start_year = int(year_match[0])
                    end_year = int(year_match[-1])
                    total_years += max(0, end_year - start_year)
        
        enhanced['years_experience'] = round(total_years, 1)
    
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
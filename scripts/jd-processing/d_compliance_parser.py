#!/usr/bin/env python3
"""
Compliance Parser - Parses HR filter requirements into structured format

Parses two types of compliance text:
1. Mandatory compliances - Hard requirements that must be met
2. Soft compliances - Preferred requirements (nice-to-have)

Outputs structured data for candidate filtering and ranking.
"""

import json
import sys
import time
from typing import Dict, Any
from pathlib import Path

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from openai_client import get_openai_client

client = get_openai_client()


def parse_compliance_text(compliance_text: str, compliance_type: str = "mandatory") -> Dict[str, Any]:
    """
    Parse HR compliance text into structured format using OpenAI.
    Matches old system's AI prompt structure exactly.
    
    Args:
        compliance_text: Raw text from HR (e.g., "Need 3+ years Python, ML experience")
        compliance_type: "mandatory" or "soft" (for logging)
        
    Returns:
        dict: {
            "raw_prompt": str (original text),
            "structured": {
                "hard_skills": {"type": "list", "specified": true, "required": [...], "optional": [...]},
                "experience": {"type": "numeric", "specified": true, "min": 3, "max": 5, "unit": "years"},
                ...
            }
        }
    """
    if not compliance_text or not compliance_text.strip():
        return {"raw_prompt": "", "structured": {}}
    
    # OpenAI function schema - EXACT match to old system (main.py)
    parse_function = {
        "name": "parse_hr_requirements",
        "description": "Parse HR requirements into structured format with proper field names",
        "parameters": {
            "type": "object",
            "properties": {
                "structured": {
                    "type": "object",
                    "description": "Structured requirements with field names. Use standard field names: hard_skills (for skills), experience (for years), location, education, etc. Each field should be a dict with 'type' and 'specified': true",
                    "properties": {
                        "hard_skills": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["list"]},
                                "specified": {"type": "boolean"},
                                "required": {"type": "array", "items": {"type": "string"}},
                                "optional": {"type": "array", "items": {"type": "string"}}
                            },
                            "description": "Required skills (use this field name for any skill requirements)"
                        },
                        "experience": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["numeric"]},
                                "specified": {"type": "boolean"},
                                "min": {"type": "number"},
                                "max": {"type": "number"},
                                "unit": {"type": "string"}
                            },
                            "description": "Experience requirement in years"
                        },
                        "location": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["location", "text"]},
                                "specified": {"type": "boolean"},
                                "required": {"type": "string"},
                                "allowed": {"type": "array", "items": {"type": "string"}}
                            },
                            "description": "Location requirement"
                        },
                        "education": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string", "enum": ["education", "text"]},
                                "specified": {"type": "boolean"},
                                "minimum": {"type": "string"},
                                "required": {"type": "string"}
                            },
                            "description": "Education requirement"
                        }
                    },
                    "additionalProperties": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string"},
                            "specified": {"type": "boolean"}
                        }
                    }
                }
            },
            "required": ["structured"]
        }
    }
    
    try:
        # Use function calling - EXACT match to old system prompt
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": """Parse HR requirements into structured JSON format.
                    CRITICAL RULES:
                    1. Use standard field names: hard_skills (for any skills), experience (for years), location, education
                    2. For skills: Use field name "hard_skills" with type "list", put skills in "required" array
                    3. For experience: Use field name "experience" with type "numeric", use "min" and "max" for range
                    4. For location: Use field name "location" with type "location" or "text"
                    5. Each field MUST have "type" and "specified": true
                    6. Return flat structure (no nested "requirements" arrays)
                    7. Map common terms: "skills" -> hard_skills, "years" -> experience, "location" -> location"""
                },
                {
                    "role": "user",
                    "content": f"Parse these HR requirements into structured JSON with proper field names:\n\n{compliance_text}\n\nRemember: Use 'hard_skills' for skills, 'experience' for years, 'location' for location."
                }
            ],
            functions=[parse_function],
            function_call={"name": "parse_hr_requirements"},
            temperature=0.0,
            max_tokens=1000
        )
        
        # Extract function call result
        msg = response.choices[0].message
        func_call = getattr(msg, "function_call", None)
        
        if func_call and func_call.arguments:
            parsed = json.loads(func_call.arguments)
            # Extract "structured" wrapper (old system returns nested)
            structured = parsed.get("structured", {})
        else:
            structured = {}
        
        return {
            "raw_prompt": compliance_text,
            "structured": structured
        }
    
    except Exception as e:
        print(f"⚠️ Error parsing {compliance_type} compliance: {e}")
        return {
            "raw_prompt": compliance_text,
            "structured": {},
            "error": str(e)
        }



def validate_and_format_compliances(job_data: dict) -> Dict:
    """
    Parse, validate and format compliance requirements in standardized format
    
    Args:
        job_data: Job data dict with filter_requirements field
        
    Returns: {
        'success': bool,
        'filter_requirements': {
            'mandatory_compliances': {raw_prompt, structured},
            'soft_compliances': {raw_prompt, structured}
        },
        'stats': {
            'mandatory_count': int,
            'soft_count': int,
            'total_count': int
        },
        'error': str or None
    }
    """
    default_compliances = {
        'mandatory_compliances': {'raw_prompt': '', 'structured': {}},
        'soft_compliances': {'raw_prompt': '', 'structured': {}}
    }
    
    try:
        parsed_compliances = process_job_compliances(job_data)
        
        filter_requirements = {
            'mandatory_compliances': parsed_compliances.get('mandatory_compliances', default_compliances['mandatory_compliances']),
            'soft_compliances': parsed_compliances.get('soft_compliances', default_compliances['soft_compliances'])
        }
        
        mandatory_count = len(filter_requirements['mandatory_compliances'].get('structured', {}))
        soft_count = len(filter_requirements['soft_compliances'].get('structured', {}))
        
        return {
            'success': True,
            'filter_requirements': filter_requirements,
            'stats': {
                'mandatory_count': mandatory_count,
                'soft_count': soft_count,
                'total_count': mandatory_count + soft_count
            },
            'error': None
        }
        
    except Exception as e:
        existing = job_data.get('filter_requirements', default_compliances)
        
        return {
            'success': False,
            'filter_requirements': existing,
            'stats': {
                'mandatory_count': 0,
                'soft_count': 0,
                'total_count': 0
            },
            'error': str(e)
        }


def process_job_compliances(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process mandatory and soft compliance requirements from job data.
    
    Args:
        job_data: Job object with filter_requirements field
        
    Returns:
        dict: {
            "mandatory_compliances": {"raw_prompt": str, "structured": dict},
            "soft_compliances": {"raw_prompt": str, "structured": dict}
        }
    """
    filter_requirements = job_data.get('filter_requirements', {})
    
    # Extract compliance texts
    mandatory_text = filter_requirements.get('mandatory_compliances', {}).get('raw_prompt', '')
    soft_text = filter_requirements.get('soft_compliances', {}).get('raw_prompt', '')
    
    result = {
        "mandatory_compliances": {"raw_prompt": "", "structured": {}},
        "soft_compliances": {"raw_prompt": "", "structured": {}}
    }
    
    # Parse mandatory compliance
    if mandatory_text and mandatory_text.strip():
        result["mandatory_compliances"] = parse_compliance_text(mandatory_text, "mandatory")
    
    # Parse soft compliance
    if soft_text and soft_text.strip():
        result["soft_compliances"] = parse_compliance_text(soft_text, "soft")
    
    return result



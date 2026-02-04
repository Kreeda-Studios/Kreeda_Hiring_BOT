#!/usr/bin/env python3
"""
Compliance Parser

Parses HR compliance text (mandatory and soft) into structured format.
Based on Old_Code_Archive/main.py parse_hr_filter_requirements() function.

This is a separate step from JD parsing to keep concerns separated.
"""

import json
import os
import time
from typing import Dict, Any, Optional
from openai import OpenAI

# Initialize OpenAI client
client = None
try:
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        client = OpenAI(api_key=api_key)
except Exception as e:
    print(f"⚠️ Failed to initialize OpenAI client: {e}")


def parse_compliance_text(compliance_text: str, compliance_type: str = "mandatory") -> Dict[str, Any]:
    """
    Parse HR compliance text into structured format using LLM.
    
    Args:
        compliance_text: Raw text from HR describing requirements
        compliance_type: "mandatory" or "soft" (for logging purposes)
        
    Returns: {
        "raw_prompt": str,
        "structured": dict with dynamic fields
    }
    """
    
    if not compliance_text or not compliance_text.strip():
        return {
            "raw_prompt": "",
            "structured": {}
        }
    
    if not client:
        print(f"⚠️ OpenAI client not initialized. Returning empty structure for {compliance_type} compliance.")
        return {
            "raw_prompt": compliance_text,
            "structured": {}
        }
    
    # LLM function definition for structured parsing
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
    
    llm_call_id = f"LLM_COMPLIANCE_{int(time.time() * 1000)}"
    print(f"[{llm_call_id}] 🔄 Parsing {compliance_type} compliance with LLM")
    start_time = time.time()
    
    try:
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
                    7. Map common terms: "skills" -> hard_skills, "years" -> experience, "location" -> location
                    8. Normalize skills to canonical forms (e.g., "Python" not "python", "Machine Learning" not "ML")"""
                },
                {
                    "role": "user",
                    "content": f"Parse these HR requirements into structured JSON with proper field names:\n\n{compliance_text}\n\nRemember: Use 'hard_skills' for skills, 'experience' for years, 'location' for location. Normalize all skill names to canonical forms."
                }
            ],
            functions=[parse_function],
            function_call={"name": "parse_hr_requirements"},
            temperature=0.0,
            max_tokens=1000
        )
        
        msg = response.choices[0].message
        func_call = getattr(msg, "function_call", None)
        
        if func_call:
            args_text = getattr(func_call, "arguments", None)
            if args_text:
                parsed = json.loads(args_text)
                structured = parsed.get("structured", {})
            else:
                structured = {}
        else:
            structured = {}
        
        duration = time.time() - start_time
        print(f"[{llm_call_id}] ✅ Parsed {compliance_type} compliance in {duration:.2f}s - {len(structured)} field(s)")
        
        # Normalize the parsed structure
        normalized = normalize_parsed_requirements(structured)
        
        return {
            "raw_prompt": compliance_text,
            "structured": normalized if isinstance(normalized, dict) else {}
        }
    
    except Exception as e:
        duration = time.time() - start_time
        print(f"[{llm_call_id}] ❌ Error parsing {compliance_type} compliance ({duration:.2f}s): {e}")
        return {
            "raw_prompt": compliance_text,
            "structured": {}
        }


def normalize_parsed_requirements(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize parsed requirements structure.
    Handles nested arrays, field name mapping, etc.
    Based on Old_Code_Archive/main.py normalize_parsed_requirements()
    """
    
    if not parsed or not isinstance(parsed, dict):
        return {}
    
    normalized = {}
    
    # Handle nested "requirements" array format (if LLM returns this)
    if "requirements" in parsed and isinstance(parsed["requirements"], list):
        for req_obj in parsed["requirements"]:
            if isinstance(req_obj, dict):
                req_type = req_obj.get("type", "").lower()
                req_data = req_obj.get("data", {}) or req_obj.get("value") or req_obj
                
                # Map skills
                if req_type in ["skills", "skill", "hard_skills"]:
                    if isinstance(req_data, dict):
                        skill_value = req_data.get("skill") or req_data.get("skills") or req_data.get("required")
                        skills_list = [s.strip() for s in skill_value.split(",")] if isinstance(skill_value, str) else (skill_value if isinstance(skill_value, list) else [])
                    else:
                        skills_list = [str(req_data)] if req_data else []
                    
                    # Filter out empty strings
                    skills_list = [s for s in skills_list if s and s.strip()]
                    if skills_list:
                        normalized["hard_skills"] = {
                            "type": "list",
                            "specified": True,
                            "required": skills_list,
                            "optional": []
                        }
                
                # Map experience
                elif req_type in ["numeric", "experience", "years"]:
                    normalized["experience"] = {
                        "type": "numeric",
                        "specified": True,
                        "min": req_data.get("min") if isinstance(req_data, dict) else (float(req_data) if req_data else None),
                        "max": req_data.get("max") if isinstance(req_data, dict) else None,
                        "unit": "years"
                    }
        
        return normalized if normalized else parsed
    
    # Standard flat format - normalize field names
    for field_name, field_value in parsed.items():
        if not isinstance(field_value, dict):
            continue
        
        # Map common field name variations to standard names
        mapped_name = field_name
        field_lower = field_name.lower()
        
        if field_lower in ["skills", "skill", "required_skills", "technical_skills"]:
            mapped_name = "hard_skills"
        elif field_lower in ["years_of_experience", "years_experience", "exp", "years"]:
            mapped_name = "experience"
        elif field_lower in ["dept", "department", "field"]:
            mapped_name = "department"
        elif field_lower in ["loc", "location"]:
            mapped_name = "location"
        elif field_lower in ["edu", "education", "degree"]:
            mapped_name = "education"
        
        # Copy with normalized name
        normalized[mapped_name] = field_value
    
    return normalized


def process_job_compliances(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process both mandatory and soft compliances from job data.
    
    Args:
        job_data: Job object from database
        
    Returns: {
        "mandatory_compliances": {raw_prompt, structured},
        "soft_compliances": {raw_prompt, structured}
    }
    """
    
    filter_requirements = job_data.get('filter_requirements', {})
    
    # Extract raw prompts
    mandatory_text = ""
    soft_text = ""
    
    if filter_requirements:
        mandatory_compliance = filter_requirements.get('mandatory_compliances', {})
        soft_compliance = filter_requirements.get('soft_compliances', {})
        
        if mandatory_compliance:
            mandatory_text = mandatory_compliance.get('raw_prompt', '')
        
        if soft_compliance:
            soft_text = soft_compliance.get('raw_prompt', '')
    
    print(f"\n📋 Compliance Parsing:")
    print(f"   Mandatory: {len(mandatory_text)} chars")
    print(f"   Soft: {len(soft_text)} chars")
    
    # Parse both compliances
    result = {
        "mandatory_compliances": {"raw_prompt": "", "structured": {}},
        "soft_compliances": {"raw_prompt": "", "structured": {}}
    }
    
    # Parse mandatory compliances if present
    if mandatory_text and mandatory_text.strip():
        print(f"\n🔴 Parsing MANDATORY compliances...")
        result["mandatory_compliances"] = parse_compliance_text(mandatory_text, "mandatory")
        structured_count = len(result["mandatory_compliances"].get("structured", {}))
        print(f"   ✅ Extracted {structured_count} mandatory requirement field(s)")
    else:
        print(f"   ℹ️ No mandatory compliances specified")
    
    # Parse soft compliances if present
    if soft_text and soft_text.strip():
        print(f"\n🟢 Parsing SOFT compliances...")
        result["soft_compliances"] = parse_compliance_text(soft_text, "soft")
        structured_count = len(result["soft_compliances"].get("structured", {}))
        print(f"   ✅ Extracted {structured_count} soft requirement field(s)")
    else:
        print(f"   ℹ️ No soft compliances specified")
    
    return result


if __name__ == "__main__":
    # Test the parser
    test_mandatory = """
    MANDATORY REQUIREMENTS (Must have ALL):
    - Minimum 5 years ML/AI experience
    - Required Skills: Python, TensorFlow, PyTorch
    - Master's degree in CS/ML/AI or related field
    - Production ML system deployment experience
    """
    
    test_soft = """
    PREFERRED QUALIFICATIONS (Nice to have):
    - PhD in Computer Science or Machine Learning
    - Experience with MLOps tools and practices
    - Knowledge of Docker and Kubernetes
    """
    
    print("Testing Compliance Parser\n")
    print("=" * 60)
    
    mandatory_result = parse_compliance_text(test_mandatory, "mandatory")
    print(f"\nMandatory Result:")
    print(json.dumps(mandatory_result, indent=2))
    
    print("\n" + "=" * 60)
    
    soft_result = parse_compliance_text(test_soft, "soft")
    print(f"\nSoft Result:")
    print(json.dumps(soft_result, indent=2))

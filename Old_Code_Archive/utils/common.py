"""
Common utilities shared across modules.
Reduces code duplication and provides consistent behavior.
"""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path


def extract_function_call(response) -> Dict[str, Any]:
    """
    Extract function call arguments from OpenAI response.
    Handles both new and legacy response formats.
    
    Args:
        response: OpenAI API response object
        
    Returns:
        Parsed function call arguments as dictionary
        
    Raises:
        RuntimeError: If function call is missing or invalid
    """
    choice = response.choices[0]
    msg = choice.message
    
    func_call = getattr(msg, "function_call", None)
    if not func_call and isinstance(msg, dict):
        func_call = msg.get("function_call")
    
    if not func_call:
        raise RuntimeError("Model did not return function_call response.")
    
    args_text = getattr(func_call, "arguments", None) or func_call.get("arguments")
    if not args_text:
        raise RuntimeError("Function call returned but 'arguments' missing.")
    
    try:
        return json.loads(args_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse function call arguments: {e}")


def safe_json_load(file_path: Path, default: Any = None) -> Any:
    """
    Safely load JSON file with error handling.
    
    Args:
        file_path: Path to JSON file
        default: Default value if file doesn't exist or is invalid
        
    Returns:
        Loaded JSON data or default value
    """
    try:
        if not file_path.exists():
            return default
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️ Error loading {file_path}: {e}")
        return default


def safe_json_save(data: Any, file_path: Path, indent: int = 2) -> bool:
    """
    Safely save data to JSON file with error handling.
    
    Args:
        data: Data to save
        file_path: Path to save file
        indent: JSON indentation
        
    Returns:
        True if successful, False otherwise
    """
    try:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=False)
        return True
    except (IOError, TypeError) as e:
        print(f"⚠️ Error saving {file_path}: {e}")
        return False


def extract_jd_skills_from_domain_tags(domain_tags: List[str]) -> Dict[str, List[str]]:
    """
    Extract required and preferred skills from JD domain_tags.
    Shared utility to avoid duplication.
    
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


def normalize_skills_list(skills: List[str]) -> List[str]:
    """
    Normalize a list of skills (lowercase, strip, dedupe).
    
    Args:
        skills: List of skill strings
        
    Returns:
        Normalized, deduplicated list
    """
    normalized = []
    seen = set()
    for skill in skills:
        if skill:
            norm = skill.lower().strip()
            if norm and norm not in seen:
                normalized.append(norm)
                seen.add(norm)
    return normalized


def canonicalize_token(token: str) -> str:
    """Normalize a single token."""
    return token.strip() if token else ""


def canonicalize_string_list(arr: List[str]) -> List[str]:
    """
    Canonicalize a list of strings (normalize, dedupe).
    Shared utility to avoid duplication.
    """
    out = []
    seen = set()
    for token in arr or []:
        can = canonicalize_token(token)
        if can and can not in seen:
            out.append(can)
            seen.add(can.lower())  # Case-insensitive deduplication
    return out


def canonicalize_skills_block(skills_block: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    Canonicalize a skills block dictionary.
    Shared utility to avoid duplication.
    """
    out = {}
    for cat, arr in (skills_block or {}).items():
        out[cat] = canonicalize_string_list(arr)
    return out

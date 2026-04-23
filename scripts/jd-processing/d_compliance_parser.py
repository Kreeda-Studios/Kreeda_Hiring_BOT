#!/usr/bin/env python3
"""
d_compliance_parser.py — DEPRECATED
=====================================
Compliance requirements (mandatory and soft) are now extracted directly
by b_ai_jd_parser.py as `mandatory_compliances` and `soft_compliances`
fields on the JDExtraction schema.

This file is kept as a no-op stub so any legacy import does not break.
"""

from typing import Dict, Any


def validate_and_format_compliances(job_data: dict) -> Dict[str, Any]:
    """Stub — compliance parsing is handled by b_ai_jd_parser.py."""
    return {
        "success": True,
        "filter_requirements": {
            "mandatory_compliances": {"raw_prompt": "", "structured": {}},
            "soft_compliances": {"raw_prompt": "", "structured": {}},
        },
        "stats": {"mandatory_count": 0, "soft_count": 0, "total_count": 0},
        "error": None,
    }


def process_job_compliances(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Stub — compliance parsing is handled by b_ai_jd_parser.py."""
    return {
        "mandatory_compliances": {"raw_prompt": "", "structured": {}},
        "soft_compliances": {"raw_prompt": "", "structured": {}},
    }


def parse_compliance_text(compliance_text: str, compliance_type: str = "mandatory") -> Dict[str, Any]:
    """Stub — compliance parsing is handled by b_ai_jd_parser.py."""
    return {"raw_prompt": compliance_text, "structured": {}}

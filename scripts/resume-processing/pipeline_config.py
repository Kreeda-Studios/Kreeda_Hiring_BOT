#!/usr/bin/env python3
"""
Pipeline Configuration & Audit Registry

Centralized source of truth for:
1. PIPELINE_VERSION locking
2. OpenAI LLM & Embedding Model declarations
3. Prompt Version Registry for Auditability
"""

import os
from typing import Dict, Any

# ============================================================================
# PIPELINE & MODEL LOCKS
# ============================================================================

PIPELINE_VERSION = "1.2.0"
LLM_MODEL_NAME = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
EMBEDDING_MODEL_NAME = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")

# ============================================================================
# PROMPT REGISTRY FOR HISTORICAL AUDITING
# ============================================================================

PROMPT_REGISTRY = {
    "version": "1.2.0",
    "parser_prompt_version": "v1.2-structured-extraction",
    "compliance_prompt_version": "v1.2-hard-requirements-strict",
    "keyword_prompt_version": "v1.2-linear-continuous-matching",
    "semantic_scoring_version": "v1.2-6-section-weighted-cosine"
}


def get_pipeline_metadata() -> Dict[str, Any]:
    """
    Get standardized pipeline metadata payload for audit logging in MongoDB.
    """
    return {
        "pipeline_version": PIPELINE_VERSION,
        "model_used": LLM_MODEL_NAME,
        "embedding_model": EMBEDDING_MODEL_NAME,
        "prompt_versions": PROMPT_REGISTRY
    }

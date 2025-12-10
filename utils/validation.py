"""
Data validation schemas using Pydantic.
Validates JSON structures from JD and Resume parsing.
"""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, validator, field_validator
from pathlib import Path


# ==================== Resume Schemas ====================

class ContactInfo(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None
    profile: Optional[str] = None


class InferredSkill(BaseModel):
    skill: str
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    provenance: Optional[List[str]] = []


class SkillProficiency(BaseModel):
    skill: str
    level: Optional[str] = None
    years_last_used: Optional[int] = None
    provenance: Optional[List[str]] = []


class ProjectMetrics(BaseModel):
    difficulty: Optional[float] = Field(None, ge=0.0, le=1.0)
    novelty: Optional[float] = Field(None, ge=0.0, le=1.0)
    skill_relevance: Optional[float] = Field(None, ge=0.0, le=1.0)
    complexity: Optional[float] = Field(None, ge=0.0, le=1.0)
    technical_depth: Optional[float] = Field(None, ge=0.0, le=1.0)
    domain_relevance: Optional[float] = Field(None, ge=0.0, le=1.0)
    execution_quality: Optional[float] = Field(None, ge=0.0, le=1.0)


class Project(BaseModel):
    name: Optional[str] = None
    duration_start: Optional[str] = None
    duration_end: Optional[str] = None
    role: Optional[str] = None
    domain: Optional[str] = None
    tech_keywords: Optional[List[str]] = []
    approach: Optional[str] = None
    impact_metrics: Optional[Dict[str, Any]] = {}
    primary_skills: Optional[List[str]] = []
    metrics: Optional[ProjectMetrics] = None


class ExperienceEntry(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    responsibilities_keywords: Optional[List[str]] = []
    achievements: Optional[List[str]] = []
    primary_tech: Optional[List[str]] = []


class EducationEntry(BaseModel):
    degree: Optional[str] = None
    field: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None


class CanonicalSkills(BaseModel):
    programming: Optional[List[str]] = []
    ml_ai: Optional[List[str]] = []
    frontend: Optional[List[str]] = []
    backend: Optional[List[str]] = []
    testing: Optional[List[str]] = []
    databases: Optional[List[str]] = []
    cloud: Optional[List[str]] = []
    infra: Optional[List[str]] = []
    devtools: Optional[List[str]] = []
    methodologies: Optional[List[str]] = []


class EmbeddingHints(BaseModel):
    profile_embed: Optional[str] = None
    projects_embed: Optional[str] = None
    skills_embed: Optional[str] = None


class ResumeSchema(BaseModel):
    """Validates parsed resume JSON structure."""
    candidate_id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    role_claim: Optional[str] = None
    years_experience: Optional[float] = Field(None, ge=0.0)
    location: Optional[str] = None
    contact: Optional[ContactInfo] = None
    domain_tags: Optional[List[str]] = []
    profile_keywords_line: str = Field(..., min_length=1)
    canonical_skills: CanonicalSkills = Field(default_factory=CanonicalSkills)
    inferred_skills: Optional[List[InferredSkill]] = []
    skill_proficiency: Optional[List[SkillProficiency]] = []
    projects: Optional[List[Project]] = []
    experience_entries: Optional[List[ExperienceEntry]] = []
    education: Optional[List[EducationEntry]] = []
    ats_boost_line: str = Field(..., min_length=1)
    embedding_hints: Optional[EmbeddingHints] = None
    explainability: Optional[Dict[str, Any]] = {}
    meta: Optional[Dict[str, Any]] = {}

    @field_validator('candidate_id')
    @classmethod
    def validate_candidate_id(cls, v):
        if not v or not v.strip():
            raise ValueError("candidate_id cannot be empty")
        return v.strip()

    @field_validator('name')
    @classmethod
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError("name cannot be empty")
        return v.strip()

    class Config:
        extra = "allow"  # Allow extra fields for backward compatibility


# ==================== JD Schemas ====================

class FilterRequirementsStructured(BaseModel):
    experience: Optional[Dict[str, Any]] = None
    hard_skills: Optional[List[str]] = []
    preferred_skills: Optional[List[str]] = []
    location: Optional[str] = None
    education: Optional[List[str]] = []
    other_criteria: Optional[List[str]] = []


class FilterRequirements(BaseModel):
    raw_prompt: Optional[str] = None
    structured: Optional[FilterRequirementsStructured] = None
    re_ranking_instructions: Optional[str] = None


class Weighting(BaseModel):
    required_skills: Optional[float] = Field(None, ge=0.0, le=1.0)
    preferred_skills: Optional[float] = Field(None, ge=0.0, le=1.0)
    responsibilities: Optional[float] = Field(None, ge=0.0, le=1.0)
    domain_relevance: Optional[float] = Field(None, ge=0.0, le=1.0)
    technical_depth: Optional[float] = Field(None, ge=0.0, le=1.0)
    soft_skills: Optional[float] = Field(None, ge=0.0, le=1.0)
    education: Optional[float] = Field(None, ge=0.0, le=1.0)
    certifications: Optional[float] = Field(None, ge=0.0, le=1.0)
    keywords_exact: Optional[float] = Field(None, ge=0.0, le=1.0)
    keywords_semantic: Optional[float] = Field(None, ge=0.0, le=1.0)


class JDSchema(BaseModel):
    """Validates parsed JD JSON structure."""
    role_title: str = Field(..., min_length=1)
    alt_titles: Optional[List[str]] = []
    seniority_level: Optional[str] = None
    department: Optional[str] = None
    industry: Optional[str] = None
    domain_tags: Optional[List[str]] = []
    location: Optional[str] = None
    work_model: Optional[str] = None
    employment_type: Optional[str] = None
    years_experience_required: Optional[float] = Field(None, ge=0.0)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: Optional[List[str]] = []
    tools_tech: Optional[List[str]] = []
    soft_skills: Optional[List[str]] = []
    responsibilities: List[str] = Field(default_factory=list)
    weighting: Weighting = Field(default_factory=Weighting)
    keywords_flat: List[str] = Field(default_factory=list)
    keywords_weighted: Optional[Dict[str, float]] = {}
    hr_points: int = Field(default=0, ge=0)
    hr_notes: Optional[List[Dict[str, Any]]] = []
    filter_requirements: Optional[FilterRequirements] = None
    meta: Optional[Dict[str, Any]] = {}

    @field_validator('role_title')
    @classmethod
    def validate_role_title(cls, v):
        if not v or not v.strip():
            raise ValueError("role_title cannot be empty")
        return v.strip()

    class Config:
        extra = "allow"  # Allow extra fields for backward compatibility


# ==================== Validation Functions ====================

def validate_resume(data: Dict[str, Any], file_path: Optional[Path] = None) -> ResumeSchema:
    """
    Validate resume JSON data.
    
    Args:
        data: Dictionary containing resume data
        file_path: Optional path for error reporting
        
    Returns:
        Validated ResumeSchema object
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        return ResumeSchema(**data)
    except Exception as e:
        file_info = f" (file: {file_path})" if file_path else ""
        raise ValueError(f"Resume validation failed{file_info}: {str(e)}") from e


def validate_jd(data: Dict[str, Any], file_path: Optional[Path] = None) -> JDSchema:
    """
    Validate JD JSON data.
    
    Args:
        data: Dictionary containing JD data
        file_path: Optional path for error reporting
        
    Returns:
        Validated JDSchema object
        
    Raises:
        ValidationError: If validation fails
    """
    try:
        return JDSchema(**data)
    except Exception as e:
        file_info = f" (file: {file_path})" if file_path else ""
        raise ValueError(f"JD validation failed{file_info}: {str(e)}") from e


def validate_resume_file(file_path: Path) -> ResumeSchema:
    """Validate resume JSON file."""
    import json
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return validate_resume(data, file_path)


def validate_jd_file(file_path: Path) -> JDSchema:
    """Validate JD JSON file."""
    import json
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return validate_jd(data, file_path)


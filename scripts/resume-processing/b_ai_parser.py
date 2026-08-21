#!/usr/bin/env python3
"""
AI Resume Parser — Pure LLM Structured Extraction
===================================================
Replaces old function-calling logic with client.responses.parse +
a strict Pydantic schema. Model and API style match resume_parser.py reference.
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path
from typing import List, Optional

# Add parent directory for imports
sys.path.append(str(Path(__file__).parent.parent))

from pydantic import BaseModel
from openai_client import get_async_openai_client

try:
    from pipeline_config import LLM_MODEL_NAME as MODEL_NAME
except ImportError:
    MODEL_NAME = "gpt-4o-mini"


# ──────────────────────────────────────────────
# PYDANTIC SCHEMA  (mirrors resume_parser.py)
# ──────────────────────────────────────────────

class MetricAI(BaseModel):
    impact: float
    difficulty: int
    complexity: int
    domain_relevance: int


class Project(BaseModel):
    title: Optional[str]
    demo_link: Optional[str]
    code_link: Optional[str]
    metric_ai: MetricAI


class ExperienceDetail(BaseModel):
    role: Optional[str]
    company: Optional[str]
    employment_type: Optional[str]
    location: Optional[str]
    start: Optional[str]
    end: Optional[str]
    duration_in_months: Optional[int]
    impact: List[str]


class Experience(BaseModel):
    date_calculation_scratchpad: str
    total_full_time_experience: int
    total_internship_experience_in_months: int
    details: List[ExperienceDetail]


class Skills(BaseModel):
    provided: List[str]
    inferred: List[str]
    soft_skills: List[str]


class Education(BaseModel):
    start: Optional[str]
    end: Optional[str]
    college: Optional[str]
    degree: Optional[str]
    department: Optional[str]
    grade: Optional[str]


class Profile(BaseModel):
    name: Optional[str]
    contact: Optional[str]
    email: Optional[str]
    linkedin: Optional[str]
    github: Optional[str]
    leetcode: Optional[str]
    hackerrank: Optional[str]
    location: Optional[str]


class ResumeExtraction(BaseModel):
    profile: Profile
    domain: str
    confidence: float
    skills: Skills
    experience: Experience
    projects: List[Project]
    educations: List[Education]
    certifications: List[str]
    achievements: List[str]


# ──────────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are a strict resume intelligence extraction engine.

Your task is to extract structured information from raw resume text and return ONLY valid JSON that follows the exact schema provided.

You are not a conversational assistant.
You are a deterministic structured extraction system.

You MUST follow these rules:

. General Rules
  - Output ONLY valid JSON.
  - No markdown. No comments. No explanations. No extra keys.
  - Do not reorder schema. Do not remove keys.
  - If a field is not present in resume → return null or empty array.
  - Never hallucinate links, experience, grades, or skills.
  - Only generate content where explicitly allowed.

. Allowed Generated Fields
  You are ONLY allowed to generate:
  - "domain"
  - "confidence"
  - "skills.inferred"
  - "projects[].metric_ai"
  Everything else must be extracted strictly from resume content.

. Domain Rules
  You MUST choose exactly one domain from:
  - Full stack
  - AIML
  - UI/UX
  - QA
  You must provide "confidence" as a float between 0 and 1.
  Do not invent domain outside the allowed list.

. Experience Rules
  - If a job role is ongoing, currently active, or says "Present", "Current", "Ongoing", "till date", or has a blank end date for the most recent job, you MUST set the "end" date field value to "Present" exactly. Do NOT attempt to replace it with a specific year or month.
  - For all other roles, extract the "start" and "end" date strings exactly as written in the resume (e.g., "July 2025", "Feb 2024").
  - Do NOT calculate duration_in_months, total_full_time_experience, or total_internship_experience_in_months yourself. Set them to 0 or null — they will be calculated automatically by the backend.
  - DATE FALLBACK RULES (Partial & Year-Only Dates):
    * If start month is given but end month is missing (e.g. "March 2023 - 2024"), extract start as "March 2023" and end as "2024". Do not force December unless explicitly written.
    * If end month is given but start month is missing (e.g. "2023 - March 2024"), extract start as "2023" and end as "March 2024".
    * If BOTH start and end months are missing (e.g. "2023 - 2024"), extract them as "2023" and "2024" respectively.
  - Employment_type must be exactly one of: Full Time, Part Time, Intern, Intern above 6 months, Contractual.
  - DEFAULT EMPLOYMENT TYPE: If employment_type is not explicitly specified as Intern, Part Time, or Contractual in the resume text, default employment_type to "Full Time".

. Skills Rules
  - provided: Extract ONLY EXPLICIT HARD/TECHNICAL SKILLS from the resume. Do NOT include soft skills here.
  - inferred: Extract every named tool, software, platform, framework, or technology that is explicitly
    mentioned ANYWHERE in the resume — in Experience bullets, Project descriptions, Certifications,
    Education, or any other section — even if it is not listed under a dedicated Skills section.
    Rules:
      * Include it if the tool/technology name appears verbatim or as a clear abbreviation in any
        sentence anywhere in the resume. Example: "Used Figma to design wireframes" → infer "Figma".
      * Do NOT invent tools not mentioned. The name must appear explicitly in the resume text.
      * No explanations — only the tool/skill name.
      * Do not duplicate skills already in `provided`.
      * This list is a complete safety net — be thorough, not conservative.
  - soft_skills: Extract any soft skills (e.g. "Analytical thinking", "Team collaboration", "Problem solving") here.
  - Do not invent technologies not mentioned anywhere in the resume.

. Projects Rules

  STEP 1 — RECOGNITION: What qualifies as a project?
  Before extracting fields, first identify what counts as a project entry.

  A. Named individual project: A specifically titled deliverable (e.g. "E-Commerce App", "Figma Redesign for XYZ")
     → Extract as one project entry per named item.

  B. Generic/collective project section: A section heading that signals project work (contains words like
     "Projects", "Portfolio", "Case Studies", "Work Samples", "Designs", "Builds", "Side Projects",
     "Personal Projects", "Academic Projects", "Contributions", "Open Source", "Freelance Work")
     BUT lists bullet points describing collective/general work with no individually named sub-projects.
     → Treat the ENTIRE section as ONE project entry:
         * title       → the section heading exactly as written
         * demo_link   → null (unless explicitly present)
         * code_link   → null (unless explicitly present)
         * metric_ai   → score based on the described work in the bullets

  C. Projects embedded in Education: If an Education entry mentions a "Final Year Project", "Capstone",
     "Thesis", "Academic Project", "Major Project", or similar academic deliverable with a description
     → Extract it as a separate Project entry (do NOT leave it only in Education).

  D. Projects mentioned in Certifications: If a certification entry describes case studies, capstone
     projects, or portfolio work (e.g. "Google UX Design Certificate – 3 case studies")
     → Extract the described work as a Project entry.

  E. Projects mentioned in Summary/About Me: If the summary describes a specific built thing
     (uses words like "built", "developed", "designed", "created", "launched") with enough detail
     → Extract it as a Project entry.

  STEP 2 — BOUNDARY: Project vs Experience (do NOT mix these)

  An entry belongs in EXPERIENCE (not Projects) if it satisfies ALL THREE:
    1. A named external organization/company acts as the EMPLOYER (not merely a client mention)
    2. A job title / role name is present
    3. A time period (start + end dates) is explicitly stated

  An entry belongs in PROJECTS if ANY of the following are true:
    - No employer at all (personal, academic, or self-directed work)
    - "Self-employed", "Freelance", "Independent" is listed as the organization but there is NO job title
    - It appears under a Projects/Portfolio/Case Studies heading regardless of format
    - The word "project", "case study", "capstone", "thesis", "hackathon", or "competition" is used
    - It describes something *built*, *designed*, *created*, or *developed* with no employer-employee structure

  GRAY AREA RULE: "Freelance Designer, Self-employed" WITH a role title AND dates → Experience.
                  "Designed logo for XYZ Corp" under a Projects section → Project.

  STEP 3 — EXTRACTION: For every identified project entry, extract:
  - title: the project name or section heading
  - demo_link: only if an explicit URL is present; otherwise null
  - code_link: only if an explicit URL is present; otherwise null
  - metric_ai: generate scores reflecting:
      * impact (0.0 to 1.0): real-world usefulness or user reach of the work
      * difficulty (1–10): technical difficulty of implementation
      * complexity (1–10): architectural or design complexity
      * domain_relevance (1–10): alignment with the candidate's identified domain
    Metrics must reflect actual described work. Do not inflate scores.

  GRACEFUL DEGRADATION RULE:
  When uncertain whether something is a project, EXTRACT IT as a project rather than skipping.
  Reason: a borderline extraction will score low via metric_ai (recoverable).
  A missed section results in a permanent 0% project score (not recoverable).
  The cost of over-extracting is always lower than the cost of under-extracting.


. Hyperlink Rules
  - The resume may contain embedded hyperlinks. These will be provided separately.
  - Use them to populate linkedin, github, leetcode, hackerrank, demo_link, code_link.
  - If a hyperlink is available for a profile or link field, use the full hyperlink URL.
  - Do not fabricate any URLs.

. Education Rules
  - Extract: start, end, college, degree, department, grade exactly as written.
  - If any field is missing, return null.

. Explicit Null and Empty Rules
  - Missing Sections: If an entire section (e.g. projects, certifications, achievements) is missing, return an empty array `[]`.
  - Array Cleanliness: Do not populate arrays (like achievements or impact) with empty strings `""`, or hallucinated keys.
  - Missing Strings: If a string field is missing, ALWAYS return `null`. NEVER return an empty string `""`.

. Strict Achievements Rules
  - Do NOT extract random hyperlinks, URLs, or labels (e.g. "Certificate Link", "Website link", "Demo Video") into Achievements.
  - Do NOT extract bullet points that belong in Projects or Experience sections.
  - MERGE any publications, hackathons, and contests directly into the achievements array.
  - Only extract explicit awards, honors, competitive ranks, publications, or scholarships into achievements.

. Failure Condition
  If resume text is empty or malformed, return:
  {"error": "Invalid resume text"}

. All skills listed under "skills.provided" must be returned in their full, expanded form, and STRICTLY no explanation of the skills(only skill name).

  If a skill appears in abbreviated or short form in the resume, you must convert it to its complete, standardized form.

  Examples:

  CNN → Convolutional Neural Network

  RNN → Recurrent Neural Network

  NLP → Natural Language Processing
"""

import re
from datetime import datetime, date

# ──────────────────────────────────────────────
# DETERMINISTIC DATE PARSING & MONTH CALCULATOR (Python Stdlib)
# ──────────────────────────────────────────────

def parse_date_to_year_month(date_str: str, is_end: bool = False) -> tuple[int, int] | None:
    if not date_str:
        return None
    
    date_str_clean = date_str.strip().lower()
    
    # Handle "present" / "current" / "now" / "ongoing" / "active" / till date
    if any(term in date_str_clean for term in ("present", "current", "now", "ongoing", "active", "till date")):
        today = date.today()
        return today.year, today.month
        
    # Check if it's year only (e.g., "2024")
    year_only_match = re.match(r'^20\d{2}$', date_str_clean)
    if year_only_match:
        year = int(year_only_match.group(0))
        # If it's start date, default to Jan. If end, default to Dec
        month = 12 if is_end else 1
        return year, month

    # Standard months list
    months_map = {
        'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
        'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
        'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
        'nov': 11, 'november': 11, 'dec': 12, 'december': 12
    }

    # Match Month Year patterns allowing any separator (comma, apostrophe, dash, slash, space)
    m = re.search(r'([a-zA-Z]{3,9})[^a-zA-Z0-9]*(?:20)?(\d{2,4})', date_str_clean)
    if m:
        m_str, y_str = m.group(1), m.group(2)
        month = months_map.get(m_str)
        if month:
            year = int(y_str)
            if len(y_str) == 2:
                year += 2000
            return year, month

    # Match numerical patterns like "07/2025", "2025-07"
    m_num = re.search(r'(\d{1,2})[\/\-](20\d{2}|\d{2})', date_str_clean)
    if m_num:
        m_str, y_str = m_num.group(1), m_num.group(2)
        month = int(m_str)
        year = int(y_str)
        if len(y_str) == 2:
            year += 2000
        if 1 <= month <= 12:
            return year, month

    m_num_rev = re.search(r'(20\d{2})[\/\-](\d{1,2})', date_str_clean)
    if m_num_rev:
        y_str, m_str = m_num_rev.group(1), m_num_rev.group(2)
        month = int(m_str)
        year = int(y_str)
        if 1 <= month <= 12:
            return year, month

    return None


def get_months_in_range(start_str: str, end_str: str) -> set[tuple[int, int]]:
    if not start_str or not end_str:
        return set()
        
    start_clean = start_str.strip().lower()
    end_clean = end_str.strip().lower()
    
    # Check if BOTH are year-only formats (e.g., "2023 - 2024" or "2024 - 2024")
    is_start_year_only = bool(re.match(r'^\d{4}$', start_clean))
    is_end_year_only = bool(re.match(r'^\d{4}$', end_clean))
    
    if is_start_year_only and is_end_year_only:
        sy = int(start_clean)
        ey = int(end_clean)
        diff_years = max(0, ey - sy)
        
        # Stated duration rule: (EndYear - StartYear) * 12 months
        total_months = diff_years * 12
        months = set()
        if total_months > 0:
            # Generate months from Jan (ey - diff_years + 1) to Dec ey
            cy = ey - diff_years + 1
            cm = 1
            for _ in range(total_months):
                months.add((cy, cm))
                cm += 1
                if cm > 12:
                    cm = 1
                    cy += 1
        return months

    # Standard case: at least one has a month or Present
    start_info = parse_date_to_year_month(start_clean, is_end=False)
    end_info = parse_date_to_year_month(end_clean, is_end=True)
    if not start_info or not end_info:
        return set()
    
    sy, sm = start_info
    ey, em = end_info
    
    months = set()
    cy, cm = sy, sm
    while (cy < ey) or (cy == ey and cm <= em):
        months.add((cy, cm))
        cm += 1
        if cm > 12:
            cm = 1
            cy += 1
    return months


def recalculate_experience(parsed_data: dict):
    """
    Recalculates all experience details duration_in_months and totals in Python.
    Prevents double-counting overlapping periods dynamically using set unions.
    """
    experience = parsed_data.get('experience') or {}
    details = experience.get('details') or []
    
    full_time_months = set()
    internship_months = set()
    
    for detail in details:
        start_str = detail.get('start') or ''
        end_str = detail.get('end') or ''
        
        job_months = get_months_in_range(start_str, end_str)
        detail['duration_in_months'] = len(job_months)
        
        emp_type = (detail.get('employment_type') or '').lower()
        if 'intern' in emp_type:
            internship_months.update(job_months)
        else:
            full_time_months.update(job_months)
            
    experience['total_full_time_experience'] = len(full_time_months)
    experience['total_internship_experience_in_months'] = len(internship_months)


# ──────────────────────────────────────────────
# LLM CALL
# ──────────────────────────────────────────────

async def parse_resume_with_ai(
    resume_text: str,
    hyperlinks: list[str] = None,
    jd_data: dict = None,
) -> dict:
    """
    Parse resume using structured LLM extraction.

    Args:
        resume_text: Raw resume text
        hyperlinks:  Embedded hyperlinks extracted from the PDF
        jd_data:     Job description data (kept for API compatibility, not used)

    Returns:
        {'success': bool, 'parsed_data': dict} or {'success': False, 'error': str}
    """
    try:
        client = get_async_openai_client()

        links = hyperlinks or []

        user_input = f"""Extract structured resume information.

RAW TEXT:
{resume_text}

HYPERLINKS:
{json.dumps(links)}
"""

        response = await client.responses.parse(
            model=MODEL_NAME,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_input},
            ],
            text_format=ResumeExtraction,
        )

        parsed = response.output_parsed
        parsed_data = parsed.model_dump()
        
        # Override LLM calculations with deterministic Python calculation
        recalculate_experience(parsed_data)
        
        return {
            "success": True,
            "parsed_data": parsed_data,
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Resume parsing failed: {str(e)}",
        }
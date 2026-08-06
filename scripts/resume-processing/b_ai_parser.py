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

MODEL_NAME = "gpt-5-mini"


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
  - Use "date_calculation_scratchpad" to explicitly list out each job role, its start/end dates, state any month assumptions made (e.g. "assumed Dec 2024 for end month"), and calculate the duration in months BEFORE outputting the final integer values. 
  - MATHEMATICAL RULE: Always use INCLUSIVE month counting. For example, "May 2023 to June 2024" is calculated as: (2024 - 2023)*12 + (6 - 5) + 1 = 14 months.
  - Convert all experience durations into months (integer values).
  - "total_full_time_experience" must be in months.
  - "total_internship_experience_in_months" must be in months.
  - If role says "Present", calculate until current date: """ + date.today().isoformat() + """.
  - Do not double count overlapping periods. If periods overlap, only count the distinct chronological months once.
  - DATE FALLBACK RULES (Partial & Year-Only Dates):
    * If start month is given but end month is missing (e.g. "March 2023 - 2024"), assume December for the end month ("March 2023 to Dec 2024"). Note this assumption in the scratchpad.
    * If end month is given but start month is missing (e.g. "2023 - March 2024"), assume January for the start month ("Jan 2023 to March 2024"). Note this assumption in the scratchpad.
    * If BOTH start and end months are missing for a year range (e.g. "2023 - 2024"), calculate duration as (EndYear - StartYear) * 12 months (e.g. 2023 to 2024 = 12 months). If end is "Present" (e.g. "2023 - Present"), assume January for start month ("Jan 2023 to current date"). Note this calculation in the scratchpad.
  - If explicit duration is stated (e.g. "3 Month", "6 months", "1 year") without start/end dates, use that stated duration directly as duration_in_months and include it in total experience.
  - If dates and duration are completely absent → exclude from total calculation.
  - Employment_type must be exactly one of: Full Time, Part Time, Intern, Intern above 6 months, Contractual.
  - DEFAULT EMPLOYMENT TYPE: If employment_type is not explicitly specified as Intern, Part Time, or Contractual in the resume text, default employment_type to "Full Time" and include its duration in total_full_time_experience.

. Skills Rules
  - provided: Extract ONLY EXPLICIT HARD/TECHNICAL SKILLS from the resume. Do NOT include soft skills here.
  - inferred: Infer explicit HARD/TECHNICAL SKILLS from Experience, Projects, Certifications, Education sections, STRICTLY No explanation of the skill, and the skill should be in the resume.
  - soft_skills: Extract any soft skills (e.g. "Analytical thinking", "Team collaboration", "Problem solving") here.
  - Do not invent technologies not mentioned anywhere in the resume.

. Projects Rules
  For each project extract: Title, Demo link (if explicitly present), Code Link (if explicitly present).
  You must generate "metric_ai" with:
  - impact (0.0 to 1.0)
  - difficulty (1–10)
  - complexity (1–10)
  - domain_relevance (1–10)
  Metrics must reflect technical depth, architecture sophistication, and alignment with chosen Domain. Do not inflate scores.

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
        return {
            "success": True,
            "parsed_data": parsed.model_dump(),
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Resume parsing failed: {str(e)}",
        }
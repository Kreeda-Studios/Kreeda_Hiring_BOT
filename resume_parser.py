from __future__ import annotations

"""
Resume Intelligence Extraction Engine
======================================
Minimal async parallel pipeline that:
1. Reads PDF resumes from input_resumes/ folder
2. Extracts text + embedded hyperlinks from each PDF
3. Sends extracted content to GPT-5-mini with a strict system prompt
4. Saves structured JSON output to output_json/ folder
"""


import asyncio
import json
import os
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import List, Optional

import fitz
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-5-mini"

INPUT_DIR = Path("input_resumes")
OUTPUT_DIR = Path("output_json")

INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# ──────────────────────────────────────────────
# SAFE SCHEMA (NO SPACES, NO ALIASES)
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
    company: Optional[str]
    role: Optional[str]
    start: Optional[str]
    end: Optional[str]
    employment_type: Optional[str]
    impact: List[str]


class Experience(BaseModel):
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
  - Convert all experience durations into months (integer values).
  - "total_full_time_experience" must be in months.
  - "total_internship_experience_in_months" must be in months.
  - If role says "Present", calculate until current date: """ + date.today().isoformat() + """.
  - Do not double count overlapping periods.
  - If dates are missing → exclude from total calculation.
  - Employment_type must be exactly one of: Full Time, Part Time,Intern,Intern above 6 months, Contractual.

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
# PDF EXTRACTION
# ──────────────────────────────────────────────

def extract_pdf_content(pdf_path: str) -> tuple[str, list[str]]:
    doc = fitz.open(pdf_path)
    text = ""
    links = set()

    for page in doc:
        text += page.get_text()
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                links.add(uri)

    doc.close()
    return text.strip(), sorted(links)


# ──────────────────────────────────────────────
# METADATA
# ──────────────────────────────────────────────

STOPWORDS = {"the", "and", "is", "to", "of", "in", "for", "on", "with"}

def compute_metadata(raw_text: str) -> dict:
    words = re.findall(r"[a-zA-Z]{2,}", raw_text.lower())
    meaningful = [w for w in words if w not in STOPWORDS]
    freq = dict(Counter(meaningful).most_common(20))
    return {
        "word_count": len(words),
        "word_frequency": freq
    }


# ──────────────────────────────────────────────
# LLM CALL (STRUCTURED)
# ──────────────────────────────────────────────

async def extract_resume_data(raw_text: str, hyperlinks: list[str]) -> ResumeExtraction:

  user_input = f"""
  Extract structured resume information.

  RAW TEXT:
  {raw_text}

  HYPERLINKS:
  {json.dumps(hyperlinks)}
  """

  response = await client.responses.parse(
        model=MODEL_NAME,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        text_format=ResumeExtraction,
    )

  return response.output_parsed

# ──────────────────────────────────────────────
# CONVERT TO FINAL FORMAT
# ──────────────────────────────────────────────

def transform_output(data: ResumeExtraction, raw_text: str) -> dict:
    result = data.model_dump()
    result["processed_date"] = date.today().isoformat()
    result["raw_text"] = raw_text.strip()
    result["meta_data"] = compute_metadata(raw_text)
    return result


# ──────────────────────────────────────────────
# PROCESS SINGLE RESUME
# ──────────────────────────────────────────────

async def process_single_resume(pdf_path: Path):
    print(f"[PROCESSING] {pdf_path.name}")

    raw_text, hyperlinks = extract_pdf_content(str(pdf_path))

    if not raw_text:
        result = {"error": "Invalid resume text"}
    else:
        structured = await extract_resume_data(raw_text, hyperlinks)
        result = transform_output(structured, raw_text)

    output_file = OUTPUT_DIR / f"{pdf_path.stem}.json"

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"[DONE] {pdf_path.name}")


# ──────────────────────────────────────────────
# PARALLEL PIPELINE
# ──────────────────────────────────────────────

async def run_pipeline():
    pdf_files = list(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print("No resumes found.")
        sys.exit(1)

    await asyncio.gather(*[process_single_resume(pdf) for pdf in pdf_files])


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_pipeline())
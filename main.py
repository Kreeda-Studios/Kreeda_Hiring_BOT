'''
"""
Resume Intelligence Extraction Engine
======================================
Minimal async parallel pipeline that:
1. Reads PDF resumes from input_resumes/ folder
2. Extracts text + embedded hyperlinks from each PDF
3. Sends extracted content to GPT-4.1 with a strict system prompt
4. Saves structured JSON output to output_json/ folder

Usage:
    python main.py
# """

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Any

import fitz  # type: ignore[import]  # PyMuPDF — for PDF text + hyperlink extraction
from dotenv import load_dotenv  # type: ignore[import]
from openai import AsyncOpenAI  # type: ignore[import]
from schemas import ResumeExtraction

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4.1")

INPUT_DIR = Path("input_resumes")
OUTPUT_DIR = Path("output_json")

# Create directories if they don't exist
INPUT_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

# Async OpenAI client — reused across all parallel calls
client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# ──────────────────────────────────────────────
# SYSTEM PROMPT — strict extraction rules
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """
You are a strict resume intelligence extraction engine.

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
  - "Domain"
  - "Confidence"
  - "Skills.Inferred"
  - "Projects[].Metric(AI)"
  Everything else must be extracted strictly from resume content.

. Domain Rules
  You MUST choose exactly one domain from:
  - Full stack
  - AIML
  - UI/UX
  - QA
  You must provide "Confidence" as a float between 0 and 1.
  Do not invent domain outside the allowed list.

. Experience Rules
  - Convert all experience durations into months (integer values).
  - "Total Full-Time Experience" must be in months.
  - "Total Internship Experience in months" must be in months.
  - If role says "Present", calculate until current date: """ + date.today().isoformat() + """.
  - Do not double count overlapping periods.
  - If dates are missing → exclude from total calculation.
  - Employment_type must be exactly one of: Full Time, Part Time,Intern,Intern above 6 months, Contractual.

. Skills Rules
  - Provided: Extract only from explicit Skills section in the resume.
  - Inferred: Infer only from Experience, Projects, Certifications, Education sections.
  - Do not invent technologies not mentioned anywhere in the resume.

. Projects Rules
  For each project extract: Title, Domain (if explicitly mentioned, else null), Skills Used, Demo link (only if explicitly present), Code Link (only if explicitly present).
  You must generate "Metric(AI)" with:
  - Difficulty (1–10)
  - Complexity (1–10)
  - Domain relevance (1–10)
  Metrics must reflect technical depth, architecture sophistication, and alignment with chosen Domain. Do not inflate scores.

. Hyperlink Rules
  - The resume may contain embedded hyperlinks. These will be provided separately.
  - Use them to populate LinkedIn, Github, Leetcode, HackerRank, Demo link, Code Link, Certification URL.
  - If a hyperlink is available for a profile or link field, use the full hyperlink URL.
  - Do not fabricate any URLs.

  . Education Rules
  - Extract: Start, End, College, Degree, Department, Grade exactly as written.
  - If any field is missing, return null.

. Strict Output Schema
  Return EXACTLY this JSON structure:
  {
    "Profile": {
      "Name": "",
      "Contact": "",
      "Email": "",
      "Linkedin": "",
      "Github": "",
      "Leetcode": "",
      "HackerRank": "",
      "Location": ""
    },
    "Domain": "",
    "Confidence": 0.0,
    "Skills": {
      "Provided": [],
      "Inferred": []
    },
    "Experience": {
      "Total Full-Time Experience": 0,
      "Total Internship Experience in months": 0,
      "Details": [
        {
          "Company": "",
          "Role": "",
          "Start": "",
          "End": "",
          "Employment_type": "",
          "Skills Used": [],
          "Impact": []
        }
      ]
    },
    "Projects": [
      {
        "Title": "",
        "Domain": "",
        "Skills Used": [],
        "Demo link": "",
        "Code Link": "",
        "Metric(AI)": {
          "Difficulty": 0,
          "Complexity": 0,
          "Domain relevance": 0
        }
      }
    ],
    "Educations": [
      {
        "Start": "",
        "End": "",
        "College": "",
        "Degree": "",
        "Department": "",
        "Grade": ""
      }
    ],
    "Certifications": [
      {
        "Title": "",
        "URL": "",
        "Skills": []
      }
    ],
    "Publications": [
      {
        "Title": "",
        "URL": "",
        "Skills": []
      }
    ],
    "Achievements": [],
    "Processed Date": "",
    "RawText": "",
    "MetaData": {
      "Word Count": 0,
      "Word Frequency": {}
    }
  }

. Failure Condition
  If resume text is empty or malformed, return:
  {"error": "Invalid resume text"}

. All skills listed under "Skills → Provided" must be returned in their full, expanded form.

  If a skill appears in abbreviated or short form in the resume, you must convert it to its complete, standardized form.

  Examples:

  CNN → Convolutional Neural Network

  RNN → Recurrent Neural Network

  NLP → Natural Language Processing
"""


# ──────────────────────────────────────────────
# STOPWORDS — for word frequency filtering
# ──────────────────────────────────────────────

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "was", "are", "were", "be", "been",
    "being", "have", "has", "had", "do", "does", "did", "will", "would",
    "could", "should", "may", "might", "shall", "can", "need", "dare",
    "it", "its", "i", "me", "my", "we", "our", "you", "your", "he",
    "him", "his", "she", "her", "they", "them", "their", "this", "that",
    "these", "those", "which", "who", "whom", "what", "where", "when",
    "how", "all", "each", "every", "both", "few", "more", "most", "other",
    "some", "such", "no", "not", "only", "same", "so", "than", "too",
    "very", "just", "because", "as", "until", "while", "about", "between",
    "through", "during", "before", "after", "above", "below", "up", "down",
    "out", "off", "over", "under", "again", "further", "then", "once",
    "also", "into", "if", "else", "any", "like", "used", "using",
}


# ──────────────────────────────────────────────
# PDF EXTRACTION — text + hyperlinks
# ──────────────────────────────────────────────

def extract_pdf_content(pdf_path: str) -> tuple[str, list[str]]:
    """
    Extracts raw text and embedded hyperlinks from a PDF file.

    Returns:
        raw_text:   Full text content of the PDF.
        hyperlinks: List of unique URLs found as embedded links in the PDF.
    """
    doc = fitz.open(pdf_path)
    full_text = ""
    links = set()

    for page in doc:
        # Extract visible text from each page
        full_text += page.get_text()

        # Extract embedded hyperlinks (annotations with URI)
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                links.add(uri)

    doc.close()
    return full_text.strip(), sorted(links)


# ──────────────────────────────────────────────
# METADATA — word count & frequency
# ──────────────────────────────────────────────

def compute_metadata(raw_text: str) -> dict:
    """
    Computes word count and top-20 word frequency (excluding stopwords).

    Returns:
        dict with "Word Count" and "Word Frequency" keys.
    """
    # Tokenize: lowercase, only alphabetic words with 2+ characters
    words = re.findall(r"[a-zA-Z]{2,}", raw_text.lower())

    # Filter stopwords
    meaningful = [w for w in words if w not in STOPWORDS]

    # Top 20 most common
    freq = dict(Counter(meaningful).most_common(20))

    return {
        "Word Count": len(words),
        "Word Frequency": freq,
    }


# ──────────────────────────────────────────────
# LLM CALL — async extraction via GPT-4.1
# ──────────────────────────────────────────────

async def extract_resume_data(raw_text: str, hyperlinks: list[str]) -> ResumeExtraction:
    user_message = "Extract structured information from the following resume text.\n\n"
    user_message += "=== RAW RESUME TEXT ===\n"
    user_message += raw_text + "\n\n"

    if hyperlinks:
        user_message += "=== EMBEDDED HYPERLINKS FOUND IN PDF ===\n"
        for link in hyperlinks:
            user_message += f"- {link}\n"

    response = await client.responses.parse(
        model="gpt-5-mini",
        temperature=0,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        text_format=ResumeExtraction,
    )

    return response.output_parsed


# ──────────────────────────────────────────────
# SINGLE RESUME PROCESSOR
# ──────────────────────────────────────────────

async def process_single_resume(pdf_path: Path) -> None:
    """
    Full pipeline for one resume:
    1. Extract text + hyperlinks from PDF
    2. Send to GPT-4.1 for structured extraction
    3. Inject metadata (word count, frequency, processed date, raw text)
    4. Save result as JSON file
    """
    print(f"  [PROCESSING] {pdf_path.name}")

    # Step 1: Extract PDF content
    raw_text, hyperlinks = extract_pdf_content(str(pdf_path))

    result: dict[str, Any]
    if not raw_text.strip():

      result = {"error": "Invalid resume text"}
    else:
      structured = await extract_resume_data(raw_text, hyperlinks)
      result = structured.model_dump(by_alias=True)

    # Step 3: Inject metadata (computed locally, not by LLM)
    if "error" not in result:
      result["Processed Date"] = date.today().isoformat()
      result["RawText"] = raw_text
      result["MetaData"] = compute_metadata(raw_text)

    # Step 4: Save JSON output
    output_file = OUTPUT_DIR / f"{pdf_path.stem}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"  [DONE] {pdf_path.name} -> {output_file}")


# ──────────────────────────────────────────────
# PARALLEL PIPELINE — processes all PDFs concurrently
# ──────────────────────────────────────────────

async def run_pipeline() -> None:
    """
    Main entry point:
    1. Scans input_resumes/ for PDF files
    2. Launches all resume extractions in parallel via asyncio.gather
    3. Reports summary
    """
    pdf_files = sorted(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"[ERROR] No PDF files found in '{INPUT_DIR}/' directory.")
        print(f"        Place your resume PDFs in the '{INPUT_DIR}/' folder and run again.")
        sys.exit(1)

    print(f"[START] Found {len(pdf_files)} resume(s) to process.\n")

    # Launch all resume processing tasks in parallel
    await asyncio.gather(*[process_single_resume(pdf) for pdf in pdf_files])

    print(f"\n[COMPLETE] All resumes processed. Output saved to '{OUTPUT_DIR}/' directory.")


# ──────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────

if __name__ == "__main__":
    asyncio.run(run_pipeline())
'''

"""
Resume Intelligence Extraction Engine
Structured Output Version (GPT-5-mini compatible)
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

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
    difficulty: int
    complexity: int
    domain_relevance: int


class Project(BaseModel):
    title: Optional[str]
    domain: Optional[str]
    skills_used: List[str]
    demo_link: Optional[str]
    code_link: Optional[str]
    metric_ai: MetricAI


class ExperienceDetail(BaseModel):
    company: Optional[str]
    role: Optional[str]
    start: Optional[str]
    end: Optional[str]
    employment_type: Optional[str]
    skills_used: List[str]
    impact: List[str]


class Experience(BaseModel):
    total_full_time_experience: int
    total_internship_experience_in_months: int
    details: List[ExperienceDetail]


class Skills(BaseModel):
    provided: List[str]
    inferred: List[str]


class Education(BaseModel):
    start: Optional[str]
    end: Optional[str]
    college: Optional[str]
    degree: Optional[str]
    department: Optional[str]
    grade: Optional[str]


class Certification(BaseModel):
    title: Optional[str]
    url: Optional[str]
    skills: List[str]


class Publication(BaseModel):
    title: Optional[str]
    url: Optional[str]
    skills: List[str]


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
    certifications: List[Certification]
    publications: List[Publication]
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
  - "Domain"
  - "Confidence"
  - "Skills.Inferred"
  - "Projects[].Metric(AI)"
  Everything else must be extracted strictly from resume content.

. Domain Rules
  You MUST choose exactly one domain from:
  - Full stack
  - AIML
  - UI/UX
  - QA
  You must provide "Confidence" as a float between 0 and 1.
  Do not invent domain outside the allowed list.

. Experience Rules
  - Convert all experience durations into months (integer values).
  - "Total Full-Time Experience" must be in months.
  - "Total Internship Experience in months" must be in months.
  - If role says "Present", calculate until current date: """ + date.today().isoformat() + """.
  - Do not double count overlapping periods.
  - If dates are missing → exclude from total calculation.
  - Employment_type must be exactly one of: Full Time, Part Time,Intern,Intern above 6 months, Contractual.

. Skills Rules
  - Provided: Extract only from explicit Skills section in the resume.
  - Inferred: Infer only from Experience, Projects, Certifications, Education sections.
  - Do not invent technologies not mentioned anywhere in the resume.

. Projects Rules
  For each project extract: Title, Domain (if explicitly mentioned, else null), Skills Used, Demo link (only if explicitly present), Code Link (only if explicitly present).
  You must generate "Metric(AI)" with:
  - Difficulty (1–10)
  - Complexity (1–10)
  - Domain relevance (1–10)
  Metrics must reflect technical depth, architecture sophistication, and alignment with chosen Domain. Do not inflate scores.

. Hyperlink Rules
  - The resume may contain embedded hyperlinks. These will be provided separately.
  - Use them to populate LinkedIn, Github, Leetcode, HackerRank, Demo link, Code Link, Certification URL.
  - If a hyperlink is available for a profile or link field, use the full hyperlink URL.
  - Do not fabricate any URLs.

  . Education Rules
  - Extract: Start, End, College, Degree, Department, Grade exactly as written.
  - If any field is missing, return null.

. Strict Output Schema
  Return EXACTLY this JSON structure:
  {
    "Profile": {
      "Name": "",
      "Contact": "",
      "Email": "",
      "Linkedin": "",
      "Github": "",
      "Leetcode": "",
      "HackerRank": "",
      "Location": ""
    },
    "Domain": "",
    "Confidence": 0.0,
    "Skills": {
      "Provided": [],
      "Inferred": []
    },
    "Experience": {
      "Total Full-Time Experience": 0,
      "Total Internship Experience in months": 0,
      "Details": [
        {
          "Company": "",
          "Role": "",
          "Start": "",
          "End": "",
          "Employment_type": "",
          "Skills Used": [],
          "Impact": []
        }
      ]
    },
    "Projects": [
      {
        "Title": "",
        "Domain": "",
        "Skills Used": [],
        "Demo link": "",
        "Code Link": "",
        "Metric(AI)": {
          "Difficulty": 0,
          "Complexity": 0,
          "Domain relevance": 0
        }
      }
    ],
    "Educations": [
      {
        "Start": "",
        "End": "",
        "College": "",
        "Degree": "",
        "Department": "",
        "Grade": ""
      }
    ],
    "Certifications": [
      {
        "Title": "",
        "URL": "",
        "Skills": []
      }
    ],
    "Publications": [
      {
        "Title": "",
        "URL": "",
        "Skills": []
      }
    ],
    "Achievements": [],
    "Processed Date": "",
    "RawText": "",
    "MetaData": {
      "Word Count": 0,
      "Word Frequency": {}
    }
  }

. Failure Condition
  If resume text is empty or malformed, return:
  {"error": "Invalid resume text"}

. All skills listed under "Skills → Provided" must be returned in their full, expanded form.

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
        "Word Count": len(words),
        "Word Frequency": freq
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
# CONVERT TO FINAL FORMAT (YOUR REQUIRED SHAPE)
# ──────────────────────────────────────────────

def transform_output(data: ResumeExtraction, raw_text: str) -> dict:

    d = data.model_dump()

    return {
        "Profile": {
            "Name": d["profile"]["name"],
            "Contact": d["profile"]["contact"],
            "Email": d["profile"]["email"],
            "Linkedin": d["profile"]["linkedin"],
            "Github": d["profile"]["github"],
            "Leetcode": d["profile"]["leetcode"],
            "HackerRank": d["profile"]["hackerrank"],
            "Location": d["profile"]["location"],
        },
        "Domain": d["domain"],
        "Confidence": d["confidence"],
        "Skills": {
            "Provided": d["skills"]["provided"],
            "Inferred": d["skills"]["inferred"],
        },
        "Experience": {
            "Total Full-Time Experience": d["experience"]["total_full_time_experience"],
            "Total Internship Experience in months": d["experience"]["total_internship_experience_in_months"],
            "Details": d["experience"]["details"],
        },
        "Projects": d["projects"],
        "Educations": d["educations"],
        "Certifications": d["certifications"],
        "Publications": d["publications"],
        "Achievements": d["achievements"],
        "Processed Date": date.today().isoformat(),
        "RawText": raw_text,
        "MetaData": compute_metadata(raw_text),
    }


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
    asyncio.run(run_pipeline())
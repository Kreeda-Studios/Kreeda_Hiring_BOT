import asyncio
import json
import os
import sys
from pathlib import Path
from typing import List, Optional

import fitz
from dotenv import load_dotenv
from openai import AsyncOpenAI
from pydantic import BaseModel

# ──────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────

# Resolve the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.resolve()

# Go up one directory to read the project's .env file
load_dotenv(dotenv_path=SCRIPT_DIR.parent / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
MODEL_NAME = "gpt-5-mini"

INPUT_DIR = SCRIPT_DIR / "input_jds"
OUTPUT_DIR = SCRIPT_DIR / "output_json"

INPUT_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

client = AsyncOpenAI(api_key=OPENAI_API_KEY)


# ──────────────────────────────────────────────
# PYDANTIC SCHEMA FOR STRUCTURED OUTPUT
# ──────────────────────────────────────────────

class JobProfile(BaseModel):
    role: Optional[str]
    domain: Optional[str]
    location: Optional[str]
    work_mode: Optional[str]
    job_type: Optional[str]
    notice_period: Optional[str]


class ExperienceRequirements(BaseModel):
    minimum_experience_months: int
    maximum_experience_months: int


class Skills(BaseModel):
    required: List[str]
    preferred: List[str]
    soft_skills: List[str]


class TechStack(BaseModel):
    languages: List[str]
    frameworks: List[str]
    libraries: List[str]
    databases: List[str]
    cloud: List[str]
    tools: List[str]
    ai_techniques: List[str]


class EducationRequirements(BaseModel):
    degrees: List[str]
    fields: List[str]


class JDExtraction(BaseModel):
    job_profile: JobProfile
    experience_requirements: ExperienceRequirements
    skills: Skills
    tech_stack: TechStack
    responsibilities: List[str]
    education_requirements: EducationRequirements
    certifications: List[str]


# ──────────────────────────────────────────────
# SYSTEM PROMPT
# ──────────────────────────────────────────────

SYSTEM_PROMPT = """You are a strict Job Description (JD) intelligence extraction engine.

Your task is to extract structured information from raw JD text and return ONLY valid JSON that follows the exact schema provided.

You MUST follow these rules carefully:

. Missing Data Rules
  - If a string field is missing from the JD, return `null`. NEVER return an empty string `""`.
  - If a list/array is missing, return `[]`.
  - If experience months are not mentioned, return -1.

. EXTRACT ONLY (Must be pulled directly from the JD text exactly as written)
  - job_profile.role, job_profile.location, job_profile.work_mode, job_profile.job_type, job_profile.notice_period.
  - experience_requirements: MUST be converted to integer MONTHS (e.g., 2 years = 24 months). If there is no max limit, set maximum_experience_months to -1.
  - responsibilities: Extract the core day-to-day responsibilities.
  - skills.required & skills.preferred: Extract exactly as stated in the JD.
  - education_requirements: Extract specific degrees and fields.
  - certifications: Extract explicit certifications mentioned.

. CLASSIFY AND INFER (Use LLM reasoning based on JD content)
  - job_profile.domain: You MUST choose exactly one domain from: Full stack, AIML, UI/UX, QA.
  - skills.soft_skills: Infer required soft skills from context (e.g. "Leadership", "Communication", "Problem Solving").
  - tech_stack: Categorize ALL mentioned technical tools into their correct buckets (languages, frameworks, libraries, databases, cloud, tools, ai_techniques).
  - NOTE: Do not invent/hallucinate technologies that are NOT explicitly mentioned anywhere in the JD. Just categorize the ones that ARE present.

. Schema Enforcement
  - Output ONLY valid JSON matching the exact schema.
  - Do not reorder, add, or rename any keys.

"""


# ──────────────────────────────────────────────
# PDF EXTRACTION
# ──────────────────────────────────────────────

def extract_pdf_content(pdf_path: str) -> str:
    """Extract raw text from a JD PDF file."""
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text.strip()


# ──────────────────────────────────────────────
# LLM CALL (STRUCTURED OUTPUT)
# ──────────────────────────────────────────────

async def extract_jd_data(raw_text: str) -> JDExtraction:
    user_input = f"""
    Extract structured job description information.

    RAW TEXT:
    {raw_text}
    """

    response = await client.responses.parse(
        model=MODEL_NAME,
        input=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_input},
        ],
        text_format=JDExtraction,
    )

    return response.output_parsed


# ──────────────────────────────────────────────
# PROCESS SINGLE JD
# ──────────────────────────────────────────────

async def process_single_jd(pdf_path: Path):
    print(f"[PROCESSING] {pdf_path.name}")

    raw_text = extract_pdf_content(str(pdf_path))

    if not raw_text:
        print(f"[ERROR] Invalid or empty text in {pdf_path.name}")
        return

    try:
        structured = await extract_jd_data(raw_text)
        result = structured.model_dump()
        
        output_file = OUTPUT_DIR / f"{pdf_path.stem}.json"

        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        print(f"[DONE] {pdf_path.name}")
    except Exception as e:
        print(f"[ERROR] Failed to process {pdf_path.name}: {e}")


# ──────────────────────────────────────────────
# PIPELINE EXECUTION
# ──────────────────────────────────────────────

async def run_pipeline():
    pdf_files = list(INPUT_DIR.glob("*.pdf"))

    if not pdf_files:
        print(f"No PDF files found in {INPUT_DIR.absolute()}.")
        sys.exit(1)

    print(f"[START] Found {len(pdf_files)} JDs to process.\n")
    await asyncio.gather(*[process_single_jd(pdf) for pdf in pdf_files])
    print("\n[COMPLETE] Extracted JSONs saved to output_json/")


if __name__ == "__main__":
    if sys.platform.startswith("win"):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_pipeline())

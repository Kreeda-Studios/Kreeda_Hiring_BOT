# Kreeda Hiring BOT — Complete AI System Documentation

> **Audience:** AI/ML developers onboarding to this project.
> **Scope:** Conceptual + code-level explanation of every AI component. No frontend, no REST API routes, no database schema.
> **Last Updated:** June 2026

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [AI Technology Stack](#2-ai-technology-stack)
3. [High-Level AI Pipeline Architecture](#3-high-level-ai-pipeline-architecture)
4. [OpenAI Client Module](#4-openai-client-module-scriptsopenaiclientpy)
5. [JD Processing Pipeline](#5-jd-processing-pipeline)
   - 5.1 [PDF Text Extractor (JD)](#51-jd-text-extractor--a_pdf_text_extractorpy)
   - 5.2 [AI JD Parser](#52-ai-jd-parser--b_ai_jd_parserpy)
   - 5.3 [JD Embedding Generator](#53-jd-embedding-generator--c_ai_embedding_generatorpy)
   - 5.4 [Compliance Parser (Deprecated)](#54-compliance-parser-deprecated--d_compliance_parserpy)
   - 5.5 [Main JD Processor (Orchestrator)](#55-main-jd-processor--main_jd_processorpy)
6. [Resume Processing Pipeline](#6-resume-processing-pipeline)
   - 6.1 [PDF Text Extractor (Resume)](#61-resume-pdf-extractor--a_pdf_extractorpy)
   - 6.2 [AI Resume Parser](#62-ai-resume-parser--b_ai_parserpy)
   - 6.3 [Resume Embedding Generator](#63-resume-embedding-generator--c_embedding_generatorpy)
   - 6.4 [Hard Requirements Checker](#64-hard-requirements-checker--d_hard_requirements_checkerpy)
   - 6.5 [Keyword Scorer](#65-keyword-scorer--e_keyword_scorerpy)
   - 6.6 [Semantic Scorer](#66-semantic-scorer--f_semantic_scorerpy)
   - 6.7 [Project Scorer](#67-project-scorer--g_project_scorerpy)
   - 6.8 [Composite Scorer](#68-composite-scorer--h_composite_scorerpy)
   - 6.9 [Main Resume Processor (Orchestrator)](#69-main-resume-processor--main_resume_processorpy)
7. [Final Ranking Pipeline](#7-final-ranking-pipeline)
   - 7.1 [Main Ranking Processor](#71-main-ranking-processor--main_ranking_processorpy)
8. [BullMQ Consumer (Queue Architecture)](#8-bullmq-consumer--bullmq_consumerpy)
9. [End-to-End Data Flow](#9-end-to-end-data-flow)
10. [AI Models Reference Table](#10-ai-models-reference-table)
11. [All Pydantic Schemas (Structured Outputs)](#11-all-pydantic-schemas-structured-outputs)
12. [All Scoring Formulas — Quick Reference](#12-all-scoring-formulas--quick-reference)
13. [All LLM Prompts — Full Text](#13-all-llm-prompts--full-text)
14. [Key Design Decisions & Rationale](#14-key-design-decisions--rationale)
15. [Error Handling & Failure Modes](#15-error-handling--failure-modes)
16. [Environment Variables (AI-Relevant)](#16-environment-variables-ai-relevant)
17. [Python Dependencies (AI-Relevant)](#17-python-dependencies-ai-relevant)

---

## 1. System Overview

The **Kreeda Hiring BOT** is an AI-powered candidate ranking system for a hiring platform. When a recruiter posts a job (JD) and uploads candidate resumes, the system automatically:

1. **Processes the JD** — extracts structured data + generates vector embeddings.
2. **Processes each resume** — extracts structured data, checks hard compliance, computes 3 AI scores.
3. **Ranks candidates** — applies a composite score + optional LLM re-ranking.

All AI processing runs in Python as a **background service** that listens to **Redis BullMQ queues**. The core entry point is `scripts/bullmq_consumer.py`. It runs **three workers** listening to three separate queues:

| Queue Name | Worker | Purpose |
|---|---|---|
| `jd-processing` | `process_jd_job` | AI-parse the JD and store embeddings |
| `resume-processing` | `process_resume_job` | AI-parse each resume, score it |
| `ranking` | `process_ranking_job` | Aggregate + re-rank all candidates |

---

## 2. AI Technology Stack

| Component | Technology | Details |
|---|---|---|
| **LLM — Structured Extraction** | OpenAI `gpt-5-mini` | Parses resume and JD text into structured JSON via `client.responses.parse()` with Pydantic schema enforcement |
| **LLM — Skill Matching** | OpenAI `gpt-4o-mini` | Boolean per-skill matching in keyword scorer and hard requirements checker |
| **LLM — Re-ranking** | OpenAI `gpt-4o-mini` | Batched candidate re-ranking via function calling |
| **Embeddings** | OpenAI `text-embedding-3-small` | 1536-dimension dense vectors for semantic matching |
| **Embedding Similarity** | NumPy cosine similarity | Pure matrix math, no external library needed |
| **PDF Extraction** | PyMuPDF (`fitz`) | Text + embedded hyperlink extraction from resumes; text extraction from JD PDFs |
| **DOCX Extraction** | `python-docx` | JD documents in Word format |
| **OCR (JD only)** | `pytesseract` + `Pillow` | Fallback for image-based JD PDFs |
| **Schema Validation** | `pydantic` v2 | Enforces structured LLM output; used with `responses.parse()` |
| **Queue System** | BullMQ (Python) + Redis | Async job dispatch and tracking |
| **Embedding Cache** | `pickle` (on-disk) | Persistent SHA-256 keyed cache to avoid redundant API calls |

---

## 3. High-Level AI Pipeline Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         REDIS BULLMQ QUEUES                         │
└────────────┬───────────────────┬────────────────────────────────────┘
             │                   │
   ┌─────────▼──────┐   ┌────────▼────────────────────────────────────┐
   │  jd-processing  │   │              resume-processing              │
   │   (concurr: 1)  │   │              (concurr: 16)                  │
   └─────────┬───────┘   └────────┬────────────────────────────────────┘
             │                    │
   ┌─────────▼──────────┐  ┌──────▼─────────────────────────────────┐
   │  JD Pipeline       │  │  Resume Pipeline (per resume)           │
   │  ─────────────     │  │  ────────────────────────────────────── │
   │  a. PDF Extract    │  │  a. PDF Extract (PyMuPDF)               │
   │  b. LLM Parse      │  │  b. AI Parse (gpt-5-mini + Pydantic)    │
   │  c. Embed (6 sec.) │  │  c. Embed (text-embedding-3-small)      │
   │  d. Save to DB     │  │  d. Hard Requirements Check             │
   └─────────┬──────────┘  │     (Phase 1: Python regex)             │
             │             │     (Phase 2: gpt-4o-mini LLM)          │
             │             │  e. Keyword Score (gpt-4o-mini + Math)  │
             │             │  f. Semantic Score (cosine similarity)   │
             │             │  g. Project Score (metric_ai math)       │
             │             │  h. Composite Score (weighted avg)       │
             │             │  i. Save Scores to DB                   │
             │             └──────┬─────────────────────────────────┘
             │                    │ (all resumes complete)
             │            ┌───────▼─────────────────────────────────┐
             │            │  ranking queue (concurr: 2)             │
             │            │  ──────────────────────────────────     │
             │            │  a. Fetch batch of 30 resumes           │
             │            │  b. Recalculate composite scores         │
             │            │  c. LLM Re-ranking (gpt-4o-mini)        │
             │            │     [if enabled by HR filter]           │
             │            │  d. Update final ranks in DB             │
             └────────────┴────────────────────────────────────────┘
```

---

## 4. OpenAI Client Module (`scripts/openai_client.py`)

### Purpose
A centralized, singleton-pattern OpenAI client wrapper used by every AI module. Prevents multiple client instantiations and enforces a single API key source.

### Functions

| Function | Type | Description |
|---|---|---|
| `get_openai_client()` | Sync | Returns singleton `OpenAI` instance. Reads `OPENAI_API_KEY` from env. |
| `get_async_openai_client()` | Async | Returns singleton `AsyncOpenAI` instance. Used by parsers and embedding generators. |
| `create_chat_completion(messages, model, temperature, max_tokens, response_format)` | Sync | Generic chat completion wrapper. |
| `create_embedding(text, model)` | Sync | Single-text embedding. Returns `List[float]` (1536 dims). |
| `create_embedding_async(text, model)` | Async | Async single-text embedding. Returns `List[float]`. |
| `create_embeddings_batch(texts, model)` | Sync | Batch embedding for multiple texts. |
| `create_embeddings_batch_async(texts, model)` | Async | Async batch embedding. |
| `parse_json_response(prompt, system_prompt, model, temperature)` | Sync | Wraps `create_chat_completion` with `response_format={"type":"json_object"}`. Returns parsed `dict`. Default model: `gpt-4o-mini`, temperature: `0.0`. |

### Key Design Decisions
- **Singleton pattern**: Both `_client_instance` and `_async_client_instance` are module-level globals. Client is created once on first call and reused.
- **`parse_json_response`** is the workhorse used by the keyword scorer and hard requirements checker. It forces `json_object` format, guaranteeing parseable output.
- **`gpt-5-mini`** is used via `client.responses.parse()` (new OpenAI Responses API), not `chat.completions`. This allows direct Pydantic model enforcement.

---

## 5. JD Processing Pipeline

The JD pipeline lives in `scripts/jd-processing/`. It is orchestrated by `main_jd_processor.py`.

### 5.1 JD Text Extractor — `a_pdf_text_extractor.py`

**Purpose:** Extract raw text from a JD file. Supports multiple formats.

**Extraction Priority:**

```
.pdf  → PyMuPDF first → OCR fallback (pytesseract + Pillow) if PyMuPDF fails
.docx → python-docx
.doc  → python-docx
.txt  → plain file read (UTF-8)
```

**Key Function: `extract_combined_text(job_data, base_path)`**

This is the function called by the orchestrator. It combines two possible text sources:
1. **PDF file** — from `job_data['jd_pdf_filename']` → path: `/app/uploads/jds/{filename}`
2. **JD text field** — from `job_data['jd_text']` (inline text typed by HR)

Both are concatenated with `\n\n` separator. This means a JD can be enriched by text that HR typed manually even if a PDF was uploaded.

**Return Schema:**
```json
{
  "success": true,
  "text": "<combined raw text>",
  "sources": ["pdf", "jd_text"],
  "char_count": 1234,
  "error": null
}
```

**Important Notes:**
- For resumes, OCR is **not supported** (image-based resume PDFs are rejected).
- For JDs, OCR **is** supported as a fallback because JDs may come from scanned letterheads.
- If both PDF extraction and `jd_text` are empty → pipeline fails immediately.

---

### 5.2 AI JD Parser — `b_ai_jd_parser.py`

**Purpose:** Transform raw JD text into a structured, validated Python object using the OpenAI Responses API with enforced Pydantic schema.

**Model:** `gpt-5-mini`
**API Style:** `client.responses.parse()` (OpenAI Responses API, not `chat.completions`)

#### Pydantic Schema: `JDExtraction`

```python
class JobProfile(BaseModel):
    role: Optional[str]          # Job title e.g. "Senior Backend Engineer"
    domain: Optional[str]        # ONE OF: "Full stack", "AIML", "UI/UX", "QA"
    location: Optional[str]
    work_mode: Optional[str]     # Remote / Hybrid / On-site
    job_type: Optional[str]      # Full-time / Part-time / Contract
    notice_period: Optional[str]

class ExperienceRequirements(BaseModel):
    minimum_experience_months: int   # Always in MONTHS (e.g. 2 years = 24)
    maximum_experience_months: int   # -1 means no upper limit

class Skills(BaseModel):
    required: List[str]              # Hard technical must-haves
    preferred: List[str]             # Nice-to-have skills
    soft_skills: List[str]           # Inferred from JD context

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

class JDExtraction(BaseModel):       # TOP-LEVEL OUTPUT
    job_profile: JobProfile
    experience_requirements: ExperienceRequirements
    skills: Skills
    tech_stack: TechStack
    responsibilities: List[str]
    education_requirements: EducationRequirements
    certifications: List[str]
    mandatory_compliances: List[str]  # Hard filter criteria
    soft_compliances: List[str]       # Preferred criteria
```

#### System Prompt Behavior (Full Logic)

The system prompt instructs the LLM on exactly what to **extract** vs. what to **classify/infer**:

| Field Category | Behavior |
|---|---|
| `job_profile.role`, `location`, `work_mode`, `job_type`, `notice_period` | **Extract only** — copy verbatim from JD |
| `experience_requirements` | **Extract** — always convert to integer months |
| `skills.required`, `skills.preferred` | **Extract** — concise skill names only, no sentences |
| `responsibilities` | **Extract** — core day-to-day duties |
| `education_requirements`, `certifications` | **Extract** |
| `job_profile.domain` | **Classify** — LLM must pick ONE of: Full stack, AIML, UI/UX, QA |
| `skills.soft_skills` | **Infer** — from JD context |
| `tech_stack` | **Categorize** — everything explicitly mentioned, no hallucination |
| `mandatory_compliances` | **Extract** — explicitly MANDATORY / MUST-HAVE items only |
| `soft_compliances` | **Extract** — PREFERRED / NICE-TO-HAVE items only |

**Missing data rules:**
- String field missing → `null` (never empty string `""`)
- List field missing → `[]`
- Experience months not mentioned → `0`
- No max experience limit → `-1`

#### LLM Call

```python
response = await client.responses.parse(
    model="gpt-5-mini",
    input=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": f"RAW TEXT:\n{raw_input}"},
    ],
    text_format=JDExtraction,   # Pydantic class enforced by SDK
)
parsed = response.output_parsed  # Type: JDExtraction
return {"success": True, "parsed_data": parsed.model_dump()}
```

**Optional HR Filter Text Injection:**
If `filter_text` is provided (HR-typed mandatory requirements), it is appended to the JD text under `### HR FILTER REQUIREMENTS:` header before sending to the LLM. This allows the LLM to extract compliance data from HR's custom text.

---

### 5.3 JD Embedding Generator — `c_ai_embedding_generator.py`

**Purpose:** Generate 6 section-specific embedding matrices for the JD. These are stored in the database and later used for semantic matching against each resume.

**Model:** `text-embedding-3-small` (1536 dimensions)

#### 6 Sections — Field Mapping

The parsed JD is decomposed into 6 semantic sections. Each section becomes a **2D array** of embedding vectors (one vector per text item):

| Section | Source Fields in `JDExtraction` |
|---|---|
| `profile` | `job_profile.role` (sentence-split) + `job_profile.domain` |
| `skills` | `skills.required` + `skills.preferred` + all `tech_stack.*` buckets |
| `projects` | `tech_stack.ai_techniques` + `tech_stack.frameworks` + `tech_stack.libraries` |
| `responsibilities` | Each item in `responsibilities[]` (sentence-split) |
| `education` | `education_requirements.degrees` + `.fields` + `certifications[]` |
| `overall` | `job_profile.role` + top 20 `skills.required` + top 10 `responsibilities` (sentence-split) |

**Why 2D arrays?** Each section produces multiple embedding vectors (one per sentence/skill/item). This enables **fine-grained cosine similarity matching** — each JD sentence is matched to the best resume sentence independently. This is the foundation of the semantic scorer.

#### Sentence Splitting (`sentence_split(text)`)
Splits on `.!?` characters and keeps only segments with ≥3 words. This filters out noise like lone punctuation or very short fragments.

#### Deduplication
Within each section, items are deduplicated (case-insensitive) while preserving insertion order.

#### Output Format (stored in DB)
```json
{
  "embedding_model": "text-embedding-3-small",
  "embedding_dimension": 1536,
  "profile_embedding": [[f1, f2, ..., f1536], [f1, f2, ..., f1536]],
  "skills_embedding": [[...], [...]],
  "projects_embedding": [[...]],
  "responsibilities_embedding": [[...]],
  "education_embedding": [[...]],
  "overall_embedding": [[...]]
}
```

---

### 5.4 Compliance Parser (Deprecated) — `d_compliance_parser.py`

> ⚠️ **This file is deprecated and kept only as a no-op stub.**

Compliance requirements (mandatory and soft) were previously extracted in a separate step. They are now extracted **inline** by `b_ai_jd_parser.py` as `mandatory_compliances` and `soft_compliances` fields in the `JDExtraction` schema.

All three public functions (`validate_and_format_compliances`, `process_job_compliances`, `parse_compliance_text`) return empty stubs. No AI logic runs here.

---

### 5.5 Main JD Processor — `main_jd_processor.py`

**Purpose:** Orchestrate the complete JD processing pipeline as a single async function called by the BullMQ consumer.

**Function:** `async def process_jd_complete(job) -> dict`

**Pipeline Steps with Progress Tracking:**

```
Progress 10%  → Fetch job data from backend API
Progress 20%  → Job data loaded
Progress 25%  → Begin text extraction
Progress 35%  → Text extracted (PDF + inline JD text combined)
Progress 40%  → Begin AI JD parsing
Progress 60%  → AI parsing complete (JDExtraction saved)
Progress 65%  → Save jd_analysis to database via /updates/jd/parsed
Progress 70%  → Analysis saved
Progress 75%  → Begin embedding generation
Progress 85%  → Embeddings generated (6 section matrices)
Progress 90%  → Save embeddings via /updates/jd/embeddings
Progress 95%  → Embeddings saved
Progress 100% → JD processing complete → POST /updates/jd/status {success: true}
```

**On any failure:** calls `POST /updates/jd/status {success: false, error: ...}` to mark the JD as failed.

---

## 6. Resume Processing Pipeline

The resume pipeline lives in `scripts/resume-processing/`. It is orchestrated by `main_resume_processor.py`. Each resume is processed independently — up to 16 concurrently (BullMQ concurrency setting).

### 6.1 Resume PDF Extractor — `a_pdf_extractor.py`

**Purpose:** Extract raw text and embedded hyperlinks from a resume PDF file. **Only PDFs are supported** — no DOCX, no OCR.

**Key Design Decision (vs JD extractor):** Resumes are almost always digital PDFs (not scanned). OCR support is deliberately excluded for resumes to keep the pipeline fast and avoid false positives from poor OCR. Image-based PDFs return `success: false` immediately.

**Detection of Image-Based PDFs:**
```python
if total_chars < 50:
    return {'success': False, 'error': 'PDF appears to be image-based. OCR not supported.'}
```

**`extract_pdf_text(pdf_path)`:**
Uses `fitz.open()` (PyMuPDF). For each page:
- Calls `page.get_text()` to get raw text.
- Calls `page.get_links()` to collect embedded `uri` hyperlinks (e.g., GitHub, LinkedIn URLs).

**`clean_resume_text(text)`:**
Post-processing applied to raw extracted text:
- Max 2 consecutive newlines (collapses blank lines)
- Max 1 consecutive space (collapses whitespace)
- Tabs converted to spaces
- Null bytes and non-printable characters removed
- Section headers normalized: `EXPERIENCE`, `EDUCATION`, `SKILLS`, `PROJECTS`, `CERTIFICATIONS`, `CONTACT`

**Return Schema:**
```json
{
  "success": true,
  "text": "<cleaned resume text>",
  "hyperlinks": ["https://github.com/user", "https://linkedin.com/in/user"],
  "metadata": {
    "file_size": 123456,
    "pages": 2,
    "characters": 3847,
    "processing_time": 0.12
  }
}
```

---

### 6.2 AI Resume Parser — `b_ai_parser.py`

**Purpose:** Transform raw resume text into a rich, structured Pydantic object using the OpenAI Responses API with strict schema enforcement.

**Model:** `gpt-5-mini`
**API Style:** `client.responses.parse()` (same as JD parser)

#### Pydantic Schema: `ResumeExtraction`

```python
class MetricAI(BaseModel):
    impact: float           # 0.0 to 1.0 — business/technical impact
    difficulty: int         # 1 to 10 — how hard to build
    complexity: int         # 1 to 10 — architectural complexity
    domain_relevance: int   # 1 to 10 — relevance to candidate's declared domain

class Project(BaseModel):
    title: Optional[str]
    demo_link: Optional[str]
    code_link: Optional[str]
    metric_ai: MetricAI     # Generated by LLM (not extracted — explicitly allowed)

class ExperienceDetail(BaseModel):
    role: Optional[str]
    company: Optional[str]
    employment_type: Optional[str]  # "Full Time" | "Part Time" | "Intern" | "Intern above 6 months" | "Contractual"
    location: Optional[str]
    start: Optional[str]
    end: Optional[str]
    duration_in_months: Optional[int]
    impact: List[str]       # Bullet points of achievements in this role

class Experience(BaseModel):
    date_calculation_scratchpad: str  # LLM's reasoning trace for date math
    total_full_time_experience: int   # In MONTHS
    total_internship_experience_in_months: int
    details: List[ExperienceDetail]

class Skills(BaseModel):
    provided: List[str]    # Explicit skills from the resume (expanded form)
    inferred: List[str]    # Inferred from projects/experience (must be in resume)
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

class ResumeExtraction(BaseModel):    # TOP-LEVEL OUTPUT
    profile: Profile
    domain: str               # ONE OF: "Full stack", "AIML", "UI/UX", "QA"
    confidence: float         # 0.0 to 1.0 — domain classification confidence
    skills: Skills
    experience: Experience
    projects: List[Project]
    educations: List[Education]
    certifications: List[str]
    achievements: List[str]
```

#### System Prompt — Strict Extraction Rules (Summarized)

The system prompt is very long and precise. Key behavioral rules:

**What LLM is ALLOWED to generate (not just extract):**
- `domain` — must be one of 4 allowed values
- `confidence` — float 0-1
- `skills.inferred` — inferred from context, but must be traceable to resume content
- `projects[].metric_ai` — LLM scores each project on 4 metrics

**Experience Calculation Logic:**
The LLM must use a `date_calculation_scratchpad` to show its work before computing totals. The rule is **inclusive month counting**:
> "May 2023 to June 2024" = (2024-2023)×12 + (6-5) + 1 = **14 months**

If "Present" appears: use today's date (injected as `date.today().isoformat()` in the prompt).
Overlapping periods are de-duplicated — only distinct chronological months count.

**Skills Expansion Rule:**
All skills in `skills.provided` must be in **full expanded form**:
- `CNN` → `Convolutional Neural Network`
- `NLP` → `Natural Language Processing`

**Hyperlink Usage:**
Embedded hyperlinks from the PDF (extracted by `a_pdf_extractor.py`) are passed separately as JSON. The LLM uses them to populate `profile.linkedin`, `profile.github`, `project.demo_link`, `project.code_link`, etc.

**Null/Empty Rules:**
- Missing string → `null` (never `""`)
- Missing list → `[]`
- No hallucinated URLs, grades, skills, or experience

#### LLM Call

```python
user_input = f"""Extract structured resume information.

RAW TEXT:
{resume_text}

HYPERLINKS:
{json.dumps(links)}
"""

response = await client.responses.parse(
    model="gpt-5-mini",
    input=[
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_input},
    ],
    text_format=ResumeExtraction,
)
parsed = response.output_parsed
return {"success": True, "parsed_data": parsed.model_dump()}
```

**Note:** The `jd_data` parameter is accepted for API compatibility but **is not used** in parsing. JD context is deliberately excluded from parsing to keep it a pure resume extraction.

---

### 6.3 Resume Embedding Generator — `c_embedding_generator.py`

**Purpose:** Generate 6 section-specific embedding matrices for each parsed resume. Mirrors the JD embedding structure for direct cosine comparison.

**Model:** `text-embedding-3-small` (1536 dimensions)
**Batch Size:** 128 texts per API call
**Retry Logic:** Up to 5 attempts with exponential backoff (base 1.4) + jitter

#### Persistent Embedding Cache

```python
class EmbedCache:
    # Stored at: scripts/resume-processing/.semantic_embed_cache.pkl
    # Key: SHA-256 of f"{MODEL_NAME}||{text}"
    # Value: normalized embedding vector as list of floats
```

The cache persists across runs. Every 100 new entries, it auto-saves. On close, it saves all remaining entries. This dramatically reduces API costs when the same skill/sentence appears across multiple resumes.

#### 6 Sections — Field Mapping (Resume)

| Section | Source Fields in `ResumeExtraction` |
|---|---|
| `profile` | `profile.name` + `domain` + `profile.location` |
| `skills` | `skills.provided` + `skills.inferred` (all as individual items) |
| `projects` | Each `project.title` (sentence-split) + all `achievements[]` |
| `responsibilities` | Role titles + `impact` bullets across all `experience.details[]` (sentence-split) |
| `education` | `degree + department + college` per education entry + `certifications[]` |
| `overall` | `name` + `domain` + top 20 `skills.provided` + top 3 experience entries' top 3 impact bullets |

**All sections are capped at 200 items** (`MAX_SENT = 200`) to prevent runaway large resumes.

#### Normalization
All embedding vectors are L2-normalized (unit norm). The full section matrix is also row-normalized:
```python
M /= np.linalg.norm(M, axis=1, keepdims=True).clip(min=1e-9)
```
This is critical because the semantic scorer uses raw dot product as cosine similarity (valid only when vectors are unit norm).

#### Return Schema
```json
{
  "success": true,
  "section_embeddings": {
    "profile": "<numpy 2D array N×1536>",
    "skills": "<numpy 2D array N×1536>",
    "projects": "<numpy 2D array N×1536>",
    "responsibilities": "<numpy 2D array N×1536>",
    "education": "<numpy 2D array N×1536>",
    "overall": "<numpy 2D array N×1536>"
  },
  "section_texts": { ... },
  "model_used": "text-embedding-3-small",
  "dimension": 1536
}
```

Before saving to DB, the numpy arrays are converted to 2D Python lists via `.tolist()`.

---

### 6.4 Hard Requirements Checker — `d_hard_requirements_checker.py`

**Purpose:** Gate-keep candidates before scoring. A candidate that fails hard requirements gets **score = 0** and is excluded from ranking.

**Data Priority:**
1. `jd_data["filter_requirements"]["mandatory_compliances"]["raw_prompt"]` — HR-typed text (PRIMARY)
2. `jd_data["jd_analysis"]["mandatory_compliances"]` — AI-extracted list from JD (FALLBACK if HR text empty)
3. If both empty → everyone passes immediately.

**Two-Phase Architecture:**

#### Phase 1 — Experience Check (Pure Python, deterministic, no LLM)

Regex patterns extract experience range from HR text. Six patterns are tried in order:

```python
# Pattern 1: "X months to Y year(s)"
r'(\d+)\s*months?\s+to\s+(\d+)\s*years?'

# Pattern 2: "X year(s) to Y year(s)"
r'(\d+)\s*years?\s+to\s+(\d+)\s*years?'

# Pattern 3: "X months to Y months"
r'(\d+)\s*months?\s+to\s+(\d+)\s*months?'

# Pattern 4: "X to Y months"
r'(\d+)\s+to\s+(\d+)\s*months?'

# Pattern 5: "X to Y years"
r'(\d+)\s+to\s+(\d+)\s*years?'
```

Text classification detects experience type:
- "internship experience" → `exp_type = "internship"`
- "full time experience" → `exp_type = "full_time"`
- Otherwise → `exp_type = "total"`

**Check Logic:**
```python
if exp_type == "internship":
    if ft_months > 0:
        REJECT # Strictly internship role but candidate has FT experience
    value_to_check = intern_months

elif exp_type == "full_time":
    value_to_check = ft_months

else:  # total
    value_to_check = ft_months + intern_months

# Then: value_to_check must be >= min_months AND <= max_months
```

If experience check **fails** → hard reject immediately, no LLM call.

#### Phase 2 — Skill Check (LLM, runs only if Phase 1 passes)

After stripping the experience clause from HR text, remaining comma-separated items are treated as required skill keywords.

**Example:**
```
"Total experience: 2 months to 1 year, RAG, GenAI"
→ skill_keywords = ["RAG", "GenAI"]
```

The LLM is asked to check each skill using **two matching rules**:

**Rule 1 — Synonym/Abbreviation Match:**
The resume contains the exact label OR any well-known synonym.
- `"GenAI"` matches `"Generative AI"`, `"Gen AI"`
- `"RAG"` matches `"Retrieval-Augmented Generation"`
- `"ML"` matches `"Machine Learning"`

**Rule 2 — Compound Phrase Containment (bidirectional):**
- (a) Resume skill phrase CONTAINS required term: `"Manual and Automation Testing"` covers requirement `"Manual Testing"` ✓
- (b) Required compound has all components individually present: required `"Manual and Automation Testing"`, resume has separate `"Manual Testing"` AND `"Automation Testing"` ✓

**What does NOT count:** Tool/framework inference. `"LangChain"` alone does NOT prove `"GenAI"`.

**LLM receives only a flat skill list**, not the full resume JSON:
- `skills.provided`, `skills.inferred`
- `project` titles (top 15)
- `experience.details[].impact` bullets (capped at 15)

**Expected LLM JSON output:**
```json
{
  "skills_check": [
    {"required": "GenAI", "found": true, "evidence": "Generative AI"},
    {"required": "RAG",   "found": false, "evidence": null}
  ],
  "all_present": false
}
```

#### Fallback Path — JD Analysis Compliances (LLM, qualitative)

When HR has not typed any filter text, falls back to `jd_analysis.mandatory_compliances` (the AI-extracted compliance list from the JD parser). Sends a **compact resume summary** (not full JSON) to keep prompt size manageable:

```python
resume_summary = {
    "domain": ...,
    "total_full_time_experience_months": ...,
    "total_internship_experience_months": ...,
    "skills_provided": [...],
    "skills_inferred": [...],
    "project_titles": [...],
    "certifications": [...],
    "education_degrees": [...]
}
```

#### Return Schema
```json
{
  "success": true,
  "meets_all_requirements": true,
  "compliance_score": 1.0,
  "requirements_met": ["Total experience: 8 months is within range (6 - 12 months)", "GenAI: found (Generative AI)"],
  "requirements_missing": [],
  "filter_reason": null,
  "error": null
}
```

---

### 6.5 Keyword Scorer — `e_keyword_scorer.py`

**Purpose:** Measure how many of the JD's required/preferred skills the candidate has. Uses a hybrid LLM + math approach.

**Architecture:**
```
┌─────────────────────────────────────────────────────────┐
│  LLM (gpt-4o-mini, temperature=0)                       │
│  Job: ONLY semantic matching — boolean YES/NO per skill  │
│  Handles: "ReactJS"="React", "ML"="Machine Learning"    │
│  Output: per-skill matched: true/false lists             │
└────────────────────────┬────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────┐
│  Python (pure math, always deterministic)               │
│  Job: compute score from boolean match counts           │
│  Applies discrete bins + fixed bonuses                  │
│  Output: overall_score float                            │
└─────────────────────────────────────────────────────────┘
```

#### Input Sources

From `jd_data` (the parsed JD stored in DB):
- `jd_data["jd_analysis"]["skills"]["required"]` — list of required skill strings
- `jd_data["jd_analysis"]["skills"]["preferred"]` — list of preferred skill strings
- `jd_data["filter_requirements"]["soft_compliances"]["raw_prompt"]` — HR-typed soft preference text

**Fallback:** If `skills.required` is empty but `tech_stack` exists, flatten all tech_stack items as `required_skills` to prevent everyone getting a perfect score.

#### LLM Call

System prompt instructs the LLM that its **only job is matching**, not scoring:

```
Synonym rules (non-exhaustive — apply broadly):
  • ReactJS  ↔  React
  • Node     ↔  Node.js  ↔  NodeJS
  • JS       ↔  JavaScript
  • TS       ↔  TypeScript
  • Postgres ↔  PostgreSQL
  • ML       ↔  Machine Learning
  • k8s      ↔  Kubernetes
  • AWS S3, EC2, Lambda etc. all match "AWS"
```

User prompt passes the **full resume JSON** (not a summary), plus the skill lists and soft compliance text.

**Expected LLM JSON output:**
```json
{
  "required_skill_matches": [
    {"skill": "Python", "matched": true, "matched_as": "Python"},
    {"skill": "Kubernetes", "matched": false, "matched_as": null}
  ],
  "preferred_skill_matches": [
    {"skill": "Go", "matched": false, "matched_as": null}
  ],
  "soft_compliance_met": false,
  "reasoning": "Candidate has strong Python/React but missing Kubernetes and DevOps tools"
}
```

#### Score Computation (Pure Python)

```python
# 1. Required skills match percentage
req_pct = req_matched / req_total  # if req_total == 0 → req_pct = 1.0

# 2. Discrete base score bins
if req_pct < 0.30:   base_score = 0.0
elif req_pct < 0.50: base_score = 0.3
elif req_pct <= 0.85: base_score = 0.7
else:                base_score = 1.0

# 3. Preferred bonus: +0.1 if ≥50% preferred matched
pref_pct = matched_preferred / (matched_preferred + missing_preferred)
preferred_bonus = 0.1 if (has_preferred and pref_pct >= 0.5) else 0.0

# 4. Soft compliance bonus: +0.05 if criteria met
soft_bonus = 0.05 if (has_soft and soft_met) else 0.0

# 5. Final, capped at 1.0
overall_score = min(1.0, base_score + preferred_bonus + soft_bonus)
```

**Key Design Decision:** The bins are intentional. `< 30%` match = score 0, not a low number. This creates a strong signal for candidates who match almost nothing.

---

### 6.6 Semantic Scorer — `f_semantic_scorer.py`

**Purpose:** Measure the semantic alignment between resume content and JD content using pre-computed embedding vectors and cosine similarity.

**No LLM call in this module.** Pure matrix math.

#### Section Weights

```python
SECTION_WEIGHTS = {
    "skills":           0.30,  # Highest weight — skills are most important
    "projects":         0.25,
    "responsibilities": 0.20,
    "profile":          0.10,
    "overall":          0.10,
    "education":        0.05,  # Lowest — education is least discriminating
}
```

#### Per-Section Score Algorithm (`compute_section_score`)

Given:
- `jd_emb`: JD section embedding matrix — shape `(M, 1536)` — M JD sentences
- `resume_emb`: Resume section embedding matrix — shape `(N, 1536)` — N resume sentences

```python
# Cosine similarity matrix (both matrices are pre-normalized to unit norm)
C = np.matmul(jd_emb, resume_emb.T)  # shape: (M, N)

# Coverage: fraction of JD sentences with strong match (>= TAU_COV = 0.65)
max_j = C.max(axis=1)   # best match score for each JD sentence
coverage = (max_j >= 0.65).sum() / len(max_j)

# Depth: average best-match similarity across all JD sentences
depth = max_j.mean()

# Density: fraction of resume sentences being "used" (>= TAU_RESUME = 0.55)
max_r = C.max(axis=0)   # best match score for each resume sentence
density = (max_r >= 0.55).sum() / len(max_r)

# Combined section score
section_score = 0.5 * coverage + 0.4 * depth + 0.1 * density
```

**Interpretation of three sub-metrics:**
- **Coverage (weight 0.5):** "Does the resume cover what the JD is asking for?" — JD-centric.
- **Depth (weight 0.4):** "How well does the resume match even the hard parts?" — Continuous quality signal.
- **Density (weight 0.1):** "How much of the resume is relevant to the JD?" — Resume-centric utilization.

**Empty section handling:**
- JD section empty → return `0.5` (neutral, not penalized — JD may not have an education requirement)
- Resume section empty → return `0.0` (candidate is missing something)

#### Overall Semantic Score

```python
overall_score = sum(section_scores[section] * SECTION_WEIGHTS[section]
                    for section in SECTION_WEIGHTS)
```

#### JD Embedding Format (MongoDB → NumPy)

JD embeddings are stored as 2D lists in MongoDB. The scorer retrieves them and converts:
```python
jd_key = f'{section}_embedding'  # e.g., "skills_embedding"
jd_section_embeddings[section] = np.array(emb_data, dtype=np.float32)
```

Validation ensures the array is 2D (`ndim == 2`). If it's 1D, a `ValueError` is raised.

---

### 6.7 Project Scorer — `g_project_scorer.py`

**Purpose:** Score a candidate's project portfolio quality using the `metric_ai` ratings generated by the AI resume parser.

**No API call.** Pure math on fields already computed by `b_ai_parser.py`.

#### Metric Weights

```python
METRIC_WEIGHTS = {
    "impact":           0.40,  # Business/technical impact (already 0-1)
    "difficulty":       0.20,  # Normalised: raw_score / 10
    "complexity":       0.20,  # Normalised: raw_score / 10
    "domain_relevance": 0.20,  # Normalised: raw_score / 10
}
```

#### Per-Project Score

```python
def calculate_weighted_score(metric_ai: dict) -> float:
    raw = {
        "impact":           float(metric_ai["impact"]),          # already 0-1
        "difficulty":       float(metric_ai["difficulty"]) / 10, # 1-10 → 0-1
        "complexity":       float(metric_ai["complexity"]) / 10,
        "domain_relevance": float(metric_ai["domain_relevance"]) / 10,
    }
    return sum(raw[m] * w for m, w in METRIC_WEIGHTS.items())
    # total_weight = 1.0, so no division needed but code uses it for safety
```

#### Aggregate Score

Simple average across all projects:
```python
overall_score = sum(project_scores) / len(project_scores)
```

**Design note:** Averaging (not max) means a candidate with 3 mediocre projects scores lower than one with 3 excellent projects, even if both have one great project.

---

### 6.8 Composite Scorer — `h_composite_scorer.py`

**Purpose:** Combine the 3 component scores into a single final score.

#### Weights

```python
WEIGHTS = {
    "project_aggregate": 0.35,  # From g_project_scorer
    "Semantic_Score":    0.35,  # From f_semantic_scorer
    "Keyword_Score":     0.30,  # From e_keyword_scorer
}
```

#### Scoring Logic

```python
# Only include scores that are numeric (including 0.0)
valid_scores = {k: v for k, v in raw_scores.items() if isinstance(v, (int, float)) and v is not None}

# Decay if only 1 score is available
ONE_SCORE_DECAY = 0.08
decay = 0.08 if len(valid_scores) == 1 else 0.0

# Weighted average (re-normalizes weights if some scores are missing)
total_weight = sum(WEIGHTS[k] for k in valid_scores)
final = sum((WEIGHTS[k] / total_weight) * valid_scores[k] for k in valid_scores)

# Apply decay and clamp to [0, 1]
final = max(0.0, min(1.0, final - decay))
```

**Design notes:**
- If all 3 scores present: straightforward weighted average (weights sum to 1.0).
- If only 2 scores: weights are proportionally re-normalized.
- If only 1 score: 0.08 decay penalty applied to discourage relying on a single signal.
- Score 0.0 is treated as valid (not missing). A candidate can genuinely score 0.

---

### 6.9 Main Resume Processor — `main_resume_processor.py`

**Purpose:** Orchestrate the complete resume processing pipeline as a single async function.

**Function:** `async def process_resume_pipeline(job) -> dict`

#### Pipeline Steps with Progress Tracking

```
Progress 5%   → Fetch resume data from DB (resume_id, filename)
Progress 8%   → File located at /app/uploads/{job_id}/resumes/{filename}
Progress 10%  → Fetch JD data from DB (needed for hard requirements + scoring)
Progress 12%  → Starting pipeline
Progress 15%  → Begin PDF text extraction
Progress 20%  → Text extracted ({N} chars)
Progress 25%  → Begin AI parsing (gpt-5-mini)
Progress 40%  → AI parsing complete → POST /updates/resume/parsed
Progress 45%  → Begin embedding generation
Progress 55%  → Embeddings generated → POST /updates/resume/embeddings
Progress 60%  → Begin scoring
Progress 65%  → Hard requirements checked
```

**Hard Requirements Gate:**
```
If hard_requirements NOT met:
  → POST /updates/resume/scores {all scores = 0.0}
  → POST /updates/resume/status/single {success: true, hard_requirements_met: false}
  → Return immediately (skip keyword, semantic, project, composite scoring)
```

```
Progress 70%  → Project scoring complete
Progress 75%  → Keyword scoring complete
Progress 80%  → Semantic scoring complete
Progress 85%  → Composite scoring complete
Progress 90%  → Final score computed
Progress 95%  → POST /updates/resume/scores {all 4 scores}
Progress 100% → POST /updates/resume/status/single {success: true, hard_requirements_met: true}
```

#### File Path Convention
```python
resume_file_path = f"/app/uploads/{job_id}/resumes/{filename}"
# Fallback if no job_id:
resume_file_path = f"/app/uploads/resumes/{filename}"
```

#### Saved Score Payload
```json
{
  "resume_id": "<id>",
  "scores": {
    "hard_requirements": {
      "meets_all_requirements": true,
      "compliance_score": 1.0,
      "requirements_met": ["..."],
      "requirements_missing": [],
      "filter_reason": null
    },
    "project_score": 0.612,
    "keyword_score": 0.700,
    "semantic_score": 0.543,
    "composite_score": 0.621
  }
}
```

---

## 7. Final Ranking Pipeline

### 7.1 Main Ranking Processor — `main_ranking_processor.py`

**Purpose:** After all resumes for a job are processed, re-normalize scores and apply optional LLM re-ranking in batches.

**Trigger:** Automatically triggered by the `process-resume-group` parent job in the BullMQ flow, after all child resume jobs complete. The backend API endpoint `POST /process/ranking/{job_id}` is called.

**Batch Size:** 30 resumes per batch (`RE_RANK_BATCH_SIZE = 30`)
**Model:** `gpt-4o-mini` (for re-ranking, via function calling)

#### Main Entry Point: `process_final_ranking(...)`

This is a synchronous function (run in a thread pool executor from the async BullMQ handler).

#### `process_ranking_batch(job_id, resume_ids, ...)`

**Step 1: Fetch Resume Batch**
```
POST /api/updates/resumes/batch {resume_ids: [...]}
```
Returns array of resume documents including `scores` and `parsed_content`.

**Step 2: Score Recalculation**
For each resume:
- Fetch `keyword_score`, `semantic_score`, `project_score` from stored scores.
- Currently: scores are used as-is (no min-max normalization applied — commented out).
- Re-run composite scorer to ensure consistent final scores.

```python
composite_result = calculate_composite_score(
    project_score_result={'overall_score': project_score},
    keyword_score_result={'overall_score': normalized_keyword},
    semantic_score_result={'overall_semantic_score': normalized_semantic}
)
```

**Step 3: Update Scores in DB**
```
POST /api/updates/resume/scores/batch {updates: [{resume_id, scores}, ...]}
```

**Step 4: Ranking**

Two modes:

**Mode A — Basic (default):** Sort by `Final_Score` descending. No LLM needed.

**Mode B — LLM Re-ranking** (if `ranking_criteria.enable_llm_rerank == true`):

#### LLM Re-ranking Logic (`llm_re_rank_batch`)

Uses **OpenAI function calling** (not `responses.parse`) with this function schema:
```json
{
  "name": "re_rank_candidates",
  "parameters": {
    "ranked_candidates": [
      {
        "candidate_id": "string",
        "re_rank_score": 0.0,          // 0-1
        "meets_requirements": false,
        "requirements_met": [],
        "requirements_missing": []
      }
    ]
  }
}
```

The LLM receives:
- The `filter_requirements` object (HR's structured requirements)
- A list of candidate summaries with abbreviated field names to minimize tokens:

```python
summary = {
    "id": candidate_id,
    "n": name,                        # name (reference only)
    "sc": {
        "p": project_aggregate,        # project score
        "k": Keyword_Score,
        "s": Semantic_Score,
        "f": Final_Score
    },
    "exp": years_experience,
    "loc": location,
    "role": role_claim,
    "sk": skills[:10],               # top 10 skills
    "pj": [{
        "n": project_name[:50],
        "tech": top5_tech_keywords,
        "score": domain_relevance
    }],
    "compliance": { ... }            # programmatic compliance check result
}
```

**LLM tasks:**
1. **Validate** programmatic compliance results (correct LLM-resistant errors).
2. **Re-rank** candidates balancing requirements compliance + all score signals.

**Strict field filter:** The LLM is constrained to only return requirement types explicitly in `specified_fields`. Any extra requirement types in the response are filtered out.

**JSON error handling:** The function has a fallback JSON repair — if `function_call.arguments` has an odd number of quotes (unterminated string), it attempts to close the last string.

---

## 8. BullMQ Consumer — `bullmq_consumer.py`

**Purpose:** Main entry point for the Python AI service. A long-running async process that starts three BullMQ workers and routes jobs to their respective pipelines.

### Workers

| Worker | Queue | Concurrency | Handler |
|---|---|---|---|
| JD Worker | `jd-processing` | 1 | `process_jd_job` |
| Resume Worker | `resume-processing` | 16 | `process_resume_job` |
| Ranking Worker | `ranking` | 2 | `process_ranking_job` |

### Resume Job Flow (Parent-Child)

Resumes are processed using a BullMQ **Flow** (parent-child pattern):

```
process-resume-group (parent)
├── process-resume (child: resume 1)
├── process-resume (child: resume 2)
├── process-resume (child: resume 3)
└── ...
```

- **Children** run with concurrency 16 — up to 16 resumes process simultaneously.
- **Parent** runs **only after all children complete** — this is BullMQ's built-in flow guarantee.
- When parent runs: calls `POST /updates/resume/status {job_id, success: true}`, then auto-triggers ranking via `POST /process/ranking/{job_id}`.

### Retry & Timeout Policy

**Each child resume job:**
- `RESUME_CHILD_TIMEOUT_SEC = 1200` (20 minutes) — guarded by `asyncio.wait_for()`.
- On timeout or failure: if NOT final attempt → raise exception (BullMQ will retry).
- On final attempt failure: mark resume as failed in DB, return `success: true` to BullMQ (so parent is not blocked).

**Key invariant:** Parent flow is never permanently stuck. Even if individual resumes fail, the parent eventually completes and triggers ranking.

### Graceful Shutdown

Signal handlers for `SIGTERM` and `SIGINT` set a `shutdown_event`. The main loop awaits this event, then calls `worker.close()` for all three workers.

---

## 9. End-to-End Data Flow

### JD Processing Flow

```
HR uploads JD PDF + types filter requirements
           │
           ▼
Backend → enqueues job to "jd-processing" BullMQ queue
           │
           ▼
bullmq_consumer.py → process_jd_job()
           │
           ▼
main_jd_processor.py → process_jd_complete(job)
    │
    ├─ GET /updates/job/{job_id}  → job_data (jd_pdf_filename, jd_text, filter_text)
    │
    ├─ a_pdf_text_extractor.py → extract_combined_text(job_data)
    │     → raw_text (PDF + inline text combined)
    │
    ├─ b_ai_jd_parser.py → process_jd_with_ai(raw_text)
    │     LLM: gpt-5-mini + Pydantic → JDExtraction dict
    │
    ├─ POST /updates/jd/parsed { jd_analysis: {...} }
    │
    ├─ c_ai_embedding_generator.py → generate_and_format_embeddings(parsed_jd)
    │     OpenAI: text-embedding-3-small
    │     → 6 section 2D embedding arrays
    │
    ├─ POST /updates/jd/embeddings { jd_embedding: {...} }
    │
    └─ POST /updates/jd/status { success: true }
```

### Resume Processing Flow (single resume)

```
HR triggers resume processing for a job
           │
           ▼
Backend → enqueues Flow: parent + N child jobs to "resume-processing" queue
           │
           ▼ (for each child)
bullmq_consumer.py → process_resume_job()
           │
           ▼
main_resume_processor.py → process_resume_pipeline(job)
    │
    ├─ GET /updates/resume/{resume_id}   → resume metadata (filename)
    ├─ GET /updates/job/{job_id}          → jd_data (for scoring)
    │
    ├─ a_pdf_extractor.py → process_resume_file(pdf_path)
    │     → cleaned_text + hyperlinks
    │
    ├─ b_ai_parser.py → parse_resume_with_ai(text, hyperlinks)
    │     LLM: gpt-5-mini + Pydantic → ResumeExtraction dict
    │
    ├─ POST /updates/resume/parsed { parsed_content: {...} }
    │
    ├─ c_embedding_generator.py → generate_resume_embeddings(parsed_resume)
    │     OpenAI: text-embedding-3-small (with pickle cache)
    │     → 6 section 2D numpy arrays
    │
    ├─ POST /updates/resume/embeddings { resume_embedding: {...} }
    │
    ├─ d_hard_requirements_checker.py → check_hard_requirements(parsed_resume, jd_data)
    │     Phase 1: Python regex (experience range check)
    │     Phase 2: LLM gpt-4o-mini (skill label/synonym check)
    │
    │     IF NOT met:
    │     ├─ POST /updates/resume/scores { all scores = 0.0 }
    │     └─ POST /updates/resume/status/single { success: true, hard_requirements_met: false }
    │         [STOP — skip remaining scoring]
    │
    ├─ e_keyword_scorer.py → calculate_keyword_scores(parsed_resume, jd_data)
    │     LLM: gpt-4o-mini (boolean matching)
    │     Math: discrete bins → keyword_score (0-1.05, capped at 1.0)
    │
    ├─ f_semantic_scorer.py → calculate_semantic_scores(resume_embeddings, jd_embeddings)
    │     Math: cosine similarity matrices → section_scores → weighted sum
    │
    ├─ g_project_scorer.py → calculate_project_scores(parsed_resume, jd_data)
    │     Math: metric_ai weighted average → project_score
    │
    ├─ h_composite_scorer.py → calculate_composite_score(project, keyword, semantic)
    │     Math: weighted average (0.35/0.35/0.30) → final_score
    │
    ├─ POST /updates/resume/scores { 4 scores + hard_requirements result }
    └─ POST /updates/resume/status/single { success: true, hard_requirements_met: true }
```

### Post-Resume → Ranking Flow

```
All child resume jobs complete
           │
           ▼
Parent job (process-resume-group) runs
    ├─ POST /updates/resume/status { job_id, success: true }  → marks job as resume_processing_completed
    └─ POST /process/ranking/{job_id}                          → backend enqueues ranking batches
           │
           ▼
"ranking" BullMQ queue → N batch jobs (each ≤30 resumes)
           │
           ▼ (for each batch)
bullmq_consumer.py → process_ranking_job()
    │
    ├─ process_final_ranking() [sync, in thread pool]
    │
    └─ process_ranking_batch()
          ├─ POST /updates/resumes/batch { resume_ids } → fetch batch resume data
          ├─ Re-calculate composite scores
          ├─ POST /updates/resume/scores/batch { updated scores }
          ├─ [IF LLM rerank enabled] → llm_re_rank_candidates() → gpt-4o-mini
          └─ Return ranked_candidates list

All batch jobs complete
    └─ Parent ranking job runs → POST /updates/ranking/status { success: true }
```

---

## 10. AI Models Reference Table

| Module | Model | Call Style | Temperature | Purpose |
|---|---|---|---|---|
| `b_ai_parser.py` | `gpt-5-mini` | `client.responses.parse()` | Default | Resume structured extraction |
| `b_ai_jd_parser.py` | `gpt-5-mini` | `client.responses.parse()` | Default | JD structured extraction |
| `d_hard_requirements_checker.py` (Phase 2) | `gpt-4o-mini` | `parse_json_response()` | `0.0` | Skill label/synonym matching |
| `d_hard_requirements_checker.py` (Fallback) | `gpt-4o-mini` | `parse_json_response()` | `0.0` | Qualitative compliance check |
| `e_keyword_scorer.py` | `gpt-4o-mini` | `parse_json_response()` | `0.0` | Per-skill boolean matching |
| `main_ranking_processor.py` | `gpt-4o-mini` | `chat.completions.create()` with function calling | Default | LLM re-ranking |
| `c_embedding_generator.py` | `text-embedding-3-small` | `client.embeddings.create()` | N/A | Resume embeddings (1536-dim) |
| `c_ai_embedding_generator.py` | `text-embedding-3-small` | `create_embedding_async()` | N/A | JD embeddings (1536-dim) |

---

## 11. All Pydantic Schemas (Structured Outputs)

### `ResumeExtraction` (b_ai_parser.py)

```python
ResumeExtraction
├── profile: Profile
│   ├── name: Optional[str]
│   ├── contact: Optional[str]
│   ├── email: Optional[str]
│   ├── linkedin: Optional[str]
│   ├── github: Optional[str]
│   ├── leetcode: Optional[str]
│   ├── hackerrank: Optional[str]
│   └── location: Optional[str]
├── domain: str                         # "Full stack" | "AIML" | "UI/UX" | "QA"
├── confidence: float                   # 0.0–1.0
├── skills: Skills
│   ├── provided: List[str]             # Explicit, expanded form
│   ├── inferred: List[str]             # Inferred from context, in resume
│   └── soft_skills: List[str]
├── experience: Experience
│   ├── date_calculation_scratchpad: str
│   ├── total_full_time_experience: int         # months
│   ├── total_internship_experience_in_months: int
│   └── details: List[ExperienceDetail]
│       ├── role: Optional[str]
│       ├── company: Optional[str]
│       ├── employment_type: Optional[str]      # strict enum
│       ├── location: Optional[str]
│       ├── start: Optional[str]
│       ├── end: Optional[str]
│       ├── duration_in_months: Optional[int]
│       └── impact: List[str]
├── projects: List[Project]
│   ├── title: Optional[str]
│   ├── demo_link: Optional[str]
│   ├── code_link: Optional[str]
│   └── metric_ai: MetricAI
│       ├── impact: float               # 0.0–1.0
│       ├── difficulty: int             # 1–10
│       ├── complexity: int             # 1–10
│       └── domain_relevance: int       # 1–10
├── educations: List[Education]
│   ├── start/end/college/degree/department/grade
├── certifications: List[str]
└── achievements: List[str]
```

### `JDExtraction` (b_ai_jd_parser.py)

```python
JDExtraction
├── job_profile: JobProfile
│   ├── role: Optional[str]
│   ├── domain: Optional[str]           # "Full stack" | "AIML" | "UI/UX" | "QA"
│   ├── location: Optional[str]
│   ├── work_mode: Optional[str]
│   ├── job_type: Optional[str]
│   └── notice_period: Optional[str]
├── experience_requirements: ExperienceRequirements
│   ├── minimum_experience_months: int
│   └── maximum_experience_months: int   # -1 = no upper limit
├── skills: Skills
│   ├── required: List[str]
│   ├── preferred: List[str]
│   └── soft_skills: List[str]
├── tech_stack: TechStack
│   ├── languages / frameworks / libraries / databases / cloud / tools / ai_techniques
├── responsibilities: List[str]
├── education_requirements: EducationRequirements
│   ├── degrees: List[str]
│   └── fields: List[str]
├── certifications: List[str]
├── mandatory_compliances: List[str]
└── soft_compliances: List[str]
```

---

## 12. All Scoring Formulas — Quick Reference

### Keyword Score (`e_keyword_scorer.py`)

```
req_pct = matched_required / total_required

base_score:
  req_pct < 0.30  → 0.0
  req_pct < 0.50  → 0.3
  req_pct ≤ 0.85  → 0.7
  req_pct > 0.85  → 1.0

preferred_bonus = 0.1  if (has_preferred AND matched_preferred/total_preferred >= 0.5) else 0.0
soft_bonus      = 0.05 if (has_soft AND soft_compliance_met) else 0.0

keyword_score = min(1.0, base_score + preferred_bonus + soft_bonus)
```

### Semantic Score (`f_semantic_scorer.py`)

Per section:
```
C = jd_emb @ resume_emb.T          (cosine similarity matrix, both pre-normalized)
coverage = count(C.max(axis=1) >= 0.65) / num_jd_sentences
depth    = mean(C.max(axis=1))
density  = count(C.max(axis=0) >= 0.55) / num_resume_sentences
section_score = 0.5*coverage + 0.4*depth + 0.1*density
```

Overall:
```
semantic_score = 0.30*skills + 0.25*projects + 0.20*responsibilities
              + 0.10*profile + 0.10*overall + 0.05*education
```

### Project Score (`g_project_scorer.py`)

Per project:
```
project_score = 0.40*impact + 0.20*(difficulty/10) + 0.20*(complexity/10) + 0.20*(domain_relevance/10)
```

Aggregate:
```
project_aggregate = mean(project_scores for all projects)
```

### Composite Score (`h_composite_scorer.py`)

```
final_score = (0.35*project_aggregate + 0.35*semantic_score + 0.30*keyword_score)
              / (sum of available score weights)
              - decay (0.08 if only 1 score available, else 0.0)
final_score = clamp(final_score, 0.0, 1.0)
```

---

## 13. All LLM Prompts — Full Text

### 13.1 Resume Parser System Prompt (`b_ai_parser.py`)

> You are a strict resume intelligence extraction engine.
>
> Your task is to extract structured information from raw resume text and return ONLY valid JSON that follows the exact schema provided.
>
> You are not a conversational assistant. You are a deterministic structured extraction system.
>
> **General Rules:**
> - Output ONLY valid JSON. No markdown. No comments. No explanations. No extra keys.
> - Do not reorder schema. Do not remove keys.
> - If a field is not present in resume → return null or empty array.
> - Never hallucinate links, experience, grades, or skills.
>
> **Allowed Generated Fields:** domain, confidence, skills.inferred, projects[].metric_ai — everything else MUST be extracted.
>
> **Domain Rules:** Choose exactly one: Full stack / AIML / UI/UX / QA. Provide confidence 0–1.
>
> **Experience Rules:**
> - Use `date_calculation_scratchpad` to show work before computing totals.
> - INCLUSIVE month counting: "May 2023 to June 2024" = 14 months.
> - Convert all durations to months. "Present" = today's date (injected dynamically).
> - Do not double-count overlapping periods.
> - Employment_type must be one of: Full Time, Part Time, Intern, Intern above 6 months, Contractual.
>
> **Skills Rules:**
> - provided: Explicit hard/technical skills from resume. Full expanded form (CNN → Convolutional Neural Network).
> - inferred: From Experience/Projects/Certifications, must be traceable to resume.
> - soft_skills: Extracted separately.
>
> **Projects Rules:**
> - Extract title, demo_link (if present), code_link (if present).
> - Generate metric_ai: impact (0-1), difficulty (1-10), complexity (1-10), domain_relevance (1-10).
> - Reflect technical depth honestly. Do not inflate.
>
> **Hyperlink Rules:**
> - Use embedded PDF hyperlinks to populate linkedin, github, leetcode, hackerrank, demo_link, code_link.
> - Do not fabricate URLs.
>
> **Null/Empty Rules:**
> - Missing string → null (NEVER "").
> - Missing array → [].
> - Achievements: only awards, honors, competitive ranks, publications, scholarships. No URLs, no project bullets.
>
> **Failure:** If text empty/malformed → {"error": "Invalid resume text"}

---

### 13.2 JD Parser System Prompt (`b_ai_jd_parser.py`)

> You are a strict Job Description (JD) intelligence extraction engine.
>
> **Missing Data Rules:** string → null, list → [], experience months unknown → 0.
>
> **EXTRACT ONLY:** role, location, work_mode, job_type, notice_period; experience_requirements (integer months); responsibilities; skills.required/preferred (concise names only); education_requirements; certifications.
>
> **CLASSIFY AND INFER:** domain (Full stack/AIML/UI/UX/QA); skills.soft_skills (from context); tech_stack (categorize what IS mentioned, no hallucination).
>
> **Compliance Extraction:**
> - mandatory_compliances: Explicitly MANDATORY / MUST-HAVE criteria. Concise, actionable strings.
> - soft_compliances: PREFERRED / NICE-TO-HAVE criteria.
> - Return [] if none mentioned.
>
> **Schema Enforcement:** Output ONLY valid JSON matching exact schema. No reordering, no extra keys.

---

### 13.3 Hard Requirements Skill Checker System Prompt (`d_hard_requirements_checker.py`)

> You are a strict skill label matcher. Your ONLY task is to check whether each required skill is present in the candidate's resume data.
>
> **RULE 1 — SYNONYM / ABBREVIATION MATCH:**
> A required skill is FOUND if the resume contains the exact label OR any well-known synonym or abbreviation.
> Examples: 'GenAI' matches 'Generative AI', 'Gen AI'; 'RAG' matches 'Retrieval-Augmented Generation'; 'ML' matches 'Machine Learning'; 'NLP' matches 'Natural Language Processing'; 'CV' matches 'Computer Vision'; 'QA' matches 'Quality Assurance'.
>
> **RULE 2 — COMPOUND PHRASE CONTAINMENT (bidirectional):**
> A required skill is FOUND if:
> (a) Any resume skill phrase CONTAINS the required term as a component: required='Manual Testing', resume has='Manual and Automation Testing' → FOUND.
> (b) The required term is a compound whose ALL components are individually present: required='Manual and Automation Testing', resume has 'Manual Testing' AND 'Automation Testing' separately → FOUND.
>
> **STRICT BOUNDARY:** Tool/framework inference does NOT count. 'LangChain' alone does NOT prove 'GenAI'. Only direct label, synonym, or compound containment match counts.
>
> Return ONLY: {"skills_check": [{"required": "...", "found": true/false, "evidence": "...or null"}], "all_present": true/false}

---

### 13.4 JD Compliance Qualitative Check System Prompt (Fallback, `d_hard_requirements_checker.py`)

> You are an HR compliance screener. Evaluate whether the candidate meets all the mandatory requirements listed.
> Use synonym and abbreviation matching for skill terms.
> For experience requirements: use the numeric month fields provided — do not re-estimate or infer experience independently.
>
> Return ONLY: {"meets_all_requirements": bool, "compliance_score": 0.0-1.0, "requirements_met": [...], "requirements_missing": [...], "filter_reason": "one-line reason if rejected, or null if passed"}

---

### 13.5 Keyword Scorer System Prompt (`e_keyword_scorer.py`)

> You are a strict technical resume evaluator.
>
> YOUR ONLY JOB IS SEMANTIC SKILL MATCHING — determine which skills from the provided lists are present in the candidate's resume. Use semantic understanding to recognise synonyms, abbreviations, and variant spellings as equivalent matches.
>
> Synonym rules (non-exhaustive — apply broadly):
> • ReactJS ↔ React • Node ↔ Node.js ↔ NodeJS • JS ↔ JavaScript • TS ↔ TypeScript • Postgres ↔ PostgreSQL • ML ↔ Machine Learning • DL ↔ Deep Learning • NLP ↔ Natural Language Processing • CV ↔ Computer Vision • k8s ↔ Kubernetes • AWS S3, EC2, Lambda etc. all match "AWS"
>
> DO NOT output a score. Output ONLY the JSON schema below.
> For each skill, return: "matched": true/false, "matched_as": exact resume text or null.

---

### 13.6 LLM Re-ranking System Prompt (`main_ranking_processor.py`)

> You are a candidate re-ranker and compliance validator. Your tasks:
> 1. VALIDATE compliance results: Review programmatic compliance checks and validate/correct them based on candidate resume data.
> 2. RE-RANK candidates: Rank candidates based on validated compliance + all ranking scores.
>
> IMPORTANT CONSTRAINT: Only return requirement types from this list: {specified_fields_str}. Do NOT return other requirement types unless explicitly listed.
>
> Validation Rules: Correct nuanced errors; relax overly strict checks; consider context.
>
> Re-ranking Rules: Requirements compliance → higher rank. Balance with JD alignment scores. Use candidate_id (not name) for identification.
>
> Consider all scores (sc.p=project, sc.k=keyword, sc.s=semantic, sc.f=final).

---

## 14. Key Design Decisions & Rationale

### 14.1 `gpt-5-mini` + `client.responses.parse()` for Extraction

The parsers (resume + JD) use the **OpenAI Responses API** with Pydantic schema enforcement instead of the classic `chat.completions` API. This means:
- The SDK enforces the exact schema at the API level — no manual JSON parsing or `try/except json.loads`.
- Invalid or malformed LLM output causes an SDK exception, not a silent bad parse.
- `response.output_parsed` gives a typed Python object directly.

### 14.2 `gpt-4o-mini` + `parse_json_response()` for Matching/Scoring

The keyword scorer and hard requirements checker use `gpt-4o-mini` via `chat.completions` with `response_format={"type":"json_object"}`. This is cheaper and faster for simpler tasks that don't need the full Pydantic enforcement of the Responses API.

### 14.3 Two-Phase Hard Requirements Checker

Experience is checked deterministically in Python (not via LLM) because LLMs frequently make arithmetic errors with months/years. The LLM is only brought in for skill label matching, which is a semantic task it excels at.

### 14.4 Keyword Scorer — Discrete Bins Instead of Continuous Score

The discrete bins (`0.0`, `0.3`, `0.7`, `1.0`) are intentional. They prevent the LLM from "micromanaging" scores (e.g., 31% match ≠ 30% match for hiring purposes). The bins create clear tiers: unqualified / partial / qualified / excellent.

### 14.5 Semantic Scorer — 3-Metric Section Score

Coverage, depth, and density capture different aspects:
- A candidate who has exactly the right skills but nothing else → high coverage, low density.
- A candidate with a broad resume that partially covers the JD → medium coverage, high density.
- The formula `0.5*coverage + 0.4*depth + 0.1*density` prioritizes JD coverage over resume breadth.

### 14.6 Embedding Cache for Resumes

Resume text tends to repeat the same skills and common phrases across candidates. The SHA-256 + pickle cache eliminates redundant API calls for identical text strings, significantly reducing cost in high-volume scenarios.

### 14.7 BullMQ Parent-Child Flow for Resumes

The parent-child flow ensures:
1. All resumes process concurrently (not serially).
2. Ranking is triggered **only** after every resume is done — no race conditions.
3. A single failed resume does not block ranking for others (final-attempt error containment).

### 14.8 `d_compliance_parser.py` Stub (Deprecated)

This file is intentionally preserved as a no-op stub rather than deleted. Any legacy import from older code will not crash — it will just silently return empty compliance structures. This is a safety net for backward compatibility.

---

## 15. Error Handling & Failure Modes

| Scenario | Handling |
|---|---|
| PDF is image-based (resume) | `a_pdf_extractor.py` returns `success: false`. Pipeline marks resume as failed. |
| AI parsing fails (LLM error) | `b_ai_parser.py` / `b_ai_jd_parser.py` returns `success: false`. Pipeline marks failed. |
| Embedding API fails (all 5 retries) | `c_embedding_generator.py` raises `RuntimeError`. Resume is marked failed. |
| Embedding API fails (JD) | Section gets empty `[]` embedding — semantic scoring returns 0.0 for that section (not a crash). |
| Hard requirements check fails (exception) | Exception caught → `meets_all_requirements: False`, score 0.0 — safe default. |
| Keyword scorer LLM fails | Exception caught → `success: false, overall_score: 0.0`. Composite scorer handles missing component. |
| Semantic scorer fails (bad array shape) | `ValueError` raised with descriptive message. Returns `success: false`. |
| Composite scorer has only 1 valid score | 0.08 decay applied. Score still returned. |
| Resume processing times out (>20 min) | BullMQ timeout: mark failed in DB, return `success: true` to unblock parent. |
| Resume processing fails on final retry | Mark failed in DB, return `success: true` to unblock parent. |
| LLM re-ranking JSON malformed | Attempts basic quote-repair; if unsuccessful, returns empty result (falls back to score-based ranking). |
| Backend API unreachable | `APIError` exception → pipeline fails the job and retries via BullMQ. |

---

## 16. Environment Variables (AI-Relevant)

| Variable | Used By | Description |
|---|---|---|
| `OPENAI_API_KEY` | `openai_client.py`, `main_ranking_processor.py` | OpenAI API key. Required for all LLM and embedding calls. |
| `REDIS_HOST` | `bullmq_consumer.py` | Redis server host (default: `localhost`) |
| `REDIS_PORT` | `bullmq_consumer.py` | Redis port (default: `6379`) |
| `REDIS_PASSWORD` | `bullmq_consumer.py` | Redis auth password (default: `password123`) |
| `RESUME_CHILD_TIMEOUT_SEC` | `bullmq_consumer.py` | Per-resume timeout in seconds (default: `1200` = 20 min) |
| `BACKEND_API_URL` | `main_ranking_processor.py` | Backend API base URL (default: `http://localhost:3001/api`) |
| `BACKEND_API_KEY` | `main_ranking_processor.py` | Optional bearer token for backend API auth |

---

## 17. Python Dependencies (AI-Relevant)

From `scripts/requirements.txt`:

| Package | Version | AI Purpose |
|---|---|---|
| `openai` | ≥1.0.0 | LLM calls (gpt-5-mini, gpt-4o-mini) + embeddings (text-embedding-3-small). Uses both `responses.parse()` API and `chat.completions`. |
| `numpy` | ≥1.24.0 | Embedding matrix operations — cosine similarity, normalization, stacking. Core of semantic scorer. |
| `pydantic` | (transitive via openai) | Schema enforcement for structured LLM outputs. `BaseModel`, `model_dump()`. |
| `pymupdf` | ≥1.23.0 | PDF text extraction for resumes AND JDs. Also extracts embedded hyperlinks. |
| `python-docx` | ≥0.8.11 | DOCX extraction for JDs. |
| `bullmq` | ≥1.0.0 | BullMQ Python worker — consumes Redis queue jobs. |
| `redis` | ≥4.5.0 | Redis client used by BullMQ. |
| `requests` | ≥2.28.0 | HTTP calls to backend API from ranking processor. |
| `scikit-learn` | ≥1.2.0 | Listed as dependency; not directly used in current scoring logic (may be legacy). |
| `beautifulsoup4` | ≥4.11.0 | Listed; not used in current AI pipeline (possibly legacy). |
| `fuzzywuzzy` | ≥0.18.0 | Listed; not used in current AI pipeline (possibly legacy). |
| `python-dotenv` | ≥1.0.0 | Loads `.env` file into environment variables. |

> [!NOTE]
> `pytesseract` and `Pillow` are used by `a_pdf_text_extractor.py` for OCR but are listed as optional (imported inside a try/except). They are NOT in `requirements.txt` — install separately if JD OCR is needed.

---

*End of AI System Documentation — Kreeda Hiring BOT*

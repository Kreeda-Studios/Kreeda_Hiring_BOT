# Python Scripts Documentation - Kreeda Hiring Bot

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [BullMQ Consumer](#bullmq-consumer)
- [JD Processing Pipeline](#jd-processing-pipeline)
- [Resume Processing Pipeline](#resume-processing-pipeline)
- [Final Ranking Pipeline](#final-ranking-pipeline)
- [Common Utilities](#common-utilities)
- [AI Integration](#ai-integration)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [Development Guide](#development-guide)

---

## 🎯 Overview

The Python scripts component is the **AI/ML processing engine** of Kreeda Hiring Bot. It consumes jobs from BullMQ queues and performs:
- Job Description (JD) parsing and analysis
- Resume extraction, parsing, and scoring
- Final candidate re-ranking using LLM

### Key Technologies
- **Runtime**: Python 3.11+
- **Queue**: BullMQ Python 1.0+ (async/await)
- **AI**: OpenAI SDK (GPT-4o-mini, text-embedding-3-small)
- **PDF Processing**: PyMuPDF (fitz), python-docx
- **ML**: scikit-learn, numpy
- **HTTP**: requests (Backend API client)

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│              BullMQ Consumer (bullmq_consumer.py)            │
│                    Async Worker Pool                         │
├──────────────────────────────────────────────────────────────┤
│  Queue Listeners:                                            │
│  ├─ jd-processing        → JD Pipeline                      │
│  ├─ resume-processing    → Resume Pipeline                  │
│  └─ final-ranking        → Ranking Pipeline                 │
└──────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌─────────────┐      ┌─────────────┐       ┌─────────────┐
│     JD      │      │   Resume    │       │   Final     │
│ Processing  │      │ Processing  │       │  Ranking    │
└─────────────┘      └─────────────┘       └─────────────┘
        │                     │                     │
        ├─ PDF Text Extract   ├─ PDF Text Extract  ├─ Fetch Scores
        ├─ AI Parsing (GPT)   ├─ AI Parsing (GPT)  ├─ LLM Re-rank
        ├─ Compliance Parse   ├─ Generate Embed    ├─ Update Rankings
        ├─ Generate Embed     ├─ Hard Requirements │
        └─ Save to Backend    ├─ Keyword Score     └─ Save to Backend
                              ├─ Semantic Score
                              ├─ Project Score
                              ├─ Composite Score
                              └─ Save to Backend
```

### Data Flow

```
Backend Enqueues Job
        ↓
Python Worker Receives Job
        ↓
Execute Pipeline (JD/Resume/Ranking)
        ↓
Call OpenAI API (Parsing/Embeddings/Re-ranking)
        ↓
Process Results
        ↓
Save to Backend via API
        ↓
Update Job Progress (BullMQ)
        ↓
Complete/Fail Job
```

---

## 📁 Directory Structure

```
scripts/
├── bullmq_consumer.py          # Main worker (async BullMQ consumer)
├── openai_client.py            # OpenAI client singleton
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Production container
├── Dockerfile.dev              # Development container
│
├── common/                     # Shared utilities
│   ├── api_client.py          # Backend REST API client
│   ├── job_logger.py          # Structured logging utility
│   └── bullmq_progress.py     # BullMQ progress tracker
│
├── jd-processing/              # Job Description Processing
│   ├── main_jd_processor.py                # Orchestrator (entry point)
│   ├── a_pdf_text_extractor.py             # Extract text from PDF/JD
│   ├── b_ai_jd_parser.py                   # AI parsing (GPT-4o-mini)
│   ├── c_ai_embedding_generator.py         # Generate JD embeddings
│   └── d_compliance_parser.py              # Parse filter requirements
│
├── resume-processing/          # Resume Processing Pipeline
│   ├── main_resume_processor.py            # Orchestrator (entry point)
│   ├── a_pdf_extractor.py                  # Extract text from PDF
│   ├── b_ai_parser.py                      # AI parsing (GPT)
│   ├── c_embedding_generator.py            # Generate resume embeddings
│   ├── d_hard_requirements_checker.py      # Compliance validation
│   ├── e_keyword_scorer.py                 # Keyword matching score
│   ├── f_semantic_scorer.py                # Semantic similarity score
│   ├── g_project_scorer.py                 # Project relevance score
│   └── h_composite_scorer.py               # Weighted composite score
│
└── final-ranking/              # Final Ranking Pipeline
    └── main_ranking_processor.py           # LLM-based re-ranking (GPT-4o-mini)
```

---

## 🔄 BullMQ Consumer

### Main Worker ([scripts/bullmq_consumer.py](scripts/bullmq_consumer.py))

**Entry Point:** Async BullMQ consumer that listens to 3 queues

**Key Features:**
- Async/await architecture for concurrency
- Separate workers per queue
- Progress tracking via BullMQ
- Error handling with retries
- Graceful shutdown on SIGTERM/SIGINT

**Implementation:**
```python
#!/usr/bin/env python3
import asyncio
import os
from bullmq import Worker, Queue

from main_jd_processor import process_jd_complete
from main_resume_processor import process_resume_pipeline
from main_ranking_processor import process_final_ranking

class KreedaJobProcessor:
    def __init__(self):
        redis_config = {
            "host": os.getenv('REDIS_HOST', 'localhost'),
            "port": int(os.getenv('REDIS_PORT', 6379)),
            "password": os.getenv('REDIS_PASSWORD', 'password123')
        }
        self.redis_config = redis_config
        self.workers = []
    
    async def process_jd_job(self, job, job_token):
        """Process JD processing job"""
        logger.info(f"🔍 Processing JD job {job.id}")
        result = await process_jd_complete(job)
        
        if result.get('success'):
            logger.info(f"✅ JD job {job.id} completed")
            return result
        else:
            raise Exception(f"JD processing failed: {result.get('error')}")
    
    async def process_resume_job(self, job, job_token):
        """Process resume processing job"""
        logger.info(f"📄 Processing resume job {job.id}")
        result = await process_resume_pipeline(job)
        
        if result.get('success'):
            logger.info(f"✅ Resume job {job.id} completed")
            return result
        else:
            raise Exception(f"Resume processing failed: {result.get('error')}")
    
    async def process_ranking_job(self, job, job_token):
        """Process final ranking job"""
        logger.info(f"🏆 Processing ranking job {job.id}")
        result = await process_final_ranking(job)
        
        if result.get('success'):
            logger.info(f"✅ Ranking job {job.id} completed")
            return result
        else:
            raise Exception(f"Ranking failed: {result.get('error')}")
    
    async def start(self):
        """Start all workers"""
        # JD Processing Worker
        jd_worker = Worker(
            'jd-processing',
            self.process_jd_job,
            {"connection": self.redis_config, "concurrency": 2}
        )
        self.workers.append(jd_worker)
        
        # Resume Processing Worker
        resume_worker = Worker(
            'resume-processing',
            self.process_resume_job,
            {"connection": self.redis_config, "concurrency": 5}  # Higher concurrency
        )
        self.workers.append(resume_worker)
        
        # Final Ranking Worker
        ranking_worker = Worker(
            'final-ranking',
            self.process_ranking_job,
            {"connection": self.redis_config, "concurrency": 1}
        )
        self.workers.append(ranking_worker)
        
        logger.info("✅ All workers started")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Gracefully stop all workers"""
        for worker in self.workers:
            await worker.close()
        logger.info("✅ All workers stopped")

# Main entry point
async def main():
    processor = KreedaJobProcessor()
    
    # Handle shutdown signals
    import signal
    def handle_shutdown(sig, frame):
        asyncio.create_task(processor.stop())
    
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)
    
    await processor.start()

if __name__ == "__main__":
    asyncio.run(main())
```

**Concurrency Settings:**
- **JD Processing**: 2 concurrent jobs (AI-heavy)
- **Resume Processing**: 5 concurrent jobs (batch processing)
- **Final Ranking**: 1 concurrent job (sequential processing)

---

## 📋 JD Processing Pipeline

### Overview
Processes job descriptions through 5 stages:
1. **Text Extraction**: PDF → text
2. **AI Parsing**: GPT-4o-mini → structured JD
3. **Compliance Parsing**: Validate filter requirements
4. **Embedding Generation**: Create vector embeddings
5. **Save to Backend**: Store results in MongoDB

---

### Stage 1: PDF Text Extraction

**Module:** [a_pdf_text_extractor.py](scripts/jd-processing/a_pdf_text_extractor.py)

**Purpose:** Extract text from JD PDF or combine JD text fields

**Function:**
```python
def extract_combined_text(job_data: dict) -> dict:
    """
    Extract and combine text from JD sources
    
    Sources (priority order):
    1. jd_file (PDF uploaded)
    2. jd_text (pasted text)
    3. description (fallback)
    
    Returns:
        {
            'success': bool,
            'text': str,
            'char_count': int,
            'sources': list[str],
            'error': str | None
        }
    """
```

**Implementation:**
```python
import fitz  # PyMuPDF

def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF using PyMuPDF"""
    doc = fitz.open(pdf_path)
    text = ""
    
    for page in doc:
        text += page.get_text()
    
    doc.close()
    return text.strip()

def extract_combined_text(job_data: dict) -> dict:
    sources = []
    combined_text = ""
    
    # Try PDF file first
    if job_data.get('jd_file'):
        pdf_path = f"./uploads/{job_data['_id']}/{job_data['jd_file']}"
        if os.path.exists(pdf_path):
            pdf_text = extract_text_from_pdf(pdf_path)
            if pdf_text:
                combined_text += pdf_text + "\n\n"
                sources.append("jd_file")
    
    # Add jd_text if present
    if job_data.get('jd_text'):
        combined_text += job_data['jd_text'] + "\n\n"
        sources.append("jd_text")
    
    # Fallback to description
    if not combined_text and job_data.get('description'):
        combined_text = job_data['description']
        sources.append("description")
    
    if not combined_text:
        return {'success': False, 'error': 'No JD text found'}
    
    return {
        'success': True,
        'text': combined_text.strip(),
        'char_count': len(combined_text),
        'sources': sources
    }
```

---

### Stage 2: AI Parsing (GPT-4o-mini)

**Module:** [b_ai_jd_parser.py](scripts/jd-processing/b_ai_jd_parser.py)

**Purpose:** Parse raw JD text into structured JSON using OpenAI function calling

**Schema Highlights:**
- **50+ fields**: role_title, required_skills, years_experience_required, etc.
- **Skill normalization**: ML → Machine Learning, RAG → Retrieval Augmented Generation
- **Weighting system**: Dynamic weights per scoring dimension
- **HR insights**: Recommendations + inferred requirements (hr_points)
- **Explainability**: Provenance spans, key phrases, rationales

**Function:**
```python
def process_jd_with_ai(jd_text: str) -> dict:
    """
    Parse JD text with AI
    
    Returns:
        {
            'success': bool,
            'parsed_data': dict,  # Full JD analysis
            'error': str | None
        }
    """
```

**OpenAI Function Call:**
```python
PARSE_FUNCTION = {
    "name": "parse_jd_detailed",
    "description": "Return detailed Job Description JSON",
    "parameters": {
        "type": "object",
        "properties": {
            "role_title": {"type": "string"},
            "required_skills": {"type": "array", "items": {"type": "string"}},
            "years_experience_required": {"type": "number"},
            "canonical_skills": {
                "type": "object",
                "properties": {
                    "programming": {"type": "array"},
                    "frameworks": {"type": "array"},
                    "ml_ai": {"type": "array"},
                    "databases": {"type": "array"},
                    "cloud": {"type": "array"}
                }
            },
            "weighting": {
                "type": "object",
                "properties": {
                    "required_skills": {"type": "number"},
                    "responsibilities": {"type": "number"},
                    "domain_relevance": {"type": "number"}
                }
            },
            "hr_notes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "type": {"type": "string"},  # recommendation | inferred_requirement
                        "note": {"type": "string"},
                        "impact": {"type": "number"}
                    }
                }
            }
            # ... 40+ more fields
        }
    }
}
```

**System Prompt:**
```
Parse JD into structured JSON. Return EXACTLY ONE function call.

SKILL NORMALIZATION (CRITICAL):
• Use canonical forms: 'ML'→'Machine Learning', 'RAG'→'Retrieval Augmented Generation'
• Normalize all skills for consistent matching
• Add missing domain-relevant skills if JD is incomplete

REQUIREMENTS:
1. Extract ALL information (explicit + implicit)
2. Build keywords_flat (deduped) and keywords_weighted (token→0-1)
3. Set weighting: required_skills > responsibilities > domain_relevance
4. Add HR notes for recommendations (type: 'recommendation' or 'inferred_requirement')
5. Set hr_points = len(hr_notes)
```

---

### Stage 3: Compliance Parsing

**Module:** [d_compliance_parser.py](scripts/jd-processing/d_compliance_parser.py)

**Purpose:** Validate and structure filter requirements (mandatory vs. soft)

**Function:**
```python
def validate_and_format_compliances(job_data: dict) -> dict:
    """
    Parse filter_requirements into structured compliance rules
    
    Input:
        job_data['filter_requirements'] = {
            'mandatory_compliances': {
                'raw_prompt': '5+ years React, Bachelor degree required'
            },
            'soft_compliances': {
                'raw_prompt': 'Prefer AWS experience'
            }
        }
    
    Output:
        {
            'filter_requirements': {
                'mandatory_compliances': {
                    'structured': {
                        'experience': {'min': 5, 'field': 'React'},
                        'education': {'minimum': 'Bachelors'},
                        'hard_skills': ['React']
                    }
                },
                'soft_compliances': {
                    'structured': {
                        'preferred_skills': ['AWS']
                    }
                }
            }
        }
    """
```

**AI Call (GPT-4o-mini):**
- Parses raw compliance prompts into structured rules
- Used in resume processing for hard requirements checking

---

### Stage 4: Embedding Generation

**Module:** [c_ai_embedding_generator.py](scripts/jd-processing/c_ai_embedding_generator.py)

**Purpose:** Generate vector embeddings for semantic matching

**Sections Embedded:**
1. `skills_embed`: Concatenated required + preferred skills
2. `responsibilities_embed`: Concatenated responsibilities
3. `overall_embed`: Full JD text (truncated to 8000 chars)

**Function:**
```python
def generate_and_format_embeddings(parsed_jd: dict) -> dict:
    """
    Generate OpenAI embeddings for JD sections
    
    Returns:
        {
            'jd_embedding': {
                'model': 'text-embedding-3-small',
                'dimension': 1536,
                'skills_embed': '<base64-encoded-vector>',
                'responsibilities_embed': '<base64-encoded-vector>',
                'overall_embed': '<base64-encoded-vector>'
            }
        }
    """
```

**Implementation:**
```python
from openai_client import get_openai_client
import base64
import numpy as np

client = get_openai_client()

def get_embedding(text: str) -> list[float]:
    """Get embedding from OpenAI"""
    response = client.embeddings.create(
        model='text-embedding-3-small',
        input=text,
        encoding_format='float'
    )
    return response.data[0].embedding

def encode_embedding(embedding: list[float]) -> str:
    """Encode embedding to base64 string for storage"""
    arr = np.array(embedding, dtype=np.float32)
    return base64.b64encode(arr.tobytes()).decode('utf-8')

def generate_and_format_embeddings(parsed_jd: dict) -> dict:
    # Skills embedding
    skills_text = ', '.join(parsed_jd.get('required_skills', []) + parsed_jd.get('preferred_skills', []))
    skills_embed = get_embedding(skills_text[:8000])
    
    # Responsibilities embedding
    resp_text = ' '.join(parsed_jd.get('responsibilities', []))
    resp_embed = get_embedding(resp_text[:8000])
    
    # Overall embedding
    overall_text = str(parsed_jd)[:8000]
    overall_embed = get_embedding(overall_text)
    
    return {
        'jd_embedding': {
            'model': 'text-embedding-3-small',
            'dimension': 1536,
            'skills_embed': encode_embedding(skills_embed),
            'responsibilities_embed': encode_embedding(resp_embed),
            'overall_embed': encode_embedding(overall_embed)
        }
    }
```

---

### Stage 5: Save to Backend

**Module:** [main_jd_processor.py](scripts/jd-processing/main_jd_processor.py) (orchestrator)

**API Call:**
```python
from common.api_client import api

# Save JD analysis + embeddings
api.patch(f'/jobs/{job_id}', {
    'status': 'completed',
    'jd_analysis': parsed_jd,
    'jd_embedding': jd_embedding,
    'filter_requirements': filter_requirements
})
```

---

## 📄 Resume Processing Pipeline

### Overview
Processes individual resumes through 8 stages:
1. **PDF Extraction**: PDF → text
2. **AI Parsing**: GPT-4o-mini → structured resume
3. **Embedding Generation**: Create 6-section embeddings
4. **Hard Requirements Check**: Pass/fail compliance
5. **Keyword Scoring**: Exact skill matches
6. **Semantic Scoring**: Cosine similarity with JD
7. **Project Scoring**: Domain relevance
8. **Composite Scoring**: Weighted average → Save to Backend

---

### Stage 1: PDF Extraction

**Module:** [a_pdf_extractor.py](scripts/resume-processing/a_pdf_extractor.py)

**Function:**
```python
def process_resume_file(resume_data: dict) -> dict:
    """
    Extract text from resume PDF
    
    Returns:
        {
            'success': bool,
            'raw_text': str,
            'char_count': int,
            'error': str | None
        }
    """
```

**Implementation:**
```python
import fitz

def extract_text_from_pdf(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ""
    
    for page in doc:
        text += page.get_text()
    
    doc.close()
    return text.strip()

def process_resume_file(resume_data: dict) -> dict:
    pdf_path = f"./uploads/{resume_data['group_id']}/{resume_data['filename']}"
    
    if not os.path.exists(pdf_path):
        return {'success': False, 'error': 'PDF not found'}
    
    raw_text = extract_text_from_pdf(pdf_path)
    
    if not raw_text:
        return {'success': False, 'error': 'No text extracted'}
    
    return {
        'success': True,
        'raw_text': raw_text,
        'char_count': len(raw_text)
    }
```

---

### Stage 2: AI Parsing (GPT-4o-mini)

**Module:** [b_ai_parser.py](scripts/resume-processing/b_ai_parser.py)

**Purpose:** Parse resume text into structured JSON

**Schema Highlights:**
- **Personal Info**: name, email, phone, linkedin, github
- **Experience**: Array of jobs with title, company, duration, description, skills_used
- **Education**: Array of degrees with degree, institution, year, gpa
- **Skills**: Categorized by programming, ml_ai, frontend, backend, databases, cloud, etc.
- **Projects**: Array with title, description, technologies, outcomes
- **Certifications**: Array of certification names

**Function:**
```python
def parse_resume_with_ai(raw_text: str) -> dict:
    """
    Parse resume text with AI
    
    Returns:
        {
            'success': bool,
            'parsed_resume': dict,  # Full resume structure
            'error': str | None
        }
    """
```

**OpenAI Function:**
```python
PARSE_FUNCTION = {
    "name": "parse_resume_detailed",
    "parameters": {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"},
            "phone": {"type": "string"},
            "experience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "company": {"type": "string"},
                        "duration": {"type": "string"},
                        "description": {"type": "string"},
                        "skills_used": {"type": "array"}
                    }
                }
            },
            "education": {"type": "array"},
            "skills": {"type": "array"},
            "canonical_skills": {
                "type": "object",
                "properties": {
                    "programming": {"type": "array"},
                    "ml_ai": {"type": "array"},
                    "databases": {"type": "array"}
                }
            },
            "projects": {"type": "array"},
            "certifications": {"type": "array"}
        }
    }
}
```

---

### Stage 3: Embedding Generation

**Module:** [c_embedding_generator.py](scripts/resume-processing/c_embedding_generator.py)

**Purpose:** Generate 6-section embeddings for semantic scoring

**Sections:**
1. `profile`: Name + summary + contact
2. `skills`: All skills concatenated
3. `projects`: Project descriptions
4. `responsibilities`: Experience descriptions
5. `education`: Education details
6. `overall`: Full resume text

**Output Format:**
```python
{
    'resume_embedding': {
        'model': 'text-embedding-3-small',
        'dimension': 1536,
        'profile': [[0.123, 0.456, ...]],      # 2D array (sentences)
        'skills': [[0.789, 0.012, ...]],
        'projects': [[...]],
        'responsibilities': [[...]],
        'education': [[...]],
        'overall': [[...]]
    }
}
```

**Why 2D Arrays?**
- Each section split into sentences
- Each sentence gets its own embedding
- Allows fine-grained semantic matching (sentence-level similarity)

---

### Stage 4: Hard Requirements Check

**Module:** [d_hard_requirements_checker.py](scripts/resume-processing/d_hard_requirements_checker.py)

**Purpose:** Validate resume against mandatory compliance rules

**Checks:**
1. **Experience**: Min years required
2. **Education**: Minimum degree level
3. **Hard Skills**: Must-have skills present
4. **Department**: IT vs. Non-IT filter

**Function:**
```python
def check_hard_requirements(resume_data: dict, jd_analysis: dict, filter_requirements: dict) -> dict:
    """
    Check resume against hard requirements
    
    Returns:
        {
            'hard_requirements': {
                'passed': bool,
                'score': float (0-100),
                'details': {
                    'experience': {'passed': bool, 'reason': str},
                    'education': {'passed': bool, 'reason': str},
                    'hard_skills': {'passed': bool, 'reason': str}
                }
            }
        }
    """
```

**Example:**
```python
def check_experience(resume, min_years):
    total_years = sum_experience_years(resume['experience'])
    passed = total_years >= min_years
    
    return {
        'passed': passed,
        'actual': total_years,
        'required': min_years,
        'reason': f"{'✓' if passed else '✗'} {total_years} years (required: {min_years})"
    }

def check_education(resume, min_degree):
    degrees = resume.get('education', [])
    degree_levels = {'Bachelors': 1, 'Masters': 2, 'PhD': 3}
    
    highest = max([degree_levels.get(d['degree'], 0) for d in degrees], default=0)
    required_level = degree_levels.get(min_degree, 0)
    
    passed = highest >= required_level
    
    return {
        'passed': passed,
        'actual': highest,
        'required': required_level,
        'reason': f"{'✓' if passed else '✗'} Degree level check"
    }
```

---

### Stage 5: Keyword Scoring

**Module:** [e_keyword_scorer.py](scripts/resume-processing/e_keyword_scorer.py)

**Purpose:** Calculate exact keyword matches (ATS-style scoring)

**Algorithm:**
1. Extract keywords from JD (`keywords_flat`)
2. Extract keywords from resume (`skills`, `tools_tech`)
3. Match keywords (case-insensitive, fuzzy matching)
4. Apply JD weighting (`keywords_weighted`)
5. Calculate weighted score

**Function:**
```python
def calculate_keyword_scores(resume_data: dict, jd_analysis: dict) -> dict:
    """
    Calculate keyword match score
    
    Returns:
        {
            'keyword_score': {
                'score': float (0-100),
                'matched_keywords': list[str],
                'missing_keywords': list[str],
                'match_details': dict
            }
        }
    """
```

**Example:**
```python
from fuzzywuzzy import fuzz

def match_keywords(resume_keywords, jd_keywords):
    matched = []
    missing = []
    
    for jd_kw in jd_keywords:
        found = False
        for res_kw in resume_keywords:
            similarity = fuzz.ratio(jd_kw.lower(), res_kw.lower())
            if similarity >= 85:  # Threshold
                matched.append(jd_kw)
                found = True
                break
        
        if not found:
            missing.append(jd_kw)
    
    return matched, missing

def calculate_keyword_scores(resume_data, jd_analysis):
    jd_keywords = jd_analysis.get('keywords_flat', [])
    resume_keywords = resume_data.get('skills', []) + resume_data.get('tools_tech', [])
    
    matched, missing = match_keywords(resume_keywords, jd_keywords)
    
    # Apply weighting
    jd_weights = jd_analysis.get('keywords_weighted', {})
    weighted_score = sum([jd_weights.get(kw, 1.0) for kw in matched])
    max_score = sum(jd_weights.values()) or len(jd_keywords)
    
    score = (weighted_score / max_score) * 100 if max_score > 0 else 0
    
    return {
        'keyword_score': {
            'score': score,
            'matched_keywords': matched,
            'missing_keywords': missing,
            'match_details': {
                'matched_count': len(matched),
                'total_keywords': len(jd_keywords)
            }
        }
    }
```

---

### Stage 6: Semantic Scoring

**Module:** [f_semantic_scorer.py](scripts/resume-processing/f_semantic_scorer.py)

**Purpose:** Calculate cosine similarity between JD and resume embeddings

**Algorithm:**
1. Decode JD embeddings (base64 → numpy arrays)
2. Decode resume embeddings
3. Compute cosine similarity for each section:
   - `skills_similarity`: JD skills ↔ Resume skills
   - `responsibilities_similarity`: JD responsibilities ↔ Resume experience
   - `overall_similarity`: JD overall ↔ Resume overall
4. Weighted average → Final semantic score

**Function:**
```python
def calculate_semantic_scores(resume_data: dict, jd_analysis: dict) -> dict:
    """
    Calculate semantic similarity scores
    
    Returns:
        {
            'semantic_score': {
                'score': float (0-100),
                'similarity_details': {
                    'skills': float,
                    'responsibilities': float,
                    'overall': float
                }
            }
        }
    """
```

**Implementation:**
```python
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

def decode_embedding(base64_str: str) -> np.ndarray:
    """Decode base64 embedding to numpy array"""
    import base64
    bytes_data = base64.b64decode(base64_str)
    return np.frombuffer(bytes_data, dtype=np.float32)

def calculate_semantic_scores(resume_data, jd_analysis):
    jd_embedding = jd_analysis.get('jd_embedding', {})
    resume_embedding = resume_data.get('resume_embedding', {})
    
    # Decode embeddings
    jd_skills = decode_embedding(jd_embedding['skills_embed'])
    resume_skills = np.array(resume_embedding['skills']).flatten()  # Average sentence embeddings
    
    jd_resp = decode_embedding(jd_embedding['responsibilities_embed'])
    resume_resp = np.array(resume_embedding['responsibilities']).flatten()
    
    jd_overall = decode_embedding(jd_embedding['overall_embed'])
    resume_overall = np.array(resume_embedding['overall']).flatten()
    
    # Calculate cosine similarities
    skills_sim = cosine_similarity([jd_skills], [resume_skills])[0][0]
    resp_sim = cosine_similarity([jd_resp], [resume_resp])[0][0]
    overall_sim = cosine_similarity([jd_overall], [resume_overall])[0][0]
    
    # Weighted average (weights from JD)
    weights = jd_analysis.get('weighting', {})
    semantic_weight = weights.get('keywords_semantic', 0.33)
    
    final_score = (
        skills_sim * 0.4 +
        resp_sim * 0.3 +
        overall_sim * 0.3
    ) * 100
    
    return {
        'semantic_score': {
            'score': final_score,
            'similarity_details': {
                'skills': skills_sim * 100,
                'responsibilities': resp_sim * 100,
                'overall': overall_sim * 100
            }
        }
    }
```

---

### Stage 7: Project Scoring

**Module:** [g_project_scorer.py](scripts/resume-processing/g_project_scorer.py)

**Purpose:** Score project relevance based on domain and technologies

**Algorithm:**
1. Extract JD domain tags
2. Extract resume projects
3. Match project technologies with JD skills
4. Score based on:
   - Technology overlap
   - Domain relevance (AI/ML, Cloud, etc.)
   - Project complexity (inferred from description length)

**Function:**
```python
def calculate_project_scores(resume_data: dict, jd_analysis: dict) -> dict:
    """
    Calculate project relevance score
    
    Returns:
        {
            'project_score': {
                'score': float (0-100),
                'relevant_projects': list[dict],
                'details': dict
            }
        }
    """
```

---

### Stage 8: Composite Scoring

**Module:** [h_composite_scorer.py](scripts/resume-processing/h_composite_scorer.py)

**Purpose:** Calculate final weighted score and save to backend

**Formula:**
```python
composite_score = (
    0.30 * hard_requirements_score +
    0.25 * keyword_score +
    0.25 * semantic_score +
    0.20 * project_score
)
```

**Adjustable Weights:** Can be overridden by JD weighting configuration

**Function:**
```python
def calculate_composite_score(
    hard_req: dict,
    keyword: dict,
    semantic: dict,
    project: dict,
    jd_analysis: dict
) -> dict:
    """
    Calculate weighted composite score
    
    Returns:
        {
            'composite_score': float (0-100)
        }
    """
```

---

## 🏆 Final Ranking Pipeline

### Overview
Re-ranks all candidates using LLM (GPT-4o-mini) after all resumes processed

**Module:** [main_ranking_processor.py](scripts/final-ranking/main_ranking_processor.py)

### Algorithm

1. **Fetch Candidates**: Get all score records for job
2. **Batch Processing**: Process in batches of 30 candidates
3. **LLM Re-ranking**: Call GPT-4o-mini with candidate summaries + JD
4. **Merge Batches**: Combine rankings from all batches
5. **Update Database**: Save `final_ranking` + `llm_explanation`

### LLM Re-ranking Prompt

**System:**
```
You are an expert technical recruiter. Re-rank candidates based on:
- Hard requirements compliance (mandatory)
- Skills match (keyword + semantic)
- Project relevance
- Overall JD fit

Return ranked list with explanations.
```

**User:**
```
Job Description:
{jd_summary}

Candidates:
1. John Doe
   - Composite Score: 87.5
   - Hard Requirements: PASS
   - Matched Skills: React, Node.js, TypeScript, AWS
   - Missing Skills: Kubernetes
   - Projects: 3 relevant projects

2. Jane Smith
   - Composite Score: 85.0
   - Hard Requirements: PASS
   - Matched Skills: React, Node.js, GraphQL
   - Missing Skills: TypeScript, AWS
   - Projects: 2 relevant projects

...

Task: Re-rank these candidates and explain your reasoning.
```

**Response:**
```json
{
  "rankings": [
    {
      "candidate_id": "resume_id_1",
      "rank": 1,
      "explanation": "Strong full-stack experience with 6 years React/Node. Has AWS expertise which is critical for this role. 3 highly relevant projects demonstrate production experience."
    },
    {
      "candidate_id": "resume_id_2",
      "rank": 2,
      "explanation": "Good React/Node skills but lacks TypeScript experience which is required. Projects show potential but less depth than top candidate."
    }
  ]
}
```

### Implementation

```python
def process_final_ranking(job) -> dict:
    job_id = job.data.get('jobId')
    
    # 1. Fetch all scores
    scores = fetch_candidate_scores(job_id)
    
    # 2. Batch into groups of 30
    batches = [scores[i:i+30] for i in range(0, len(scores), 30)]
    
    # 3. Re-rank each batch
    all_rankings = []
    for batch in batches:
        llm_rankings = rerank_with_llm(batch, jd_data)
        all_rankings.extend(llm_rankings)
    
    # 4. Sort by LLM rank
    all_rankings.sort(key=lambda x: x['rank'])
    
    # 5. Update database
    for i, ranking in enumerate(all_rankings):
        api.patch(f'/scores/{ranking["score_id"]}', {
            'final_ranking': i + 1,
            'llm_explanation': ranking['explanation']
        })
    
    return {'success': True}
```

---

## 🛠️ Common Utilities

### API Client ([common/api_client.py](scripts/common/api_client.py))

**Purpose:** Wrapper for backend REST API calls

**Implementation:**
```python
import requests
import os

class APIClient:
    def __init__(self):
        self.base_url = os.getenv('BACKEND_API_URL', 'http://localhost:3001/api')
        self.api_key = os.getenv('BACKEND_API_KEY', '')
    
    def _headers(self):
        headers = {'Content-Type': 'application/json'}
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        return headers
    
    def get(self, path: str):
        res = requests.get(f'{self.base_url}{path}', headers=self._headers())
        res.raise_for_status()
        return res.json()
    
    def patch(self, path: str, data: dict):
        res = requests.patch(f'{self.base_url}{path}', json=data, headers=self._headers())
        res.raise_for_status()
        return res.json()
    
    def post(self, path: str, data: dict):
        res = requests.post(f'{self.base_url}{path}', json=data, headers=self._headers())
        res.raise_for_status()
        return res.json()

api = APIClient()
```

**Usage:**
```python
from common.api_client import api

# Fetch job
job_data = api.get(f'/jobs/{job_id}')

# Update job
api.patch(f'/jobs/{job_id}', {'status': 'completed'})
```

---

### Job Logger ([common/job_logger.py](scripts/common/job_logger.py))

**Purpose:** Structured logging per job/resume

**Implementation:**
```python
import logging

class JobLogger:
    def __init__(self, job_id: str, job_type: str):
        self.job_id = job_id
        self.job_type = job_type
        self.logger = logging.getLogger(f'{job_type}:{job_id}')
    
    def progress(self, message: str):
        self.logger.info(f'[{self.job_id}] {message}')
    
    def fail(self, error: str):
        self.logger.error(f'[{self.job_id}] ❌ {error}')
    
    def complete(self, message: str):
        self.logger.info(f'[{self.job_id}] ✅ {message}')
    
    @staticmethod
    def for_jd(job_id: str):
        return JobLogger(job_id, 'JD')
    
    @staticmethod
    def for_resume(resume_id: str):
        return JobLogger(resume_id, 'RESUME')
```

**Usage:**
```python
from common.job_logger import JobLogger

logger = JobLogger.for_jd(job_id)
logger.progress("Extracting text from PDF")
logger.complete("JD processing completed")
```

---

### Progress Tracker ([common/bullmq_progress.py](scripts/common/bullmq_progress.py))

**Purpose:** Update BullMQ job progress

**Implementation:**
```python
class ProgressTracker:
    def __init__(self, job):
        self.job = job
    
    async def update(self, percent: int, stage: str, message: str):
        """Update job progress"""
        await self.job.updateProgress({
            'percent': percent,
            'stage': stage,
            'message': message
        })
    
    async def failed(self, error: str, error_type: str, stage: str):
        """Mark job as failed"""
        await self.job.updateProgress({
            'percent': 100,
            'stage': stage,
            'message': f'Failed: {error}',
            'error_type': error_type
        })
```

**Usage:**
```python
from common.bullmq_progress import ProgressTracker

tracker = ProgressTracker(job)
await tracker.update(50, 'ai_parsing', 'Parsing JD with AI')
```

---

## 🤖 AI Integration

### OpenAI Client ([openai_client.py](scripts/openai_client.py))

**Singleton client for OpenAI API**

```python
from openai import OpenAI
import os

_client = None

def get_openai_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            raise ValueError('OPENAI_API_KEY not set')
        _client = OpenAI(api_key=api_key)
    return _client
```

**Usage:**
```python
from openai_client import get_openai_client

client = get_openai_client()

# Chat completion
response = client.chat.completions.create(
    model='gpt-4o-mini',
    messages=[{'role': 'user', 'content': 'Hello'}]
)

# Embeddings
response = client.embeddings.create(
    model='text-embedding-3-small',
    input='Sample text'
)
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# OpenAI API
OPENAI_API_KEY=sk-proj-xxxxx

# Redis (BullMQ)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=password123

# Backend API
BACKEND_API_URL=http://backend:3001/api
BACKEND_API_KEY=                # Optional

# Logging
LOG_LEVEL=INFO                  # DEBUG | INFO | WARNING | ERROR
```

---

## 🚨 Error Handling

### Retry Strategy

**Automatic retries** configured in BullMQ:
```python
job_options = {
    'attempts': 3,
    'backoff': {
        'type': 'exponential',
        'delay': 5000  # Start with 5s, double each retry
    }
}
```

### Error Types

1. **API Errors**: OpenAI rate limits, API failures
2. **Parsing Errors**: Invalid JSON, missing fields
3. **File Errors**: PDF not found, corrupted files
4. **Database Errors**: MongoDB connection issues

**Handling:**
```python
try:
    result = process_jd_complete(job)
except OpenAIError as e:
    logger.error(f"OpenAI API error: {e}")
    return {'success': False, 'error': 'AI processing failed'}
except FileNotFoundError as e:
    logger.error(f"File not found: {e}")
    return {'success': False, 'error': 'File missing'}
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    return {'success': False, 'error': str(e)}
```

---

## 🚀 Performance Optimization

### Concurrency Settings

**BullMQ Worker Concurrency:**
- JD Processing: 2 concurrent (AI-heavy)
- Resume Processing: 5 concurrent (batch processing)
- Final Ranking: 1 concurrent (sequential)

### Batch Processing

**OpenAI Embeddings:** Batch multiple texts in single API call
```python
# Instead of:
for text in texts:
    embedding = client.embeddings.create(input=text)

# Use:
embeddings = client.embeddings.create(input=texts)  # Batch API call
```

### Caching

**Embedding Cache:** Cache embeddings for duplicate skills
```python
embedding_cache = {}

def get_embedding_cached(text: str):
    if text in embedding_cache:
        return embedding_cache[text]
    
    embedding = client.embeddings.create(input=text)
    embedding_cache[text] = embedding
    return embedding
```

---

## 🛠️ Development Guide

### Run Worker Locally

```bash
cd scripts
pip install -r requirements.txt

# Set environment variables
export OPENAI_API_KEY=sk-proj-xxxxx
export REDIS_HOST=localhost
export REDIS_PORT=6379
export BACKEND_API_URL=http://localhost:3001/api

# Run worker
python bullmq_consumer.py
```

### Test Individual Module

```python
# Test JD parsing
from jd_processing.b_ai_jd_parser import process_jd_with_ai

jd_text = "We are looking for a Senior React Developer..."
result = process_jd_with_ai(jd_text)
print(result)
```

### Add New Scorer

1. Create file: `scripts/resume-processing/i_new_scorer.py`
2. Implement function:
```python
def calculate_new_score(resume_data: dict, jd_analysis: dict) -> dict:
    score = 0.0
    details = {}
    
    # Your scoring logic
    
    return {
        'new_score': {
            'score': score,
            'details': details
        }
    }
```

3. Import in orchestrator:
```python
from i_new_scorer import calculate_new_score

# Add to pipeline
new_score = calculate_new_score(parsed_resume, jd_analysis)

# Update composite scorer weights
```

---

## 🐛 Troubleshooting

### "OpenAI API key not found"
```bash
# Check environment variable
echo $OPENAI_API_KEY

# Set in shell
export OPENAI_API_KEY=sk-proj-xxxxx

# Or add to .env
echo "OPENAI_API_KEY=sk-proj-xxxxx" >> .env
```

### "Redis connection refused"
```bash
# Check Redis is running
docker ps | grep redis

# Test connection
redis-cli -h localhost -p 6379 -a password123 ping
```

### "Job stuck in processing"
```bash
# Check worker logs
docker logs kreeda-python-processor -f

# Manually fail job (Python)
from bullmq import Queue
queue = Queue('jd-processing', {"connection": redis_config})
await queue.getJob(job_id).moveToFailed({"message": "Manual reset"})
```

---

**Last Updated**: February 5, 2026
**Version**: 1.0.0

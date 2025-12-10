# HR Hiring Bot - Complete Codebase Summary

## Overview
This is an AI-powered resume screening system that automates candidate evaluation against job descriptions. It uses OpenAI GPT models for parsing, embeddings for semantic matching, and a hybrid scoring system for ranking candidates.

---

## 📁 Root Directory Files

### `main.py`
**Role:** Main Streamlit application entry point and UI orchestrator
**Functionality:**
- Creates the Streamlit web interface with 4 tabs: Documentation, Upload Requirements, Upload Resumes, Rankings
- Handles JD upload (PDF or text) and triggers JD processing
- Manages resume uploads and triggers the full processing pipeline
- Displays rankings and provides download functionality
- Cleans up previous run data
- Uses `runpy.run_path()` to execute processing scripts in-process (safer for Streamlit)
- Manages session state to prevent duplicate processing

### `requirements.txt`
**Role:** Python package dependencies list
**Functionality:**
- Lists all required packages with specific versions
- Includes: Streamlit, OpenAI, pandas, numpy, PyMuPDF, PyPDF2, and other utilities

### `utils.py`
**Role:** Utility functions for file operations
**Functionality:**
- `save_text_to_file()`: Saves cleaned text to files
- `get_file_extension()`: Extracts file extension
- `is_pdf_scanned()`: Heuristic to detect scanned PDFs (no extractable text)
- `clean_text()`: Basic text cleaning for resume content
- `detect_mime_type()`: Detects MIME type from filename

### `README.md`
**Role:** HR User Guide
**Functionality:**
- Complete user guide for HR team members
- Step-by-step instructions for using the Streamlit app
- Understanding filter requirements
- Best practices and troubleshooting
- Common questions and answers

### `text.json`
**Role:** Empty/placeholder file (not actively used in pipeline)

### `.gitignore`
**Role:** Git ignore rules
**Functionality:**
- Excludes virtual environment, cache files, processed data, and sensitive files

---

## 📁 utils/ Directory (Shared Utilities)

### `utils/__init__.py`
**Role:** Python package initializer (empty)

### `utils/validation.py`
**Role:** Data validation using Pydantic schemas
**Functionality:**
- `ResumeSchema`: Complete Pydantic schema for resume JSON validation
- `JDSchema`: Complete Pydantic schema for JD JSON validation
- `validate_resume()`: Validates resume data against schema
- `validate_jd()`: Validates JD data against schema
- Field validation, type checking, range validation
- Provides warnings for validation issues (non-blocking)

### `utils/retry.py`
**Role:** Retry logic and circuit breakers
**Functionality:**
- `retry_api_call()`: Decorator for OpenAI API retries with exponential backoff
- `retry_file_operation()`: Decorator for file operation retries
- `CircuitBreaker`: Circuit breaker pattern to prevent cascading failures
- `openai_circuit_breaker`: Global circuit breaker instance for OpenAI API
- Configurable retry attempts, wait times, and backoff strategies

### `utils/cache.py`
**Role:** File-based caching utilities
**Functionality:**
- `FileCache`: Cache class with hash-based keys (content-based)
- `resume_cache`: Global cache instance for resume parsing (`.cache/resumes/`)
- `jd_cache`: Global cache instance for JD parsing (`.cache/jd/`)
- `get_resume_cache_key()`: Generate cache key from resume file
- `get_jd_cache_key()`: Generate cache key from JD file
- Automatic cache directory creation
- Hash-based cache invalidation

### `utils/common.py`
**Role:** Shared utility functions
**Functionality:**
- `extract_function_call()`: Extract OpenAI function call from response
- `safe_json_load()`: Safe JSON loading with error handling
- `safe_json_save()`: Safe JSON saving with error handling
- `extract_jd_skills_from_domain_tags()`: Extract skills from JD domain tags
- `normalize_name()`: Normalize candidate names
- `canonicalize_string_list()`: Normalize string lists (lowercase, strip)
- `canonicalize_skills_block()`: Normalize skills blocks for comparison
- Reduces code duplication across modules

---

## 📁 InputThread/ Directory

### `InputThread/__init__.py`
**Role:** Python package initializer (empty)

### `InputThread/file_router.py`
**Role:** PDF routing and classification
**Functionality:**
- `is_text_based_pdf()`: Detects if PDF contains extractable text using PyMuPDF
- `log_skipped()`: Logs image-based or unsupported PDFs to `Skipped_List.txt`
- `route_pdf()`: Main router function that:
  - Checks if file is PDF
  - Determines if text-based or image-based
  - Routes text-based PDFs to `extract_pdf.py` for processing
  - Skips and logs image-based PDFs (would need OCR, not implemented)

### `InputThread/extract_pdf.py`
**Role:** PDF text extraction engine
**Functionality:**
- `process_pdf()`: Extracts text from PDF using PyMuPDF (fitz)
- Saves extracted text to `Processed-TXT/` directory
- Maintains `Processed_Resume_Index.txt` with list of processed files
- Preserves original filename when possible
- Returns path to saved .txt file or None on failure

### `InputThread/extract_docx.py`
**Role:** DOCX file text extraction (not actively used in main pipeline)
**Functionality:**
- `extract_text_from_docx()`: Extracts text from .docx files using python-docx library
- Also handles .txt files directly
- Currently not integrated into main workflow

### `InputThread/extract_ocr.py`
**Role:** OCR extraction for scanned PDFs (not actively used)
**Functionality:**
- `extract_text_from_scanned_pdf()`: Uses pytesseract and pdf2image for OCR
- Converts PDF pages to images, then extracts text via OCR
- Requires Tesseract installation (not in requirements.txt)
- Currently not integrated into main workflow

### `InputThread/readme.md`
**Role:** Documentation for InputThread module (minimal content)

---

## 📁 InputThread/AI Processing/ Directory

### `InputThread/AI Processing/JDGpt.py`
**Role:** Job Description parser using OpenAI GPT
**Functionality:**
- Converts raw JD text (`JD.txt`) into structured JSON (`JD.json`)
- Uses OpenAI GPT-4o-mini with function calling for structured output
- Extracts comprehensive JD information:
  - Role details (title, seniority, department, industry)
  - Skills (required, preferred, canonical categories) - **normalized to canonical forms**
  - Responsibilities, deliverables, KPIs
  - Education, certifications, experience requirements
  - Compensation, benefits, work model
  - Keywords (flat and weighted) for ATS matching
  - Embedding hints for semantic matching
  - HR notes and recommendations
  - Filter requirements (structured from HR input)
- Enriches `domain_tags` with structured summary payload (JSON-encoded)
- Adds skill tags, HR notes, and explainability phrases to domain_tags
- **Optimizations:**
  - Optimized prompts (~350 tokens, 50% reduction)
  - Skill normalization instructions for consistent skill naming
  - File-based caching (`.cache/jd/`) for repeated processing
  - Retry logic with exponential backoff and circuit breaker
  - Pydantic data validation for output integrity
- Output: `InputThread/JD/JD.json` (overwrites on each run)

### `InputThread/AI Processing/GptJson.py`
**Role:** Resume parser using OpenAI GPT
**Functionality:**
- Converts extracted resume text (`Processed-TXT/*.txt`) into structured JSON (`ProcessedJson/*.json`)
- Uses OpenAI GPT-4o-mini with function calling
- Loads JD domain_tags to guide parsing and scoring
- Extracts from each resume:
  - Candidate info (name, contact, location, experience years)
  - Candidate ID (deterministic hash-based for duplicate detection)
  - Domain tags (AIML, Fullstack, Cloud, etc.)
  - Canonical skills (programming, frameworks, libraries, ML/AI, frontend, backend, testing, databases, cloud, infra, devtools, methodologies) - **normalized to match JD format**
  - Inferred skills with confidence and provenance
  - Projects with detailed metrics (difficulty, novelty, skill_relevance, complexity, technical_depth, domain_relevance, execution_quality)
  - Experience entries with responsibilities and achievements
  - ATS boost line (normalized skill keywords)
  - Embedding hints for semantic matching
- Scores projects based on JD domain alignment (strict evaluation)
- **Optimizations:**
  - Optimized prompts (~300 tokens, 40% reduction)
  - Skill normalization to match JD's skill format
  - **Parallel processing support** (ThreadPoolExecutor, configurable workers)
  - File-based caching (`.cache/resumes/`) for repeated processing
  - Retry logic with exponential backoff and circuit breaker
  - Pydantic data validation for output integrity
  - Duplicate detection based on candidate_id
- Skips already processed resumes (checks if output JSON exists)
- Output: `ProcessedJson/*.json` (one per resume)

### `InputThread/AI Processing/readme.md`
**Role:** Documentation for AI Processing module (empty)

---

## 📁 JD/ Directory

### `JD/JD.txt`
**Role:** Raw job description text file
**Functionality:**
- Stores extracted JD text (from PDF upload or manual input)
- Input for `JDGpt.py` processing

### `JD/JD.json`
**Role:** Structured job description JSON
**Functionality:**
- Output from `JDGpt.py`
- Contains all parsed JD information in structured format
- Used by all ranking/comparison modules

### `JD/JDextract_pdf.py`
**Role:** JD-specific PDF extraction utility (not actively used in main pipeline)
**Functionality:**
- `process_jd_pdf()`: Extracts text from JD PDF using PyMuPDF
- Saves to `JD.txt`
- Currently, main.py handles JD extraction directly

### `JD/readme.md`
**Role:** Documentation for JD module (empty)

---

## 📁 ResumeProcessor/ Directory

### `ResumeProcessor/EarlyFilter.py`
**Role:** HR requirements filtering module
**Functionality:**
- Filters candidates based on HR requirements before scoring
- Validates experience ranges (min/max years)
- Matches skills using normalized skill names (from LLM parsing)
- Validates location requirements
- Checks other criteria (semantic matching)
- **Features:**
  - Configurable filtering mode (strict/flexible)
  - Flexible mode: 50% skill match threshold
  - Experience extraction from other_criteria
  - Moves filtered resumes to `ProcessedJson/FilteredResumes/`
  - Updates `Ranking/Skipped.json` with filtered candidates
- Input: `ProcessedJson/*.json`, `InputThread/JD/JD.json`
- Output: Filtered resumes moved to separate directory, skipped list updated

### `ResumeProcessor/ProjectProcess.py`
**Role:** Project-based scoring module
**Functionality:**
- Reads processed resume JSONs from `ProcessedJson/`
- Calculates weighted aggregate score for each candidate's projects
- Uses 7 metrics with equal weights (1/7 each):
  - difficulty, novelty, skill_relevance, complexity, technical_depth, domain_relevance, execution_quality
- `calculate_weighted_score()`: Computes weighted average of project metrics
- `process_resume()`: Processes single resume and returns project aggregate score
- Merges results into `Ranking/Scores.json` (updates existing entries)
- Output: Adds `project_aggregate` field to Scores.json

### `ResumeProcessor/KeywordComparitor.py`
**Role:** ATS-style keyword matching module
**Functionality:**
- Performs weighted keyword matching between JD and resumes
- Collects JD keywords from multiple sources:
  - required_skills, preferred_skills, weighted_keywords, domain_tags, responsibilities, education
- Collects resume tokens from:
  - canonical_skills, inferred_skills, skill_proficiency, projects, experience_entries, profile keywords
- Scoring components:
  - `score_overlap()`: Percentage of JD keywords found in resume
  - `score_weighted_keywords()`: Weighted keyword match using JD's keyword weights
  - `score_experience_keywords()`: Matches experience action verbs (led, architected, scaled, etc.) with weights
  - `score_project_metrics()`: Uses project metrics from resume JSON
- Default weights (can be overridden by JD weighting):
  - required_skills: 0.18, preferred_skills: 0.08, weighted_keywords: 0.15, experience_keywords: 0.25, domain_relevance: 0.10, technical_depth: 0.10, project_metrics: 0.09, responsibilities: 0.03, education: 0.02
- Normalizes final Keyword_Score to 0-1 range across all candidates
- Handles errors gracefully (assigns 0.0 score on failure, continues processing)
- Output: Adds/updates `Keyword_Score` field in `Ranking/Scores.json`

### `ResumeProcessor/SemanticComparitor.py`
**Role:** Semantic similarity matching using OpenAI embeddings
**Functionality:**
- Uses OpenAI `text-embedding-3-small` model for embeddings
- Implements embedding cache (`.semantic_embed_cache.pkl`) to avoid re-computing
- Extracts sections from JD and resumes:
  - profile, skills, projects, responsibilities, education, overall
- `extract_sections_from_jd()`: Breaks JD into semantic sections
- `extract_sections_from_resume()`: Breaks resume into semantic sections
- `embed_texts()`: Converts text sections to embeddings (with caching and batching)
- `compute_section_score()`: Calculates cosine similarity between JD and resume sections
  - Uses coverage (TAU_COV=0.65), depth, and density (TAU_RESUME=0.55) metrics
- Section weights:
  - skills: 0.30, projects: 0.25, responsibilities: 0.20, profile: 0.10, education: 0.05, overall: 0.10
- Normalizes Semantic_Score to 0-1 range across all candidates
- Output: Adds/updates `Semantic_Score` field in `Ranking/Scores.json`

### `ResumeProcessor/Ranker/FinalRanking.py`
**Role:** Final ranking aggregation and output generation
**Functionality:**
- Aggregates all three scores: project_aggregate, Semantic_Score, Keyword_Score
- Weights: project_aggregate: 0.35, Semantic_Score: 0.35, Keyword_Score: 0.30
- `compute_final_score()`: Calculates weighted final score
  - If all scores = 0 → returns None (candidate skipped)
  - If only 1 score available → applies decay of 0.08 (ranks lower but not excluded)
  - If 2+ scores → normal weighted average
- **LLM Re-ranking:** Uses GPT to re-rank candidates based on filter requirements
- **Compliance Checking:** Validates candidates against filter requirements and reports compliance
- `_ranking_core()`: Core ranking logic, returns (ranked_list, skipped_list)
- `run_ranking()`: Streamlit-safe function that stores results in `RANKING_RAM` for UI display
- Outputs:
  - `Ranking/Final_Ranking.json`: Complete ranked candidate list with all scores and compliance details
  - `Ranking/Skipped.json`: Candidates with all scores = 0
  - `Ranking/DisplayRanks.txt`: HR-friendly text format (Rank. Name | Score)

---

## 📁 Processed-TXT/ Directory
**Role:** Temporary storage for extracted resume text
**Functionality:**
- Stores raw text extracted from PDF resumes
- Files: `{resume_name}.txt`
- Input for `GptJson.py` processing
- Cleared between runs (via main.py cleanup)

---

## 📁 ProcessedJson/ Directory
**Role:** Storage for structured resume JSON files
**Functionality:**
- Stores AI-parsed resume JSONs (one per resume)
- Files: `{resume_name}.json`
- Output from `GptJson.py`
- Input for all ranking modules
- Cleared between runs (via main.py cleanup)

---

## 📁 Ranking/ Directory
**Role:** Output directory for all ranking results
**Functionality:**
- `Scores.json`: Consolidated scores from all modules (project_aggregate, Keyword_Score, Semantic_Score)
- `Final_Ranking.json`: Final ranked list with Final_Score
- `Skipped.json`: Candidates excluded (all scores = 0)
- `DisplayRanks.txt`: Human-readable ranking list

---

## 🔄 Complete Pipeline Flow

1. **JD Processing:**
   - User uploads JD (PDF or text) → saved to `InputThread/JD/JD.txt`
   - User optionally adds filter requirements → saved to `InputThread/JD/Filter_Requirements.txt`
   - `JDGpt.py` runs → creates `InputThread/JD/JD.json`
     - Skill normalization to canonical forms
     - Filter requirements parsing
     - Caching for repeated processing

2. **Resume Processing:**
   - User uploads resumes (PDFs) → `file_router.py` routes text-based PDFs
   - `extract_pdf.py` extracts text → saves to `Processed-TXT/*.txt`
   - `GptJson.py` parses resumes → creates `ProcessedJson/*.json` **[PARALLEL PROCESSING]**
     - Skill normalization to match JD format
     - Caching for repeated processing
     - Duplicate detection

3. **Early Filtering:**
   - `EarlyFilter.py` → filters candidates based on HR requirements
     - Experience validation
     - Skills matching (normalized)
     - Location validation
     - Moves filtered resumes to `ProcessedJson/FilteredResumes/`

4. **Scoring (runs sequentially):**
   - `ProjectProcess.py` → calculates project_aggregate → updates `Scores.json`
   - `KeywordComparitor.py` → calculates Keyword_Score → updates `Scores.json`
   - `SemanticComparitor.py` → calculates Semantic_Score → updates `Scores.json`

5. **Final Ranking:**
   - `FinalRanking.py` → aggregates all scores → creates final ranking files
     - LLM re-ranking based on filter requirements
     - Compliance checking and reporting

---

## 🔑 Key Design Decisions

1. **Hybrid Scoring:** Combines project depth, keyword matching, and semantic similarity
2. **Error Handling:** Graceful degradation (assigns 0 scores, continues processing)
3. **Caching:** 
   - Embedding cache to reduce API costs and improve speed
   - File-based caching for JD and resume parsing (hash-based keys)
4. **Normalization:** 
   - All scores normalized to 0-1 range for fair comparison
   - Skill normalization to canonical forms for consistent matching
5. **Streamlit Integration:** Uses `runpy` instead of subprocess for safer execution
6. **RAM-based Display:** FinalRanking exposes `RANKING_RAM` for UI even if file write fails
7. **Parallel Processing:** ThreadPoolExecutor for I/O-bound resume processing (3-4x speedup)
8. **Robustness:**
   - Retry logic with exponential backoff for API calls
   - Circuit breaker pattern to prevent cascading failures
   - Pydantic data validation for output integrity
9. **Early Filtering:** HR requirements filtering before scoring to reduce processing time
10. **LLM Re-ranking:** Uses GPT to re-rank candidates based on filter requirements for better alignment

---

## ✅ Recent Improvements (Version 2.0)

### Performance Optimizations
1. **Prompt Optimization:** 
   - JD prompts reduced by ~50% (from ~700 to ~350 tokens)
   - Resume prompts reduced by ~40% (from ~500 to ~300 tokens)
   - Significant cost and speed improvements

2. **Parallel Processing:**
   - Resume processing now runs in parallel (ThreadPoolExecutor)
   - 3-4x speedup for batch processing
   - Configurable worker count (default: 5)

3. **Caching:**
   - File-based caching for JD parsing (`.cache/jd/`)
   - File-based caching for resume parsing (`.cache/resumes/`)
   - Hash-based cache keys (content-based invalidation)
   - Instant processing for repeated inputs

### Robustness Improvements
4. **Retry Logic:**
   - Exponential backoff for OpenAI API calls
   - Circuit breaker pattern to prevent cascading failures
   - Configurable retry attempts and wait times

5. **Data Validation:**
   - Pydantic schemas for JD and resume JSON validation
   - Type checking, range validation, field validation
   - Non-blocking warnings for validation issues

6. **Error Handling:**
   - Graceful degradation across all modules
   - Comprehensive error logging
   - User-friendly error messages in UI

### Feature Enhancements
7. **Skill Normalization:**
   - LLM-based skill normalization to canonical forms
   - Consistent skill matching across JD and resumes
   - Reduced false negatives in filtering

8. **Early Filtering:**
   - HR requirements filtering before scoring
   - Configurable filtering modes (strict/flexible)
   - Experience, skills, location validation

9. **LLM Re-ranking:**
   - GPT-based re-ranking using filter requirements
   - Better alignment with HR needs
   - Compliance checking and reporting

10. **Code Quality:**
    - Shared utilities in `utils/` package
    - Reduced code duplication
    - Better maintainability

### 🟡 Optional Features (Only Needed If HRs Use These Formats)
- **OCR Support:** `extract_ocr.py` exists but not integrated. Only needed if HRs upload scanned/image-based PDFs.
- **DOCX Support:** `extract_docx.py` exists but not used. Only needed if HRs upload .docx files.

### 🟢 Configuration Notes
- **API Key:** Uses environment variables (`.env` file) or Streamlit secrets for cloud deployment
- **Parallel Processing:** Enabled by default, can be configured via environment variables

---

## 📝 Notes for HR Team

- **Input:** Upload JD first, then process it. Then upload resumes and process them.
- **Output:** Check Rankings tab for final results. Download `DisplayRanks.txt` for easy sharing.
- **Troubleshooting:** If rankings don't appear, check that all three scoring modules completed successfully.
- **Performance:** Processing time depends on number of resumes and API response times (OpenAI).

---

## ❓ Frequently Asked Questions & Answers

### 1. Where is `Processed_Resume_Index.txt` stored?

**Answer:** The file is stored in the **root directory** of the project (same level as `main.py`).

- **Location:** `D:\Kreeda_Hiring_BOT\Processed_Resume_Index.txt`
- **Purpose:** Maintains a list of all processed resume text files (one path per line)
- **Content:** Contains paths like `Processed-TXT\ResumeName.txt`
- **Note:** The file uses relative path `"Processed_Resume_Index.txt"` in `extract_pdf.py`, which means it's created in the current working directory (project root when running from Streamlit)

**Why you might not see it:**
- If you're looking in a subdirectory, check the root folder
- The file is created only after successful PDF extraction
- It's appended to (not overwritten), so it accumulates entries across runs

---

### 2. How Does JD Extraction Work?

**JD Processing Flow:**

1. **Input:** HR uploads JD (PDF or text) → saved to `InputThread/JD/JD.txt`

2. **AI Processing (`JDGpt.py`):**
   - Uses OpenAI GPT-4o-mini to parse raw JD text
   - Extracts structured information into `JD.json`:
     - **Role details:** title, seniority, department, industry
     - **Skills:** required, preferred, canonical categories (programming, frameworks, etc.)
     - **Requirements:** responsibilities, education, certifications, experience years
     - **Keywords:** flat list and weighted keywords for ATS matching
     - **HR Notes:** recommendations and inferred requirements (see below)
     - **Embedding hints:** text snippets for semantic matching

3. **Domain Tags Enrichment:**
   - Adds structured tags to `domain_tags` array:
     - `JD_SUMMARY:{...}` - JSON-encoded summary with role, seniority, skills
     - `REQ_SKILL:...` - Each required skill as a tag
     - `PREF_SKILL:...` - Each preferred skill as a tag
     - `TOOL:...` - Technology tools
     - `HR_NOTE:cat=...;type=...;impact=...;note=...` - HR recommendations (see below)
     - `PHRASE:...` - Key JD phrases for semantic matching

4. **Output:** `InputThread/JD/JD.json` - Complete structured JD data

**What Gets Used Ahead:**
- `required_skills`, `preferred_skills` → Used in `KeywordComparitor.py` for keyword matching
- `domain_tags` → Used in `GptJson.py` to guide resume parsing and project scoring
- `keywords_weighted` → Used in `KeywordComparitor.py` for weighted keyword matching
- `embedding_hints` → Used in `SemanticComparitor.py` for semantic similarity
- `hr_notes` → **Currently NOT used for filtering** (see issue #3 below)

---

### 3. How Do HR Notes Work?

**HR Notes Structure:**

HR notes are generated by the AI when it identifies:
- **Recommendations:** Suggestions to improve JD clarity (e.g., "Specify years of experience for Gen AI")
- **Inferred Requirements:** Requirements implied but not explicitly stated in JD

**Format in JD.json:**
```json
{
  "hr_notes": [
    {
      "category": "clarity",  // or "compliance", "security", etc.
      "type": "recommendation",  // or "inferred_requirement"
      "note": "Specify the level of experience required...",
      "impact": 0.5,  // 0-1 scale
      "reason": "Clarifying experience levels can help...",
      "source_provenance": ["Familiarity with Lang chain..."]
    }
  ],
  "hr_points": 3  // Count of HR notes
}
```

**Also Added to domain_tags as:**
```
HR_NOTE:cat=clarity;type=recommendation;impact=0.5;note=Specify the level...
```

**Intended Purpose:**
HR notes should act as **filters or boosters** to:
- Filter out candidates who don't meet inferred requirements
- Boost candidates who meet recommended criteria
- Apply penalties for missing critical inferred skills

**Current Status:** ❌ **HR NOTES ARE NOT BEING USED FOR FILTERING**

---

### 4. How Are HR Notes Currently Handled in Resume Processing?

**Current Implementation:**

1. **In `JDGpt.py`:** ✅ HR notes are extracted and added to `domain_tags` as `HR_NOTE:...` tags

2. **In `GptJson.py`:** ⚠️ HR notes are passed via `domain_tags` to the resume parser, but:
   - They're only used as **context** for the AI to understand JD requirements
   - The AI is instructed to score projects/skills based on domain alignment
   - **No explicit filtering or scoring based on HR note criteria**

3. **In `KeywordComparitor.py`:** ❌ HR notes are **NOT checked** - only skills, keywords, and domain tags are matched

4. **In `SemanticComparitor.py`:** ❌ HR notes are **NOT used** - only semantic similarity of skills/projects/responsibilities

5. **In `FinalRanking.py`:** ❌ HR notes are **NOT used** - only aggregates the three scores

**Result:** HR notes are extracted and stored but **completely ignored** in the ranking/filtering process.

---

## 🔍 Pipeline Analysis & Recommendations

### Current Pipeline Strengths:
✅ **Hybrid Scoring:** Combines project depth, keyword matching, and semantic similarity  
✅ **Structured Parsing:** Comprehensive JD and resume extraction  
✅ **Error Handling:** Graceful degradation with 0 scores  
✅ **Caching:** Embedding cache reduces API costs  

### Critical Gaps:

#### 🔴 Gap 1: HR Notes Not Used for Filtering
**Problem:** HR notes contain valuable filtering criteria (e.g., "requires 5+ years Gen AI experience") but are completely ignored.

**Impact:** Candidates who don't meet inferred requirements may still rank high.

#### 🔴 Gap 2: No Hard Filters
**Problem:** No mechanism to automatically exclude candidates who fail critical requirements.

**Impact:** All candidates are ranked, even those clearly unqualified.

#### 🟡 Gap 3: HR Notes Not Parsed from domain_tags
**Problem:** HR notes are embedded in `domain_tags` as strings but never extracted/parsed in ranking modules.

**Impact:** Even if we wanted to use them, they're not accessible in a structured format.

---

## 🚀 Recommended Improvements to Use HR Notes for Filtering

### **Improvement 1: Extract HR Notes in Ranking Modules**

**Location:** `ResumeProcessor/KeywordComparitor.py` or create new `ResumeProcessor/HRFilter.py`

**Action:**
1. Parse `HR_NOTE:` tags from JD's `domain_tags`
2. Extract structured data: category, type, impact, note
3. Parse `inferred_requirement` type notes to extract criteria (years, skills, etc.)

**Example Code:**
```python
def extract_hr_notes(jd: dict) -> list:
    """Extract and parse HR notes from domain_tags."""
    hr_notes = []
    for tag in jd.get("domain_tags", []):
        if tag.startswith("HR_NOTE:"):
            # Parse: HR_NOTE:cat=clarity;type=inferred_requirement;impact=0.8;note=...
            parts = tag[8:].split(";")
            note_data = {}
            for part in parts:
                if "=" in part:
                    key, value = part.split("=", 1)
                    note_data[key] = value
            hr_notes.append(note_data)
    return hr_notes
```

---

### **Improvement 2: Create HR Filter Module**

**New File:** `ResumeProcessor/HRFilter.py`

**Functionality:**
1. **Parse HR Notes:** Extract requirements from `inferred_requirement` type notes
2. **Check Resume Compliance:** 
   - Years of experience requirements
   - Specific skill requirements mentioned in HR notes
   - Education/certification requirements
3. **Calculate HR Compliance Score:**
   - For each HR note of type `inferred_requirement`, check if resume meets criteria
   - Weight by `impact` value (0-1)
   - Return compliance score (0-1) and list of failed requirements

**Example Logic:**
```python
def check_hr_compliance(resume: dict, hr_notes: list) -> dict:
    """
    Check resume against HR note requirements.
    Returns: {
        "hr_compliance_score": 0.85,
        "passed_requirements": [...],
        "failed_requirements": [...],
        "should_filter": False  # True if critical requirement failed
    }
    """
    # Parse requirements from HR notes
    # Check resume against each requirement
    # Calculate weighted compliance score
    # Identify critical failures
```

---

### **Improvement 3: Integrate HR Filter into Final Ranking**

**Location:** `ResumeProcessor/Ranker/FinalRanking.py`

**Changes:**
1. Load HR notes from JD.json
2. Run HR compliance check for each candidate
3. **Filter Logic:**
   - If `should_filter = True` → Move to `Skipped.json` with reason
   - If `hr_compliance_score < threshold` (e.g., 0.3) → Apply penalty or filter
4. **Scoring Integration:**
   - Add `HR_Compliance_Score` as 4th scoring dimension
   - Update weights: Project (30%), Semantic (30%), Keyword (25%), HR Compliance (15%)
   - Or use HR compliance as multiplier: `Final_Score = base_score * hr_compliance_multiplier`

---

### **Improvement 4: Parse Requirements from HR Notes**

**Challenge:** HR notes are free-form text (e.g., "Define the expected years of experience for advanced Gen AI solutions")

**Solution:** Use GPT to parse requirements from HR notes into structured format:

```python
def parse_hr_requirements(hr_notes: list) -> dict:
    """
    Parse HR notes to extract structured requirements.
    Returns: {
        "min_years_experience": {"gen_ai": 5, "langchain": 3},
        "required_skills": ["Lang chain", "Vector Database"],
        "education_requirements": [...],
        "critical_filters": [...]  # Must-pass requirements
    }
    """
    # Use GPT to parse free-form HR notes into structured requirements
    # Or use regex/NLP to extract numbers, skills, etc.
```

---

### **Improvement 5: Add HR Filter to KeywordComparitor**

**Location:** `ResumeProcessor/KeywordComparitor.py`

**Changes:**
1. Load HR notes in `main()`
2. Extract requirements from HR notes
3. Add HR compliance check to scoring:
   ```python
   hr_score = check_hr_compliance(resume, hr_notes)
   # Add to final keyword score or use as multiplier
   final = base_keyword_score * (0.7 + 0.3 * hr_score["hr_compliance_score"])
   ```

---

## 📋 Implementation Priority

### **Phase 1: Critical (Do First)**
1. ✅ Fix model name in `GptJson.py` (`gpt-4.1-nano` → `gpt-4o-mini`)
2. 🔴 Create `HRFilter.py` module to extract and check HR notes
3. 🔴 Integrate HR filter into `FinalRanking.py` to filter non-compliant candidates

### **Phase 2: Important (Do Next)**
4. 🟡 Add HR compliance score as 4th dimension in final ranking
5. 🟡 Parse structured requirements from HR notes (use GPT or regex)
6. 🟡 Add HR compliance to `KeywordComparitor.py` scoring

### **Phase 3: Enhancement (Nice to Have)**
7. 🟢 Add HR note explanations to ranking output (why candidate passed/failed)
8. 🟢 Allow HR to configure filter thresholds in UI
9. 🟢 Add HR note compliance report in Streamlit UI

---

## 🎯 Expected Impact

**After implementing HR note filtering:**
- ✅ Candidates failing critical requirements automatically excluded
- ✅ Better alignment with JD's inferred requirements
- ✅ More accurate rankings based on complete JD understanding
- ✅ Reduced manual screening time for HR team
- ✅ Transparent filtering with explanations

**Current State:** HR notes are extracted and stored in JD.json and domain_tags. Filter requirements from HR input are actively used in EarlyFilter.py for filtering candidates. LLM re-ranking in FinalRanking.py uses filter requirements for better alignment.

**Note:** The system now uses explicit filter requirements (from HR input) rather than inferred HR notes for filtering. This provides more direct control over filtering criteria.

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────┐
│         Streamlit UI (main.py)          │
│  - JD Upload & Processing               │
│  - Resume Upload & Processing           │
│  - Rankings Display                     │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┴──────────┐
    │                     │
┌───▼────────┐    ┌───────▼────────┐
│ JD Parser  │    │ Resume Parser  │
│ (JDGpt.py) │    │ (GptJson.py)   │
└───┬────────┘    └───────┬────────┘
    │                     │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │   Early Filtering   │
    │  (EarlyFilter.py)   │
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │   Scoring Layer     │
    │  - ProjectProcess   │
    │  - KeywordComparitor│
    │  - SemanticComparitor│
    └──────────┬──────────┘
               │
    ┌──────────▼──────────┐
    │   Final Ranking     │
    │  (FinalRanking.py)  │
    └─────────────────────┘
```

### Technology Stack

| Component | Technology |
|-----------|-----------|
| **UI Framework** | Streamlit 1.51.0 |
| **LLM** | OpenAI GPT-4o-mini (function calling) |
| **Embeddings** | OpenAI text-embedding-3-small |
| **PDF Processing** | PyMuPDF 1.26.4, PyPDF2 3.0.1 |
| **Data Validation** | Pydantic 2.11.7 |
| **Retry Logic** | Tenacity 8.2.3 |
| **Data Processing** | Pandas 2.3.2, NumPy 2.3.2 |
| **Orchestration** | runpy (in-process execution) |

---

## Configuration & Setup

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- OpenAI API key (get from https://platform.openai.com/api-keys)

### Step 1: Create Virtual Environment

**On Windows (PowerShell)**:
```powershell
# Navigate to project directory
cd D:\Kreeda_Hiring_BOT

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

**On Windows (Command Prompt)**:
```cmd
# Navigate to project directory
cd D:\Kreeda_Hiring_BOT

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate.bat
```

**On Linux/Mac**:
```bash
# Navigate to project directory
cd /path/to/Kreeda_Hiring_BOT

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### Step 2: Install Dependencies

After activating the virtual environment, install all required packages:

```bash
pip install -r requirements.txt
```

**Note**: If you encounter any issues with specific packages, you may need to upgrade pip first:
```bash
pip install --upgrade pip
```

**Key Dependencies**:
- `streamlit==1.51.0`
- `openai==1.106.1`
- `pydantic==2.11.7`
- `tenacity==8.2.3` (retry logic)
- `pandas==2.3.2`
- `numpy==2.3.2`
- `PyMuPDF==1.26.4`
- `PyPDF2==3.0.1`

### Step 3: Set Up Environment Variables

**Create .env file**:

Create a `.env` file in the root directory with the following content:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

**Important**: 
- Replace `your_openai_api_key_here` with your actual OpenAI API key
- You can get an API key from: https://platform.openai.com/api-keys
- **Never commit the .env file to version control** (it should be in .gitignore)

**Alternative: Set Environment Variable Directly**

**Windows (PowerShell)**:
```powershell
$env:OPENAI_API_KEY="your_openai_api_key_here"
```

**Windows (Command Prompt)**:
```cmd
set OPENAI_API_KEY=your_openai_api_key_here
```

**Linux/Mac**:
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
```

**For Streamlit Cloud Deployment**:
1. Go to your app → Manage App → Settings → Secrets
2. Add:
   ```toml
   OPENAI_API_KEY = "your_openai_api_key_here"
   ```

### Step 4: Verify Setup

1. **Check Python version**:
   ```bash
   python --version
   ```
   Should be 3.10 or higher.

2. **Verify packages are installed**:
   ```bash
   pip list
   ```
   You should see packages like `streamlit`, `openai`, `pandas`, etc.

3. **Test OpenAI API key**:
   ```bash
   python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('API Key set:', 'Yes' if os.getenv('OPENAI_API_KEY') else 'No')"
   ```

### Step 5: Run the Application

**Development**:
```bash
streamlit run main.py
```

The application will open in your default web browser, typically at `http://localhost:8501`

**Individual Modules**:
```bash
# JD Processing
python "InputThread/AI Processing/JDGpt.py"

# Resume Processing (Sequential)
python "InputThread/AI Processing/GptJson.py"

# Resume Processing (Parallel)
python "InputThread/AI Processing/GptJson.py" --parallel --workers 5
```

### Environment Variables Summary

| Variable | Description | Required | Source |
|----------|-------------|----------|--------|
| `OPENAI_API_KEY` | Your OpenAI API key for GPT models and embeddings | **Yes** | https://platform.openai.com/api-keys |

### Troubleshooting

**Issue: "Module not found" errors**
- **Solution**: Make sure your virtual environment is activated and all dependencies are installed:
  ```bash
  pip install -r requirements.txt
  ```

**Issue: "OPENAI_API_KEY not found"**
- **Solution**: 
  - Check that your `.env` file exists in the root directory
  - Verify the key is correctly set (no extra spaces or quotes)
  - For Streamlit Cloud, configure secrets in the UI

**Issue: PDF extraction errors**
- **Solution**: Make sure PyMuPDF and PyPDF2 are properly installed. Try reinstalling:
  ```bash
  pip install --upgrade PyMuPDF PyPDF2
  ```

**Issue: Cache directory creation errors**
- **Solution**: Ensure write permissions in the project directory. The `.cache/` directory is created automatically.

### Project Structure Notes

The application creates several output directories automatically:
- `Processed-TXT/` - Extracted resume text
- `ProcessedJson/` - Structured resume JSON
- `Ranking/` - Final ranking results
- `InputThread/JD/` - Job description files
- `.cache/` - Cache directory (jd/, resumes/, scores/)

Log files are created for debugging:
- `processing_errors.log` - General processing errors
- `processing_errors.log1` - Resume processing errors

---

## Development Guidelines

### Code Style

- Follow PEP 8 Python style guide
- Use type hints where possible
- Document functions with docstrings
- Keep functions focused and modular

### Error Handling

- Use try-except blocks for external operations
- Log errors to appropriate log files
- Graceful degradation (assign 0 scores, continue)
- User-friendly error messages in UI

### Testing

- Test individual modules independently
- Test with various resume formats
- Test error scenarios
- Verify caching behavior

### Performance Optimization

- Use caching for expensive operations
- Parallel processing for batch operations
- Optimize prompts to reduce tokens
- Minimize redundant file I/O

### Adding New Features

1. **New Scoring Module**:
   - Create in `ResumeProcessor/`
   - Update `Ranking/Scores.json`
   - Integrate into `FinalRanking.py`
   - Add to pipeline in `main.py`

2. **New Filter**:
   - Add to `EarlyFilter.py`
   - Update filter requirements schema
   - Test with various criteria

3. **New Utility**:
   - Add to `utils/` package
   - Document in this guide
   - Use shared utilities to avoid duplication

---

## Shared Utilities (`utils/` Package) - Detailed

### `utils/validation.py`

**Purpose**: Data validation using Pydantic schemas.

**Key Functions**:
- `validate_resume(data, file_path)`: Validates resume JSON
- `validate_jd(data, file_path)`: Validates JD JSON
- `validate_resume_file(file_path)`: Validates resume file
- `validate_jd_file(file_path)`: Validates JD file

**Schemas**:
- `ResumeSchema`: Complete resume validation
- `JDSchema`: Complete JD validation
- Nested schemas for projects, skills, experience, etc.

**Usage**:
```python
from utils.validation import validate_resume

result = validate_resume(resume_data, "resume.json")
if result["valid"]:
    # Process resume
    pass
else:
    # Handle validation errors
    print(result["errors"])
```

### `utils/retry.py`

**Purpose**: Retry logic and circuit breakers.

**Key Functions**:
- `retry_api_call()`: Decorator for API retries
- `retry_file_operation()`: Decorator for file retries
- `CircuitBreaker`: Circuit breaker class
- `openai_circuit_breaker`: Global circuit breaker instance

**Usage**:
```python
from utils.retry import retry_api_call

@retry_api_call(max_attempts=3, initial_wait=1.0, max_wait=10.0)
def call_api():
    # API call with automatic retry
    pass
```

### `utils/cache.py`

**Purpose**: File-based caching utilities.

**Key Functions**:
- `FileCache`: Cache class with hash-based keys
- `resume_cache`: Global cache for resumes
- `jd_cache`: Global cache for JD
- `get_resume_cache_key()`: Generate cache key from file
- `get_jd_cache_key()`: Generate cache key from file

**Usage**:
```python
from utils.cache import resume_cache, get_resume_cache_key

cache_key = get_resume_cache_key("resume.txt")
cached = resume_cache.get(cache_key)
if cached:
    return cached
result = compute()
resume_cache.set(cache_key, result)
```

### `utils/common.py`

**Purpose**: Shared utility functions.

**Key Functions**:
- `extract_function_call(response)`: Extract OpenAI function call
- `safe_json_load(file_path, default)`: Safe JSON loading
- `safe_json_save(data, file_path)`: Safe JSON saving
- `extract_jd_skills_from_domain_tags()`: Extract skills from tags
- `canonicalize_string_list()`: Normalize string lists
- `canonicalize_skills_block()`: Normalize skills blocks

---

## Data Structures

### JD JSON Structure

```json
{
  "role_title": "AI & Machine Learning Engineer",
  "seniority_level": "Mid",
  "domain_tags": ["AIML", "REQ_SKILL:Machine Learning", ...],
  "required_skills": ["Machine Learning", "Python"],
  "preferred_skills": ["Deep Learning"],
  "filter_requirements": {
    "structured": {
      "experience": {"min": 1, "max": 2},
      "hard_skills": ["RAG", "ML"],
      "other_criteria": ["1-2 years of experience"]
    }
  },
  "keywords_flat": [...],
  "keywords_weighted": {...},
  "hr_notes": [...],
  "hr_points": 3
}
```

### Resume JSON Structure

```json
{
  "candidate_id": "john_doe_abc123",
  "name": "John Doe",
  "years_experience": 3.5,
  "canonical_skills": {
    "programming": ["Python"],
    "ml_ai": ["Machine Learning"]
  },
  "projects": [{
    "name": "Project Name",
    "metrics": {
      "difficulty": 0.8,
      "technical_depth": 0.9,
      ...
    }
  }],
  "experience_entries": [...],
  "ats_boost_line": "python, machine learning, ..."
}
```

### Scores JSON Structure

```json
{
  "candidates": [{
    "name": "John Doe",
    "candidate_id": "john_doe_abc123",
    "project_aggregate": 0.75,
    "Keyword_Score": 0.82,
    "Semantic_Score": 0.68
  }]
}
```

---

## Performance Characteristics

### Processing Times (Estimated)

| Operation | Time | Notes |
|-----------|------|-------|
| JD Processing | 5-10 sec | First run |
| JD Processing (cached) | <1 sec | Subsequent runs |
| Resume Processing (1, sequential) | 10-15 sec | Per resume |
| Resume Processing (20, sequential) | 5-7 min | Total |
| Resume Processing (20, parallel) | 1-2 min | 3-4x faster |
| Resume Processing (20, cached) | 10-30 sec | All cached |
| Filtering | 1-2 sec | Per batch |
| Scoring (all modules) | 5-10 sec | Per resume |
| Final Ranking | 5-10 sec | Total |

### Token Usage

- **JD Parsing**: ~350 tokens per JD (optimized)
- **Resume Parsing**: ~300 tokens per resume (optimized)
- **Embeddings**: ~800 tokens per resume (cached)
- **Total per resume**: ~1,100 tokens (first run), ~300 tokens (cached)

---

## Troubleshooting (Detailed)

### Common Issues

1. **Import Errors**:
   - Verify `utils/` package exists
   - Check Python path
   - Ensure all dependencies installed

2. **Cache Errors**:
   - Check write permissions
   - Verify `.cache/` directory can be created
   - Clear cache if corrupted

3. **API Errors**:
   - Check API key is set
   - Verify API quota/rate limits
   - Retry logic should handle transient failures

4. **Validation Errors**:
   - Check data format matches schemas
   - Review validation error messages
   - Validation warnings don't stop pipeline

5. **Parallel Processing Issues**:
   - Verify environment variables set
   - Check worker count (default: 5)
   - Test with sequential mode first

---

## Future Enhancements

### Potential Improvements

1. **Database Integration**: Replace file-based storage with PostgreSQL
2. **REST API**: Add FastAPI backend for programmatic access
3. **Enhanced Logging**: Structured logging with metrics
4. **Unit Tests**: Comprehensive test coverage
5. **CI/CD Pipeline**: Automated testing and deployment
6. **Monitoring**: Prometheus metrics and Grafana dashboards

---

## Contact & Support

For technical questions or issues, refer to:
- Code comments and docstrings
- This codebase summary
- Log files: `processing_errors.log`, `processing_errors.log1`

---

**Last Updated**: 2025-01-XX  
**Version**: 2.0 (with High Priority improvements)


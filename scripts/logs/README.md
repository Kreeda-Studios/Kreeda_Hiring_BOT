# Scoring Input Data Logs

This directory contains detailed logs of input data for the three main scoring functions:

## Log Types

### 1. Keyword Scorer Input Logs (`keyword_scorer_input_*.json`)
**Function**: `calculate_keyword_scores()` in `e_keyword_scorer.py`

**Logged Resume Data**:
- Candidate name and email
- Skills arrays (skills, canonical_skills, inferred_skills, skill_proficiency)
- Experience count and full experience data
- Project count and full project data
- Keywords extracted (keywords_flat)

**Logged JD Data**:
- Job title and ID
- Required skills and preferred skills
- Tools/tech and soft skills
- Weighted keywords with weights
- Job domain and role type
- Custom weighting configuration

**Purpose**: Debug keyword matching issues, verify skill extraction, check category weights

---

### 2. Semantic Scorer Input Logs (`semantic_scorer_input_*.json`)
**Function**: `calculate_semantic_scores()` in `f_semantic_scorer.py`

**Logged Resume Embeddings**:
- Shape and dtype of each section embedding (profile, skills, projects, responsibilities, education, overall)
- Data availability status
- Sample values (first 5 elements) for verification

**Logged JD Embeddings**:
- Structure (1D vs 2D arrays)
- Embedding dimensions
- Sample values for verification
- Available embedding keys

**Purpose**: Debug embedding mismatches, verify numpy array shapes, check data flow from embedding generation

---

### 3. Project Scorer Input Logs (`project_scorer_input_*.json`)
**Function**: `calculate_project_scores()` in `g_project_scorer.py`

**Logged Resume Projects**:
- Project name, description, and role
- Technologies, tech_keywords, primary_skills
- GitHub URL and live URL
- Duration

**Logged JD Data**:
- Job title and ID
- Required/preferred skills
- Tools and technologies
- Job domain and role type
- Responsibilities

**Purpose**: Debug project relevance scoring, verify technology matching, check domain alignment

---

## Log File Naming Convention

Format: `{scorer_type}_input_{timestamp}.json`
- Timestamp: `YYYYMMDD_HHMMSS_microseconds`
- Example: `keyword_scorer_input_20260206_143025_123456.json`

## Usage

Logs are automatically generated when the main calculation functions are called. Each log includes:
- Timestamp of when the function was invoked
- Complete input data structure
- Metadata for easy debugging

## Notes

- Semantic scorer logs include embedding shapes but not full vectors to save space
- All logs are in JSON format for easy parsing
- Console output shows the log file path: `[LOG] Input data logged to: {path}`
- Logs help identify data quality issues before scoring calculations

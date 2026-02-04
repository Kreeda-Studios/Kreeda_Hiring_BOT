# 📊 Old Code Scoring System - Complete Analysis

## 🔄 Processing Pipeline Overview

```
Resume TXT → AI Parser → Scoring (5 types) → Final Ranking → LLM Re-ranking
```

---

## 1️⃣ AI PARSER (OpenAI GPT-4o-mini) - Resume Processing

### 📍 Location: `Old_Code_Archive/InputThread/AI Processing/GptJson.py`

### 🎯 What Fields OpenAI Returns:

#### **Core Identity:**
- `candidate_id` (string)
- `name` (string)
- `role_claim` (string) - What role candidate claims
- `years_experience` (number)
- `location` (string)
- `contact` (object): email, phone, profile

#### **Domain & Skills:**
- `domain_tags` (array): High-level areas (AIML, Fullstack, Testing, DB, Cloud, Solution Arch, Sales)
- `profile_keywords_line` (string): Single-line skill summary
- **`canonical_skills`** (object) - Structured skills by category:
  ```json
  {
    "programming": ["Python", "JavaScript"],
    "ml_ai": ["TensorFlow", "PyTorch"],
    "frontend": ["React", "Vue"],
    "backend": ["Django", "Flask"],
    "testing": ["Pytest", "Jest"],
    "databases": ["PostgreSQL", "MongoDB"],
    "cloud": ["AWS", "GCP"],
    "infra": ["Docker", "Kubernetes"],
    "devtools": ["Git", "Jenkins"],
    "methodologies": ["Agile", "Scrum"]
  }
  ```
- **`inferred_skills`** (array of objects):
  ```json
  {
    "skill": "Machine Learning",
    "confidence": 0.85,
    "provenance": ["Mentioned in project X", "Used in company Y"]
  }
  ```
- **`skill_proficiency`** (array):
  ```json
  {
    "skill": "Python",
    "level": "expert",
    "years_last_used": 2,
    "provenance": ["5 years in Company X"]
  }
  ```

#### **Projects (with 7 metrics):**
- **`projects`** (array of objects):
  ```json
  {
    "name": "AI Chatbot",
    "duration_start": "2022-01",
    "duration_end": "2023-06",
    "role": "Lead Developer",
    "domain": "AIML",
    "tech_keywords": ["Python", "TensorFlow", "Flask"],
    "approach": "Built transformer-based model with 95% accuracy",
    "impact_metrics": {"users": 50000, "revenue_increase": "30%"},
    "primary_skills": ["Python", "ML", "NLP"],
    "metrics": {
      "difficulty": 0.85,         // 0-1 scale
      "novelty": 0.75,           // 0-1 scale
      "skill_relevance": 0.90,   // 0-1 scale
      "complexity": 0.80,        // 0-1 scale
      "technical_depth": 0.85,   // 0-1 scale
      "domain_relevance": 0.95,  // 0-1 scale
      "execution_quality": 0.90  // 0-1 scale
    }
  }
  ```

#### **Experience:**
- **`experience_entries`** (array):
  ```json
  {
    "company": "Tech Corp",
    "title": "Senior Engineer",
    "duration": "2020-2023",
    "primary_tech": ["Python", "AWS"],
    "responsibilities_keywords": ["Led team", "Architected system"],
    "achievements": ["Reduced latency by 40%"]
  }
  ```

#### **Education & Other:**
- `education` (array of strings/objects)
- `certifications` (array)
- `ats_boost_line` (string) - Keywords for ATS optimization
- **`embedding_hints`** (object):
  ```json
  {
    "profile_embed": "Senior Python dev with ML expertise",
    "projects_embed": "Built scalable AI systems with TensorFlow",
    "skills_embed": "Python, ML, AWS, Docker",
    "experience_embed": "5 years in AIML, 3 years cloud"
  }
  ```

---

## 2️⃣ EMBEDDINGS GENERATION

### 📍 Location: `Old_Code_Archive/ResumeProcessor/SemanticComparitor.py`

### 🔧 Model Used:
- **OpenAI**: `text-embedding-3-small`
- **Dimensions**: 1536
- **Batch Size**: 256 texts per API call

### 📦 What Embeddings Are Created:

#### For **RESUME**, 6 section embeddings:
1. **`profile`** embeddings (from profile_keywords_line)
2. **`skills`** embeddings (from canonical_skills + inferred_skills with confidence ≥ 0.6)
3. **`projects`** embeddings (from project names + approaches + tech_keywords)
4. **`responsibilities`** embeddings (from experience achievements + primary_tech)
5. **`education`** embeddings (from education entries + certifications)
6. **`overall`** embeddings (combined from profile + projects + experience)

#### For **JD**, 6 section embeddings:
1. **`profile`** (from role_title)
2. **`skills`** (from required_skills + preferred_skills)
3. **`projects`** (from embedding_hints.projects_embed)
4. **`responsibilities`** (from responsibilities array)
5. **`education`** (from certifications_required + education_requirements)
6. **`overall`** (from embedding_hints.overall_embed)

### 🎯 Important: `embedding_hints` Field

**Required in JD JSON for semantic scoring:**
```json
{
  "embedding_hints": {
    "overall_embed": "Senior ML Engineer role building production AI systems...",
    "projects_embed": "Experience with TensorFlow, PyTorch, deploying models to production..."
  }
}
```

❌ **Current Implementation Missing**: Our new JD processor does NOT generate `embedding_hints`!

---

## 3️⃣ SCORE CALCULATIONS

---

### 🎯 **SCORE 1: PROJECT SCORE** (project_aggregate)

#### 📍 Location: `Old_Code_Archive/ResumeProcessor/ProjectProcess.py`

#### 🧮 Formula:
```python
# Weighted average of 7 project metrics
WEIGHTS = {
    "difficulty": 0.142857,        # 1/7
    "novelty": 0.142857,
    "skill_relevance": 0.142857,
    "complexity": 0.142857,
    "technical_depth": 0.142857,
    "domain_relevance": 0.142857,
    "execution_quality": 0.142857
}

# For each project:
project_score = sum(metric * weight for metric, weight in WEIGHTS.items())

# Final aggregate:
project_aggregate = average(all_project_scores)
```

#### 📊 Output Range: 0.0 - 1.0

#### 🔍 What It Measures:
- Quality and relevance of candidate's projects
- Technical depth and execution quality
- Domain alignment with JD

---

### 🎯 **SCORE 2: KEYWORD SCORE** (Keyword_Score)

#### 📍 Location: `Old_Code_Archive/ResumeProcessor/KeywordComparitor.py`

#### 🧮 Formula:
```python
DEFAULT_WEIGHTS = {
    "required_skills": 0.18,      # Must-have skills
    "preferred_skills": 0.08,     # Nice-to-have skills
    "weighted_keywords": 0.15,    # JD's weighted keywords
    "experience_keywords": 0.25,  # Action verbs (led, built, etc.)
    "domain_relevance": 0.10,     # Domain tags match
    "technical_depth": 0.10,      # Technical complexity
    "project_metrics": 0.09,      # Project quality
    "responsibilities": 0.03,     # Responsibilities match
    "education": 0.02             # Education/certifications
}

# Calculate each component:
req = score_overlap(jd.required_skills, resume_tokens)
pref = score_overlap(jd.preferred_skills, resume_tokens)
weighted_kw = score_weighted_keywords(jd.keywords_weighted, resume_tokens)
exp = score_experience_keywords(resume)  # Checks for: led, managed, built, etc.
proj = score_project_metrics(resume)

# Final score:
Keyword_Score = (
    req * 0.18 +
    pref * 0.08 +
    weighted_kw * 0.15 +
    exp * 0.25 +
    domain * 0.10 +
    proj * 0.09 +
    resp * 0.03 +
    edu * 0.02
)

# Penalty for missing >50% required skills:
if req < 0.5:
    required_penalty = (0.5 - req) * 0.3  # Up to 15% penalty
    Keyword_Score -= required_penalty
```

#### 📊 Experience Keywords Weights:
```python
EXPERIENCE_KEYWORD_WEIGHTS = {
    "lead": 4.0, "led": 4.0,
    "manager": 4.0, "managed": 4.0,
    "architect": 4.0, "architected": 4.0,
    "designed": 3.6, "design": 3.6,
    "owned": 3.6, "built": 3.6,
    "scaled": 3.4, "scale": 3.4,
    "implemented": 3.2, "deployed": 3.2,
    "optimized": 3.2, "productionized": 3.6,
    "mentored": 2.8, "improved": 3.0
}
```

#### 📊 Output Range: 0.0 - 1.0 (normalized across all candidates)

#### 🔍 What It Measures:
- Exact keyword matches with JD
- Experience depth (leadership verbs)
- Domain alignment
- Technical breadth

---

### 🎯 **SCORE 3: SEMANTIC SCORE** (Semantic_Score)

#### 📍 Location: `Old_Code_Archive/ResumeProcessor/SemanticComparitor.py`

#### 🧮 Formula:
```python
# Step 1: Generate embeddings for 6 sections (JD and Resume)
jd_embeddings = {
    "profile": embed_texts(jd.profile_sections),
    "skills": embed_texts(jd.skills_sections),
    "projects": embed_texts(jd.projects_sections),
    "responsibilities": embed_texts(jd.responsibilities_sections),
    "education": embed_texts(jd.education_sections),
    "overall": embed_texts(jd.overall_sections)
}

resume_embeddings = {
    # Same 6 sections for resume
}

# Step 2: Compute section scores (for each section)
def compute_section_score(jd_vectors, resume_vectors):
    # Cosine similarity matrix
    C = cosine_similarity(jd_vectors, resume_vectors)
    
    # Max similarity per JD sentence
    max_j = C.max(axis=1)
    
    # Coverage: % of JD sentences with similarity > TAU_COV (0.65)
    coverage = (max_j >= 0.65).mean()
    
    # Max similarity per resume sentence
    max_i = C.max(axis=0)
    
    # Resume alignment: % of resume sentences with similarity > TAU_RESUME (0.55)
    resume_alignment = (max_i >= 0.55).mean()
    
    # Average of top matches
    best = C.max()
    
    # Combine: 50% coverage + 40% alignment + 10% best match
    section_score = (
        0.5 * coverage +
        0.4 * resume_alignment +
        0.1 * best
    )
    
    return section_score

# Step 3: Weight sections
SECTION_WEIGHTS = {
    "skills": 0.30,
    "projects": 0.25,
    "responsibilities": 0.20,
    "profile": 0.10,
    "education": 0.05,
    "overall": 0.10
}

# Final semantic score
raw_score = sum(
    compute_section_score(jd_emb[section], resume_emb[section]) * weight
    for section, weight in SECTION_WEIGHTS.items()
)

# Normalize across all candidates (0-1 range)
Semantic_Score = (raw_score - min_score) / (max_score - min_score)
```

#### 📊 Output Range: 0.0 - 1.0

#### 🔍 What It Measures:
- Deep semantic similarity between JD and Resume
- Context understanding (not just keywords)
- Coverage: How much of JD is addressed
- Alignment: How relevant resume content is

---

### 🎯 **SCORE 4: FINAL SCORE** (Final_Score)

#### 📍 Location: `Old_Code_Archive/ResumeProcessor/Ranker/FinalRanking.py`

#### 🧮 Formula:
```python
WEIGHTS = {
    "project_aggregate": 0.35,
    "Semantic_Score": 0.35,
    "Keyword_Score": 0.30
}

# Calculate weighted average
Final_Score = (
    project_aggregate * 0.35 +
    Semantic_Score * 0.35 +
    Keyword_Score * 0.30
)

# Special case: If only 1 score available, apply decay penalty
ONE_SCORE_DECAY = 0.08
if only_one_score_available:
    Final_Score = max(single_score - 0.08, 0.0)
```

#### 📊 Output Range: 0.0 - 1.0

#### 🔍 What It Measures:
- Overall candidate quality
- Balanced mix of:
  - Project quality (35%)
  - Semantic match (35%)
  - Keyword match (30%)

---

### 🎯 **SCORE 5: LLM RE-RANKING SCORE** (re_rank_score)

#### 📍 Location: `Old_Code_Archive/ResumeProcessor/Ranker/FinalRanking.py`

#### 🧮 Process:
```python
# Model: gpt-4o-mini
# Batch size: 30 candidates
RE_RANK_BATCH_SIZE = 30

# For each batch of 30 candidates:
llm_re_rank_batch(
    candidates_summaries=[
        {
            "id": candidate_id,
            "n": name,
            "sc": {
                "p": project_aggregate,
                "k": Keyword_Score,
                "s": Semantic_Score,
                "f": Final_Score
            },
            "exp": years_experience,
            "loc": location,
            "sk": top_10_skills,
            "pj": top_3_projects,
            "compliance": {
                "experience": {"meets": True, "details": "..."},
                "hard_skills": {"meets": False, "details": "..."},
                # ... other requirements
            }
        }
    ],
    filter_requirements={
        "structured": {
            "experience": {"min": 5, "max": 10, "type": "numeric"},
            "hard_skills": {"required": ["Python", "ML"], "type": "list"},
            # ... dynamic requirements
        }
    }
)

# LLM analyzes:
# 1. All 4 scores (project, keyword, semantic, final)
# 2. Compliance with HR requirements
# 3. Resume quality and relevance
# 4. Nuances and context

# Returns:
{
    "candidate_id": "...",
    "re_rank_score": 0.87,  # 0-1 scale
    "meets_requirements": True,
    "requirements_met": ["experience", "hard_skills"],
    "requirements_missing": ["certifications"]
}
```

#### 📊 Output Range: 0.0 - 1.0

#### 🔍 What It Measures:
- **Human-like judgment** of candidate quality
- **Compliance validation** (corrects programmatic errors)
- **Contextual understanding** (synonyms, nuances)
- **Holistic assessment** of all factors

#### 🎯 LLM Function Calling Schema:
```python
RE_RANK_FUNCTION = {
    "name": "re_rank_candidates",
    "parameters": {
        "ranked_candidates": [
            {
                "candidate_id": "string",
                "re_rank_score": "number (0-1)",
                "meets_requirements": "boolean",
                "requirements_met": ["list of requirement types"],
                "requirements_missing": ["list of requirement types"]
            }
        ]
    }
}
```

---

## 📊 SCORING SUMMARY TABLE

| Score Type | Weight in Final | Range | Primary Focus | Generated By |
|-----------|----------------|-------|---------------|-------------|
| **Project Score** | 35% | 0-1 | Project quality, complexity, domain relevance | AI parser metrics |
| **Keyword Score** | 30% | 0-1 | Exact matches, experience verbs, technical breadth | Pattern matching |
| **Semantic Score** | 35% | 0-1 | Deep meaning, context, coverage, alignment | OpenAI embeddings |
| **Final Score** | - | 0-1 | Weighted average of above 3 | Calculation |
| **LLM Re-rank Score** | - | 0-1 | Human-like judgment + compliance validation | GPT-4o-mini |

---

## 🔄 COMPLETE WORKFLOW

```
1. Resume TXT
   ↓
2. OpenAI GPT-4o-mini (AI Parser)
   → Returns 50+ fields including:
     - canonical_skills (10 categories)
     - projects (with 7 metrics each)
     - inferred_skills (with confidence)
     - experience_entries
     - embedding_hints
   ↓
3. SCORING PHASE (Parallel)
   ├─ ProjectProcess.py
   │  └─ project_aggregate = avg(project metrics)
   │
   ├─ KeywordComparitor.py
   │  └─ Keyword_Score = weighted_sum(8 components)
   │
   └─ SemanticComparitor.py
      └─ Semantic_Score = weighted_sum(6 section similarities)
         - Generates embeddings (text-embedding-3-small, 1536 dims)
         - Cosine similarity matrices
         - Coverage + alignment scoring
   ↓
4. FinalRanking.py
   ├─ Final_Score = 0.35*project + 0.35*semantic + 0.30*keyword
   ├─ HR Compliance Checking (dynamic requirements)
   └─ LLM Re-ranking (GPT-4o-mini, batches of 30)
      - Validates compliance results
      - Provides human-like ranking
      - Corrects programmatic errors
   ↓
5. OUTPUT:
   - Final_Ranking.json (sorted by Final_Score)
   - DisplayRanks.txt (human-readable)
   - Skipped.json (filtered candidates)
```

---

## 🚨 CRITICAL FINDINGS FOR NEW IMPLEMENTATION

### ❌ **Missing in Current System:**

1. **`embedding_hints` field** in JD processing
   - Old semantic scorer DEPENDS on this
   - Need: `overall_embed` and `projects_embed` text hints
   - Current: NOT GENERATED

2. **Different embedding approach:**
   - Old: Generate embeddings **on-the-fly** during scoring
   - New: Pre-generate and **store** embeddings in DB
   - **Incompatible** without adapter layer

3. **7 Project Metrics:**
   - Old: AI parser generates all 7 metrics per project
   - New: Need to verify if AI parser generates same metrics

4. **Experience Keywords:**
   - Old: Heavy weight on leadership verbs (led, built, etc.)
   - New: Need to implement same scoring logic

5. **Section-based Semantic Scoring:**
   - Old: 6 sections with different weights
   - New: Pre-generated embeddings structure is different

---

## ✅ RECOMMENDATIONS

### For **Compatibility Mode** (use old scoring):
1. Add `embedding_hints` generation to JD processor
2. Keep pre-generated embeddings for efficiency
3. Convert to on-the-fly format when needed

### For **New Optimized Mode** (better approach):
1. Use pre-generated embeddings (faster)
2. Adapt semantic scoring to use stored vectors
3. Maintain 6-section structure but with pre-computed vectors
4. Keep same weights and formulas

### For **Resume Processing**:
1. Ensure AI parser generates all required fields
2. Especially: 7 project metrics, canonical_skills structure
3. Generate embedding_hints for compatibility

---

## 📈 SCORING WEIGHTS REFERENCE

```python
# Final Score Composition
FINAL_WEIGHTS = {
    "project_aggregate": 0.35,
    "Semantic_Score": 0.35,
    "Keyword_Score": 0.30
}

# Keyword Score Components
KEYWORD_WEIGHTS = {
    "required_skills": 0.18,
    "preferred_skills": 0.08,
    "weighted_keywords": 0.15,
    "experience_keywords": 0.25,
    "domain_relevance": 0.10,
    "technical_depth": 0.10,
    "project_metrics": 0.09,
    "responsibilities": 0.03,
    "education": 0.02
}

# Semantic Score Section Weights
SEMANTIC_WEIGHTS = {
    "skills": 0.30,
    "projects": 0.25,
    "responsibilities": 0.20,
    "profile": 0.10,
    "education": 0.05,
    "overall": 0.10
}

# Project Score (Equal weight to all 7 metrics)
PROJECT_WEIGHTS = {
    "difficulty": 0.142857,
    "novelty": 0.142857,
    "skill_relevance": 0.142857,
    "complexity": 0.142857,
    "technical_depth": 0.142857,
    "domain_relevance": 0.142857,
    "execution_quality": 0.142857
}
```

---

## 🎯 KEY TAKEAWAYS

1. **5 Scores Total:**
   - Project Score (from AI parser metrics)
   - Keyword Score (pattern matching + weights)
   - Semantic Score (OpenAI embeddings + cosine similarity)
   - Final Score (weighted average of above 3)
   - LLM Re-rank Score (GPT-4o-mini validation)

2. **Embeddings are CRITICAL:**
   - Model: text-embedding-3-small (1536 dims)
   - Structure: 6 sections for both JD and Resume
   - Depends on `embedding_hints` field in JD

3. **AI Parser Returns 50+ Fields:**
   - Including project metrics, canonical skills, inferred skills
   - All used in different scoring components

4. **Current Implementation Gaps:**
   - Missing embedding_hints generation
   - Different embedding storage approach
   - Need compatibility layer for old semantic scorer

---

**Document Created:** 2026-02-03  
**Analysis Based On:** Old_Code_Archive complete scoring system

# 🗄️ MongoDB Schema - Complete 3-Collection Architecture

**Purpose:** Store AI Parser Output + Pre-generated Embeddings + Score Results  
**Approach:** Same 5-score algorithms, optimized with pre-computed embeddings

**Architecture:**
- **resumes** collection: Resume data (reusable across multiple JDs)
- **jobs** collection: JD data + list of resume groups to process
- **score_results** collection: Scores linking job_id + resume_id (many-to-many)

**Date:** 2026-02-03

---

## 📦 1. RESUME COLLECTION

### Collection: `resumes`

**One resume can be scored against multiple jobs**

```json
{
  "_id": "ObjectId('...')",
  "candidate_id": "johnsmith_a4f3e8b1c9d2",
  "resume_group_id": "ObjectId('...')",  // Which group this resume belongs to
  
  // ===== FROM AI PARSER (OpenAI Output) =====
  "name": "John Smith",
  "email": "john.smith@email.com",
  "phone": "+1-234-567-8900",
  "location": "San Francisco, CA",
  "role_claim": "Senior Machine Learning Engineer",
  "years_experience": 6.5,
  
  "contact": {
    "email": "john.smith@email.com",
    "phone": "+1-234-567-8900",
    "profile": "https://linkedin.com/in/johnsmith"
  },
  
  "domain_tags": ["AIML", "Machine Learning", "Python"],
  
  "profile_keywords_line": "Senior ML Engineer | Python, TensorFlow, PyTorch | 6 years",
  "ats_boost_line": "Python / TensorFlow / AWS / Docker / ML",
  
  "canonical_skills": {
    "programming": ["Python", "Java", "SQL"],
    "ml_ai": ["TensorFlow", "PyTorch", "Scikit-learn"],
    "frontend": ["React"],
    "backend": ["FastAPI", "Django"],
    "testing": ["Pytest"],
    "databases": ["PostgreSQL", "MongoDB", "Redis"],
    "cloud": ["AWS"],
    "infra": ["Docker", "Kubernetes"],
    "devtools": ["Git"],
    "methodologies": ["Agile", "MLOps"]
  },
  
  "inferred_skills": [
    {
      "skill": "RAG",
      "confidence": 0.92,
      "provenance": ["Built RAG pipeline in Project X"]
    },
    {
      "skill": "LLM Fine-tuning",
      "confidence": 0.85,
      "provenance": ["Fine-tuned GPT-3.5"]
    }
  ],
  
  "skill_proficiency": [
    {
      "skill": "Python",
      "level": "expert",
      "years_last_used": 0
    },
    {
      "skill": "TensorFlow",
      "level": "advanced",
      "years_last_used": 0
    }
  ],
  
  "projects": [
    {
      "name": "AI-Powered Recommendation Engine",
      "duration_start": "2023-01",
      "duration_end": "2024-06",
      "role": "Lead ML Engineer",
      "domain": "AIML",
      "approach": "Implemented collaborative filtering with deep learning, deployed to production",
      "tech_keywords": ["Python", "TensorFlow", "AWS", "Docker"],
      "primary_skills": ["Machine Learning", "MLOps"],
      "impact_metrics": {"users_impacted": 5000000},
      
      // === 7 METRICS (for scoring) ===
      "metrics": {
        "difficulty": 0.85,
        "novelty": 0.75,
        "skill_relevance": 0.95,
        "complexity": 0.88,
        "technical_depth": 0.90,
        "domain_relevance": 0.95,
        "execution_quality": 0.92
      }
    },
    {
      "name": "RAG-based Knowledge Assistant",
      "duration_start": "2022-06",
      "duration_end": "2023-03",
      "role": "Senior ML Engineer",
      "domain": "AIML",
      "approach": "Semantic search with embeddings, fine-tuned GPT-3.5",
      "tech_keywords": ["Python", "OpenAI", "Pinecone", "FastAPI"],
      "primary_skills": ["LLM", "RAG"],
      "impact_metrics": {"accuracy": "92%"},
      
      "metrics": {
        "difficulty": 0.82,
        "novelty": 0.88,
        "skill_relevance": 0.90,
        "complexity": 0.85,
        "technical_depth": 0.87,
        "domain_relevance": 0.92,
        "execution_quality": 0.85
      }
    }
  ],
  
  "experience_entries": [
    {
      "company": "Tech Corp",
      "title": "Senior Machine Learning Engineer",
      "period_start": "2022-01",
      "period_end": "Present",
      "responsibilities_keywords": [
        "Led ML team",
        "Architected pipelines",
        "Built recommendation systems"
      ],
      "achievements": ["Increased model accuracy by 25%"],
      "primary_tech": ["Python", "TensorFlow", "AWS"]
    },
    {
      "company": "AI Startup",
      "title": "Machine Learning Engineer",
      "period_start": "2020-03",
      "period_end": "2021-12",
      "responsibilities_keywords": ["Developed NLP models", "Built pipelines"],
      "achievements": ["Built 5 production models"],
      "primary_tech": ["Python", "PyTorch"]
    }
  ],
  
  "education": [
    {
      "degree": "M.S.",
      "field": "Computer Science",
      "institution": "Stanford University",
      "year": "2020"
    },
    {
      "degree": "B.E.",
      "field": "Computer Engineering",
      "institution": "MIT",
      "year": "2018"
    }
  ],
  
  // ===== EMBEDDINGS (Pre-generated, used by semantic scorer) =====
  "embeddings": {
    "embedding_model": "text-embedding-3-small",
    "resume_embedding": [0.012, -0.045, 0.078, ...], // 1536 dims - full resume
    "profile_embedding": [0.023, -0.034, 0.056, ...], // 1536 dims
    "skills_embedding": [0.015, -0.028, 0.089, ...],
    "projects_embedding": [0.019, -0.041, 0.067, ...],
    "experience_embedding": [0.021, -0.038, 0.072, ...],
    "education_embedding": [0.018, -0.032, 0.061, ...]
  },
  
  // ===== EMBEDDING HINTS (Text snippets required by semantic scorer) =====
  // Semantic score algorithm extracts these texts and generates embeddings from them
  "embedding_hints": {
    "profile_embed": "Senior ML Engineer with 6 years experience. Python, TensorFlow, PyTorch.",
    "projects_embed": "Built recommendation engine, RAG system. Production ML on AWS.",
    "skills_embed": "Python, TensorFlow, AWS, Docker, RAG, LLM"
  },
  
  // ===== METADATA =====
  "title": "John Smith - ML Engineer Resume",
  "filename": "johnsmith_resume.pdf",
  "file_path": "uploads/resumes/johnsmith_resume.pdf",
  "candidate_name": "John Smith",
  "raw_text": "Full extracted text from PDF...",
  
  "extraction_status": "success",  // pending | success | failed
  "parsing_status": "success",
  "embedding_status": "success",
  
  "created_at": "2024-01-15T10:20:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

**Note:** No `job_id` or `scores` here - resumes are reusable across multiple jobs!

---

## 📋 2. JOB COLLECTION

### Collection: `jobs`

**JD data + list of resume groups to process**

```json
{
  "_id": "ObjectId('...')",
  
  // ===== USER INPUT =====
  "title": "Senior Machine Learning Engineer",
  "description": "We are looking for a Senior ML Engineer with 5+ years experience...",
  "company_name": "Tech Innovations Inc.",
  
  // ===== RESUME GROUPS TO PROCESS =====
  "resume_groups": [
    "ObjectId('resume_group_1')",
    "ObjectId('resume_group_2')"
  ],
  
  // ===== FROM AI PARSER =====
  "jd_analysis": {
    "role_title": "Senior Machine Learning Engineer",
    "seniority_level": "Senior",
    "domain_tags": ["AIML", "Machine Learning", "MLOps"],
    "years_experience_required": 5,
  
    "required_skills": ["Python", "TensorFlow", "Machine Learning", "AWS"],
    "preferred_skills": ["Kubernetes", "LLM", "RAG"],
    "tools_tech": ["Python", "TensorFlow", "PyTorch", "AWS", "Docker"],
    "soft_skills": ["Leadership", "Communication"],
    
    "canonical_skills": {
      "programming": ["Python"],
      "ml_ai": ["TensorFlow", "PyTorch", "Machine Learning"],
      "cloud": ["AWS"],
      "infra": ["Docker", "Kubernetes"],
      "devtools": ["Git"],
      "methodologies": ["MLOps"]
    },
    
    "responsibilities": [
      "Design production ML systems",
      "Lead model development",
      "Mentor engineers"
    ],
    
    "keywords_flat": ["python", "tensorflow", "machine learning", "aws", "docker"],
    "keywords_weighted": {
      "python": 1.0,
      "tensorflow": 0.95,
      "machine learning": 1.0,
      "aws": 0.9,
      "mlops": 0.85
    },
    
    "weighting": {
      "required_skills": 0.18,
      "preferred_skills": 0.08,
      "experience_keywords": 0.25,
      "keywords_weighted": 0.15,
      "project_metrics": 0.09
    },
    
    // ===== EMBEDDINGS (Pre-generated for semantic scorer) =====
    "embeddings": {
      "embedding_model": "text-embedding-3-small",
      "jd_embedding": [0.018, -0.042, 0.065, ...], // 1536 dims
      "skills_embedding": [0.022, -0.038, 0.071, ...],
      "responsibilities_embedding": [0.019, -0.040, 0.068, ...]
    },
    
    // ===== EMBEDDING HINTS (Text for semantic scorer algorithm) =====
    // Semantic scorer uses these texts to compute cosine similarity
    "embedding_hints": {
      "overall_embed": "Senior ML Engineer, 5+ years. TensorFlow/PyTorch. Production ML on AWS.",
      "projects_embed": "Scalable ML systems, Docker/Kubernetes deployment, MLOps pipelines.",
      "skills_embed": "Python, TensorFlow, PyTorch, ML, AWS, Docker"
    }
  },
  
  // ===== FILTER REQUIREMENTS (from HR UI - parsed by JDGpt.py) =====
  "filter_requirements": {
    "raw_prompt": "Must have 5+ years Python and ML. IT field only. Not Mechanical/Chemical. Preferred: Kubernetes, LLM/RAG projects",
    "structured": {
      "experience": {
        "min": 5,
        "max": null,
        "field": "Machine Learning",
        "specified": true
      },
      "hard_skills": ["Python", "Machine Learning", "TensorFlow"],
      "preferred_skills": ["Kubernetes", "LLM", "RAG"],
      "department": {
        "category": "IT",  // "IT" | "Non-IT" | "Specific"
        "allowed_departments": ["CS", "CE", "IT", "AIDS", "ENTC"],
        "excluded_departments": ["Mechanical", "Chemical"],
        "specified": true
      },
      "location": null,  // null = not specified, "Any" = flexible, "Mumbai" = specific
      "education": [],  // e.g., ["Bachelors", "Masters"]
      "other_criteria": []  // Any other requirements in natural language
    },
    "re_ranking_instructions": "Prioritize candidates with production ML experience"
  },
  
  // ===== HR INSIGHTS & EXPLAINABILITY =====
  "hr_points": 3,  // Count of recommendations/inferred requirements
  "hr_notes": [
    {
      "category": "clarity",  // compensation | clarity | security | compliance
      "type": "recommendation",  // recommendation | inferred_requirement
      "note": "Consider specifying TensorFlow version",
      "impact": 0.6,  // 0-1 impact on hiring quality
      "reason": "Version specificity helps candidate matching",
      "source_provenance": ["TensorFlow mentioned at line 45"]
    }
  ],
  
  "explainability": {
    "top_jd_sentences": [
      "Design and deploy ML models in production",
      "5+ years experience with Python and ML frameworks"
    ],
    "key_phrases": ["production ML", "deep learning", "model deployment"],
    "rationales": ["Focus on production experience over research"]
  },
  
  "provenance_spans": [
    {
      "type": "skill",  // skill | responsibility | exclusion
      "text": "TensorFlow"
    },
    {
      "type": "responsibility",
      "text": "Deploy ML models to production"
    }
  ],
  
  // ===== METADATA =====
  "jd_file_path": "uploads/jds/ml_engineer_jd.pdf",
  "jd_pdf_filename": "ml_engineer_jd.pdf",
  "jd_text": "Full JD text...",
  
  "status": "active",  // draft | active | completed | archived
  "locked": false,     // true = no edits after processing starts
  
  "meta": {
    "jd_version": "1.0",
    "raw_text_length": 8500,
    "sections_detected": ["skills", "responsibilities", "requirements"]
  },
  
  "created_at": "2024-01-10T14:00:00Z",
  "updated_at": "2024-01-10T14:20:00Z"
}
```

---
---

## 🔗 5. RELATIONSHIPS & DATA FLOW

```
┌─────────────────┐
│  resume_groups  │
│  - name         │
│  - source       │
└────────┬────────┘
         │ has many
         ▼
┌─────────────────┐       ┌──────────────────┐
│    resumes      │       │      jobs        │
│  - resume_      │       │  - title         │
│    group_id     │       │  - jd_analysis   │
│  - parsed_      │       │  - embeddings    │
│    content      │       │  - resume_groups │
│  - embeddings   │       │    [] (to process)│
└────────┬────────┘       └────────┬─────────┘
         │                         │
         │         scored          │
         └────────against──────────┘
                   │
                   ▼
         ┌─────────────────┐
         │ score_results   │
         │  - job_id       │
         │  - resume_id    │
         │  - 5 scores     │
         │  - rank         │
         └─────────────────┘
```

### Flow:
1. **Upload resumes** → Create `resume_group` → Create `resumes` with `resume_group_id`
2. **Create job** → Parse JD → Store in `jobs` with list of `resume_groups` to process
3. **Score resumes** → For each resume in resume_groups, compute 5 scores → Store in `score_results`
4. **View results** → Query `score_results` by `job_id`, join with `resumes` data

---

## 🎯 6
## 🎯 3. SCORE_RESULTS COLLECTION

### Collection: `score_results`

**Many-to-many: One resume can be scored against many jobs**

```json
{
  "_id": "ObjectId('...')",
  
  // ===== REFERENCES =====
  "job_id": "ObjectId('...')",      // Which job
  "resume_id": "ObjectId('...')",   // Which resume
  
  // ===== 5 SCORES (0-100 scale) =====
  "project_score": 85.5,           // Score 1: Project aggregate
  "keyword_score": 78.3,           // Score 2: Keyword matching
  "semantic_score": 82.7,          // Score 3: Semantic similarity
  "final_score": 82.1,             // Score 4: Weighted combination (35% project + 35% semantic + 30% keyword)
  "recalculated_llm_score": 88.0,  // Score 5: LLM rerank
  
  // ===== COMPLIANCE & RANKING =====
  "hard_requirements_met": true,   // Passed mandatory filters
  "rank": 3,                       // Rank among all candidates for this job
  "adjusted_score": 85.0,          // Final adjusted score after LLM rerank
  
  // ===== COMPLIANCE DETAILS (from filtering) =====
  "compliance_details": {
    "compliance_score": 1.0,       // 0-1 scale (mandatory: must be 1.0)
    "requirements_met": ["experience", "hard_skills"],
    "requirements_missing": [],
    "filter_reason": null,
    "specified_requirements_count": 2,
    "compliance_breakdown": {
      "experience": {
        "meets": true,
        "candidate_value": 6.5,
        "requirement": {"min": 5, "max": null},
        "details": "Has 6.5 years, requires at least 5 years"
      },
      "hard_skills": {
        "meets": true,
        "found": ["Python", "Machine Learning", "TensorFlow"],
        "missing": [],
        "details": "Has all required skills"
      }
    }
  },
  
  // ===== SCORE BREAKDOWN (detailed explanation) =====
  "score_breakdown": {
    "project_metrics": {
      "difficulty": 0.85,
      "novelty": 0.75,
      "skill_relevance": 0.95,
      "complexity": 0.88,
      "technical_depth": 0.90,
      "domain_relevance": 0.95,
      "execution_quality": 0.92,
      "weighted_avg": 0.855
    },
    "keyword_components": {
      "required_skills_match": 0.90,
      "preferred_skills_match": 0.65,
      "experience_keywords": 0.85,
      "weighted_score": 0.783
    },
    "semantic_components": {
      "skills_similarity": 0.88,
      "projects_similarity": 0.82,
      "experience_similarity": 0.80,
      "weighted_score": 0.827
    },
    "llm_feedback": "Strong ML background with relevant production experience. Excellent project portfolio."
  },
  
  // ===== METADATA =====
  "created_at": "2024-01-15T11:00:00Z",
  "updated_at": "2024-01-15T11:30:00Z"
}
```

**Indexes:**
```javascript
// For fast lookup by job
{ "job_id": 1, "final_score": -1 }

// For fast lookup by resume
{ "resume_id": 1 }

// Unique constraint: one score per job-resume pair
{ "job_id": 1, "resume_id": 1 }, { unique: true }
```

---

## 📁 4. RESUME_GROUPS COLLECTION

### Collection: `resume_groups`

**Groups of resumes (uploaded together or from same source)**

```json
{
  "_id": "ObjectId('...')",
  "name": "January 2024 Applications",
  "source": "upload",  // upload | email | api
  "resume_count": 45,
  "created_at": "2024-01-10T09:00:00Z",
  "updated_at": "2024-01-10T09:3
    }
  },
  
  // ===== METADATA =====
  "file_path": "uploads/jds/ml_engineer_jd.pdf",
  "status": "processed",
  "locked": false,
  "created_at": "2024-01-10T14:00:00Z",
  "updated_at": "2024-01-10T14:20:00Z"
}
```

---

## 🎯 3. COMPLIANCE CHECKING (Before Scoring)

### When Compliance is Checked:
**Before computing any scores** - filters out non-compliant candidates to improve efficiency

### Process Flow:
```
1. Job created → filter_requirements stored in jobs collection
   ↓
2. Scoring triggered for job_id → Load job.filter_requirements.mandatory_compliances
   ↓
3. For each resume in job.resume_groups:
   - Check compliance using resume.parsed_content
   - Dynamically check each requirement (experience, skills, location, etc.)
   - Calculate: compliance_score = requirements_met / total_requirements
   ↓
4. Filter Decision (100% strict for mandatory):
   - compliance_score = 1.0 → PASS (proceed to scoring)
   - compliance_score < 1.0 → FILTER (skip scoring, save reason)
   ↓
5. Only compliant resumes get scored → Results in score_results collection
```

### Requirement Types:

#### **Numeric (Experience, Years):**
```javascript
// Example: {"type": "numeric", "min": 5, "max": null, "unit": "years"}
meets = resume.years_experience >= requirement.min
// Note: max not used for filtering, only for ranking
```

#### **List (Skills, Tools):**
```javascript
// Example: {"type": "list", "required": ["Python", "ML", "AWS"]}
// For MANDATORY: 100% strict - ALL skills must be present
found = requiredSkills.filter(skill => resumeSkills.includes(skill))
meets = found.length === requiredSkills.length
```

#### **Location:**
```javascript
// Example: {"type": "location", "required": "Remote" or "San Francisco"}
// Checks remote/onsite/hybrid preferences and location matching
meets = checkLocationMatch(resume.location, requirement.required)
```

#### **Dynamic Requirements:**
- System supports any requirement type dynamically
- No hardcoded field names
- See [COMPLIANCE_FILTERING_ANALYSIS.md](COMPLIANCE_FILTERING_ANALYSIS.md) for full formulas

### Compliance Storage:

**In Jobs Collection:**
```json
{
  "filter_requirements": {
    "mandatory_compliances": {
      "raw_prompt": "Must have 5+ years...",
      "structured": {
        "experience": {"type": "numeric", "min": 5, "specified": true},
        "hard_skills": {"type": "list", "required": [...], "specified": true}
      }
    },
    "soft_compliances": {
      "raw_prompt": "Preferred: Kubernetes...",
      "structured": {...}
    }
  }
}
```

**In Score_Results Collection:**
```json
{
  "hard_requirements_met": true,
  "compliance_details": {
    "compliance_score": 1.0,
    "requirements_met": ["experience", "hard_skills"],
    "requirements_missing": [],
    "filter_reason": null,
    "compliance_breakdown": {
      "experience": {
        "meets": true,
        "candidate_value": 6.5,
        "requirement": {"min": 5},
        "details": "Has 6.5 years, requires at least 5 years"
      }
    }
  }
}
```

**Important:** Only compliant resumes (compliance_score = 1.0) get score_results entries!

---

## 🎯 4. WHAT WE STORE VS DON'T STORE

### ✅ **STORED (What we need):**
- AI parser output (all fields OpenAI returns)
- Pre-generated embeddings (for fast scoring)
- Embedding hints (for semantic scorer)
- 7 project metrics (for project score)
- Canonical skills (for keyword matching)
- Filter requirements (for compliance checking)
- Scores + compliance details (5 scores + filtering results)
- Minimal metadata (file paths, timestamps, status)

### ❌ **NOT STORED (Extra fields):**
- Interview process details
- Compensation & benefits
- Team context details
- Screening questions
- Extra HR logistics not from parsing

---

## 🚀 5. USAGE IN SCORING

### **Project Score:**
```javascript
// Use pre-computed metrics from resume.projects[].metrics
const projectSco3-COLLECTION ARCHITECTURE:**

1. **Reusable Resumes**: One resume can be scored against multiple jobs (no duplication)
2. **Efficient**: Pre-generated embeddings in resume/job (10x faster scoring)
3. **Scalable**: Score results in separate collection (many-to-many relationship)
4. **Clean Separation**: Resume data ≠ Job data ≠ Score data
5. **Flexible**: Can add/remove resume groups to jobs without affecting resumes

**Flow:**
```
Upload Resumes → Create resume_group → Parse & embed resumes
    ↓
Create Job → Parse & embed JD → Link resume_groups
    ↓
Score Processing → Compute 5 scores for each resume × job
    ↓
Store in score_results → Rank by final_score
```

---

## 🎯 7rojectAggregate = average(projectScores);
```

### **Semantic Score:**
```javascript
// Use pre-generated embeddings
const jdEmbedding = job.jd_analysis.embeddings.jd_embedding;
const resumeEmbedding = resume.embeddings.resume_embedding;

// Cosine similarity (fast!)
const semanticScore = cosineSimilarity(jdEmbedding, resumeEmbedding);

// OR use section-level embeddings for granular matching
const skillsSimilarity = cosineSimilarity(
  job.jd_analysis.embeddings.skills_embedding,
  resume.embeddings.skills_embedding
);
```

### **Keyword Score:**
```javascript
// Use structured canonical_skills
const requiredSkillsMatch = countMatches(
  job.required_skills,
  resume.canonical_skills // Flattened
);
```

---

## ✅ **WHY THIS STRUCTURE:**

1. **Efficient**: Pre-generated embeddings = 10x faster scoring (no repeated API calls)
2. **Complete**: All data needed for 5 scoring algorithms
3. **Simple**: Only essential fields, nothing extra
4. **Ready**: Embeddings + hints ready for semantic scorer
5. **Proven**: Same scoring logic as old system, just optimized

**Flow: Job Title + Description → AI Parsing → Generate Embeddings → Store in DB → Score Resumes → Rank** 🎯

---

## 🎯 5. THE 5 SCORING ALGORITHMS

### Score 1: Project Score (0-1)
- Uses: `projects[].metrics` (7 values)
- Formula: Weighted average of difficulty, novelty, skill_relevance, complexity, technical_depth, domain_relevance, execution_quality

### Score 2: Keyword Score (0-1)
- Uses: `required_skills`, `preferred_skills`, `keywords_weighted`, `experience_entries`
- Formula: 8 components with specific weights

### Score 3: Semantic Score (0-1)
- Uses: `embedding_hints` from resume and JD
- Formula: Cosine similarity with section weights (skills: 0.30, projects: 0.25, etc.)
- **Why embedding_hints:** Algorithm extracts text sections and computes embeddings

### Score 4: Final Score (0-1)
- Uses: Scores 1, 2, 3
- Formula: 35% project + 35% semantic + 30% keyword

### Score 5: LLM Rerank (0-1)
- Uses: Top candidates from Score 4
- Formula: GPT-4o-mini validation in batches of 30

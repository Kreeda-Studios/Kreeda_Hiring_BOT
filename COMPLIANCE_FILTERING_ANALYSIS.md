# 🔍 Compliance & Filtering System - Complete Analysis

**Based on:** Old Code Archive (EarlyFilter.py, HRFilter.py, FinalRanking.py)  
**Date:** 2026-02-03

---

## 📋 1. OVERVIEW

The old system has **2-stage filtering**:
1. **EarlyFilter.py**: Filters candidates BEFORE scoring (mandatory compliances - 100% strict)
2. **FinalRanking.py**: Displays soft compliances AFTER scoring (for information only)

### Key Principles:
- **Mandatory compliances**: 100% strict - candidate must meet ALL requirements
- **Soft compliances**: Optional preferences - shown but don't filter
- **Dynamic requirements**: Works with any requirement type (experience, skills, location, etc.)

---

## 📦 2. DATA STRUCTURES

### 2.1 Filter Requirements JSON Structure

```json
{
  "mandatory_compliances": {
    "raw_prompt": "Must have 5+ years Python. Required: TensorFlow, AWS",
    "structured": {
      "experience": {
        "type": "numeric",
        "specified": true,
        "min": 5,
        "max": null,
        "unit": "years"
      },
      "hard_skills": {
        "type": "list",
        "specified": true,
        "required": ["Python", "TensorFlow", "AWS"],
        "optional": []
      }
    }
  },
  "soft_compliances": {
    "raw_prompt": "Preferred: Kubernetes, LLM experience",
    "structured": {
      "preferred_skills": {
        "type": "list",
        "specified": true,
        "required": ["Kubernetes", "LLM"],
        "optional": []
      }
    }
  },
  "re_ranking_instructions": "Prioritize candidates with production ML experience"
}
```

### 2.2 Resume Compliance Result

```json
{
  "should_filter": false,
  "filter_reason": null,
  "compliance": {
    "experience": {
      "meets": true,
      "field": "experience",
      "type": "numeric",
      "candidate_value": 6.5,
      "requirement": {"min": 5, "max": null},
      "details": "Has 6.5 years, requires at least 5 years"
    },
    "hard_skills": {
      "meets": true,
      "field": "hard_skills",
      "type": "list",
      "candidate_value": ["Python", "TensorFlow", "AWS", "Docker"],
      "requirement": {"required": ["Python", "TensorFlow", "AWS"]},
      "found": ["Python", "TensorFlow", "AWS"],
      "missing": [],
      "details": "Has all required skills: Python, TensorFlow, AWS"
    }
  },
  "requirements_met": ["experience", "hard_skills"],
  "requirements_missing": [],
  "compliance_score": 1.0,
  "specified_requirements_count": 2
}
```

---

## 🔍 3. COMPLIANCE CHECKING LOGIC

### 3.1 Dynamic Requirement Checker

The system uses `check_dynamic_requirement()` function that automatically determines checking logic based on requirement type:

```python
def check_dynamic_requirement(resume_json: dict, field_name: str, requirement_spec) -> dict:
    """
    Generic dynamic requirement checker - handles ANY requirement type.
    Automatically determines checking logic based on requirement type.
    """
    requirement_type = requirement_spec.get("type", "text")
    
    if requirement_type == "numeric":
        return check_numeric_requirement(resume_json, field_name, requirement_spec)
    elif requirement_type == "list":
        return check_list_requirement(resume_json, field_name, requirement_spec)
    elif requirement_type == "location":
        return check_location_requirement(resume_json, field_name, requirement_spec)
    elif requirement_type == "education":
        return check_education_requirement(resume_json, field_name, requirement_spec)
    elif requirement_type == "boolean":
        # Boolean check logic
    else:
        return check_text_requirement(resume_json, field_name, requirement_spec)
```

### 3.2 Requirement Types & Formulas

#### A. **NUMERIC Requirements** (Experience, Years, etc.)

**Formula:**
```python
# For filtering: Only check MINIMUM (don't filter by max)
# Max is used for SORTING in ranking, not filtering

meets = candidate_value >= min_value

# Example:
# Requirement: min=5 years
# Candidate: 6.5 years
# Result: meets = True (6.5 >= 5)
```

**Logic:**
- Extract requirement: `min` (required), `max` (optional, not used for filtering)
- Extract candidate value from resume: `years_experience` field
- Compare: `candidate_years >= min_years`
- **Important**: Max is NOT checked during filtering (only used for ranking sort order)

**Code:**
```python
def check_experience_compliance(resume: dict, exp_req: dict):
    resume_years = resume.get("years_experience")
    min_years = exp_req.get("min", 0)
    
    # Only filter by minimum - max handled in ranking
    if resume_years < min_years:
        return False, f"Has {resume_years} years, requires at least {min_years} years"
    
    return True, f"Meets experience requirement ({resume_years} years, min: {min_years})"
```

---

#### B. **LIST Requirements** (Skills, Tools, etc.)

**Formula:**
```python
# For MANDATORY: 100% strict - ALL required skills must be present
required_skills = ["Python", "TensorFlow", "AWS"]
found_skills = [skill for skill in required_skills if skill in resume_skills]

meets = len(found_skills) == len(required_skills)
compliance_score = len(found_skills) / len(required_skills)

# Example:
# Required: ["Python", "TensorFlow", "AWS"]
# Candidate has: ["Python", "TensorFlow", "Docker"]
# Found: ["Python", "TensorFlow"]
# Missing: ["AWS"]
# meets = False (2/3 = 66.7% < 100%)
```

**Skill Extraction (from resume):**
```python
# 1. From canonical_skills (10 categories)
resume_skills = set()
for cat_skills in canonical_skills.values():
    resume_skills.update(s.lower() for s in cat_skills)

# 2. From inferred_skills
for inf in inferred_skills:
    resume_skills.add(inf["skill"].lower())

# 3. From skill_proficiency
for sp in skill_proficiency:
    resume_skills.add(sp["skill"].lower())

# 4. From projects
for proj in projects:
    resume_skills.update(proj["tech_keywords"])
    resume_skills.update(proj["primary_skills"])

# 5. Fallback: Check in resume text
if skill not in resume_skills:
    # Check if skill appears in project/experience descriptions
    if skill_lower in resume_text_lower:
        resume_skills.add(skill)
```

**Matching Logic:**
```python
def check_skills_compliance(resume: dict, required_skills: List[str]):
    found = []
    missing = []
    
    for req_skill in required_skills:
        req_skill_normalized = req_skill.lower().strip()
        
        # 1. Exact match in skills set
        if req_skill_normalized in resume_skills:
            found.append(req_skill)
        # 2. Fallback: check in resume text
        elif any(term in resume_text for term in req_skill_normalized.split() if len(term) > 3):
            found.append(req_skill)
        else:
            missing.append(req_skill)
    
    # Mandatory: 100% strict
    meets = len(found) == len(required_skills)
    
    return meets, found, missing
```

---

#### C. **LOCATION Requirements**

**Formula:**
```python
# Check remote/onsite/hybrid preferences
is_remote_req = "remote" in requirement.lower()
candidate_remote = "remote" in candidate_location.lower()

if is_remote_req and candidate_remote:
    meets = True
elif requirement.lower() in ["any", "anywhere", "flexible"]:
    meets = True
else:
    # Generic location match
    meets = (requirement.lower() in candidate_location.lower() or 
             candidate_location.lower() in requirement.lower())
```

**Code:**
```python
def check_location_compliance(resume: dict, requirement: str):
    req_loc = requirement.lower().strip()
    
    # Flexible requirements
    if req_loc in ["any", "anywhere", "remote/onsite", "flexible", ""]:
        return True, "Location requirement is flexible (Any)"
    
    candidate_loc = resume.get("location", "").lower()
    
    # Remote/Onsite/Hybrid matching
    is_remote_req = "remote" in req_loc
    candidate_remote = "remote" in candidate_loc
    
    if is_remote_req and candidate_remote:
        return True, "Candidate is available for remote work"
    
    # Generic match
    if req_loc in candidate_loc or candidate_loc in req_loc:
        return True, f"Location matches: {resume.get('location')}"
    
    return False, f"Location mismatch: {resume.get('location')} (required: {requirement})"
```

---

#### D. **DEPARTMENT/EDUCATION Requirements**

**Formula:**
```python
# IT vs Non-IT categorization
IT_DEPARTMENTS = {
    "computer science", "cs", "cse", "computer engineering",
    "information technology", "it", "software engineering",
    "data science", "ai", "ml", "artificial intelligence"
}

candidate_departments = [edu["field"].lower() for edu in resume["education"]]
candidate_has_it = any(dept in IT_DEPARTMENTS for dept in candidate_departments)

if category == "it":
    meets = candidate_has_it
elif category == "non-it":
    meets = not candidate_has_it
```

**Code:**
```python
def check_department_compliance(resume: dict, dept_req: dict):
    candidate_departments = [edu.get("field", "").lower() for edu in resume.get("education", [])]
    
    category = dept_req.get("category", "").lower()
    allowed = [d.lower() for d in dept_req.get("allowed_departments", [])]
    excluded = [d.lower() for d in dept_req.get("excluded_departments", [])]
    
    # IT category check
    if category == "it":
        candidate_has_it = any(dept in IT_DEPARTMENTS for dept in candidate_departments)
        if not candidate_has_it:
            return False, f"Department not IT-related. Found: {', '.join(candidate_departments[:3])}"
        return True, f"IT department found"
    
    # Allowed departments check
    if allowed:
        matches = [d for d in candidate_departments if any(allowed_dept in d for allowed_dept in allowed)]
        if not matches:
            return False, f"Department not in allowed list"
        return True, f"Department matches: {', '.join(matches[:2])}"
    
    # Excluded departments check
    if excluded:
        matches = [d for d in candidate_departments if any(excluded_dept in d for excluded_dept in excluded)]
        if matches:
            return False, f"Department in excluded list: {', '.join(matches[:2])}"
        return True, "Department not excluded"
    
    return True, "Department requirement met"
```

---

#### E. **OTHER_CRITERIA Requirements** (Text-based)

**Formula:**
```python
# Extract key terms from criterion
key_terms = [word for word in criterion.lower().split() if len(word) > 3]

# Check match in resume text
matches = sum(1 for term in key_terms if term in resume_text_lower)
match_ratio = matches / len(key_terms)

# At least 50% of key terms or first 2 key terms must match
meets = match_ratio >= 0.5 or any(term in resume_text_lower for term in key_terms[:2])
```

**Code:**
```python
def check_other_criteria_compliance(resume: dict, other_criteria: List[str]):
    # Collect resume text
    resume_text = ""
    resume_text += " ".join(resume.get("summary", []))
    for exp in resume.get("experience", []):
        resume_text += exp.get("description", "")
    for proj in resume.get("projects", []):
        resume_text += proj.get("description", "")
    
    resume_text_lower = resume_text.lower()
    
    met_criteria = []
    failed_criteria = []
    
    for criterion in other_criteria:
        key_terms = [word for word in criterion.lower().split() if len(word) > 3]
        matches = sum(1 for term in key_terms if term in resume_text_lower)
        match_ratio = matches / len(key_terms) if key_terms else 0
        
        if match_ratio >= 0.5 or any(term in resume_text_lower for term in key_terms[:2]):
            met_criteria.append(criterion)
        else:
            failed_criteria.append(criterion)
    
    meets = len(failed_criteria) == 0
    return meets, met_criteria, failed_criteria
```

---

## 🎯 4. FILTERING LOGIC

### 4.1 Mandatory Compliances (100% Strict)

**Formula:**
```python
# Check all specified requirements
specified_requirements = [field for field, val in structured.items() if has_value(val)]

requirements_met = []
requirements_missing = []

for field_name, field_spec in structured.items():
    result = check_dynamic_requirement(resume, field_name, field_spec)
    if result["meets"]:
        requirements_met.append(field_name)
    else:
        requirements_missing.append(field_name)

# Calculate compliance score
compliance_score = len(requirements_met) / len(specified_requirements)

# Filter decision: 100% strict (must meet ALL requirements)
should_filter = len(requirements_missing) > 0
```

**Code:**
```python
def check_all_requirements(resume: dict, filter_requirements: dict) -> dict:
    mandatory_compliances = filter_requirements.get("mandatory_compliances", {})
    structured = mandatory_compliances.get("structured", {})
    
    compliance = {}
    requirements_met = []
    requirements_missing = []
    filter_reasons = []
    
    for field_name, field_spec in structured.items():
        if not field_has_value(field_spec):
            continue  # Skip empty fields
        
        result = check_dynamic_requirement(resume, field_name, field_spec)
        compliance[field_name] = result
        
        if result["meets"]:
            requirements_met.append(field_name)
        else:
            requirements_missing.append(field_name)
            filter_reasons.append(f"{field_name}: {result['details']}")
    
    # Calculate compliance score
    specified_count = len([f for f, v in structured.items() if field_has_value(v)])
    compliance_score = len(requirements_met) / specified_count if specified_count > 0 else 1.0
    
    # Filter decision: 100% strict
    should_filter = len(requirements_missing) > 0
    filter_reason = "; ".join(filter_reasons[:3]) if should_filter else None
    
    return {
        "should_filter": should_filter,
        "filter_reason": filter_reason,
        "compliance": compliance,
        "requirements_met": requirements_met,
        "requirements_missing": requirements_missing,
        "compliance_score": compliance_score,
        "specified_requirements_count": specified_count
    }
```

### 4.2 Filtering Workflow

```
1. Load HR_Filter_Requirements.json
   ↓
2. Check if mandatory_compliances exist
   ↓
3. For each resume:
   a. Check all mandatory requirements dynamically
   b. Calculate compliance_score = met / total
   c. Decide: should_filter = (missing > 0)
   ↓
4. If should_filter = True:
   - Move resume to FilteredResumes/
   - Save to Skipped.json
   ↓
5. If should_filter = False:
   - Keep in ProcessedJson/ for scoring
```

---

## 📊 5. COMPLIANCE SCORE CALCULATION

### 5.1 Mandatory Compliance Score

**Formula:**
```python
# Count specified requirements (non-empty)
specified_requirements = [field for field, val in structured.items() if has_value(val)]
specified_count = len(specified_requirements)

# Count met requirements
requirements_met = [field for field in specified_requirements if compliance[field]["meets"]]
met_count = len(requirements_met)

# Calculate score
compliance_score = met_count / specified_count if specified_count > 0 else 1.0

# Examples:
# Scenario 1: 2/2 requirements met = 100% (1.0)
# Scenario 2: 1/2 requirements met = 50% (0.5) → FILTERED
# Scenario 3: 0/2 requirements met = 0% (0.0) → FILTERED
# Scenario 4: No requirements = 100% (1.0) → NOT FILTERED
```

### 5.2 Soft Compliance Score (Display Only)

**Formula:**
```python
# Same calculation as mandatory, but doesn't affect filtering
soft_compliances = filter_requirements.get("soft_compliances", {})
soft_structured = soft_compliances.get("structured", {})

soft_score = met_soft / total_soft if total_soft > 0 else 1.0

# Used for display/ranking bonus, NOT for filtering
```

---

## 🔧 6. WHERE COMPLIANCE IS USED

### 6.1 In EarlyFilter.py (Before Scoring)

**Purpose:** Filter out candidates who don't meet mandatory requirements

**Flow:**
1. Load resumes from `ProcessedJson/`
2. Check `mandatory_compliances` for each resume
3. If `should_filter = True`:
   - Move to `ProcessedJson/FilteredResumes/`
   - Save to `Ranking/Skipped.json`
4. If `should_filter = False`:
   - Keep in `ProcessedJson/` for scoring

**Output:**
- Compliant resumes → Continue to scoring
- Filtered resumes → Saved in Skipped.json with reasons

### 6.2 In FinalRanking.py (After Scoring)

**Purpose:** Display soft compliances (preferences) for information

**Flow:**
1. After scoring is complete
2. Check `soft_compliances` for each candidate
3. Add compliance info to ranking output
4. Used for display/bonus scoring, NOT filtering

**Output:**
```json
{
  "name": "John Smith",
  "final_score": 85.2,
  "soft_compliances": {
    "preferred_skills": {
      "meets": true,
      "found": ["Kubernetes", "LLM"],
      "missing": []
    }
  },
  "compliance_display": "Meets all preferred requirements ✅"
}
```

---

## 📝 7. IMPLEMENTATION IN NEW SYSTEM

### 7.1 MongoDB Schema Updates

```typescript
// In Job model - store filter requirements
interface IJob {
  filter_requirements: {
    mandatory_compliances: {
      raw_prompt: string;
      structured: {
        [key: string]: {
          type: "numeric" | "list" | "location" | "education" | "text";
          specified: boolean;
          // Type-specific fields
          min?: number;
          max?: number;
          required?: string[];
          optional?: string[];
          // ... etc
        };
      };
    };
    soft_compliances: {
      raw_prompt: string;
      structured: Record<string, any>;
    };
  };
}

// In ScoreResult model - store compliance results
interface IScoreResult {
  hard_requirements_met: boolean;
  compliance_details: {
    compliance_score: number;
    requirements_met: string[];
    requirements_missing: string[];
    filter_reason?: string;
  };
}
```

### 7.2 Python Scoring Service

**Module:** `scripts/compliance-checker/compliance_checker.py`

```python
def check_resume_compliance(resume_json: dict, job_filter_reqs: dict) -> dict:
    """
    Check if resume meets job filter requirements.
    Returns compliance result with should_filter flag.
    """
    # Use same logic as EarlyFilter.py
    return check_all_requirements(resume_json, job_filter_reqs)

def filter_resumes_before_scoring(job_id: str, resume_ids: list) -> dict:
    """
    Filter resumes before scoring.
    Returns: {"compliant": [...], "filtered": [...]}
    """
    job = get_job_from_db(job_id)
    filter_reqs = job["filter_requirements"]
    
    compliant = []
    filtered = []
    
    for resume_id in resume_ids:
        resume = get_resume_from_db(resume_id)
        result = check_resume_compliance(resume["parsed_content"], filter_reqs)
        
        if result["should_filter"]:
            filtered.append({
                "resume_id": resume_id,
                "filter_reason": result["filter_reason"],
                "compliance_score": result["compliance_score"]
            })
        else:
            compliant.append(resume_id)
    
    return {"compliant": compliant, "filtered": filtered}
```

### 7.3 Integration with Scoring Pipeline

```
1. Job created → Parse JD → Store filter_requirements
   ↓
2. Resumes uploaded → Parse resumes → Store in DB
   ↓
3. START SCORING for job_id
   ↓
4. CHECK COMPLIANCE FIRST:
   - Load filter_requirements from Job
   - For each resume: check_resume_compliance()
   - Split into: compliant (score) vs filtered (skip)
   ↓
5. SCORE only compliant resumes:
   - Compute 5 scores
   - Store in ScoreResult with compliance_details
   ↓
6. RANK compliant resumes by final_score
   ↓
7. Display results with compliance info
```

---

## ✅ 8. KEY TAKEAWAYS

### Important Rules:
1. **Mandatory = 100% strict**: ALL requirements must be met
2. **Soft = Display only**: Shown but don't filter
3. **Dynamic checking**: Works with any requirement type
4. **Field-based**: No hardcoded requirement names
5. **Experience max**: NOT used for filtering (only for ranking sort)
6. **Skills matching**: Extracts from 5 sources (canonical, inferred, proficiency, projects, text)
7. **Compliance score**: `met / total` (0-1 scale, but mandatory requires 1.0)

### Where Used:
- **Before scoring**: Filter non-compliant candidates (EarlyFilter.py)
- **After scoring**: Display soft compliances (FinalRanking.py)
- **In ranking**: Bonus points for meeting soft requirements

### Data Flow:
```
HR_Filter_Requirements.json 
  → mandatory_compliances (100% strict filter)
  → soft_compliances (display only)
  → Resume compliance check
  → Filter decision (should_filter: boolean)
  → Compliant resumes → Scoring
  → Filtered resumes → Skipped.json
```

---

**This compliance system enables flexible, dynamic HR filtering without hardcoding specific fields!** 🎯

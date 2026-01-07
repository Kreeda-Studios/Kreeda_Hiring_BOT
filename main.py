import os
from dotenv import load_dotenv
# Load environment variables from .env file
load_dotenv()

import streamlit as st
from pathlib import Path
import tempfile
import shutil
import subprocess
import json
import runpy
import zipfile
from typing import List, Dict, Optional

from InputThread.file_router import route_pdf  # updated function name
from PyPDF2 import PdfReader  # for PDF extraction

# Constants
PROCESSED_TXT_DIR = Path("Processed-TXT")
PROCESSED_JSON_DIR = Path("ProcessedJson")
JD_FILE = Path("InputThread/JD/JD.txt")
UPLOADED_RESUMES_DIR = Path("Uploaded_Resumes")  # Store original PDFs
PDF_MAPPING_FILE = Path("Uploaded_Resumes/pdf_mapping.json")  # Map candidate_id to PDF path

# Ranking files
DISPLAY_RANKS = Path("Ranking/DisplayRanks.txt")
FINAL_RANKING_SCRIPT = Path("ResumeProcessor/Ranker/FinalRanking.py")

# Files to clear between runs
FILES_TO_CLEAR = [
    "Ranking/Final_Ranking.json",
    "Ranking/Scores.json",
    "Ranking/Skipped.json",
    "ResumeProcessor/.semantic_embed_cache.pkl",
    "Ranking/DisplayRanks.txt",
    "Processed_Resume_Index.txt"  # Clear index to prevent accumulation
]

# Folders to clear between runs (for manual clear button)
FOLDERS_TO_CLEAR = [
    "ProcessedJson",
    "Processed-TXT",
]

# Folders to clear automatically before processing (only ProcessedJson to preserve extracted text)
FOLDERS_TO_CLEAR_BEFORE_PROCESSING = [
    "ProcessedJson",  # Clear old JSONs, but preserve Processed-TXT (extracted text files)
]

# Ensure output directories exist
PROCESSED_TXT_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_JSON_DIR.mkdir(parents=True, exist_ok=True)
JD_FILE.parent.mkdir(parents=True, exist_ok=True)
UPLOADED_RESUMES_DIR.mkdir(parents=True, exist_ok=True)

# ZIP download configuration
DISPLAY_RANKS_FILE = Path("Ranking/DisplayRanks.txt")

# PDF extraction helper
def extract_pdf_text(pdf_file) -> str:
    reader = PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

# Cleanup helper - clears all files and folders (for manual clear button)
def clear_previous_run():
    cleared = []
    for f in FILES_TO_CLEAR:
        try:
            if os.path.exists(f):
                os.remove(f)
                cleared.append(f)
        except Exception as e:
            st.error(f"❌ Error deleting {f}: {e}")

    for folder in FOLDERS_TO_CLEAR:
        if os.path.exists(folder):
            for root, _, files in os.walk(folder):
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                        cleared.append(file)
                    except Exception as e:
                        st.error(f"❌ Error deleting {file}: {e}")
    return cleared

# Cleanup helper - clears only ProcessedJson before processing (preserves Processed-TXT)
def clear_before_processing():
    """Clear only ProcessedJson folder before processing, preserving Processed-TXT."""
    cleared = []
    # Clear ranking files
    for f in FILES_TO_CLEAR:
        try:
            if os.path.exists(f):
                os.remove(f)
                cleared.append(f)
        except Exception as e:
            print(f"⚠️ Error deleting {f}: {e}")
    
    # Clear only ProcessedJson (preserve Processed-TXT)
    for folder in FOLDERS_TO_CLEAR_BEFORE_PROCESSING:
        if os.path.exists(folder):
            for root, _, files in os.walk(folder):
                for file in files:
                    try:
                        os.remove(os.path.join(root, file))
                        cleared.append(file)
                    except Exception as e:
                        print(f"⚠️ Error deleting {file}: {e}")
    return cleared


def normalize_parsed_requirements(parsed: dict) -> dict:
    """
    Normalize parsed requirements structure.
    Handles nested arrays, maps field names, and ensures proper structure.
    """
    if not isinstance(parsed, dict):
        return {}
    
    normalized = {}
    
    # Field name mapping for common variations
    field_mapping = {
        "skills": "hard_skills",
        "required_skills": "hard_skills",
        "technical_skills": "hard_skills",
        "must_have_skills": "hard_skills",
        "years_of_experience": "experience",
        "years_experience": "experience",
        "exp": "experience",
        "loc": "location",
        "edu": "education"
    }
    
    for field_name, field_value in parsed.items():
        # Handle nested "requirements" array structure
        if field_name == "requirements" and isinstance(field_value, list):
            # Convert array of requirement objects to flat fields
            for req_obj in field_value:
                if not isinstance(req_obj, dict):
                    continue
                
                req_type = req_obj.get("type", "").lower()
                req_data = req_obj.get("data", {}) or req_obj.get("value") or req_obj
                
                # Map requirement type to field name
                if req_type in ["skills", "skill"]:
                    mapped_field = "hard_skills"
                    # Extract skills from data
                    if isinstance(req_data, dict):
                        skill_value = req_data.get("skill") or req_data.get("skills") or req_data.get("required")
                        if isinstance(skill_value, str):
                            skills_list = [s.strip() for s in skill_value.split(",")]
                        elif isinstance(skill_value, list):
                            skills_list = skill_value
                        else:
                            skills_list = []
                    else:
                        skills_list = [str(req_data)] if req_data else []
                    
                    # Filter out empty strings and only create field if skills exist
                    skills_list = [s for s in skills_list if s and s.strip()]
                    if skills_list:  # Only create field if we have skills
                        normalized[mapped_field] = {
                            "type": "list",
                            "specified": True,
                            "required": skills_list,
                            "optional": []
                        }
                
                elif req_type in ["numeric", "experience", "years"]:
                    mapped_field = "experience"
                    if isinstance(req_data, dict):
                        normalized[mapped_field] = {
                            "type": "numeric",
                            "specified": True,
                            "min": req_data.get("min") or req_data.get("value") or req_data.get("years"),
                            "max": req_data.get("max"),
                            "unit": req_data.get("unit", "years")
                        }
                    else:
                        # Only create field if we have a valid numeric value
                        try:
                            min_val = float(req_data) if req_data else None
                            if min_val is not None:
                                normalized[mapped_field] = {
                                    "type": "numeric",
                                    "specified": True,
                                    "min": min_val,
                                    "unit": "years"
                                }
                        except (ValueError, TypeError):
                            pass  # Skip invalid numeric values
                
                elif req_type in ["location", "loc"]:
                    mapped_field = "location"
                    if isinstance(req_data, dict):
                        normalized[mapped_field] = {
                            "type": "location",
                            "specified": True,
                            "required": req_data.get("required") or req_data.get("location"),
                            "allowed": req_data.get("allowed", [])
                        }
                    else:
                        normalized[mapped_field] = {
                            "type": "location",
                            "specified": True,
                            "required": str(req_data) if req_data else ""
                        }
                
                else:
                    # Generic field - use type as field name or keep original
                    generic_field = req_type if req_type else "other_criteria"
                    base_dict = {
                        "type": req_type or "text",
                        "specified": True
                    }
                    if isinstance(req_data, dict):
                        # Merge dictionaries
                        base_dict.update(req_data)
                        normalized[generic_field] = base_dict
                    else:
                        base_dict["value"] = req_data
                        normalized[generic_field] = base_dict
        
        else:
            # Normal field - map name if needed
            mapped_name = field_mapping.get(field_name.lower(), field_name)
            
            # Ensure proper structure
            if isinstance(field_value, dict):
                # Already structured
                if "type" not in field_value:
                    # Try to infer type
                    if "required" in field_value or "optional" in field_value:
                        field_value["type"] = "list"
                    elif "min" in field_value or "max" in field_value:
                        field_value["type"] = "numeric"
                    else:
                        field_value["type"] = "text"
                
                if "specified" not in field_value:
                    field_value["specified"] = True
                
                normalized[mapped_name] = field_value
            
            elif isinstance(field_value, list):
                # List value - convert to proper structure
                normalized[mapped_name] = {
                    "type": "list",
                    "specified": True,
                    "required": field_value,
                    "optional": []
                }
            
            elif isinstance(field_value, (int, float)):
                # Numeric value
                normalized[mapped_name] = {
                    "type": "numeric",
                    "specified": True,
                    "min": float(field_value),
                    "unit": "years" if mapped_name == "experience" else ""
                }
            
            elif isinstance(field_value, str):
                # String value
                normalized[mapped_name] = {
                    "type": "text" if mapped_name != "location" else "location",
                    "specified": True,
                    "required": field_value
                }
    
    return normalized


# Parse HR filter requirements from text (Dynamic - optimized for cost/latency)
def parse_hr_filter_requirements(hr_text: str) -> dict:
    """
    Parse HR requirements text into structured format using LLM (dynamic fields).
    Optimized for minimum latency and cost - uses efficient prompt and model.
    Returns: {"raw_prompt": str, "structured": dict} where structured can have any field names.
    """
    import time
    
    if not hr_text or not hr_text.strip():
        return {
            "raw_prompt": "",
            "structured": {}
        }
    
    # Use OpenAI to structure the HR requirements dynamically
    try:
        from openai import OpenAI
        import os
        
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            try:
                api_key = st.secrets.get("OPENAI_API_KEY", None)
            except:
                api_key = None
        
        if not api_key:
            # Fallback: return empty structure (no parsing without API)
            st.warning("⚠️ OpenAI API not configured. Returning empty structure.")
            return {
                "raw_prompt": hr_text,
                "structured": {}
            }
        
        client = OpenAI(api_key=api_key)
        
        # Optimized prompt for cost/latency - use JSON mode for faster parsing
        llm_call_id = f"LLM_{int(time.time() * 1000)}"
        print(f"[{llm_call_id}] 🔄 Starting LLM call: parse_hr_requirements")
        print(f"[{llm_call_id}] 📤 Request: gpt-4o-mini, dynamic parsing")
        start_time = time.time()
        
        # Use function calling for better structure control
        # This ensures proper field names and structure
        parse_function = {
            "name": "parse_hr_requirements",
            "description": "Parse HR requirements into structured format with proper field names",
            "parameters": {
                "type": "object",
                "properties": {
                    "structured": {
                        "type": "object",
                        "description": "Structured requirements with field names. Use standard field names: hard_skills (for skills), experience (for years), location, education, etc. Each field should be a dict with 'type' and 'specified': true",
                        "properties": {
                            "hard_skills": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "enum": ["list"]},
                                    "specified": {"type": "boolean"},
                                    "required": {"type": "array", "items": {"type": "string"}},
                                    "optional": {"type": "array", "items": {"type": "string"}}
                                },
                                "description": "Required skills (use this field name for any skill requirements)"
                            },
                            "experience": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "enum": ["numeric"]},
                                    "specified": {"type": "boolean"},
                                    "min": {"type": "number"},
                                    "max": {"type": "number"},
                                    "unit": {"type": "string"}
                                },
                                "description": "Experience requirement in years"
                            },
                            "location": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "enum": ["location", "text"]},
                                    "specified": {"type": "boolean"},
                                    "required": {"type": "string"},
                                    "allowed": {"type": "array", "items": {"type": "string"}}
                                },
                                "description": "Location requirement"
                            },
                            "education": {
                                "type": "object",
                                "properties": {
                                    "type": {"type": "string", "enum": ["education", "text"]},
                                    "specified": {"type": "boolean"},
                                    "minimum": {"type": "string"},
                                    "required": {"type": "string"}
                                },
                                "description": "Education requirement"
                            }
                        },
                        "additionalProperties": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "specified": {"type": "boolean"}
                            }
                        }
                    }
                },
                "required": ["structured"]
            }
        }
        
        try:
            # Use function calling for structured output
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """Parse HR requirements into structured JSON format.
CRITICAL RULES:
1. Use standard field names: hard_skills (for any skills), experience (for years), location, education
2. For skills: Use field name "hard_skills" with type "list", put skills in "required" array
3. For experience: Use field name "experience" with type "numeric", use "min" and "max" for range
4. For location: Use field name "location" with type "location" or "text"
5. Each field MUST have "type" and "specified": true
6. Return flat structure (no nested "requirements" arrays)
7. Map common terms: "skills" -> hard_skills, "years" -> experience, "location" -> location"""
                    },
                    {
                        "role": "user",
                        "content": f"Parse these HR requirements into structured JSON with proper field names:\n\n{hr_text}\n\nRemember: Use 'hard_skills' for skills, 'experience' for years, 'location' for location."
                    }
                ],
                functions=[parse_function],
                function_call={"name": "parse_hr_requirements"},
                temperature=0.0,
                max_tokens=1000
            )
            
            msg = response.choices[0].message
            func_call = getattr(msg, "function_call", None)
            if func_call:
                args_text = getattr(func_call, "arguments", None)
                if args_text:
                    parsed = json.loads(args_text)
                    parsed = parsed.get("structured", {})
                else:
                    parsed = {}
            else:
                parsed = {}
            
        except Exception as parse_error:
            print(f"[{llm_call_id}] ⚠️ Function calling failed: {parse_error}")
            parsed = {}
        
        duration = time.time() - start_time
        print(f"[{llm_call_id}] ✅ Completed in {duration:.2f}s")
        print(f"[{llm_call_id}] 📥 Response: {len(parsed)} field(s)")
        
        # Normalize parsed structure (handle nested arrays, map field names)
        normalized = normalize_parsed_requirements(parsed)
        
        if normalized != parsed:
            print(f"[{llm_call_id}] 🔄 Normalized structure: {len(normalized)} field(s)")
        
        return {
            "raw_prompt": hr_text,
            "structured": normalized if isinstance(normalized, dict) else {}
        }
    
    except Exception as e:
        print(f"⚠️ Error parsing HR requirements with LLM: {e}")
        import traceback
        traceback.print_exc()
        # Return empty structure on error
        return {
            "raw_prompt": hr_text,
            "structured": {}
        }


def parse_hr_requirements_fallback(hr_text: str) -> dict:
    """
    Fallback parsing for HR requirements if LLM is not available.
    Simple regex-based extraction.
    """
    import re
    
    structured = {
        "experience": None,
        "hard_skills": [],
        "preferred_skills": [],
        "department": None,
        "location": None,
        "education": [],
        "other_criteria": []
    }
    
    text_lower = hr_text.lower()
    
    # Extract experience (e.g., "2-3 years", "1+ years")
    exp_match = re.search(r'(\d+)\s*[-–to]+\s*(\d+)\s*years?', text_lower)
    if exp_match:
        structured["experience"] = {
            "min": int(exp_match.group(1)),
            "max": int(exp_match.group(2)),
            "field": None,
            "specified": True
        }
    else:
        min_match = re.search(r'(?:at least|minimum|min|requires?)\s*(\d+)\s*years?', text_lower)
        if min_match:
            structured["experience"] = {
                "min": int(min_match.group(1)),
                "max": None,
                "field": None,
                "specified": True
            }
    
    # Extract location
    if "location" in text_lower and "any" not in text_lower:
        location_match = re.search(r'location[:\s]+([^,.;]+)', hr_text, re.IGNORECASE)
        if location_match:
            structured["location"] = location_match.group(1).strip()
    
    # Extract skills (basic - looks for "skills:", "must have:", "required:")
    skills_patterns = [
        r'(?:must have|required|hard skills?)[:\s]+([^,.;]+)',
        r'skills?[:\s]+([^,.;]+)'
    ]
    for pattern in skills_patterns:
        matches = re.finditer(pattern, hr_text, re.IGNORECASE)
        for match in matches:
            skills_text = match.group(1)
            skills = [s.strip() for s in skills_text.split(',') if s.strip()]
            structured["hard_skills"].extend(skills)
    
    # Extract preferred skills
    if "preferred" in text_lower or "nice-to-have" in text_lower:
        pref_patterns = [
            r'(?:preferred|nice-to-have)[:\s]+([^,.;]+)',
        ]
        for pattern in pref_patterns:
            matches = re.finditer(pattern, hr_text, re.IGNORECASE)
            for match in matches:
                skills_text = match.group(1)
                skills = [s.strip() for s in skills_text.split(',') if s.strip()]
                structured["preferred_skills"].extend(skills)
    
    # Deduplicate skills
    structured["hard_skills"] = list(set(structured["hard_skills"]))
    structured["preferred_skills"] = list(set(structured["preferred_skills"]))
    
    return {
        "raw_prompt": hr_text,
        "structured": structured
    }


# ZIP download helper function
def create_resumes_zip(selected_candidates: List[Dict], get_pdf_path_func) -> Optional[bytes]:
    """
    Create a ZIP file containing selected resume PDFs and DisplayRanks.txt.
    
    Args:
        selected_candidates: List of candidate dictionaries
        get_pdf_path_func: Function to get PDF path for a candidate
    
    Returns:
        ZIP file bytes or None if error
    """
    try:
        import io
        
        # Create ZIP in memory
        zip_buffer = io.BytesIO()
        
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            # Add DisplayRanks.txt if it exists
            if DISPLAY_RANKS_FILE.exists():
                zip_file.write(DISPLAY_RANKS_FILE, DISPLAY_RANKS_FILE.name)
            
            # Add all selected PDFs
            for candidate in selected_candidates:
                candidate_id = candidate.get("candidate_id")
                name = candidate.get("name", "Unknown")
                
                # Get PDF path using the provided function
                pdf_path = get_pdf_path_func(candidate_id, name)
                
                if pdf_path and pdf_path.exists():
                    # Add PDF to ZIP with original filename
                    zip_file.write(pdf_path, pdf_path.name)
                else:
                    # Skip if PDF not found (shouldn't happen, but handle gracefully)
                    print(f"⚠️ Warning: PDF not found for {name}, skipping...")
        
        zip_buffer.seek(0)
        return zip_buffer.read()
        
    except Exception as e:
        print(f"❌ Error creating ZIP file: {e}")
        import traceback
        traceback.print_exc()
        return None


# ---------------- UI Layout ----------------
def main():
    st.set_page_config(page_title="HR Resume Processor", layout="wide")

    # Custom styling for a professional look
    st.markdown(
        """
        <style>
        .main-title {
            text-align: center;
            font-size: 36px !important;
            font-weight: bold;
            color: #2E86C1;
        }
        .sub-header {
            font-size: 20px !important;
            font-weight: 600;
            color: #1B4F72;
            margin-top: 20px;
        }
        .stTabs [role="tablist"] button {
            font-size: 16px !important;
            font-weight: 600 !important;
        }
        .stDownloadButton button {
            background-color: #2E86C1;
            color: white;
            border-radius: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="main-title">📄 AI Resume Screening Platform</div>', unsafe_allow_html=True)

    # Tabs (Documentation first, then JD, Resumes, Rankings)
    tabs = st.tabs(["📘 Documentation", "📌 Upload Requirements", "📁 Upload Resumes", "🏆 Rankings"])

    # ---------------- Tab 1: Documentation ----------------
    with tabs[0]:
        st.markdown('<div class="sub-header">📘 How the System Works</div>', unsafe_allow_html=True)

        st.markdown("""
        Welcome to the **AI Resume Screening Platform**.  
        This tool automates resume evaluation against Job Descriptions (JDs).  
        
        ### 🔄 Data Flow:
        1. **Upload JD** → Extracted and processed with AI to capture role-specific keywords.
        2. **Upload Resumes** → Extracted and converted to structured text.
        3. **AI Processing** → Each resume analyzed for:
            - Technical skills
            - Domain relevance
            - Projects & experience
        4. **Ranking** → Candidates are scored & sorted based on JD alignment.

        ### ⚠️ Precautions:
        - Ensure resumes are in **PDF format**.
        - JD should be **specific and complete** for better ranking accuracy.
        - Avoid duplicate resumes; only latest versions should be uploaded.

        ### ✅ Ideal Steps:
        1. Upload the **Job Description** (PDF or text).
        2. Process JD using **"⚙️ Process JD"** button.
        3. Upload all **Resumes** in PDF format.
        4. Click **"⚙️ Process & Rank Resumes"**.
        5. View/download results from **Rankings tab**.
        """)

    # ---------------- Tab 2: Upload JD ----------------
    with tabs[1]:
        st.markdown('<div class="sub-header">📌 Job Description Input</div>', unsafe_allow_html=True)
        st.info(
            "- Upload the official Job Description PDF.\n"
            "- Or paste raw JD text in the text area below.\n"
            "- This will be used as the benchmark for evaluating resumes."
        )

        jd_pdf = st.file_uploader("Upload JD (PDF only):", type=["pdf"], key="jd_pdf")
        jd_text_input = st.text_area("Or paste JD text here:", height=200, key="jd_text")
        
        st.markdown("---")
        st.markdown("### 🔍 Filter Requirements (Optional)")
        st.info(
            "Enter filtering criteria for candidate screening.\n"
            "**Mandatory Compliances**: Candidates missing ANY mandatory requirement will be filtered out.\n"
            "**Soft Compliances**: These will be shown in rankings but won't filter candidates."
        )
        
        # Two separate sections for mandatory and soft compliances
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 🔴 Mandatory Compliances (Must-Have)")
            mandatory_requirements = st.text_area(
                "Mandatory Requirements:",
                height=120,
                key="mandatory_requirements",
                placeholder="Example: Must have: Python, React. Experience: 2-3 years. Department: IT only.",
                help="Candidates missing ANY mandatory requirement will be filtered out before ranking."
            )
        
        with col2:
            st.markdown("#### 🟢 Soft Compliances (Nice-to-Have)")
            soft_requirements = st.text_area(
                "Soft Requirements:",
                height=120,
                key="soft_requirements",
                placeholder="Example: Location: Pune preferred. Nice to have: AWS, Docker.",
                help="These will be displayed in rankings but won't filter candidates."
            )

        if st.button("⚙️ Process JD", disabled=st.session_state.get("jd_done", False)):
            final_text = ""
            if jd_pdf:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    shutil.copyfileobj(jd_pdf, tmp)
                    tmp_path = tmp.name
                try:
                    pdf_text = extract_pdf_text(tmp_path)
                    final_text += pdf_text + "\n"
                    st.success("📄 Extracted text from uploaded JD PDF.")
                except Exception as e:
                    st.error(f"❌ Error extracting PDF: {e}")

            if jd_text_input.strip():
                final_text += jd_text_input.strip()
                st.success("📝 Added text input to JD.")

            if final_text.strip():
                with open(JD_FILE, "w", encoding="utf-8") as f:
                    f.write(final_text.strip())
                st.success(f"✅ JD saved at {JD_FILE}")
                
                # Parse and save HR filter requirements (mandatory and soft separately)
                hr_filter_json = Path("InputThread/JD/HR_Filter_Requirements.json")
                hr_filter_json.parent.mkdir(parents=True, exist_ok=True)
                
                # Parse mandatory requirements if provided
                mandatory_text = mandatory_requirements.strip() if mandatory_requirements else ""
                soft_text = soft_requirements.strip() if soft_requirements else ""
                
                if mandatory_text or soft_text:
                    # Parse both sections separately
                    hr_filter_structured = {}
                    
                    if mandatory_text:
                        st.info("🔄 Parsing mandatory compliances...")
                        mandatory_parsed = parse_hr_filter_requirements(mandatory_text)
                        hr_filter_structured["mandatory_compliances"] = {
                            "raw_prompt": mandatory_text,
                            "structured": mandatory_parsed.get("structured", {})
                        }
                        st.success(f"✅ Parsed {len(mandatory_parsed.get('structured', {}))} mandatory requirement field(s)")
                    
                    if soft_text:
                        st.info("🔄 Parsing soft compliances...")
                        soft_parsed = parse_hr_filter_requirements(soft_text)
                        hr_filter_structured["soft_compliances"] = {
                            "raw_prompt": soft_text,
                            "structured": soft_parsed.get("structured", {})
                        }
                        st.success(f"✅ Parsed {len(soft_parsed.get('structured', {}))} soft requirement field(s)")
                    
                    # Ensure both sections exist (even if empty)
                    if "mandatory_compliances" not in hr_filter_structured:
                        hr_filter_structured["mandatory_compliances"] = {
                            "raw_prompt": "",
                            "structured": {}
                        }
                    if "soft_compliances" not in hr_filter_structured:
                        hr_filter_structured["soft_compliances"] = {
                            "raw_prompt": "",
                            "structured": {}
                        }
                    
                    # Save as JSON
                    with open(hr_filter_json, "w", encoding="utf-8") as f:
                        json.dump(hr_filter_structured, f, indent=2)
                    st.success("✅ HR filter requirements parsed and saved")
                else:
                    # Create empty filter structure if no requirements provided
                    empty_filter = {
                        "mandatory_compliances": {
                            "raw_prompt": "",
                            "structured": {}
                        },
                        "soft_compliances": {
                            "raw_prompt": "",
                            "structured": {}
                        }
                    }
                    with open(hr_filter_json, "w", encoding="utf-8") as f:
                        json.dump(empty_filter, f, indent=2)
                    st.info("ℹ️ No HR requirements provided - all candidates will pass through without filtering")

                try:
                    st.info("🔄 Running AI JD processing...")
                    # Run JDGpt.py in-process (main thread) instead of subprocess
                    try:
                        runpy.run_path('InputThread/AI Processing/JDGpt.py', run_name='__main__')
                        st.success("🎯 JD processing complete!")
                        st.session_state.jd_done = True
                    except Exception as _e:
                        st.error(f"❌ Error running JDGpt.py: {_e}")
                    
                except Exception as e:
                    st.error(f"❌ Error in JD processing: {e}")
            else:
                st.warning("⚠️ Please upload a JD PDF or enter text before processing.")

    # ---------------- Tab 3: Upload Resumes ----------------
    with tabs[2]:
        st.markdown('<div class="sub-header">📁 Upload Resume Folder (PDFs only)</div>', unsafe_allow_html=True)
        st.info(
            "- Upload one or multiple resumes in **PDF format**.\n"
            "- Each resume will be extracted into plain text.\n"
            "- Only supported and readable resumes will be processed."
        )

        uploaded_files = st.file_uploader(
            "Upload multiple PDF resumes:",
            type=["pdf"],
            accept_multiple_files=True
        )

        # Show already processed resumes
        processed_files = list(PROCESSED_TXT_DIR.glob("*.txt"))
        if processed_files:
            st.markdown("### 📂 Already Processed Resumes:")
            with st.container():
                for txt_file in processed_files:
                    st.text(txt_file.name)

        if uploaded_files:
            # Load existing PDF mapping
            pdf_mapping = {}
            if PDF_MAPPING_FILE.exists():
                try:
                    with open(PDF_MAPPING_FILE, "r", encoding="utf-8") as f:
                        pdf_mapping = json.load(f)
                except Exception:
                    pdf_mapping = {}
            
            # Clear Processed-TXT and ProcessedJson before uploading new files (removes old resumes from previous sessions)
            cleared_txt_count = 0
            cleared_json_count = 0
            
            # Clear Processed-TXT directory
            if list(PROCESSED_TXT_DIR.glob("*.txt")):
                st.info("🧹 Clearing old resumes from previous session...")
                for txt_file in PROCESSED_TXT_DIR.glob("*.txt"):
                    try:
                        txt_file.unlink()
                        cleared_txt_count += 1
                    except Exception as e:
                        st.warning(f"⚠️ Could not delete {txt_file.name}: {e}")
            
            # Clear ProcessedJson directory (old processed JSONs)
            if PROCESSED_JSON_DIR.exists():
                for json_file in PROCESSED_JSON_DIR.glob("*.json"):
                    if json_file.name != "example_output.json":  # Don't delete example
                        try:
                            json_file.unlink()
                            cleared_json_count += 1
                        except Exception as e:
                            st.warning(f"⚠️ Could not delete {json_file.name}: {e}")
            
            if cleared_txt_count > 0 or cleared_json_count > 0:
                st.success(f"✅ Cleared {cleared_txt_count} old text file(s) and {cleared_json_count} old JSON file(s) from previous session")
            
            # Track newly uploaded files for this batch
            newly_uploaded_files = []
            
            # Extract new PDFs and save originals
            for file in uploaded_files:
                # Save original PDF to Uploaded_Resumes directory
                resume_name = Path(file.name).stem
                saved_pdf_path = UPLOADED_RESUMES_DIR / file.name
                
                # Save the PDF file
                with open(saved_pdf_path, "wb") as f:
                    f.write(file.getbuffer())
                
                # Update PDF mapping immediately with filename (will be updated with candidate_id later)
                pdf_mapping_file = UPLOADED_RESUMES_DIR / "pdf_mapping.json"
                if pdf_mapping_file.exists():
                    try:
                        with open(pdf_mapping_file, "r", encoding="utf-8") as f:
                            pdf_mapping = json.load(f)
                    except Exception:
                        pdf_mapping = {}
                else:
                    pdf_mapping = {}
                
                # Map by filename (will be updated with candidate_id during processing)
                pdf_mapping[file.name] = str(saved_pdf_path.resolve())
                pdf_mapping[resume_name] = str(saved_pdf_path.resolve())  # Also map by stem
                
                try:
                    with open(pdf_mapping_file, "w", encoding="utf-8") as f:
                        json.dump(pdf_mapping, f, indent=2)
                except Exception:
                    pass  # Non-critical
                
                # Use saved PDF for extraction
                try:
                    output_text = route_pdf(str(saved_pdf_path), str(PROCESSED_TXT_DIR), original_name=file.name)
                    if output_text:
                        st.success(f"✅ Extracted: {file.name}")
                        # Track this as a newly uploaded file
                        newly_uploaded_files.append(Path(output_text).name)  # Store just the filename
                    else:
                        st.warning(f"⚠️ Skipped: {file.name}")
                except Exception as e:
                    st.error(f"❌ Error processing {file.name}: {e}")
            
            # Store list of newly uploaded files in session state for processing
            st.session_state.newly_uploaded_files = newly_uploaded_files

            if st.button("⚙️ Process & Rank Resumes", disabled=st.session_state.get("pipeline_ran", False)):
                if not st.session_state.get("pipeline_ran", False):
                    st.session_state.pipeline_ran = True
                    
                    # Clear ranking files before processing (ProcessedJson already cleared when resumes were uploaded)
                    st.info("🧹 Clearing previous ranking results...")
                    cleared = []
                    for f in FILES_TO_CLEAR:
                        try:
                            if os.path.exists(f):
                                os.remove(f)
                                cleared.append(f)
                        except Exception as e:
                            print(f"⚠️ Error deleting {f}: {e}")
                    if cleared:
                        st.success(f"✅ Cleared {len(cleared)} ranking file(s) from previous run")

                    # Enable parallel processing by default - optimized for local processing
                    import multiprocessing
                    # Use CPU count or default to 8 for optimal performance
                    max_workers = min(os.cpu_count() or 8, 16)  # Cap at 16 to avoid overwhelming system
                    os.environ["ENABLE_PARALLEL"] = "true"
                    os.environ["MAX_WORKERS"] = str(max_workers)
                    
                    # Step 1: AI processing (must run first)
                    try:
                        st.info("🔄 Step 1/6: Running AI processing (TXT → JSON) [PARALLEL]...")
                        print(f"\n{'='*60}")
                        print("STEP 1/6: Running AI processing (TXT → JSON) [PARALLEL]...")
                        print(f"{'='*60}\n")
                        
                        # Pass newly uploaded files list to GptJson via environment variable
                        newly_uploaded = st.session_state.get("newly_uploaded_files", [])
                        if newly_uploaded:
                            os.environ["ONLY_PROCESS_FILES"] = ",".join(newly_uploaded)
                            print(f"[INFO] Processing only {len(newly_uploaded)} newly uploaded file(s)")
                        
                        runpy.run_path("InputThread/AI Processing/GptJson.py", run_name='__main__')
                        
                        # Clear the environment variable after use
                        if newly_uploaded:
                            os.environ.pop("ONLY_PROCESS_FILES", None)
                        
                        print("✅ Step 1 completed successfully\n")
                    except Exception as e:
                        error_msg = f"❌ Error in step 1: {str(e)}"
                        print(f"\n{'='*60}\nERROR: {error_msg}\n{'='*60}\n")
                        import traceback
                        traceback.print_exc()
                        st.error(error_msg)
                        st.exception(e)
                        st.stop()
                    
                    # Step 2: Early Filtering (must run after AI processing)
                    try:
                        st.info("🔄 Step 2/6: Running Early Filtering (HR Requirements)...")
                        print(f"\n{'='*60}\nSTEP 2/6: Running Early Filtering...\n{'='*60}\n")
                        runpy.run_path("ResumeProcessor/EarlyFilter.py", run_name='__main__')
                        print("✅ Step 2 completed successfully\n")
                    except Exception as e:
                        error_msg = f"❌ Error in step 2: {str(e)}"
                        print(f"\n{'='*60}\nERROR: {error_msg}\n{'='*60}\n")
                        import traceback
                        traceback.print_exc()
                        st.error(error_msg)
                        st.exception(e)
                        st.stop()
                    
                    # Steps 3-5: Parallel scoring modules (can run in parallel)
                    from concurrent.futures import ThreadPoolExecutor, as_completed
                    
                    scoring_steps = [
                        ("Running ProjectProcess.py...", "ResumeProcessor/ProjectProcess.py"),
                        ("Running KeywordComparitor.py...", "ResumeProcessor/KeywordComparitor.py"),
                        ("Running SemanticComparitor.py...", "ResumeProcessor/SemanticComparitor.py"),
                    ]
                    
                    st.info("🔄 Steps 3-5/6: Running scoring modules in parallel...")
                    print(f"\n{'='*60}\nSTEPS 3-5/6: Running scoring modules in parallel...\n{'='*60}\n")
                    
                    with ThreadPoolExecutor(max_workers=3) as executor:
                        futures = {executor.submit(runpy.run_path, script_path, run_name='__main__'): (i+3, msg) 
                                  for i, (msg, script_path) in enumerate(scoring_steps)}
                        
                        for future in as_completed(futures):
                            step_num, msg = futures[future]
                            try:
                                future.result()
                                print(f"✅ Step {step_num} ({msg}) completed successfully")
                            except Exception as e:
                                error_msg = f"❌ Error in step {step_num} ({msg}): {str(e)}"
                                print(f"\n{'='*60}\nERROR: {error_msg}\n{'='*60}\n")
                                import traceback
                                traceback.print_exc()
                                st.error(error_msg)
                                st.exception(e)
                                st.stop()
                    
                    # Step 6: Final Ranking (must run last)
                    try:
                        st.info("🔄 Step 6/6: Running FinalRanking.py (with LLM Re-ranking)...")
                        print(f"\n{'='*60}\nSTEP 6/6: Running FinalRanking.py...\n{'='*60}\n")
                        runpy.run_path(str(FINAL_RANKING_SCRIPT), run_name='__main__')
                        print("✅ Step 6 completed successfully\n")
                    except Exception as e:
                        error_msg = f"❌ Error in step 6: {str(e)}"
                        print(f"\n{'='*60}\nERROR: {error_msg}\n{'='*60}\n")
                        import traceback
                        traceback.print_exc()
                        st.error(error_msg)
                        st.exception(e)
                        st.stop()
                    
                    print(f"\n{'='*60}\n✅ ALL STEPS COMPLETED SUCCESSFULLY\n{'='*60}\n")
                    st.success("🎯 Resume ranking complete!")
                    st.session_state.active_tab = 3  # auto-jump to Rankings

    # ---------------- Tab 4: Rankings ----------------
    with tabs[3]:
        st.markdown('<div class="sub-header">🏆 Final Rankings</div>', unsafe_allow_html=True)
        st.info(
            "- Ranked candidates based on JD alignment and HR filter requirements.\n"
            "- Higher scores = stronger match to the requirements.\n"
            "- Click on candidate name to view detailed compliance information."
        )

        # Load ranking data
        ranking_file = Path("Ranking/Final_Ranking.json")
        if ranking_file.exists():
            try:
                with open(ranking_file, "r", encoding="utf-8") as f:
                    ranking_data = json.load(f)
                
                ranking = ranking_data.get("ranking", {}).get("candidates", [])
                
                if ranking:
                    st.success(f"Showing {len(ranking)} ranked candidates (pre-filtered for HR requirements)")
                    
                    # Helper function to get PDF path for candidate (defined before use)
                    def get_resume_pdf_path(candidate_id: str, candidate_name: str) -> Path | None:
                        """Get PDF path for a candidate by candidate_id or name."""
                        # Try to load mapping file
                        if PDF_MAPPING_FILE.exists():
                            try:
                                with open(PDF_MAPPING_FILE, "r", encoding="utf-8") as f:
                                    pdf_mapping = json.load(f)
                                    
                                    # Try candidate_id first (most reliable)
                                    if candidate_id and candidate_id in pdf_mapping:
                                        pdf_path = Path(pdf_mapping[candidate_id])
                                        if pdf_path.exists():
                                            return pdf_path
                                    
                                    # Try normalized candidate name
                                    if candidate_name:
                                        normalized_name = candidate_name.strip().title()
                                        if normalized_name in pdf_mapping:
                                            pdf_path = Path(pdf_mapping[normalized_name])
                                            if pdf_path.exists():
                                                return pdf_path
                                        
                                        # Try various name formats
                                        name_variants = [
                                            candidate_name,
                                            candidate_name.replace(" ", "_"),
                                            candidate_name.replace(" ", "-"),
                                            candidate_name.lower(),
                                            candidate_name.upper(),
                                        ]
                                        for variant in name_variants:
                                            if variant in pdf_mapping:
                                                pdf_path = Path(pdf_mapping[variant])
                                                if pdf_path.exists():
                                                    return pdf_path
                            except Exception as e:
                                print(f"⚠️ Error reading PDF mapping: {e}")
                        
                        # Fallback: search in Uploaded_Resumes directory by name
                        if candidate_name and UPLOADED_RESUMES_DIR.exists():
                            # Normalize candidate name for matching
                            normalized_candidate = candidate_name.lower().replace(" ", "_").replace("-", "_")
                            
                            # Try to find PDF with similar name
                            for pdf_file in UPLOADED_RESUMES_DIR.glob("*.pdf"):
                                pdf_stem = pdf_file.stem.lower().replace(" ", "_").replace("-", "_")
                                # Check if names match (either direction)
                                if normalized_candidate in pdf_stem or pdf_stem in normalized_candidate:
                                    return pdf_file
                                
                                # Also try exact match with original name
                                if candidate_name.lower() in pdf_file.stem.lower() or \
                                   pdf_file.stem.lower() in candidate_name.lower():
                                    return pdf_file
                        
                        return None
                    
                    # Download selected resumes as ZIP - wrapped in form to prevent reruns on checkbox clicks
                    st.markdown("### 📥 Download Selected Resumes")
                    st.info("Select candidates using checkboxes below, then click the download button to get all selected resumes in a ZIP file.")
                    
                    # Wrap checkboxes and download in a form to prevent reruns
                    with st.form("resume_selection_form", clear_on_submit=False):
                        st.markdown("---")
                        st.markdown("### 🏆 Candidate Rankings")
                        
                        # Add "Select All" / "Deselect All" buttons
                        col_select_all, col_deselect_all = st.columns(2)
                        with col_select_all:
                            if st.form_submit_button("✅ Select All", use_container_width=True):
                                for cand in ranking:
                                    candidate_id = cand.get("candidate_id")
                                    rank = cand.get("Rank", 0)
                                    checkbox_key = f"select_{candidate_id}_{rank}"
                                    st.session_state[checkbox_key] = True
                        
                        with col_deselect_all:
                            if st.form_submit_button("❌ Deselect All", use_container_width=True):
                                for cand in ranking:
                                    candidate_id = cand.get("candidate_id")
                                    rank = cand.get("Rank", 0)
                                    checkbox_key = f"select_{candidate_id}_{rank}"
                                    st.session_state[checkbox_key] = False
                        
                        st.markdown("---")
                        
                        # Helper function to get compliance summary
                        def get_compliance_summary(candidate):
                            """Get compliance summary for display."""
                            met = candidate.get("requirements_met", [])
                            missing = candidate.get("requirements_missing", [])
                            total = len(met) + len(missing)
                            
                            if total == 0:
                                return "No filters", "info"
                            
                            met_count = len(met)
                            if met_count == total:
                                return f"✅ {met_count}/{total}", "success"
                            elif met_count > 0:
                                return f"⚠️ {met_count}/{total}", "warning"
                            else:
                                return f"❌ 0/{total}", "error"
                        
                        # Determine whether HR requirements exist (check soft compliances for display)
                        hr_filter_file = Path("InputThread/JD/HR_Filter_Requirements.json")
                        hr_has_requirements = False
                        if hr_filter_file.exists():
                            try:
                                with hr_filter_file.open("r", encoding="utf-8") as _f:
                                    _hr = json.load(_f)
                                
                                # Check new format: soft_compliances
                                _soft_compliances = _hr.get("soft_compliances", {})
                                _structured = _soft_compliances.get("structured", {}) if _soft_compliances else {}
                                
                                # Backward compatibility: check old format
                                if not _structured and _hr.get("structured"):
                                    _structured = _hr.get("structured", {})
                                
                                def _field_has_value(v):
                                    if v is None:
                                        return False
                                    if isinstance(v, bool):
                                        return v
                                    if isinstance(v, (list, tuple, set)):
                                        return len(v) > 0
                                    if isinstance(v, dict):
                                        if v.get("specified", False):
                                            return True
                                        for kk, vv in v.items():
                                            if kk != "specified" and vv not in (None, [], {}, ""):
                                                return True
                                        return False
                                    return bool(v)
                                
                                # Check if ANY soft compliance field has value (dynamic - works with any field)
                                hr_has_requirements = any(_field_has_value(v) for v in _structured.values())
                            except:
                                hr_has_requirements = False

                        # Display candidates with expandable details
                        for cand in ranking:
                            rank = cand.get("Rank", 0)
                            name = cand.get("name", "Unknown")
                            score = cand.get("Re_Rank_Score", cand.get("Final_Score", 0.0))
                            candidate_id = cand.get("candidate_id")
                            
                            # Create expander for each candidate
                            with st.expander(f"**#{rank}** {name} | Score: {score:.3f}"):
                                col1, col2, col3 = st.columns([2, 2, 1])
                                
                                with col1:
                                    st.markdown(f"**Rank:** {rank}")
                                    st.markdown(f"**Score:** {score:.3f}")
                                    
                                    # Show compliance summary - check both requirement_compliance and requirements_met/missing
                                    requirements_met = cand.get("requirements_met", [])
                                    requirements_missing = cand.get("requirements_missing", [])
                                    
                                    # If not set, try to extract from requirement_compliance
                                    if (not requirements_met and not requirements_missing) and cand.get("requirement_compliance"):
                                        compliance = cand.get("requirement_compliance", {})
                                        if isinstance(compliance, dict) and compliance:
                                            requirements_met = [req_type for req_type, comp in compliance.items() if comp.get("meets", False)]
                                            requirements_missing = [req_type for req_type, comp in compliance.items() if not comp.get("meets", False)]
                                    
                                    # Update cand dict for get_compliance_summary
                                    if requirements_met or requirements_missing:
                                        cand["requirements_met"] = requirements_met
                                        cand["requirements_missing"] = requirements_missing
                                    
                                    # Show compliance if candidate has compliance data OR if HR requirements exist
                                    has_compliance_data = (cand.get("requirement_compliance") or requirements_met or requirements_missing)
                                    if (hr_has_requirements or has_compliance_data) and has_compliance_data:
                                        compliance_summary, status = get_compliance_summary(cand)
                                        if status == "success":
                                            st.success(f"**Compliance:** {compliance_summary}")
                                        elif status == "warning":
                                            st.warning(f"**Compliance:** {compliance_summary}")
                                        elif status == "error":
                                            st.error(f"**Compliance:** {compliance_summary}")
                                        else:
                                            st.info(f"**Compliance:** {compliance_summary}")
                                
                                with col2:
                                    # Show scores breakdown
                                    st.markdown("**Score Breakdown:**")
                                    if cand.get("project_aggregate") is not None:
                                        st.write(f"  • Project: {cand.get('project_aggregate', 0):.3f}")
                                    if cand.get("Keyword_Score") is not None:
                                        st.write(f"  • Keyword: {cand.get('Keyword_Score', 0):.3f}")
                                    if cand.get("Semantic_Score") is not None:
                                        st.write(f"  • Semantic: {cand.get('Semantic_Score', 0):.3f}")
                                
                                with col3:
                                    # Checkbox for download selection
                                    pdf_path = get_resume_pdf_path(candidate_id, name)
                                    if pdf_path and pdf_path.exists():
                                        # Checkbox for selecting candidate for ZIP download
                                        st.checkbox(
                                            "Select for download",
                                            key=f"select_{candidate_id}_{rank}",
                                            help="Check to include this candidate's resume in the ZIP download"
                                        )
                                    else:
                                        st.info("📄 PDF not available")
                                
                                # Show compliance details - ensure we have the data
                                requirements_met = cand.get("requirements_met", [])
                                requirements_missing = cand.get("requirements_missing", [])
                                compliance = cand.get("requirement_compliance", {})
                                
                                # If not set, try to extract from requirement_compliance
                                if (not requirements_met and not requirements_missing) and compliance:
                                    if isinstance(compliance, dict) and compliance:
                                        requirements_met = [req_type for req_type, comp in compliance.items() if comp.get("meets", False)]
                                        requirements_missing = [req_type for req_type, comp in compliance.items() if not comp.get("meets", False)]
                                
                                # Show compliance details if candidate has compliance data OR if HR requirements exist
                                has_compliance_data = (compliance or requirements_met or requirements_missing)
                                if (hr_has_requirements or has_compliance_data) and has_compliance_data:
                                    st.markdown("---")
                                    st.markdown("### 📋 Compliance Details")
                                    
                                    if requirements_met:
                                        st.success(f"**✅ Requirements Met ({len(requirements_met)}):** {', '.join(requirements_met)}")
                                        for req_type in requirements_met:
                                            req_comp = compliance.get(req_type, {})
                                            if req_comp:
                                                details = req_comp.get("details", "")
                                                if details:
                                                    st.write(f"  • **{req_type.replace('_', ' ').title()}**: {details}")
                                    
                                    if requirements_missing:
                                        st.error(f"**❌ Requirements Missing ({len(requirements_missing)}):** {', '.join(requirements_missing)}")
                                        for req_type in requirements_missing:
                                            req_comp = compliance.get(req_type, {})
                                            if req_comp:
                                                details = req_comp.get("details", "")
                                                if details:
                                                    st.write(f"  • **{req_type.replace('_', ' ').title()}**: {details}")
                        
                        # Collect selected candidates from session state (after form submission)
                        selected_candidates = []
                        for cand in ranking:
                            candidate_id = cand.get("candidate_id")
                            rank = cand.get("Rank", 0)
                            checkbox_key = f"select_{candidate_id}_{rank}"
                            if st.session_state.get(checkbox_key, False):
                                selected_candidates.append(cand)
                        
                        # Form submit button - only triggers rerun when clicked
                        form_submitted = st.form_submit_button(
                            label=f"📥 Download {len(selected_candidates)} Selected Resume(s) as ZIP" if selected_candidates else "📥 Download Selected Resumes (ZIP)",
                            type="primary",
                            use_container_width=True
                        )
                        
                        # Process form submission
                        if form_submitted:
                            if selected_candidates:
                                zip_filename = f"Selected_Resumes_{len(selected_candidates)}_candidates.zip"
                                
                                # Create ZIP file
                                with st.spinner(f"Preparing ZIP file with {len(selected_candidates)} resume(s)..."):
                                    zip_data = create_resumes_zip(selected_candidates, get_resume_pdf_path)
                                    
                                    if zip_data:
                                        # Store ZIP data in session state for download
                                        st.session_state["zip_download_data"] = zip_data
                                        st.session_state["zip_download_filename"] = zip_filename
                                        st.session_state["zip_download_count"] = len(selected_candidates)
                                        st.success(f"✅ ZIP file ready! Click the download button below.")
                                    else:
                                        st.error("❌ Error creating ZIP file. Please try again.")
                            else:
                                st.warning("⚠️ Please select at least one candidate to download.")
                    
                    # Display download button outside form (only shown after form submission)
                    if "zip_download_data" in st.session_state and st.session_state.get("zip_download_count", 0) > 0:
                        st.markdown("---")
                        st.download_button(
                            label=f"📥 Download {st.session_state['zip_download_count']} Selected Resume(s) as ZIP",
                            data=st.session_state["zip_download_data"],
                            file_name=st.session_state["zip_download_filename"],
                            mime="application/zip",
                            type="primary",
                            use_container_width=True,
                            key="final_download_zip_button"
                        )
                        st.success(f"✅ Ready to download {st.session_state['zip_download_count']} resume(s) + DisplayRanks.txt")
                    
                    # Download button
                    with open(DISPLAY_RANKS, "rb") as f:
                        st.download_button(
                            label="⬇️ Download Rankings File",
                            data=f,
                            file_name="DisplayRanks.txt",
                            mime="text/plain"
                        )
                else:
                    st.info("No candidates in ranking. Run the pipeline first.")
                    
            except json.JSONDecodeError:
                st.error("Error reading ranking file. Please run the pipeline again.")
            except Exception as e:
                st.error(f"Error loading rankings: {e}")
        else:
            st.info("No rankings available yet. Run 'Process & Rank Resumes' first.")

        if st.button("🗑️ Clear Previous Run Data"):
            cleared = clear_previous_run()
            if cleared:
                st.success(f"✅ Cleared {len(cleared)} files/folders")
                st.session_state.pipeline_ran = False  # Reset pipeline state
                st.session_state.jd_done = False  # Reset JD state
            else:
                st.info("No files to clear.")
        
        st.markdown("---")
        st.markdown("### 📋 About File Management")
        st.info(
            "**When to clear files:**\n"
            "- Clear before starting a new batch of resumes\n"
            "- Clear if you see duplicate candidates in rankings\n"
            "- Clear if you want to reprocess all resumes from scratch\n\n"
            "**Files that are cleared:**\n"
            "- All processed resumes (ProcessedJson/, Processed-TXT/)\n"
            "- All ranking files (Ranking/)\n"
            "- Processing index (Processed_Resume_Index.txt)\n\n"
            "**Files that are NOT cleared:**\n"
            "- JD files (JD/JD.txt, JD/JD.json) - kept for reuse"
        )



if __name__ == "__main__":
    main()

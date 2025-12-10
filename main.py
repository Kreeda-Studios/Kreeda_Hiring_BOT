import os
import streamlit as st
from pathlib import Path
import tempfile
import shutil
import subprocess
import json
import runpy

from InputThread.file_router import route_pdf  # updated function name
from PyPDF2 import PdfReader  # for PDF extraction

# Constants
PROCESSED_TXT_DIR = Path("Processed-TXT")
PROCESSED_JSON_DIR = Path("ProcessedJson")
JD_FILE = Path("InputThread/JD/JD.txt")

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
    
    # Warning notice for Streamlit Cloud (ephemeral storage)
    st.warning(
        "⚠️ **Note for Streamlit Cloud users:** This app uses ephemeral storage. "
        "All uploaded files and processed data will be lost when the app restarts or sleeps. "
        "Please download your results before closing the session."
    )

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
        - **Streamlit Cloud users:** Data is ephemeral - download results before closing the session.

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
            "Enter additional filtering criteria for candidate re-ranking.\n"
            "Examples: 'Experience needed: 2-3 years in Python', 'Must have: React, Node.js', 'Location: Remote only'"
        )
        filter_requirements = st.text_area(
            "Filter Requirements:",
            height=100,
            key="filter_requirements",
            placeholder="Example: Experience needed: 2-3 years in Python development. Must have: React, Node.js, AWS. Location: Remote only."
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
                
                # Save filter requirements if provided
                if filter_requirements and filter_requirements.strip():
                    filter_file = Path("InputThread/JD/Filter_Requirements.txt")
                    filter_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(filter_file, "w", encoding="utf-8") as f:
                        f.write(filter_requirements.strip())
                    st.success("✅ Filter requirements saved")
                else:
                    # Clear filter file if empty
                    filter_file = Path("InputThread/JD/Filter_Requirements.txt")
                    if filter_file.exists():
                        filter_file.unlink()

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
            # Clear Processed-TXT before uploading new files (removes old resumes from previous sessions)
            if list(PROCESSED_TXT_DIR.glob("*.txt")):
                st.info("🧹 Clearing old resumes from previous session...")
                cleared_count = 0
                for txt_file in PROCESSED_TXT_DIR.glob("*.txt"):
                    try:
                        txt_file.unlink()
                        cleared_count += 1
                    except Exception as e:
                        st.warning(f"⚠️ Could not delete {txt_file.name}: {e}")
                if cleared_count > 0:
                    st.success(f"✅ Cleared {cleared_count} old resume(s) from previous session")
            
            # Extract new PDFs
            for file in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    shutil.copyfileobj(file, tmp)
                    tmp_path = tmp.name
                try:
                    output_text = route_pdf(tmp_path, str(PROCESSED_TXT_DIR), original_name=file.name)
                    if output_text:
                        st.success(f"✅ Extracted: {file.name}")
                    else:
                        st.warning(f"⚠️ Skipped: {file.name}")
                except Exception as e:
                    st.error(f"❌ Error processing {file.name}: {e}")

            if st.button("⚙️ Process & Rank Resumes", disabled=st.session_state.get("pipeline_ran", False)):
                if not st.session_state.get("pipeline_ran", False):
                    st.session_state.pipeline_ran = True
                    
                    # Auto-clear old JSONs before processing (preserves Processed-TXT extracted text files)
                    st.info("🧹 Clearing previous processing results...")
                    cleared = clear_before_processing()
                    if cleared:
                        st.success(f"✅ Cleared {len(cleared)} files from previous run (preserved extracted text files)")

                    # Enable parallel processing by default (can be disabled if needed)
                    # Reduced to 2 workers for Streamlit Cloud free tier compatibility
                    import os
                    os.environ["ENABLE_PARALLEL"] = "true"
                    os.environ["MAX_WORKERS"] = "2"  # Reduced from 5 for Streamlit Cloud free tier
                    
                    steps = [
                        ("Running AI processing (TXT → JSON) [PARALLEL]...",
                         ["python3", "InputThread/AI Processing/GptJson.py"]),
                        ("Running Early Filtering (HR Requirements)...",
                         ["python3", "ResumeProcessor/EarlyFilter.py"]),
                        ("Running ProjectProcess.py ...",
                         ["python3", "ResumeProcessor/ProjectProcess.py"]),
                        ("Running KeywordComparitor.py ...",
                         ["python3", "ResumeProcessor/KeywordComparitor.py"]),
                        ("Running SemanticComparitor.py ...",
                         ["python3", "ResumeProcessor/SemanticComparitor.py"]),
                        ("Running FinalRanking.py (with LLM Re-ranking)...",
                         ["python3", str(FINAL_RANKING_SCRIPT)]),
                    ]

                    progress = st.progress(0)
                    total = len(steps)

                    for i, (msg, cmd) in enumerate(steps, start=1):
                        try:
                            st.info(f"🔄 Step {i}/{total}: {msg}")
                            print(f"\n{'='*60}")
                            print(f"STEP {i}/{total}: {msg}")
                            print(f"{'='*60}\n")
                                
                            script_path = cmd[1] if isinstance(cmd, (list, tuple)) and len(cmd) > 1 else cmd
                            print(f"Executing: {script_path}")
                            
                            # Run the script
                            runpy.run_path(script_path, run_name='__main__')
                            
                            print(f"✅ Step {i} completed successfully\n")
                            progress.progress(i / total)
                            
                        except Exception as e:
                            error_msg = f"❌ Error in step {i}/{total} ({msg}): {str(e)}"
                            print(f"\n{'='*60}")
                            print(f"ERROR: {error_msg}")
                            print(f"{'='*60}\n")
                            import traceback
                            traceback.print_exc()
                            st.error(error_msg)
                            st.exception(e)  # Show full traceback in UI
                            break

                    if i == total:
                        print(f"\n{'='*60}")
                        print("✅ ALL STEPS COMPLETED SUCCESSFULLY")
                        print(f"{'='*60}\n")
                        st.success("🎯 Resume ranking complete!")
                        st.session_state.active_tab = 3  # auto-jump to Rankings
                    else:
                        st.warning(f"⚠️ Pipeline stopped at step {i}/{total}. Please check errors above.")

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
                    
                    # Display candidates with expandable details
                    for cand in ranking:
                        rank = cand.get("Rank", 0)
                        name = cand.get("name", "Unknown")
                        score = cand.get("Re_Rank_Score", cand.get("Final_Score", 0.0))
                        
                        # Create expander for each candidate
                        with st.expander(f"**#{rank}** {name} | Score: {score:.3f}"):
                            col1, col2 = st.columns(2)
                            
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
                                
                                if cand.get("requirement_compliance") or requirements_met or requirements_missing:
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
                            
                            # Show compliance details - ensure we have the data
                            requirements_met = cand.get("requirements_met", [])
                            requirements_missing = cand.get("requirements_missing", [])
                            compliance = cand.get("requirement_compliance", {})
                            
                            # If not set, try to extract from requirement_compliance
                            if (not requirements_met and not requirements_missing) and compliance:
                                if isinstance(compliance, dict) and compliance:
                                    requirements_met = [req_type for req_type, comp in compliance.items() if comp.get("meets", False)]
                                    requirements_missing = [req_type for req_type, comp in compliance.items() if not comp.get("meets", False)]
                            
                            if compliance or requirements_met or requirements_missing:
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

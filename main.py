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
    "Ranking/DisplayRanks.txt"
]

# Folders to clear between runs
FOLDERS_TO_CLEAR = [
    "ProcessedJson",
    "Processed-TXT",
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

# Cleanup helper
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

                    steps = [
                        ("Running AI processing (TXT → JSON)...",
                         ["python3", "InputThread/AI Processing/GptJson.py"]),
                        ("Running ProjectProcess.py ...",
                         ["python3", "ResumeProcessor/ProjectProcess.py"]),
                        ("Running KeywordComparitor.py ...",
                         ["python3", "ResumeProcessor/KeywordComparitor.py"]),
                        ("Running SemanticComparitor.py ...",
                         ["python3", "ResumeProcessor/SemanticComparitor.py"]),
                        ("Running FinalRanking.py ...",
                         ["python3", str(FINAL_RANKING_SCRIPT)]),
                    ]

                    progress = st.progress(0)
                    total = len(steps)

                    for i, (msg, cmd) in enumerate(steps, start=1):
                        try:
                            st.info(msg)
                                
                            script_path = cmd[1] if isinstance(cmd, (list, tuple)) and len(cmd) > 1 else cmd
                            runpy.run_path(script_path, run_name='__main__')
                        
                            progress.progress(i / total)
                        except Exception as e:
                            st.error(f"❌ Error running {cmd}: {e}")
                            break

                    if i == total:
                        st.success("🎯 Resume ranking complete!")
                        st.session_state.active_tab = 3  # auto-jump to Rankings

    # ---------------- Tab 4: Rankings ----------------
    with tabs[3]:
        st.markdown('<div class="sub-header">🏆 Final Rankings</div>', unsafe_allow_html=True)
        st.info(
            "- Ranked candidates based on JD alignment.\n"
            "- Higher scores = stronger match to the requirements.\n"
            "- You can scroll and also download the ranking file."
        )
    
        # 🔥 RAM-based ranking import (works even if writing to repo fails)
        try:
            from ResumeProcessor.Ranker.FinalRanking import run_ranking, RANKING_RAM
        except Exception:
            RANKING_RAM = []
    
        # 🔘 Button to refresh & load ranking even if file writing fails
        if st.button("🔄 Refresh Rankings"):
            try:
                run_ranking()
                st.success("Rankings refreshed!")
            except Exception as e:
                st.error(f"⚠️ Error refreshing rankings: {e}")
    
        # 🔥 Live ranking table (RAM first preference)
        if RANKING_RAM:
            df = [
                {"Rank": i+1, "Candidate": c["name"], "Score": c["Final_Score"]}
                for i, c in enumerate(RANKING_RAM)
            ]
            st.success(f"Showing {len(df)} ranked candidates")
            st.dataframe(df, use_container_width=True)
    
            # Allow download from RAM
            downloadable = "\n".join(f"{row['Rank']}. {row['Candidate']} | {row['Score']}" for row in df)
            st.download_button(
                label="⬇️ Download Latest Rankings",
                data=downloadable,
                file_name="Rankings.txt",
                mime="text/plain"
            )
    
            st.write("---")  # separator for visual clarity
    
        # ---------------- OLD BEHAVIOUR (kept exactly)
        if DISPLAY_RANKS.exists():
            with open(DISPLAY_RANKS, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]
    
            if lines:
                st.success(f"📄 Showing {len(lines)} ranked candidates from DisplayRanks.txt")
                st.dataframe({"Ranked Candidates": lines})
    
                with open(DISPLAY_RANKS, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Rankings File (Legacy)",
                        data=f,
                        file_name="DisplayRanks.txt",
                        mime="text/plain"
                    )
            else:
                st.info("Ranking file is empty. Run the pipeline first.")
        else:
            st.info("No rankings available yet. Run 'Process & Rank Resumes' first.")
    
        # ---------------- Clear button (unchanged)
        if st.button("🗑️ Clear Previous Run Data"):
            cleared = clear_previous_run()
            if cleared:
                st.success(f"✅ Cleared {len(cleared)} files")
            else:
                st.info("No files to clear.")



if __name__ == "__main__":
    main()

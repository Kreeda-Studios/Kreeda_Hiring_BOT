import os
import streamlit as st
from pathlib import Path
import tempfile
import shutil
import subprocess
import json

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

    tabs = st.tabs(["📘 Documentation", "📌 Upload Requirements", "📁 Upload Resumes", "🏆 Rankings"])

    # ---------------- Tab 1: Documentation ----------------
    with tabs[0]:
        st.markdown('<div class="sub-header">📘 How the System Works</div>', unsafe_allow_html=True)
        st.markdown("""
        Welcome to the **AI Resume Screening Platform**.  
        This tool automates resume evaluation against Job Descriptions (JDs).  
        
        ### 🔄 Data Flow:
        1. **Upload JD**
        2. **Upload Resumes**
        3. **AI Processing**
        4. **Ranking**
        """)

    # ---------------- Tab 2: Upload JD ----------------
    with tabs[1]:
        st.markdown('<div class="sub-header">📌 Job Description Input</div>', unsafe_allow_html=True)
        st.info("- Upload JD PDF or paste JD text below.")

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
                except Exception as e:
                    st.error(f"❌ Error extracting PDF: {e}")

            if jd_text_input.strip():
                final_text += jd_text_input.strip()

            if final_text.strip():
                with open(JD_FILE, "w", encoding="utf-8") as f:
                    f.write(final_text.strip())

                st.info("🔄 Running AI JD processing...")

                # 🔥 main-thread import + execute (NO SUBPROCESS)
                from InputThread.AI_Processing.JDGpt import process_jd
                process_jd()

                st.success("🎯 JD processing complete!")
                st.session_state.jd_done = True
            else:
                st.warning("⚠️ Upload a JD PDF or enter JD text before processing.")

    # ---------------- Tab 3: Upload Resumes ----------------
    with tabs[2]:
        st.markdown('<div class="sub-header">📁 Upload Resume Folder (PDFs only)</div>', unsafe_allow_html=True)
        st.info("- Upload multiple resumes in PDF format.")

        uploaded_files = st.file_uploader(
            "Upload multiple PDF resumes:",
            type=["pdf"],
            accept_multiple_files=True
        )

        processed_files = list(PROCESSED_TXT_DIR.glob("*.txt"))
        if processed_files:
            st.markdown("### 📂 Already Processed Resumes:")
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

                st.session_state.pipeline_ran = True
                progress = st.progress(0)

                # 🔥 direct callable imports (NO SUBPROCESS)
                from InputThread.AI_Processing.GptJson import process_resumes_to_json
                from ResumeProcessor.ProjectProcess import process_projects
                from ResumeProcessor.KeywordComparitor import compare_keywords
                from ResumeProcessor.SemanticComparitor import semantic_compare
                from ResumeProcessor.Ranker.FinalRanking import generate_final_ranking

                steps = [
                    ("Running AI processing (TXT → JSON)...", process_resumes_to_json),
                    ("Running ProjectProcess.py ...", process_projects),
                    ("Running KeywordComparitor.py ...", compare_keywords),
                    ("Running SemanticComparitor.py ...", semantic_compare),
                    ("Running FinalRanking.py ...", generate_final_ranking),
                ]

                total = len(steps)

                for i, (msg, func) in enumerate(steps, start=1):
                    st.info(msg)
                    func()    # 🔥 main thread execution
                    progress.progress(i / total)

                st.success("🎯 Resume ranking complete!")
                st.session_state.active_tab = 3

    # ---------------- Tab 4: Rankings ----------------
    with tabs[3]:
        st.markdown('<div class="sub-header">🏆 Final Rankings</div>', unsafe_allow_html=True)
        st.info("- Download the ranked results.")

        if DISPLAY_RANKS.exists():
            with open(DISPLAY_RANKS, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f.readlines() if line.strip()]

            if lines:
                st.success(f"Showing {len(lines)} ranked candidates")
                st.dataframe({"Ranked Candidates": lines})

                with open(DISPLAY_RANKS, "rb") as f:
                    st.download_button(
                        label="⬇️ Download Rankings File",
                        data=f,
                        file_name="DisplayRanks.txt",
                        mime="text/plain"
                    )
            else:
                st.info("Ranking file is empty.")
        else:
            st.info("No rankings available yet.")

        if st.button("🗑️ Clear Previous Run Data"):
            cleared = clear_previous_run()
            if cleared:
                st.success(f"Cleared {len(cleared)} files")
            else:
                st.info("No files to clear.")


if __name__ == "__main__":
    main()

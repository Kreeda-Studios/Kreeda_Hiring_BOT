# HR Hiring Bot - AI Resume Screening Platform

## Overview

An AI-powered resume screening system that automates candidate evaluation against job descriptions. The system uses OpenAI GPT models for parsing, embeddings for semantic matching, and a hybrid scoring system for ranking candidates.

**Key Features:**
- 📄 Automatic resume parsing from PDFs
- 🎯 AI-powered JD analysis and skill extraction
- 🔍 Multi-dimensional candidate scoring (Project, Semantic, Keyword)
- 📊 Intelligent ranking with compliance filtering
- 🚀 Parallel processing for fast batch operations
- 💾 Smart caching to reduce API costs

---

## Quick Start

> **📖 For detailed setup instructions, see [SETUP.md](SETUP.md)**

### Prerequisites

- Python 3.10 or higher
- pip (Python package manager)
- OpenAI API key ([Get one here](https://platform.openai.com/api-keys))

### Quick Installation

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd Kreeda_Hiring_BOT
   ```

2. **Create and activate virtual environment:**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   
   # Linux/Mac
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   
   Create a `.env` file in the root directory:
   ```env
   OPENAI_API_KEY=your_openai_api_key_here
   ```

5. **Run the application:**
   ```bash
   streamlit run main.py
   ```

   The application will open in your browser at `http://localhost:8501`

**For detailed setup instructions, troubleshooting, and verification steps, see [SETUP.md](SETUP.md)**

---

## Project Structure

```
Kreeda_Hiring_BOT/
├── main.py                          # Streamlit UI and orchestration
├── requirements.txt                 # Python dependencies
├── utils/                           # Shared utilities
│   ├── validation.py               # Pydantic schemas for data validation
│   ├── retry.py                    # Retry logic and circuit breakers
│   ├── cache.py                    # File-based caching
│   └── common.py                   # Common utility functions
├── InputThread/                    # Input processing
│   ├── file_router.py              # PDF routing and classification
│   ├── extract_pdf.py              # PDF text extraction
│   └── AI Processing/
│       ├── JDGpt.py                # JD parsing with GPT
│       └── GptJson.py              # Resume parsing with GPT (parallel)
├── ResumeProcessor/                # Ranking and scoring
│   ├── EarlyFilter.py              # HR requirements filtering
│   ├── ProjectProcess.py           # Project-based scoring
│   ├── KeywordComparitor.py       # Keyword matching scoring
│   ├── SemanticComparitor.py      # Semantic similarity scoring
│   └── Ranker/
│       └── FinalRanking.py         # Final ranking aggregation
├── JD/                             # Job description files
│   ├── JD.txt                      # Raw JD text
│   └── JD.json                     # Structured JD data
├── Processed-TXT/                  # Extracted resume text
├── ProcessedJson/                   # Structured resume JSON
└── Ranking/                        # Final ranking results
    ├── Scores.json                 # All scores combined
    ├── Final_Ranking.json          # Ranked candidates
    └── DisplayRanks.txt            # Human-readable ranking
```

---

## Usage Guide

### For HR Users

1. **Upload Job Description:**
   - Go to "📌 Upload Requirements" tab
   - Upload JD PDF or paste text
   - (Optional) Add filter requirements (experience, skills, location, etc.)
   - Click "⚙️ Process JD"

2. **Upload Resumes:**
   - Go to "📁 Upload Resumes" tab
   - Upload one or multiple PDF resumes
   - Wait for extraction confirmation

3. **Process & Rank:**
   - Click "⚙️ Process & Rank Resumes"
   - Wait for all 6 steps to complete (progress bar shows progress)
   - Processing typically takes 1-2 minutes for 20 resumes

4. **View Rankings:**
   - Go to "🏆 Rankings" tab
   - View ranked candidates with scores
   - Click candidate names for detailed compliance information
   - Use "✅ Select All" / "❌ Deselect All" for bulk download
   - Download rankings or selected PDFs

### Understanding Scores

- **Score Range**: 0.0 to 1.0 (higher is better)
- **0.9 - 1.0**: Excellent match
- **0.7 - 0.9**: Good match
- **0.5 - 0.7**: Moderate match
- **Below 0.5**: Weak match

**Score Components:**
- **Project Score**: Technical depth and project quality (35%)
- **Semantic Score**: Deep understanding and relevance (35%)
- **Keyword Score**: Skills and experience matching (30%)

---

## Configuration

### Environment Variables

| Variable | Description | Required | Source |
|----------|-------------|----------|--------|
| `OPENAI_API_KEY` | OpenAI API key for GPT models and embeddings | **Yes** | [OpenAI Platform](https://platform.openai.com/api-keys) |

### Optional Configuration

- **Parallel Processing**: Enabled by default (5 workers)
- **Caching**: Enabled by default (reduces API costs)
- **Filtering Mode**: Flexible (50% skill match threshold)

---

## Key Features

### 1. Smart Caching
- File-based caching for JD and resume parsing
- Hash-based cache keys (content-based invalidation)
- Embedding cache to reduce API costs
- Instant processing for repeated inputs

### 2. Parallel Processing
- ThreadPoolExecutor for batch resume processing
- 3-4x speedup for large batches
- Configurable worker count (default: 5)

### 3. Robust Error Handling
- Retry logic with exponential backoff
- Circuit breaker pattern to prevent cascading failures
- Graceful degradation (assigns 0 scores, continues processing)
- Comprehensive error logging

### 4. Data Validation
- Pydantic schemas for JD and resume validation
- Type checking and range validation
- Non-blocking warnings for validation issues

### 5. HR Requirements Filtering
- Dynamic filtering based on user-specified requirements
- Experience, skills, location, department validation
- Flexible or strict filtering modes
- Compliance reporting for each candidate

---

## Performance

### Processing Times (Estimated)

| Operation | Time | Notes |
|-----------|------|-------|
| JD Processing | 5-10 sec | First run |
| JD Processing (cached) | <1 sec | Subsequent runs |
| Resume Processing (20, parallel) | 1-2 min | 3-4x faster than sequential |
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

## Troubleshooting

### Common Issues

**Issue: "Module not found" errors**
- **Solution**: Ensure virtual environment is activated and dependencies installed:
  ```bash
  pip install -r requirements.txt
  ```

**Issue: "OPENAI_API_KEY not found"**
- **Solution**: 
  - Check that `.env` file exists in root directory
  - Verify key is correctly set (no extra spaces or quotes)
  - For Streamlit Cloud, configure secrets in UI

**Issue: PDF extraction errors**
- **Solution**: Ensure PyMuPDF and PyPDF2 are installed:
  ```bash
  pip install --upgrade PyMuPDF PyPDF2
  ```
  - Only text-based PDFs are supported (scanned/image PDFs are skipped)

**Issue: No rankings appear**
- **Solution**:
  - Check that all 6 processing steps completed
  - Review filter requirements (may be too strict)
  - Check error messages in UI
  - Try clearing and reprocessing

---

## Technology Stack

| Component | Technology |
|-----------|-----------|
| **UI Framework** | Streamlit 1.51.0 |
| **LLM** | OpenAI GPT-4o-mini (function calling) |
| **Embeddings** | OpenAI text-embedding-3-small |
| **PDF Processing** | PyMuPDF 1.26.4, PyPDF2 3.0.1 |
| **Data Validation** | Pydantic 2.11.7 |
| **Retry Logic** | Tenacity 8.2.3 |
| **Data Processing** | Pandas 2.3.2, NumPy 2.3.2 |

---

## Deployment

### Streamlit Cloud

1. **Prepare repository:**
   - Ensure all changes are committed
   - Verify `main.py` and `requirements.txt` exist

2. **Deploy:**
   - Go to [Streamlit Cloud](https://share.streamlit.io/)
   - Sign in with GitHub
   - Click "New app"
   - Select repository and branch
   - Set main file path: `main.py`

3. **Configure secrets:**
   - Go to Settings → Secrets
   - Add:
     ```toml
     OPENAI_API_KEY = "sk-your-actual-api-key-here"
     ```

**Note**: Free tier has limitations (ephemeral storage, timeout limits). Process small batches (5-10 resumes) and download results immediately.

---

## Documentation

- **[SETUP.md](SETUP.md)** - Detailed setup and installation guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture and design
- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development workflow and testing

---

## Support

For technical issues:
- Check error messages in the UI
- Review log files: `processing_errors.log`, `processing_errors.log1`
- Check `Ranking/Skipped.json` for filtered candidates
- Review code comments and docstrings

---

## License

[Add your license information here]

---

**Last Updated**: 2025-01-XX  
**Version**: 2.0

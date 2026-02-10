# Logging Summary for Scoring Functions

## Changes Made

Added comprehensive input data logging to three main scoring calculation functions:

### 1. **Keyword Scorer** (`e_keyword_scorer.py`)
- **Function**: `calculate_keyword_scores(resume, jd_data)`
- **Logs**: Resume skills, projects, experience, and JD requirements
- **Key Data Logged**:
  - All skill arrays from resume
  - Experience descriptions and responsibilities
  - Project technologies and keywords
  - JD required/preferred skills
  - Weighted keywords with their weights
  - Category weighting configuration

### 2. **Semantic Scorer** (`f_semantic_scorer.py`)
- **Function**: `calculate_semantic_scores(resume_section_embeddings, jd_embeddings_data)`
- **Logs**: Embedding shapes, dimensions, and sample values
- **Key Data Logged**:
  - Resume embedding shapes for all 6 sections (profile, skills, projects, responsibilities, education, overall)
  - JD embedding structure (1D vs 2D)
  - Numpy array metadata (dtype, shape, size)
  - Sample values for verification (first 5 elements)
  - Data availability flags

### 3. **Project Scorer** (`g_project_scorer.py`)
- **Function**: `calculate_project_scores(resume, jd_data)`
- **Logs**: Project details and JD requirements
- **Key Data Logged**:
  - All projects with full details
  - Technologies and skills per project
  - Project URLs (GitHub, live)
  - JD domain and role requirements
  - Skills needed from JD

## Log File Structure

All logs are saved as JSON files in: `scripts/logs/`

Each log file contains:
```json
{
  "timestamp": "20260206_143025_123456",
  "log_type": "keyword_scorer_input | semantic_scorer_input | project_scorer_input",
  "resume": { /* resume data */ },
  "jd": { /* JD data */ }
}
```

## How to Use the Logs

1. **Check Console Output**: Look for `[LOG] Input data logged to: {path}`
2. **Open JSON File**: View the structured input data
3. **Debug Issues**: Compare expected vs actual input data
4. **Verify Data Flow**: Ensure data is being passed correctly between functions

## Example Use Cases

- **Missing Skills**: Check if skills are being extracted properly from resume
- **Low Keyword Match**: Verify JD keywords are normalized correctly
- **Embedding Errors**: Check embedding shapes and ensure 2D format for JD
- **Project Not Scoring**: Verify project technologies are being captured
- **Weight Issues**: Review custom weights from JD analysis

## Console Output

When functions run, you'll see:
```
[LOG] Input data logged to: /path/to/scripts/logs/keyword_scorer_input_20260206_143025_123456.json
[LOG] Semantic input data logged to: /path/to/scripts/logs/semantic_scorer_input_20260206_143026_789012.json
[LOG] Project input data logged to: /path/to/scripts/logs/project_scorer_input_20260206_143027_345678.json
```

## Error Handling

If logging fails, a warning is printed but the scoring continues normally:
```
[WARNING] Failed to log input data: {error message}
```

This ensures logging doesn't break the scoring pipeline.

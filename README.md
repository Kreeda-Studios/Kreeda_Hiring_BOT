# HR User Guide - Resume Screening Platform

## Welcome

This guide will help you use the **AI Resume Screening Platform** to efficiently evaluate candidates against job descriptions. The system uses AI to automatically parse, score, and rank resumes based on your requirements.

---

## Quick Start

### Step 1: Start the Application

1. Open your web browser
2. Navigate to the application URL (provided by your IT team)
3. You'll see the main dashboard with 4 tabs

### Step 2: Upload Job Description

1. Go to the **"📌 Upload Requirements"** tab
2. Either:
   - Upload a JD PDF file, OR
   - Paste the JD text directly
3. (Optional) Add filter requirements (see below)
4. Click **"⚙️ Process JD"**
5. Wait for confirmation: **"🎯 JD processing complete!"**

### Step 3: Upload Resumes

1. Go to the **"📁 Upload Resumes"** tab
2. Upload one or multiple resume PDFs
3. Wait for extraction confirmation for each resume

### Step 4: Process & Rank

1. Click **"⚙️ Process & Rank Resumes"**
2. Wait for all 6 steps to complete (progress bar will show progress)
3. Processing typically takes 1-2 minutes for 20 resumes

### Step 5: View Rankings

1. Go to the **"🏆 Rankings"** tab
2. View ranked candidates with scores
3. Click on candidate names to see detailed compliance information
4. Download rankings using the download button

---

## Detailed Instructions

### Tab 1: 📘 Documentation

This tab provides:
- Overview of how the system works
- Data flow explanation
- Precautions and best practices
- Ideal workflow steps

**Read this first** if you're new to the platform.

---

### Tab 2: 📌 Upload Requirements

#### Uploading Job Description

**Option A: Upload PDF**
- Click "Upload JD (PDF only)"
- Select your JD PDF file
- The system will extract text automatically

**Option B: Paste Text**
- Type or paste JD text in the text area
- You can combine both PDF and text input

#### Filter Requirements (Optional)

Use this section to add **additional filtering criteria** that aren't in the main JD:

**Examples**:
- `Experience needed: 1-2 years in Python development`
- `Must have: React, Node.js, AWS`
- `Location: Remote only`
- `Must have worked in fintech industry`

**How it works**:
- The system will filter candidates based on these requirements
- Candidates not meeting requirements will be filtered out
- You'll see compliance details in the rankings

**Tips**:
- Be specific: "2-3 years" is better than "some experience"
- List must-have skills clearly
- Mention location preferences if important

#### Processing JD

1. After uploading JD and (optionally) filter requirements
2. Click **"⚙️ Process JD"**
3. Wait for processing (usually 5-10 seconds)
4. You'll see: **"🎯 JD processing complete!"**

**What happens**:
- JD is analyzed by AI
- Skills are extracted and normalized
- Requirements are structured for matching
- System is ready for resume processing

---

### Tab 3: 📁 Upload Resumes

#### Uploading Resumes

1. Click "Upload multiple PDF resumes"
2. Select one or multiple PDF files
3. Each resume will be extracted automatically
4. You'll see: **"✅ Extracted: filename.pdf"** for each

**Important**:
- Only PDF format is supported
- Resumes should be text-based (not scanned images)
- You can upload multiple resumes at once

#### Already Processed Resumes

- The system shows resumes that were already processed
- These won't be reprocessed (saves time and cost)

#### Processing & Ranking

1. After uploading resumes, click **"⚙️ Process & Rank Resumes"**
2. The system will run 6 steps:
   - Step 1: AI processing (converts resumes to structured data) [PARALLEL]
   - Step 2: Early filtering (applies your filter requirements)
   - Step 3: Project scoring (evaluates project depth)
   - Step 4: Keyword matching (ATS-style matching)
   - Step 5: Semantic matching (deep understanding)
   - Step 6: Final ranking (combines all scores)

3. Wait for completion (progress bar shows progress)
4. You'll see: **"🎯 Resume ranking complete!"**

**Processing Time**:
- 1-2 minutes for 20 resumes (parallel processing)
- Faster if resumes were processed before (caching)

---

### Tab 4: 🏆 Rankings

#### Viewing Rankings

The rankings tab shows:
- **Rank**: Candidate's position (1, 2, 3, ...)
- **Name**: Candidate name
- **Score**: Final match score (0.0 to 1.0, higher is better)
- **Compliance**: How well candidate meets filter requirements

#### Understanding Scores

**Score Range**: 0.0 to 1.0
- **0.9 - 1.0**: Excellent match (strong candidate)
- **0.7 - 0.9**: Good match (worth considering)
- **0.5 - 0.7**: Moderate match (may need review)
- **Below 0.5**: Weak match (may not be suitable)

**Score Components**:
- **Project Score**: Technical depth and project quality
- **Keyword Score**: Skills and experience matching
- **Semantic Score**: Deep understanding and relevance

#### Candidate Details

Click on a candidate's name to expand and see:
- **Compliance Details**: Which requirements were met/missing
- **Score Breakdown**: Individual scores for each component
- **Requirements Met**: List of requirements candidate satisfies
- **Requirements Missing**: List of requirements candidate lacks

#### Compliance Indicators

- **✅ Green**: All requirements met
- **⚠️ Yellow**: Some requirements met (partial compliance)
- **❌ Red**: Requirements not met

#### Download Rankings

1. Click **"⬇️ Download Rankings File"**
2. File will download as `DisplayRanks.txt`
3. Format: `Rank. Name | Score`
4. Easy to share with hiring managers

#### Clearing Previous Run

**When to clear**:
- Starting a new batch of resumes
- Seeing duplicate candidates
- Want to reprocess everything from scratch

**What gets cleared**:
- All processed resumes
- All ranking files
- Processing index

**What doesn't get cleared**:
- JD files (can be reused)

**To clear**: Click **"🗑️ Clear Previous Run Data"**

---

## Understanding Filter Requirements

### What Are Filter Requirements?

Filter requirements are **additional criteria** you specify beyond the main JD. They help narrow down candidates to those who meet specific needs.

### Examples

**Experience Requirements**:
```
Experience needed: 2-3 years in Python development
```

**Skill Requirements**:
```
Must have: React, Node.js, AWS
```

**Location Requirements**:
```
Location: Remote only
```

**Industry Requirements**:
```
Must have worked in fintech or healthcare
```

**Combined Requirements**:
```
Experience needed: 1-2 years
Must have: RAG, ML
Location: Remote
```

### How Filtering Works

The system has two modes:

**Flexible Mode** (Default):
- Candidates need to meet **at least 50%** of skill requirements
- Example: If you require "RAG" and "ML", candidate with just "ML" will pass
- More candidates pass through

**Strict Mode**:
- Candidates must meet **ALL** requirements
- Example: Must have both "RAG" and "ML"
- Fewer candidates pass through

**Current Setting**: Flexible mode (can be changed by developers)

### Filtering Results

After filtering, you'll see:
- **Compliant resumes**: Passed all/most requirements → Continue to ranking
- **Filtered resumes**: Failed requirements → Moved to skipped list

---

## Best Practices

### 1. JD Quality

**Do**:
- ✅ Provide complete, detailed JD
- ✅ Include all required skills
- ✅ Specify experience ranges clearly
- ✅ Mention preferred qualifications

**Don't**:
- ❌ Use vague descriptions
- ❌ Skip important requirements
- ❌ Use only abbreviations (spell out skills)

### 2. Filter Requirements

**Do**:
- ✅ Be specific: "2-3 years" not "some experience"
- ✅ List must-have skills clearly
- ✅ Mention location if important
- ✅ Add industry experience if relevant

**Don't**:
- ❌ Be too vague
- ❌ Add conflicting requirements
- ❌ Over-filter (you might miss good candidates)

### 3. Resume Upload

**Do**:
- ✅ Upload text-based PDFs
- ✅ Upload multiple resumes at once
- ✅ Wait for processing to complete

**Don't**:
- ❌ Upload scanned/image PDFs (won't work)
- ❌ Upload non-PDF files
- ❌ Interrupt processing

### 4. Interpreting Results

**Do**:
- ✅ Review top-ranked candidates first
- ✅ Check compliance details
- ✅ Consider score breakdown
- ✅ Use rankings as a guide, not absolute truth

**Don't**:
- ❌ Ignore candidates with lower scores (may still be good)
- ❌ Rely solely on scores (review resumes manually too)
- ❌ Skip checking compliance details

---

## Common Questions

### Q: How long does processing take?

**A**: 
- JD processing: 5-10 seconds
- Resume processing: 1-2 minutes for 20 resumes
- Faster if resumes were processed before (caching)

### Q: Can I process multiple JDs?

**A**: 
- Process one JD at a time
- Clear previous run before processing new JD
- Or use different filter requirements for same JD

### Q: What if a candidate is filtered out?

**A**: 
- Check the compliance details to see why
- They may still be in the rankings if they partially meet requirements
- Filtered candidates are in the "Skipped" list

### Q: Can I change filter requirements after processing?

**A**: 
- Yes, update filter requirements and reprocess
- Or clear previous run and start fresh

### Q: What if processing fails?

**A**: 
- Check error messages in the UI
- Verify JD and resumes are in correct format
- Contact IT support if issues persist

### Q: How accurate are the rankings?

**A**: 
- Rankings are based on AI analysis and scoring
- Use as a guide, but always review resumes manually
- Top-ranked candidates are most likely to be good matches

### Q: Can I export results?

**A**: 
- Yes, download rankings using the download button
- File format: `DisplayRanks.txt`
- Easy to share with hiring managers

---

## Troubleshooting

### Issue: JD Processing Fails

**Possible Causes**:
- JD file is corrupted
- JD text is empty
- API connection issue

**Solutions**:
- Try uploading JD again
- Or paste JD text directly
- Check internet connection

### Issue: Resume Processing Fails

**Possible Causes**:
- Resume PDF is scanned/image-based
- Resume file is corrupted
- Too many resumes at once

**Solutions**:
- Ensure resumes are text-based PDFs
- Try processing fewer resumes at once
- Check individual resume files

### Issue: No Rankings Appear

**Possible Causes**:
- Processing didn't complete
- All candidates were filtered out
- Error in processing

**Solutions**:
- Check that all 6 steps completed
- Review filter requirements (may be too strict)
- Check error messages
- Try clearing and reprocessing

### Issue: Rankings Seem Wrong

**Possible Causes**:
- JD or filter requirements unclear
- Resumes don't match JD well
- Scoring weights may need adjustment

**Solutions**:
- Review JD and filter requirements
- Check candidate compliance details
- Consider adjusting filter requirements
- Contact developers if persistent issues

---

## Tips for Best Results

1. **Clear JD**: Write detailed, specific job descriptions
2. **Specific Filters**: Be precise with filter requirements
3. **Review Top Candidates**: Focus on top 5-10 ranked candidates
4. **Check Compliance**: Review why candidates passed/failed filters
5. **Manual Review**: Always review resumes manually, don't rely solely on scores
6. **Iterate**: Adjust filter requirements based on results

---

## Support

For technical issues or questions:
- Check error messages in the UI
- Review this user guide
- Contact your IT support team

---

## What to Expect

### Typical Workflow

1. **Upload JD** → 5-10 seconds
2. **Add Filter Requirements** → Instant
3. **Process JD** → 5-10 seconds
4. **Upload Resumes** → Instant (file upload)
5. **Process & Rank** → 1-2 minutes (20 resumes)
6. **Review Rankings** → Instant display

### Expected Results

- **Ranked list** of candidates (best match first)
- **Scores** showing match quality (0.0 to 1.0)
- **Compliance details** for each candidate
- **Downloadable rankings** for sharing

### Performance

- **Fast processing** with parallel execution
- **Caching** for repeated processing (instant)
- **Accurate rankings** based on AI analysis
- **Transparent filtering** with compliance details

---

**Last Updated**: 2025-01-XX  
**Version**: 2.0


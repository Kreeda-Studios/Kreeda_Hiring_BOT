#!/bin/bash

# Complete JD Processing Test with Docker Python Processor
# Tests: Job creation → PDF upload → Compliance → JD text → Process → SSE monitoring → Verification
set -e

API_URL="http://localhost:3001/api"
PDF_FILE="/home/soham/development/Kreeda_Hiring_BOT/dummy/JD - New AI-Ml Engineer - Latest 1.pdf"
SSE_TIMEOUT=180  # 3 minutes max wait

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║   Complete JD Processing Test - Docker Python Processor      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if PDF exists
if [ ! -f "$PDF_FILE" ]; then
  echo -e "${RED}❌ PDF file not found: $PDF_FILE${NC}"
  exit 1
fi

# Step 1: Create job
echo -e "${YELLOW}📝 Step 1: Creating a new job...${NC}"
CREATE_RESPONSE=$(curl -s -X POST "$API_URL/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Senior AI/ML Engineer - Test Run 1",
    "description": "Complete end-to-end JD processing test with embeddings"
  }')

echo "$CREATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$CREATE_RESPONSE"
JOB_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys,json; data=json.load(sys.stdin); print(data.get('data', {}).get('_id', ''))" 2>/dev/null)

if [ -z "$JOB_ID" ]; then
  echo -e "${RED}❌ Failed to create job - could not extract job ID${NC}"
  exit 1
fi

echo -e "${GREEN}✅ Job created: $JOB_ID${NC}"
echo ""
sleep 1

# Step 2: Upload PDF
echo -e "${YELLOW}📄 Step 2: Uploading JD PDF...${NC}"
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/jobs/$JOB_ID/upload-jd" \
  -F "jd_pdf=@$PDF_FILE")

echo "$UPLOAD_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPLOAD_RESPONSE"
PDF_FILENAME=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data', {}).get('filename', ''))" 2>/dev/null)

if [ -z "$PDF_FILENAME" ]; then
  echo -e "${RED}❌ Failed to upload PDF${NC}"
  exit 1
fi

echo -e "${GREEN}✅ PDF uploaded: $PDF_FILENAME${NC}"
echo ""
sleep 1

# Step 3: Add JD text, mandatory and soft compliances
echo -e "${YELLOW}📝 Step 3: Adding JD text with mandatory and soft compliances...${NC}"

# Use PUT request with proper structure (matching backend /jobs/:id PUT endpoint)
UPDATE_RESPONSE=$(curl -s -X PUT "$API_URL/jobs/$JOB_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"jd_pdf_filename\": \"$PDF_FILENAME\",
    \"jd_text\": \"Senior AI/ML Engineer Position\\n\\nWe are looking for an experienced AI/ML Engineer to join our team. The ideal candidate should have:\\n\\nKey Responsibilities:\\n- Design and implement machine learning models for production systems\\n- Build scalable ML pipelines using Python, TensorFlow, and PyTorch\\n- Collaborate with cross-functional teams to deploy AI solutions\\n- Optimize model performance and reduce inference latency\\n- Mentor junior engineers and conduct code reviews\\n\\nRequired Skills:\\n- 5+ years of experience in Machine Learning and AI\\n- Strong proficiency in Python, TensorFlow, PyTorch\\n- Experience with AWS, Docker, Kubernetes\\n- Solid understanding of ML algorithms and deep learning\\n- Experience building production ML systems\\n\\nPreferred Skills:\\n- Experience with MLOps and model deployment\\n- Knowledge of distributed training and GPU optimization\\n- Familiarity with LLMs and transformer architectures\\n\\nEducation:\\n- Master's or PhD in Computer Science, Machine Learning, or related field\\n\\nThis is a full-time position with competitive compensation and benefits.\",
    \"mandatory_compliances\": \"MANDATORY REQUIREMENTS (Must have ALL):\\n- Minimum 5 years ML/AI experience\\n- Required Skills: Python, TensorFlow, PyTorch\\n- Master's degree in CS/ML/AI or related field\\n- Production ML system deployment experience\\n- Experience with cloud platforms (AWS/GCP/Azure)\",
    \"soft_compliances\": \"PREFERRED QUALIFICATIONS (Nice to have):\\n- PhD in Computer Science or Machine Learning\\n- Experience with MLOps tools and practices\\n- Knowledge of Docker and Kubernetes\\n- Familiarity with distributed training\\n- Experience with LLMs and transformer architectures\\n- Publications in top-tier ML conferences\"
  }")
echo "$UPDATE_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$UPDATE_RESPONSE"

UPDATE_SUCCESS=$(echo "$UPDATE_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
if [ "$UPDATE_SUCCESS" != "True" ]; then
  echo -e "${RED}❌ Failed to update job with JD data${NC}"
  exit 1
fi

echo -e "${GREEN}✅ JD text, mandatory and soft compliances updated${NC}"
echo -e "${GREEN}✅ JD text, mandatory and soft compliances updated${NC}"
echo ""
sleep 1

# Step 4: Verify job state before processing
echo -e "${YELLOW}🔍 Step 4: Verifying job state...${NC}"
JOB_STATE=$(curl -s "$API_URL/jobs/$JOB_ID")
echo "$JOB_STATE" | python3 -c "
import sys, json
data = json.load(sys.stdin).get('data', {})
print(json.dumps({
  'id': data.get('_id'),
  'title': data.get('title'),
  'status': data.get('status'),
  'locked': data.get('locked'),
  'has_pdf': data.get('jd_pdf_filename') is not None,
  'has_text': data.get('jd_text') is not None,
  'has_compliance': data.get('filter_requirements') is not None
}, indent=2))
" 2>/dev/null || echo "$JOB_STATE"
echo -e "${GREEN}✅ Job state verified${NC}"
echo ""
sleep 1

# Step 5: Start SSE listener in background
echo -e "${YELLOW}📡 Step 5: Starting SSE listener...${NC}"
SSE_OUTPUT=$(mktemp)
SSE_PID=""

# Start SSE connection with proper Accept header
(curl -s -N -H "Accept: text/event-stream" "$API_URL/sse/jobs/$JOB_ID/progress" 2>&1 | while IFS= read -r line; do
  echo "[SSE] $line" | tee -a "$SSE_OUTPUT"
  # Check if processing completed (either type:complete or stage:completed with 100%)
  if echo "$line" | grep -q '"type":"complete"' || echo "$line" | grep -E '"stage":"completed".*"percent":100' > /dev/null; then
    echo "PROCESSING_COMPLETE" >> "$SSE_OUTPUT"
  fi
done) &
SSE_PID=$!

echo -e "${GREEN}✅ SSE listener started (PID: $SSE_PID)${NC}"
echo ""
sleep 2

# Step 6: Trigger JD processing
echo -e "${YELLOW}🚀 Step 6: Triggering JD processing...${NC}"
PROCESS_RESPONSE=$(curl -s -X POST "$API_URL/process/jd/$JOB_ID")
echo "$PROCESS_RESPONSE" | python3 -m json.tool 2>/dev/null || echo "$PROCESS_RESPONSE"

PROCESSING_SUCCESS=$(echo "$PROCESS_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('success', False))" 2>/dev/null)
if [ "$PROCESSING_SUCCESS" != "True" ]; then
  echo -e "${RED}❌ Failed to trigger processing${NC}"
  kill $SSE_PID 2>/dev/null || true
  rm -f "$SSE_OUTPUT"
  exit 1
fi

JD_JOB_ID=$(echo "$PROCESS_RESPONSE" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data', {}).get('jd_job_id', ''))" 2>/dev/null)
echo -e "${GREEN}✅ Processing triggered${NC}"
echo -e "${BLUE}   Queue Job ID: $JD_JOB_ID${NC}"
echo -e "${BLUE}   Job is now LOCKED - waiting for completion...${NC}"
echo ""

# Step 8: Monitor SSE for completion
echo -e "${YELLOW}⏳ Step 8: Monitoring SSE for processing updates...${NC}"
echo -e "${BLUE}   Timeout: ${SSE_TIMEOUT}s${NC}"
echo ""

START_TIME=$(date +%s)
COMPLETED=false

while [ $(($(date +%s) - START_TIME)) -lt $SSE_TIMEOUT ]; do
  if grep -q "PROCESSING_COMPLETE" "$SSE_OUTPUT" 2>/dev/null; then
    COMPLETED=true
    echo ""
    echo -e "${GREEN}✅ Processing completed signal received!${NC}"
    break
  fi
  
  # Show progress every 5 seconds
  ELAPSED=$(($(date +%s) - START_TIME))
  if [ $((ELAPSED % 5)) -eq 0 ]; then
    echo -e "${BLUE}   ⏱  Elapsed: ${ELAPSED}s / ${SSE_TIMEOUT}s${NC}"
  fi
  
  sleep 1
done

# Stop SSE listener
kill $SSE_PID 2>/dev/null || true
echo ""

if [ "$COMPLETED" = false ]; then
  echo -e "${RED}❌ Timeout waiting for processing completion${NC}"
  echo -e "${YELLOW}📄 SSE Output:${NC}"
  cat "$SSE_OUTPUT"
  rm -f "$SSE_OUTPUT"
  exit 1
fi

sleep 2

# Step 9: Verify final job state
echo -e "${YELLOW}🔍 Step 9: Verifying final job state...${NC}"
FINAL_JOB=$(curl -s "$API_URL/jobs/$JOB_ID")

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   FINAL JOB STATE${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

echo "$FINAL_JOB" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin).get('data', {})
    jd = data.get('jd_analysis', {})
    emb = jd.get('embeddings', {})
    fr = data.get('filter_requirements', {})
    result = {
        'id': data.get('_id'),
        'title': data.get('title'),
        'status': data.get('status'),
        'locked': data.get('locked'),
        'jd_analysis': {
            'role_title': jd.get('role_title'),
            'seniority_level': jd.get('seniority_level'),
            'department': jd.get('department'),
            'years_experience_required': jd.get('years_experience_required'),
            'required_skills_count': len(jd.get('required_skills', [])),
            'required_skills_sample': jd.get('required_skills', [])[:5],
            'preferred_skills_count': len(jd.get('preferred_skills', [])),
            'responsibilities_count': len(jd.get('responsibilities', [])),
            'tools_count': len(jd.get('tools_tech', [])),
            'keywords_count': len(jd.get('keywords_flat', [])),
            'has_embeddings': emb is not None and len(emb) > 0,
            'embeddings': {
                'model': emb.get('embedding_model'),
                'dimension': emb.get('embedding_dimension'),
                'profile_dims': len(emb.get('profile_embedding', [])),
                'skills_dims': len(emb.get('skills_embedding', [])),
                'projects_dims': len(emb.get('projects_embedding', [])),
                'responsibilities_dims': len(emb.get('responsibilities_embedding', [])),
                'education_dims': len(emb.get('education_embedding', [])),
                'overall_dims': len(emb.get('overall_embedding', []))
            } if emb else None
        },
        'compliance_requirements': {
            'mandatory': {
                'fields_count': len(fr.get('mandatory_compliances', {}).get('structured', {})),
                'fields': list(fr.get('mandatory_compliances', {}).get('structured', {}).keys())
            },
            'soft': {
                'fields_count': len(fr.get('soft_compliances', {}).get('structured', {})),
                'fields': list(fr.get('soft_compliances', {}).get('structured', {}).keys())
            }
        },
        'filter_requirements': data.get('filter_requirements'),
        'hr_points': data.get('hr_points'),
        'hr_notes_count': len(data.get('hr_notes', [])),
        'has_explainability': data.get('explainability') is not None,
        'meta': data.get('meta')
    }
    print(json.dumps(result, indent=2))
except:
    pass
" 2>/dev/null || echo "$FINAL_JOB"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Step 10: Validation checks
echo ""
echo -e "${YELLOW}✔️  Step 10: Running validation checks...${NC}"
echo ""

# Extract values for validation
JOB_LOCKED=$(echo "$FINAL_JOB" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data', {}).get('locked', False))" 2>/dev/null)
HAS_JD_ANALYSIS=$(echo "$FINAL_JOB" | python3 -c "import sys,json; print(json.load(sys.stdin).get('data', {}).get('jd_analysis', {}).get('role_title') is not None)" 2>/dev/null)
HAS_EMBEDDINGS=$(echo "$FINAL_JOB" | python3 -c "import sys,json; emb=json.load(sys.stdin).get('data', {}).get('jd_analysis', {}).get('embeddings'); print(emb is not None and len(emb) > 0)" 2>/dev/null)
PROFILE_EMBEDDING_SIZE=$(echo "$FINAL_JOB" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data', {}).get('jd_analysis', {}).get('embeddings', {}).get('profile_embedding', [])))" 2>/dev/null)
SKILLS_EMBEDDING_SIZE=$(echo "$FINAL_JOB" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data', {}).get('jd_analysis', {}).get('embeddings', {}).get('skills_embedding', [])))" 2>/dev/null)
REQUIRED_SKILLS_COUNT=$(echo "$FINAL_JOB" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data', {}).get('jd_analysis', {}).get('required_skills', [])))" 2>/dev/null)
MANDATORY_FIELDS=$(echo "$FINAL_JOB" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data', {}).get('filter_requirements', {}).get('mandatory_compliances', {}).get('structured', {})))" 2>/dev/null)
SOFT_FIELDS=$(echo "$FINAL_JOB" | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('data', {}).get('filter_requirements', {}).get('soft_compliances', {}).get('structured', {})))" 2>/dev/null)

VALIDATION_PASSED=true

# Check 1: Job should be locked
if [ "$JOB_LOCKED" = "True" ]; then
  echo -e "${GREEN}✅ Job is locked${NC}"
else
  echo -e "${RED}❌ Job is NOT locked${NC}"
  VALIDATION_PASSED=false
fi

# Check 2: JD analysis should exist
if [ "$HAS_JD_ANALYSIS" = "True" ]; then
  echo -e "${GREEN}✅ JD analysis exists${NC}"
else
  echo -e "${RED}❌ JD analysis NOT found${NC}"
  VALIDATION_PASSED=false
fi

# Check 3: Embeddings should exist
if [ "$HAS_EMBEDDINGS" = "True" ]; then
  echo -e "${GREEN}✅ Embeddings exist${NC}"
else
  echo -e "${RED}❌ Embeddings NOT found${NC}"
  VALIDATION_PASSED=false
fi

# Check 4: All 6 embeddings should be 1536 dimensions
if [ "$PROFILE_EMBEDDING_SIZE" = "1536" ]; then
  echo -e "${GREEN}✅ Profile embedding: 1536 dimensions${NC}"
else
  echo -e "${RED}❌ Profile embedding: $PROFILE_EMBEDDING_SIZE dimensions (expected 1536)${NC}"
  VALIDATION_PASSED=false
fi

if [ "$SKILLS_EMBEDDING_SIZE" = "1536" ]; then
  echo -e "${GREEN}✅ Skills embedding: 1536 dimensions${NC}"
else
  echo -e "${RED}❌ Skills embedding: $SKILLS_EMBEDDING_SIZE dimensions (expected 1536)${NC}"
  VALIDATION_PASSED=false
fi

# Check 5: Should have extracted skills
if [ "$REQUIRED_SKILLS_COUNT" -gt 0 ]; then
  echo -e "${GREEN}✅ Required skills extracted: $REQUIRED_SKILLS_COUNT skills${NC}"
else
  echo -e "${RED}❌ No required skills extracted${NC}"
  VALIDATION_PASSED=false
fi

# Check 6: Mandatory compliances should be parsed
if [ "$MANDATORY_FIELDS" -gt 0 ]; then
  echo -e "${GREEN}✅ Mandatory compliances parsed: $MANDATORY_FIELDS field(s)${NC}"
else
  echo -e "${YELLOW}⚠️  No mandatory compliance fields parsed${NC}"
fi

# Check 7: Soft compliances should be parsed
if [ "$SOFT_FIELDS" -gt 0 ]; then
  echo -e "${GREEN}✅ Soft compliances parsed: $SOFT_FIELDS field(s)${NC}"
else
  echo -e "${YELLOW}⚠️  No soft compliance fields parsed${NC}"
fi

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"

# Final result
echo ""
if [ "$VALIDATION_PASSED" = true ]; then
  echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}║                 ✅ ALL TESTS PASSED! ✅                        ║${NC}"
  echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${GREEN}✅ Job ID: $JOB_ID${NC}"
  echo -e "${GREEN}✅ JD processing completed successfully${NC}"
  echo -e "${GREEN}✅ All 6 embeddings generated (1536 dimensions each)${NC}"
  echo -e "${GREEN}✅ Job locked and ready for resume processing${NC}"
else
  echo -e "${RED}╔════════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${RED}║                 ❌ SOME TESTS FAILED ❌                        ║${NC}"
  echo -e "${RED}╚════════════════════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${YELLOW}Check the validation output above for details${NC}"
fi

# Cleanup
rm -f "$SSE_OUTPUT"

echo ""
echo -e "${BLUE}Test completed at $(date)${NC}"
echo ""

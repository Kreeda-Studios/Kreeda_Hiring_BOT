#!/bin/bash

# Complete workflow test script
set -e

API_URL="http://localhost:80/api"
JD_FILE="./dummy/JD - New AI-Ml Engineer - Latest 1.pdf"
RESUME_FILES=(
    "./dummy/Resume_Anurag_Gupta.pdf"
    "./dummy/Resume_AtharvBhat.pdf"
    "./dummy/Resume_Om_Singh.pdf"
)

echo "🚀 Starting Complete Workflow Test"
echo "=================================="

# Step 1: Create Job
echo ""
echo "📝 Step 1: Creating a new job..."
CREATE_RESPONSE=$(curl -s -X POST "$API_URL/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI/ML Engineer",
    "description": "Looking for experienced AI/ML engineer with Python and deep learning expertise"
  }')

echo "$CREATE_RESPONSE" | python3 -m json.tool
JOB_ID=$(echo "$CREATE_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['_id'])")
echo "✅ Job created with ID: $JOB_ID"

# Step 2: Upload JD PDF
echo ""
echo "📄 Step 2: Uploading JD PDF..."
UPLOAD_RESPONSE=$(curl -s -X POST "$API_URL/jobs/$JOB_ID/upload-jd" \
  -F "jd_pdf=@$JD_FILE")

echo "$UPLOAD_RESPONSE" | python3 -m json.tool
JD_FILENAME=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['filename'])")
echo "✅ JD uploaded with filename: $JD_FILENAME"

# Step 3: Update Job with JD filename
echo ""
echo "🔄 Step 3: Updating job with JD filename..."
UPDATE_RESPONSE=$(curl -s -X PUT "$API_URL/jobs/$JOB_ID" \
  -H "Content-Type: application/json" \
  -d "{
    \"jd_pdf_filename\": \"$JD_FILENAME\",
    \"mandatory_compliances\": \"Must have 3+ years Python experience, Deep learning expertise required\",
    \"soft_compliances\": \"Preferred: TensorFlow, PyTorch, cloud experience\"
  }")

echo "$UPDATE_RESPONSE" | python3 -m json.tool
echo "✅ Job updated with JD filename"

# Step 4: Start JD Processing
echo ""
echo "⚙️  Step 4: Starting JD processing..."
PROCESS_JD_RESPONSE=$(curl -s -X POST "$API_URL/process/jd/$JOB_ID")
echo "$PROCESS_JD_RESPONSE" | python3 -m json.tool

# Check if processing started successfully
if echo "$PROCESS_JD_RESPONSE" | grep -q '"success": true'; then
    echo "✅ JD processing started successfully"
else
    echo "❌ JD processing failed to start"
    exit 1
fi

# Step 5: Wait for JD processing to complete
echo ""
echo "⏳ Step 5: Waiting for JD processing to complete..."
MAX_WAIT=120
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    
    JOB_STATUS=$(curl -s "$API_URL/jobs/$JOB_ID" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['status'])")
    echo "   Current status: $JOB_STATUS (${ELAPSED}s elapsed)"
    
    if [ "$JOB_STATUS" = "jd_completed" ]; then
        echo "✅ JD processing completed!"
        break
    elif [ "$JOB_STATUS" = "jd_processing_failed" ]; then
        echo "❌ JD processing failed!"
        curl -s "$API_URL/jobs/$JOB_ID" | python3 -m json.tool
        exit 1
    fi
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "⚠️  Timeout waiting for JD processing"
    exit 1
fi

# Step 6: Upload Resumes
echo ""
echo "📑 Step 6: Uploading resumes..."
RESUME_IDS=()
for RESUME_FILE in "${RESUME_FILES[@]}"; do
    RESUME_NAME=$(basename "$RESUME_FILE")
    echo "   Uploading: $RESUME_NAME"
    
    RESUME_RESPONSE=$(curl -s -X POST "$API_URL/resumes/upload" \
      -F "resume_pdf=@$RESUME_FILE" \
      -F "job_id=$JOB_ID")
    
    RESUME_ID=$(echo "$RESUME_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['_id'])" 2>/dev/null || echo "")
    
    if [ -n "$RESUME_ID" ]; then
        RESUME_IDS+=("$RESUME_ID")
        echo "   ✅ Uploaded: $RESUME_NAME (ID: $RESUME_ID)"
    else
        echo "   ❌ Failed to upload: $RESUME_NAME"
        echo "$RESUME_RESPONSE" | python3 -m json.tool
    fi
done

echo "✅ Uploaded ${#RESUME_IDS[@]} resumes"

# Step 7: Start Resume Processing
echo ""
echo "⚙️  Step 7: Starting resume processing..."
PROCESS_RESUME_RESPONSE=$(curl -s -X POST "$API_URL/process/resume/$JOB_ID")
echo "$PROCESS_RESUME_RESPONSE" | python3 -m json.tool

if echo "$PROCESS_RESUME_RESPONSE" | grep -q '"success": true'; then
    echo "✅ Resume processing started successfully"
else
    echo "❌ Resume processing failed to start"
    exit 1
fi

# Step 8: Wait for Resume processing to complete
echo ""
echo "⏳ Step 8: Waiting for resume processing to complete..."
ELAPSED=0
MAX_WAIT=180
while [ $ELAPSED -lt $MAX_WAIT ]; do
    sleep 5
    ELAPSED=$((ELAPSED + 5))
    
    JOB_STATUS=$(curl -s "$API_URL/jobs/$JOB_ID" | python3 -c "import sys, json; print(json.load(sys.stdin)['data']['status'])")
    echo "   Current status: $JOB_STATUS (${ELAPSED}s elapsed)"
    
    if [ "$JOB_STATUS" = "resume_completed" ]; then
        echo "✅ Resume processing completed!"
        break
    elif [ "$JOB_STATUS" = "resume_processing_failed" ]; then
        echo "❌ Resume processing failed!"
        curl -s "$API_URL/jobs/$JOB_ID" | python3 -m json.tool
        exit 1
    fi
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "⚠️  Timeout waiting for resume processing"
    exit 1
fi

# Step 9: Get Final Scores
echo ""
echo "📊 Step 9: Retrieving final scores..."
SCORES_RESPONSE=$(curl -s "$API_URL/scores/resumes/$JOB_ID")
echo "$SCORES_RESPONSE" | python3 -m json.tool

echo ""
echo "🎉 Complete workflow test finished successfully!"
echo "=================================="
echo "Job ID: $JOB_ID"
echo "Resumes processed: ${#RESUME_IDS[@]}"
echo ""

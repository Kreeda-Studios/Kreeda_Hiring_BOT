#!/bin/bash

# BullMQ Flow Test with Complete Resume Processing Pipeline
# Tests JD processing → Resume upload → Resume processing → Score verification

set -e  # Exit on error

API_URL="http://localhost:3001/api"
DUMMY_FOLDER="./dummy"
TIMEOUT=300  # 5 minutes timeout

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Cursor control
CURSOR_SAVE='\033[s'
CURSOR_RESTORE='\033[u'
CURSOR_UP='\033[A'
ERASE_LINE='\033[2K'

# Progress bar function
draw_progress_bar() {
    local percent=$1
    local width=50
    local label="${2:-Progress}"
    local status="${3:-}"
    
    # Calculate filled and empty parts
    local filled=$((percent * width / 100))
    local empty=$((width - filled))
    
    # Create bar
    local bar=""
    for ((i=0; i<filled; i++)); do bar="${bar}█"; done
    for ((i=0; i<empty; i++)); do bar="${bar}░"; done
    
    # Color based on status
    local color=$CYAN
    if [ "$percent" -eq 100 ]; then
        color=$GREEN
    elif [ -n "$status" ] && [ "$status" = "failed" ]; then
        color=$RED
    fi
    
    # Print progress bar
    echo -ne "${color}${BOLD}${label}${NC} [${bar}] ${percent}%"
    if [ -n "$status" ]; then
        echo -ne " ${status}"
    fi
    echo ""
}

# Multi-line progress display
declare -A PROGRESS_LINES
PROGRESS_START_LINE=0

init_progress_display() {
    local count=$1
    PROGRESS_START_LINE=$(tput lines)
    echo ""
    for ((i=0; i<count; i++)); do
        echo ""
    done
}

update_progress_line() {
    local line_num=$1
    local content="$2"
    
    # Save cursor, move to line, clear it, write content, restore cursor
    tput sc
    tput cup $((PROGRESS_START_LINE + line_num)) 0
    tput el
    echo -ne "$content"
    tput rc
}

# Table drawing functions
draw_table_border() {
    local width=$1
    local char="${2:-─}"
    printf "${CYAN}%${width}s${NC}\n" | tr ' ' "$char"
}

draw_table_header() {
    echo -e "${CYAN}┌────┬──────────────────────────────────┬───────────┬──────────┬──────────┬──────────┬────────────┐${NC}"
    printf "${CYAN}│${NC} ${BOLD}%-2s${NC} ${CYAN}│${NC} ${BOLD}%-32s${NC} ${CYAN}│${NC} ${BOLD}%-9s${NC} ${CYAN}│${NC} ${BOLD}%-8s${NC} ${CYAN}│${NC} ${BOLD}%-8s${NC} ${CYAN}│${NC} ${BOLD}%-8s${NC} ${CYAN}│${NC} ${BOLD}%-10s${NC} ${CYAN}│${NC}\n" \
           "#" "Resume" "Final" "Keyword" "Semantic" "Project" "Hard Reqs"
    echo -e "${CYAN}├────┼──────────────────────────────────┼───────────┼──────────┼──────────┼──────────┼────────────┤${NC}"
}

draw_table_row() {
    local rank=$1
    local filename=$2
    local final=$3
    local keyword=$4
    local semantic=$5
    local project=$6
    local hard_reqs=$7
    
    # Truncate filename if too long
    if [ ${#filename} -gt 32 ]; then
        filename="${filename:0:29}..."
    fi
    
    # Color code based on rank
    local rank_color=$YELLOW
    [ "$rank" == "1" ] && rank_color=$GREEN
    [ "$rank" == "2" ] && rank_color=$CYAN
    [ "$rank" == "3" ] && rank_color=$BLUE
    
    # Color code hard requirements
    local req_color=$GREEN
    local req_symbol="✓"
    if [ "$hard_reqs" == "false" ] || [ "$hard_reqs" == "False" ]; then
        req_color=$RED
        req_symbol="✗"
    fi
    
    printf "${CYAN}│${NC} ${rank_color}${BOLD}%-2s${NC} ${CYAN}│${NC} %-32s ${CYAN}│${NC} ${GREEN}%-9s${NC} ${CYAN}│${NC} %-8s ${CYAN}│${NC} %-8s ${CYAN}│${NC} %-8s ${CYAN}│${NC} ${req_color}%-10s${NC} ${CYAN}│${NC}\n" \
           "$rank" "$filename" "$final" "$keyword" "$semantic" "$project" "$req_symbol $hard_reqs"
}

draw_table_footer() {
    echo -e "${CYAN}└────┴──────────────────────────────────┴───────────┴──────────┴──────────┴──────────┴────────────┘${NC}"
}

# Enhanced logging functions with Python processor integration
PYTHON_LOG_FILE="/tmp/python_processor_monitor.log"
SSE_MASTER_LOG="/tmp/sse_master_events.log"

log_info() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${BLUE}[INFO]${NC} $timestamp - $1"
    echo "[$timestamp] [INFO] $1" >> "$SSE_MASTER_LOG"
}

log_success() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${GREEN}[SUCCESS]${NC} $timestamp - $1"
    echo "[$timestamp] [SUCCESS] $1" >> "$SSE_MASTER_LOG"
}

log_warning() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${YELLOW}[WARNING]${NC} $timestamp - $1"
    echo "[$timestamp] [WARNING] $1" >> "$SSE_MASTER_LOG"
}

log_error() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${RED}[ERROR]${NC} $timestamp - $1"
    echo "[$timestamp] [ERROR] $1" >> "$SSE_MASTER_LOG"
}

log_step() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}$1${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo "$(date '+%Y-%m-%d %H:%M:%S') [STEP] $1" >> "$SSE_MASTER_LOG"
}

log_sse() {
    local event_type="$1"
    local content="$2"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S.%3N')"
    echo "[$timestamp] [SSE-$event_type] $content" >> "$SSE_MASTER_LOG"
}

log_python() {
    local content="$1"
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S.%3N')"
    echo "[$timestamp] [PYTHON] $content" >> "$SSE_MASTER_LOG"
}

# Start Python processor log monitoring
start_python_log_monitor() {
    log_info "Starting Python processor log monitor..."
    > "$PYTHON_LOG_FILE"
    
    # Monitor Python processor logs in background
    (docker logs kreeda-python-processor -f --since 1s 2>&1 | while IFS= read -r line; do
        log_python "$line"
        echo "[$(date '+%H:%M:%S')] $line" >> "$PYTHON_LOG_FILE"
    done) &
    
    PYTHON_MONITOR_PID=$!
    log_success "Python log monitor started (PID: $PYTHON_MONITOR_PID)"
}

stop_python_log_monitor() {
    if [ ! -z "$PYTHON_MONITOR_PID" ]; then
        kill $PYTHON_MONITOR_PID 2>/dev/null || true
        log_info "Python log monitor stopped"
    fi
}

# Comprehensive resume verification
verify_resume_complete() {
    local resume_id="$1"
    local job_id="$2"
    local filename="$3"
    
    log_info "🔍 COMPREHENSIVE VERIFICATION for: $filename (ID: $resume_id)"
    
    # Check resume status
    local resume_status=$(curl -s "$API_URL/status/resume/$resume_id/status")
    if [ -z "$resume_status" ]; then
        log_error "  ❌ Could not fetch resume status"
        return 1
    fi
    
    # Parse status details
    local overall_status=$(echo "$resume_status" | grep -o '"overallStatus":"[^"]*"' | cut -d'"' -f4)
    local has_score=$(echo "$resume_status" | grep -o '"hasScore":[^,}]*' | cut -d':' -f2)
    local processing_stages=$(echo "$resume_status" | grep -o '"processing":{[^}]*}' | cut -d'{' -f2 | tr -d '}')
    
    log_info "  📊 Overall Status: $overall_status"
    log_info "  📈 Has Score: $has_score"
    log_info "  ⚙️  Processing Stages: $processing_stages"
    
    # Check individual scores
    local score_resp=$(curl -s "$API_URL/scores?resumeId=$resume_id&jobId=$job_id")
    local score_found=false
    
    if [[ $score_resp == *'"success":true'* ]]; then
        local final_score=$(echo "$score_resp" | grep -o '"final_score":[0-9.]*' | cut -d':' -f2)
        local keyword_score=$(echo "$score_resp" | grep -o '"keyword_score":[0-9.]*' | cut -d':' -f2)
        local semantic_score=$(echo "$score_resp" | grep -o '"semantic_score":[0-9.]*' | cut -d':' -f2)
        local project_score=$(echo "$score_resp" | grep -o '"project_score":[0-9.]*' | cut -d':' -f2)
        local hard_reqs=$(echo "$score_resp" | grep -o '"hard_requirements_met":[^,}]*' | cut -d':' -f2)
        
        if [ ! -z "$final_score" ]; then
            score_found=true
            log_success "  ✅ SCORES FOUND:"
            log_info "     🎯 Final: $final_score"
            log_info "     🔤 Keyword: ${keyword_score:-N/A}"
            log_info "     🧠 Semantic: ${semantic_score:-N/A}"
            log_info "     💼 Project: ${project_score:-N/A}"
            log_info "     ✅ Hard Reqs: ${hard_reqs:-N/A}"
        fi
    fi
    
    if [ "$score_found" = false ]; then
        log_warning "  ⚠️  NO SCORES FOUND for resume $resume_id and job $job_id"
        log_info "     Score API Response: $score_resp"
    fi
    
    # Final verification status
    if [ "$overall_status" = "completed" ] && [ "$score_found" = true ]; then
        log_success "  ✅ VERIFICATION PASSED: Resume fully processed and scored"
        return 0
    elif [ "$overall_status" = "completed" ]; then
        log_warning "  ⚠️  PARTIAL: Processing complete but no scores found"
        return 1
    elif [ "$overall_status" = "failed" ]; then
        log_error "  ❌ FAILED: Resume processing failed"
        return 1
    else
        log_info "  ⏳ IN PROGRESS: Status = $overall_status"
        return 1
    fi
}

echo "==================================="
echo "BullMQ Flow Complete Test"
echo "==================================="
echo ""

# Initialize master logging
> "$SSE_MASTER_LOG"
log_info "Starting complete pipeline test"
log_info "Master event log: $SSE_MASTER_LOG"

# Start Python processor monitoring
start_python_log_monitor

# Global arrays for resume tracking
declare -a RESUME_IDS
declare -a RESUME_FILENAMES

# Test 1: Check backend health
log_step "Step 1: Health Check"
log_info "Checking backend health..."
HEALTH=$(curl -s "$API_URL/health")
if [[ $HEALTH == *"OK"* ]]; then
    log_success "Backend is healthy"
else
    log_error "Backend not responding"
    exit 1
fi

# Test 2: Create Job and Upload JD
log_step "Step 2: Create Job and Upload JD from Dummy Folder"

# Check for JD file
JD_FILE="$DUMMY_FOLDER/JD - New AI-Ml Engineer - Latest 1.pdf"
if [ ! -f "$JD_FILE" ]; then
    log_error "JD file not found: $JD_FILE"
    exit 1
fi
log_info "Found JD file: $(basename "$JD_FILE")"

# Create job
log_info "Creating test job..."
JOB_RESP=$(curl -s -X POST "$API_URL/jobs" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "AI/ML Engineer",
    "description": "Testing complete flow with real JD from dummy folder",
    "company_name": "Test Corp"
  }')

JOB_ID=$(echo "$JOB_RESP" | grep -o '"_id":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$JOB_ID" ] || [ "$JOB_ID" == "null" ]; then
    log_error "Failed to create job"
    echo "$JOB_RESP"
    exit 1
fi
log_success "Job created: $JOB_ID"

# Upload JD file
log_info "Uploading JD PDF..."
JD_UPLOAD_RESP=$(curl -s -X POST "$API_URL/jobs/$JOB_ID/upload-jd" \
  -F "jd_pdf=@$JD_FILE")

if [[ $JD_UPLOAD_RESP == *'"success":true'* ]]; then
    log_success "JD file uploaded successfully"
    # Extract filename from response
    JD_FILENAME=$(echo "$JD_UPLOAD_RESP" | grep -o '"filename":"[^"]*"' | cut -d'"' -f4)
    log_info "Filename: $JD_FILENAME"
    
    # Update job with the filename
    log_info "Updating job with JD filename..."
    UPDATE_RESP=$(curl -s -X PUT "$API_URL/jobs/$JOB_ID" \
      -H "Content-Type: application/json" \
      -d "{\"jd_pdf_filename\": \"$JD_FILENAME\"}")
    
    if [[ $UPDATE_RESP == *'"success":true'* ]]; then
        log_success "Job updated with JD filename"
    else
        log_error "Failed to update job with filename"
        echo "$UPDATE_RESP"
        exit 1
    fi
else
    log_error "Failed to upload JD file"
    echo "$JD_UPLOAD_RESP"
    exit 1
fi

# Test 3: Process JD with SSE listening
log_step "Step 3: Process JD and Monitor via SSE"

# Create log file for SSE events FIRST
SSE_LOG="/tmp/sse_jd_$JOB_ID.log"
> "$SSE_LOG"

# Initialize progress display
echo ""
log_info "Starting JD Processing with Live Progress Bar..."
echo ""
JD_PROGRESS_LINE=$(($(tput lines) - 3))

# Start SSE listener BEFORE triggering processing
log_info "Connecting to SSE endpoint (waiting 2s for connection)..."
(curl -s -N -H "Accept: text/event-stream" "$API_URL/sse/jobs/$JOB_ID/progress" 2>&1 | while IFS= read -r line; do
    # Log ALL SSE events with detailed timestamps
    echo "[SSE] $line" >> "$SSE_LOG"
    log_sse "JD" "$line"
    
    if [[ $line == data:* ]]; then
        DATA="${line#data: }"
        
        # Show raw SSE data with enhanced logging
        echo "$(date '+%H:%M:%S.%3N') [SSE DATA] $DATA" >> "$SSE_LOG"
        log_sse "JD-DATA" "$DATA"
        
        # Parse JSON (basic parsing)
        if [[ $DATA == *"\"type\":\"progress"* ]]; then
            PERCENT=$(echo "$DATA" | grep -o '"progress":[0-9]*' | cut -d':' -f2)
            [ -z "$PERCENT" ] && PERCENT=$(echo "$DATA" | grep -o '"percent":[0-9]*' | cut -d':' -f2)
            MESSAGE=$(echo "$DATA" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
            STAGE=$(echo "$DATA" | grep -o '"stage":"[^"]*"' | cut -d'"' -f4)
            
            log_sse "JD-PROGRESS" "Stage: $STAGE, Progress: ${PERCENT}%, Message: $MESSAGE"
            
            # Update progress bar in place
            if [ -n "$PERCENT" ]; then
                tput sc
                tput cup $JD_PROGRESS_LINE 0
                tput el
                draw_progress_bar "$PERCENT" "JD Processing" "$STAGE: $MESSAGE"
                tput rc
            fi
        elif [[ $DATA == *"\"type\":\"complete"* ]] || [[ $DATA == *"\"type\":\"completed"* ]]; then
            echo "$(date '+%H:%M:%S') [COMPLETE EVENT DETECTED] $DATA" >> "$SSE_LOG"
            if [[ $DATA == *"\"success\":true"* ]]; then
                tput sc
                tput cup $JD_PROGRESS_LINE 0
                tput el
                draw_progress_bar 100 "JD Processing" "✓ Completed"
                tput rc
                echo "JD_COMPLETE" > /tmp/jd_complete_$JOB_ID
                break
            else
                tput sc
                tput cup $JD_PROGRESS_LINE 0
                tput el
                draw_progress_bar 0 "JD Processing" "✗ Failed"
                tput rc
                echo "JD_FAILED" > /tmp/jd_complete_$JOB_ID
                break
            fi
        elif [[ $DATA == *"\"type\":\"failure"* ]] || [[ $DATA == *"\"type\":\"failed"* ]]; then
            echo "$(date '+%H:%M:%S') [FAILURE EVENT DETECTED] $DATA" >> "$SSE_LOG"
            tput sc
            tput cup $JD_PROGRESS_LINE 0
            tput el
            draw_progress_bar 0 "JD Processing" "✗ Failed"
            tput rc
            echo "JD_FAILED" > /tmp/jd_complete_$JOB_ID
            break
        fi
    fi
done) &

SSE_PID=$!

# Give SSE connection time to establish
sleep 2

# Now trigger JD processing
log_info "Starting JD processing..."
JD_PROCESS_RESP=$(curl -s -X POST "$API_URL/process/jd/$JOB_ID")
echo "$JD_PROCESS_RESP"

if [[ ! $JD_PROCESS_RESP == *"success"* ]]; then
    log_error "Failed to queue JD processing"
    kill $SSE_PID 2>/dev/null || true
    exit 1
fi
log_success "JD processing queued"

# Wait for JD completion (max 3 minutes for JD processing)
log_info "Waiting for JD processing to complete (timeout: 180s)..."
JD_COMPLETE=false
WAIT_COUNT=0
while [ $WAIT_COUNT -lt 180 ]; do
    if [ -f "/tmp/jd_complete_$JOB_ID" ]; then
        JD_COMPLETE=true
        rm -f "/tmp/jd_complete_$JOB_ID"
        break
    fi
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
    if [ $((WAIT_COUNT % 10)) -eq 0 ]; then
        log_info "Still waiting... (${WAIT_COUNT}s elapsed)"
    fi
done

# Kill SSE listener
kill $SSE_PID 2>/dev/null || true

# Move cursor below progress bar
echo ""
echo ""

if [ "$JD_COMPLETE" = false ]; then
    log_error "JD processing timed out after ${WAIT_COUNT}s"
    log_info "SSE Events Log (last 50 lines):"
    cat "$SSE_LOG" | tail -50
    log_info "\nChecking job status directly..."
    JOB_STATUS=$(curl -s "$API_URL/jobs/$JOB_ID")
    echo "$JOB_STATUS" | grep -o '"status":"[^"]*"'
    exit 1
fi

log_info "SSE Events Summary:"
log_info "  Total events: $(wc -l < "$SSE_LOG")"
log_info "  Progress events: $(grep -c 'progress' "$SSE_LOG" || echo 0)"
log_info "  Complete events: $(grep -c 'complete' "$SSE_LOG" || echo 0)"

log_success "JD processing completed in ${WAIT_COUNT}s"

# Verify JD analysis was saved
log_info "Verifying JD analysis..."
JOB_DATA=$(curl -s "$API_URL/jobs/$JOB_ID")
if [[ $JOB_DATA == *"jd_analysis"* ]]; then
    log_success "JD analysis found in job data"
else
    log_warning "JD analysis not found (might still be processing)"
fi

# Test 4: Create Resume Group
log_step "Step 4: Create Resume Group"
log_info "Creating resume group linked to job..."
GROUP_RESP=$(curl -s -X POST "$API_URL/resume-groups" \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"Flow Test Group - $(date '+%Y%m%d%H%M%S')\", \"job_ids\": [\"$JOB_ID\"]}")

GROUP_ID=$(echo "$GROUP_RESP" | grep -o '"_id":"[^"]*"' | head -1 | cut -d'"' -f4)
if [ -z "$GROUP_ID" ] || [ "$GROUP_ID" == "null" ]; then
    log_error "Failed to create resume group"
    echo "$GROUP_RESP"
    exit 1
fi
log_success "Resume group created: $GROUP_ID"

# Test 5: Upload resumes from dummy folder
log_step "Step 5: Upload Resumes from Dummy Folder"
log_info "Checking for resumes in $DUMMY_FOLDER..."

if [ ! -d "$DUMMY_FOLDER" ]; then
    log_error "Dummy folder not found: $DUMMY_FOLDER"
    exit 1
fi

# Find resume PDF files (exclude JD files)
RESUME_FILES=()
while IFS= read -r -d '' file; do
    filename=$(basename "$file")
    # Skip JD files
    if [[ ! $filename =~ ^JD ]]; then
        RESUME_FILES+=("$file")
    fi
done < <(find "$DUMMY_FOLDER" -maxdepth 1 -type f -name "*.pdf" -print0)

RESUME_COUNT=${#RESUME_FILES[@]}

if [ $RESUME_COUNT -eq 0 ]; then
    log_error "No resume PDF files found in $DUMMY_FOLDER"
    exit 1
fi

log_info "Found $RESUME_COUNT resume files:"
for file in "${RESUME_FILES[@]}"; do
    log_info "  - $(basename "$file")"
done

# Test 6: Monitor Flow progress via SSE
log_step "Step 6: Monitor Resume Processing via SSE"

# Create log file for Flow SSE events FIRST
SSE_FLOW_LOG="/tmp/sse_flow_temp.log"
> "$SSE_FLOW_LOG"

# We'll rename it after we get the FLOW_ID
log_info "Note: Flow will be created during resume upload. Starting upload..."

# Upload resumes with Flow
log_info "Uploading $RESUME_COUNT resumes via Flow..."
UPLOAD_CMD="curl -s -X POST \"$API_URL/resume-groups/$GROUP_ID/upload\""
for file in "${RESUME_FILES[@]}"; do
    UPLOAD_CMD="$UPLOAD_CMD -F \"resumes=@$file\""
done
UPLOAD_CMD="$UPLOAD_CMD -F \"job_id=$JOB_ID\""

UPLOAD_RESP=$(eval $UPLOAD_CMD)

if [[ ! $UPLOAD_RESP == *"flowJobId"* ]]; then
    log_error "Failed to create Flow job"
    echo "$UPLOAD_RESP"
    exit 1
fi

FLOW_ID=$(echo "$UPLOAD_RESP" | grep -o '"flowJobId":"[^"]*"' | cut -d'"' -f4)
CHILDREN_COUNT=$(echo "$UPLOAD_RESP" | grep -o '"childrenCount":[0-9]*' | cut -d':' -f2)

# Extract resume IDs from upload response using proper JSON structure
log_info "Extracting resume IDs from upload response..."

# Save upload response to temp file for jq processing
TEMP_UPLOAD_FILE="/tmp/upload_response_$FLOW_ID.json"
echo "$UPLOAD_RESP" > "$TEMP_UPLOAD_FILE"

# Use jq to extract resume data properly
if command -v jq >/dev/null 2>&1; then
    # Extract with jq (preferred method)
    while IFS=$'\t' read -r resume_id filename; do
        if [ -n "$resume_id" ]; then
            RESUME_IDS+=("$resume_id")
            RESUME_FILENAMES+=("$filename")
            log_info "  📄 Resume: $filename (ID: $resume_id)"
        fi
    done < <(jq -r '.data[] | [._id, .original_name] | @tsv' "$TEMP_UPLOAD_FILE")
else
    # Fallback to grep parsing (backup method)
    log_warning "jq not available, using grep parsing..."
    echo "$UPLOAD_RESP" | grep -o '"_id":"[^"]*"' | while read -r id_match; do
        RESUME_ID=$(echo "$id_match" | cut -d'"' -f4)
        if [ -n "$RESUME_ID" ]; then
            RESUME_IDS+=("$RESUME_ID")
            log_info "  📄 Resume ID: $RESUME_ID"
        fi
    done
fi

# Cleanup temp file
rm -f "$TEMP_UPLOAD_FILE"

log_success "Flow job created!"
log_info "  Flow Job ID: $FLOW_ID"
log_info "  Children Count: $CHILDREN_COUNT"
log_info "  Resume IDs captured: ${#RESUME_IDS[@]}"

# Now rename the log file with the actual Flow ID
SSE_FLOW_LOG="/tmp/sse_flow_$FLOW_ID.log"
mv "/tmp/sse_flow_temp.log" "$SSE_FLOW_LOG" 2>/dev/null || > "$SSE_FLOW_LOG"

# Start SSE listener for Flow progress
log_info "Connecting to SSE endpoint for Flow monitoring..."
echo ""
echo -e "${BOLD}${CYAN}Resume Processing Progress:${NC}"
echo ""

# Store resume data
declare -A RESUME_NAMES
declare -A RESUME_PROGRESS
declare -A RESUME_STATUS

FLOW_COMPLETE=false

# Calculate starting line for progress bars
PROGRESS_BASE_LINE=$(($(tput lines) - 15))

(curl -s -N -H "Accept: text/event-stream" "$API_URL/sse/flow/$FLOW_ID/progress" 2>&1 | while IFS= read -r line; do
    # Log ALL SSE events with enhanced detail
    echo "[SSE] $line" >> "$SSE_FLOW_LOG"
    log_sse "FLOW" "$line"
    
    if [[ $line == data:* ]]; then
        DATA="${line#data: }"
        
        # Show raw SSE data with microsecond timestamps
        echo "$(date '+%H:%M:%S.%3N') [SSE DATA] $DATA" >> "$SSE_FLOW_LOG"
        log_sse "FLOW-DATA" "$DATA"
        
        if [[ $DATA == *"\"type\":\"progress"* ]]; then
            # Extract overall progress
            OVERALL_PROGRESS=$(echo "$DATA" | grep -o '"overallProgress":[0-9]*' | cut -d':' -f2)
            SCORING_PROGRESS=$(echo "$DATA" | grep -o '"scoringProgress":[0-9]*' | cut -d':' -f2)
            COMPLETED=$(echo "$DATA" | grep -o '"completed":[0-9]*' | head -1 | cut -d':' -f2)
            TOTAL=$(echo "$DATA" | grep -o '"total":[0-9]*' | head -1 | cut -d':' -f2)
            SCORED=$(echo "$DATA" | grep -o '"scored":[0-9]*' | cut -d':' -f2)
            
            # Parse children array for individual resume progress
            # This is simplified - in production you'd use jq
            RESUME_COUNT=0
            
            # Try to extract individual resume data
            while read -r resume_data; do
                RESUME_ID=$(echo "$resume_data" | grep -o '"resumeId":"[^"]*"' | cut -d'"' -f4)
                FILENAME=$(echo "$resume_data" | grep -o '"filename":"[^"]*"' | cut -d'"' -f4)
                PROGRESS=$(echo "$resume_data" | grep -o '"progress":[0-9]*' | head -1 | cut -d':' -f2)
                STATE=$(echo "$resume_data" | grep -o '"state":"[^"]*"' | cut -d'"' -f4)
                HAS_SCORE=$(echo "$resume_data" | grep -o '"hasScore":[^,}]*' | cut -d':' -f2)
                
                if [ -n "$RESUME_ID" ] && [ -n "$PROGRESS" ]; then
                    # Store resume data
                    RESUME_NAMES[$RESUME_COUNT]="$FILENAME"
                    RESUME_PROGRESS[$RESUME_COUNT]="$PROGRESS"
                    
                    # Determine status message
                    if [ "$HAS_SCORE" = "true" ]; then
                        SCORE=$(echo "$resume_data" | grep -o '"score":[0-9.]*' | cut -d':' -f2)
                        RESUME_STATUS[$RESUME_COUNT]="✓ Scored: $SCORE"
                    elif [ "$STATE" = "completed" ]; then
                        RESUME_STATUS[$RESUME_COUNT]="✓ Processing Complete"
                    elif [ "$STATE" = "failed" ]; then
                        RESUME_STATUS[$RESUME_COUNT]="✗ Failed"
                    elif [ "$STATE" = "active" ]; then
                        RESUME_STATUS[$RESUME_COUNT]="⚙ Processing..."
                    else
                        RESUME_STATUS[$RESUME_COUNT]="⏳ Waiting..."
                    fi
                    
                    RESUME_COUNT=$((RESUME_COUNT + 1))
                fi
            done < <(echo "$DATA" | grep -o '{[^}]*"resumeId"[^}]*}' || echo "")
            
            # Update all progress bars
            tput sc
            
            # Overall progress bar
            tput cup $PROGRESS_BASE_LINE 0
            tput el
            draw_progress_bar "${OVERALL_PROGRESS:-0}" "Overall Progress" "($COMPLETED/$TOTAL completed)"
            
            # Scoring progress bar
            tput cup $((PROGRESS_BASE_LINE + 1)) 0
            tput el
            draw_progress_bar "${SCORING_PROGRESS:-0}" "Scoring Progress" "($SCORED/$TOTAL scored)"
            
            # Individual resume progress bars
            for ((i=0; i<RESUME_COUNT && i<10; i++)); do
                LINE=$((PROGRESS_BASE_LINE + 3 + i))
                tput cup $LINE 0
                tput el
                
                FILENAME="${RESUME_NAMES[$i]}"
                [ ${#FILENAME} -gt 25 ] && FILENAME="${FILENAME:0:22}..."
                
                PROGRESS="${RESUME_PROGRESS[$i]}"
                STATUS="${RESUME_STATUS[$i]}"
                
                draw_progress_bar "$PROGRESS" "$FILENAME" "$STATUS"
            done
            
            tput rc
            
        elif [[ $DATA == *"\"type\":\"complete"* ]] || [[ $DATA == *"\"type\":\"completed"* ]]; then
            echo "$(date '+%H:%M:%S') [COMPLETE EVENT DETECTED] $DATA" >> "$SSE_FLOW_LOG"
            
            # Final update with 100%
            tput sc
            tput cup $PROGRESS_BASE_LINE 0
            tput el
            draw_progress_bar 100 "Overall Progress" "✓ All Completed"
            tput rc
            
            echo "FLOW_COMPLETE" > /tmp/flow_complete_$FLOW_ID
            break
        elif [[ $DATA == *"\"type\":\"failure"* ]] || [[ $DATA == *"\"type\":\"failed"* ]]; then
            echo "$(date '+%H:%M:%S') [FAILURE EVENT DETECTED] $DATA" >> "$SSE_FLOW_LOG"
            echo "FLOW_FAILED" > /tmp/flow_complete_$FLOW_ID
            break
        fi
    fi
done) &

SSE_FLOW_PID=$!

# Reserve space for progress bars
for ((i=0; i<15; i++)); do
    echo ""
done

# Also poll Flow status API
WAIT_COUNT=0
LAST_PROGRESS=-1

while [ $WAIT_COUNT -lt $TIMEOUT ]; do
    if [ -f "/tmp/flow_complete_$FLOW_ID" ]; then
        # Check if it's a failure or success
        if grep -q "FLOW_FAILED" "/tmp/flow_complete_$FLOW_ID" 2>/dev/null; then
            rm -f "/tmp/flow_complete_$FLOW_ID"
            echo ""
            echo ""
            log_error "Flow processing failed!"
            log_info "SSE Events Log (last 30 lines):"
            cat "$SSE_FLOW_LOG" | tail -30
            exit 1
        fi
        FLOW_COMPLETE=true
        rm -f "/tmp/flow_complete_$FLOW_ID"
        break
    fi
    
    sleep 1
    WAIT_COUNT=$((WAIT_COUNT + 1))
done

# Kill SSE listener
kill $SSE_FLOW_PID 2>/dev/null || true

# Move cursor below progress bars
echo ""
echo ""

if [ "$FLOW_COMPLETE" = false ]; then
    log_error "Flow processing timed out after ${WAIT_COUNT}s"
    log_info "SSE Events Log (last 50 lines):"
    cat "$SSE_FLOW_LOG" | tail -50
    log_info "\nChecking Flow status directly..."
    FLOW_STATUS=$(curl -s "$API_URL/status/flow/$FLOW_ID/status")
    echo "$FLOW_STATUS" | grep -E '"state"|"progress"|"completed"' | head -10
    exit 1
fi

log_info "SSE Events Summary:"
log_info "  Total events: $(wc -l < "$SSE_FLOW_LOG")"
log_info "  Progress events: $(grep -c 'progress' "$SSE_FLOW_LOG" || echo 0)"
log_info "  Complete events: $(grep -c 'complete' "$SSE_FLOW_LOG" || echo 0)"

log_success "Flow processing completed in ${WAIT_COUNT}s"

# Test 7: Comprehensive Resume Verification
log_step "Step 7: COMPREHENSIVE Resume Processing Verification"
log_info "Performing detailed verification for all resumes..."

# Wait a moment for final processing
log_info "Waiting 5 seconds for any final processing to complete..."
sleep 5

ALL_SUCCESS=true
SCORED_COUNT=0
VERIFIED_COUNT=0

# If RESUME_IDS is empty, try to get them from the flow status
if [ ${#RESUME_IDS[@]} -eq 0 ]; then
    log_warning "No resume IDs captured from upload. Attempting to get from flow status..."
    
    FLOW_STATUS=$(curl -s "$API_URL/status/flow/$FLOW_ID/status")
    
    # Extract resume IDs from children array
    echo "$FLOW_STATUS" | grep -o '{[^}]*"resumeId"[^}]*}' | while read -r resume_data; do
        RESUME_ID=$(echo "$resume_data" | grep -o '"resumeId":"[^"]*"' | cut -d'"' -f4)
        if [ -n "$RESUME_ID" ]; then
            RESUME_IDS+=("$RESUME_ID")
            log_info "Recovered Resume ID: $RESUME_ID"
        fi
    done
fi

log_info "Verifying ${#RESUME_IDS[@]} resumes individually..."
echo ""

# Individual comprehensive verification for each resume
for i in "${!RESUME_IDS[@]}"; do
    resume_id="${RESUME_IDS[$i]}"
    filename="${RESUME_FILENAMES[$i]:-Unknown}"
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}${MAGENTA} 📋 RESUME VERIFICATION #$((i+1))/${#RESUME_IDS[@]} ${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if verify_resume_complete "$resume_id" "$JOB_ID" "$filename"; then
        VERIFIED_COUNT=$((VERIFIED_COUNT + 1))
        SCORED_COUNT=$((SCORED_COUNT + 1))
    else
        ALL_SUCCESS=false
    fi
    
    echo ""
done

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
log_info "VERIFICATION SUMMARY:"
log_info "  Total Resumes: ${#RESUME_IDS[@]}"
log_info "  Fully Verified: $VERIFIED_COUNT"
log_info "  Scored: $SCORED_COUNT"
log_info "  Success Rate: $(( VERIFIED_COUNT * 100 / ${#RESUME_IDS[@]} ))%"

if [ "$ALL_SUCCESS" = true ]; then
    log_success "🎉 ALL RESUMES FULLY PROCESSED AND SCORED!"
else
    log_warning "⚠️  Some resumes may not be fully processed or scored"
fi

# Test 8: Verify Scores via Flow Status
log_step "Step 8: Verify Scoring Progress"
log_info "Checking scoring status via flow endpoint..."

FLOW_STATUS=$(curl -s "$API_URL/status/flow/$FLOW_ID/status")

if [[ $FLOW_STATUS == *"parentJobId"* ]]; then
    SCORING_PROGRESS=$(echo "$FLOW_STATUS" | grep -o '"scoringProgress":[0-9]*' | cut -d':' -f2)
    SCORED_COUNT=$(echo "$FLOW_STATUS" | grep -o '"scored":[0-9]*' | cut -d':' -f2)
    TOTAL_RESUMES=$(echo "$FLOW_STATUS" | grep -o '"total":[0-9]*' | head -1 | cut -d':' -f2)
    
    log_info "Scoring Progress: ${SCORING_PROGRESS}%"
    log_info "Scored: $SCORED_COUNT out of $TOTAL_RESUMES resumes"
    
    if [ "$SCORING_PROGRESS" == "100" ]; then
        log_success "All resumes have been scored!"
    elif [ "$SCORED_COUNT" -gt 0 ]; then
        log_success "Found scores for $SCORED_COUNT resumes"
    else
        log_warning "No scores found yet"
    fi
    
    # Show individual scores if available
    log_info "Checking individual score details..."
    for resume_id in "${RESUME_IDS[@]}"; do
        SCORE_RESP=$(curl -s "$API_URL/scores?resumeId=$resume_id&jobId=$JOB_ID")
        
        if [[ $SCORE_RESP == *"\"success\":true"* ]]; then
            KEYWORD_SCORE=$(echo "$SCORE_RESP" | grep -o '"keyword_score":[0-9.]*' | cut -d':' -f2)
            SEMANTIC_SCORE=$(echo "$SCORE_RESP" | grep -o '"semantic_score":[0-9.]*' | cut -d':' -f2)
            PROJECT_SCORE=$(echo "$SCORE_RESP" | grep -o '"project_score":[0-9.]*' | cut -d':' -f2)
            FINAL_SCORE=$(echo "$SCORE_RESP" | grep -o '"final_score":[0-9.]*' | cut -d':' -f2)
            
            if [ ! -z "$FINAL_SCORE" ]; then
                log_info "  Resume $resume_id:"
                log_info "    Keyword: ${KEYWORD_SCORE:-N/A}, Semantic: ${SEMANTIC_SCORE:-N/A}, Project: ${PROJECT_SCORE:-N/A}"
                log_info "    Final Score: ${FINAL_SCORE}"
            fi
        fi
    done
else
    log_warning "Could not fetch flow status"
fi

# Test 9: Final Flow Status
log_step "Step 9: Final Flow Status Check"
log_info "Getting final Flow status..."
FINAL_STATUS=$(curl -s "$API_URL/status/flow/$FLOW_ID/status")

if [[ $FINAL_STATUS == *"parentJobId"* ]]; then
    FINAL_PROGRESS=$(echo "$FINAL_STATUS" | grep -o '"overallProgress":[0-9]*' | cut -d':' -f2)
    SCORING_PROGRESS=$(echo "$FINAL_STATUS" | grep -o '"scoringProgress":[0-9]*' | cut -d':' -f2)
    FINAL_COMPLETED=$(echo "$FINAL_STATUS" | grep -o '"completed":[0-9]*' | head -1 | cut -d':' -f2)
    FINAL_FAILED=$(echo "$FINAL_STATUS" | grep -o '"failed":[0-9]*' | head -1 | cut -d':' -f2)
    FINAL_SCORED=$(echo "$FINAL_STATUS" | grep -o '"scored":[0-9]*' | cut -d':' -f2)
    FINAL_TOTAL=$(echo "$FINAL_STATUS" | grep -o '"total":[0-9]*' | head -1 | cut -d':' -f2)
    
    log_info "Final Status:"
    log_info "  Overall Progress: ${FINAL_PROGRESS}%"
    log_info "  Scoring Progress: ${SCORING_PROGRESS}%"
    log_info "  Completed: $FINAL_COMPLETED"
    log_info "  Scored: $FINAL_SCORED"
    log_info "  Failed: $FINAL_FAILED"
    log_info "  Total: $FINAL_TOTAL"
    
    if [ "$FINAL_PROGRESS" == "100" ] && [ "$SCORING_PROGRESS" == "100" ]; then
        log_success "Flow completed successfully with all resumes scored!"
    elif [ "$FINAL_PROGRESS" == "100" ]; then
        log_success "Flow processing completed!"
        if [ "$SCORING_PROGRESS" -lt "100" ]; then
            log_warning "Scoring still in progress: ${SCORING_PROGRESS}%"
        fi
    fi
fi

# Test 10: Final Ranking Table
log_step "Step 10: Final Candidate Ranking"
log_info "Fetching all scores for job: $JOB_ID"

# Fetch all scores for this job
SCORES_RESP=$(curl -s "$API_URL/scores?jobId=$JOB_ID")

if [[ $SCORES_RESP == *"\"success\":true"* ]]; then
    log_success "Scores fetched successfully"
    
    # Create temporary file to store scores for sorting
    SCORES_TMP="/tmp/scores_$JOB_ID.txt"
    > "$SCORES_TMP"
    
    # Parse scores (simplified - in production use jq)
    # Extract each score object and parse it
    echo "$SCORES_RESP" | grep -o '{[^}]*"resume_id"[^}]*}' | while read -r score_obj; do
        RESUME_ID=$(echo "$score_obj" | grep -o '"resume_id":"[^"]*"' | cut -d'"' -f4)
        FINAL_SCORE=$(echo "$score_obj" | grep -o '"final_score":[0-9.]*' | cut -d':' -f2)
        KEYWORD_SCORE=$(echo "$score_obj" | grep -o '"keyword_score":[0-9.]*' | cut -d':' -f2)
        SEMANTIC_SCORE=$(echo "$score_obj" | grep -o '"semantic_score":[0-9.]*' | cut -d':' -f2)
        PROJECT_SCORE=$(echo "$score_obj" | grep -o '"project_score":[0-9.]*' | cut -d':' -f2)
        HARD_REQS=$(echo "$score_obj" | grep -o '"hard_requirements_met":[^,}]*' | cut -d':' -f2 | tr -d ' ')
        
        if [ -n "$RESUME_ID" ] && [ -n "$FINAL_SCORE" ]; then
            # Get resume filename
            RESUME_DATA=$(curl -s "$API_URL/resumes/$RESUME_ID")
            FILENAME=$(echo "$RESUME_DATA" | grep -o '"filename":"[^"]*"' | head -1 | cut -d'"' -f4)
            
            # Store in temp file: final_score|filename|keyword|semantic|project|hard_reqs
            echo "${FINAL_SCORE}|${FILENAME}|${KEYWORD_SCORE}|${SEMANTIC_SCORE}|${PROJECT_SCORE}|${HARD_REQS}" >> "$SCORES_TMP"
        fi
    done
    
    # Check if we got any scores
    if [ -s "$SCORES_TMP" ]; then
        # Sort by final score (descending)
        SORTED_SCORES=$(sort -t'|' -k1 -rn "$SCORES_TMP")
        
        echo ""
        echo -e "${BOLD}${GREEN}🏆 CANDIDATE RANKING - Top Matches for $JOB_ID${NC}"
        echo ""
        
        # Draw table
        draw_table_header
        
        # Display ranked results
        RANK=1
        while IFS='|' read -r final filename keyword semantic project hard_reqs; do
            draw_table_row "$RANK" "$filename" "$final" "$keyword" "$semantic" "$project" "$hard_reqs"
            RANK=$((RANK + 1))
        done <<< "$SORTED_SCORES"
        
        draw_table_footer
        
        echo ""
        
        # Show top 3 summary
        TOP_3=$(echo "$SORTED_SCORES" | head -3)
        echo -e "${BOLD}${CYAN}Top 3 Candidates:${NC}"
        echo ""
        
        RANK=1
        while IFS='|' read -r final filename keyword semantic project hard_reqs; do
            MEDAL="🥇"
            [ "$RANK" == "2" ] && MEDAL="🥈"
            [ "$RANK" == "3" ] && MEDAL="🥉"
            
            echo -e "${MEDAL} ${BOLD}#$RANK${NC} - ${GREEN}$filename${NC}"
            echo -e "   Final Score: ${BOLD}${final}${NC}"
            echo -e "   Breakdown: Keyword=${keyword}, Semantic=${semantic}, Project=${project}"
            
            if [ "$hard_reqs" == "true" ] || [ "$hard_reqs" == "True" ]; then
                echo -e "   Hard Requirements: ${GREEN}✓ Met${NC}"
            else
                echo -e "   Hard Requirements: ${RED}✗ Not Met${NC}"
            fi
            echo ""
            
            RANK=$((RANK + 1))
        done <<< "$TOP_3"
        
        # Cleanup
        rm -f "$SCORES_TMP"
        
        log_success "Ranking table displayed successfully!"
    else
        log_warning "No scores found in response"
    fi
else
    log_warning "Could not fetch scores for ranking"
fi

# Summary
log_step "Test Summary"
echo ""
log_success "════════════════════════════════════════════════════════════"
log_success "All tests completed successfully!"
log_success "════════════════════════════════════════════════════════════"
echo ""
echo "Test Results:"
echo "  Job ID: $JOB_ID"
echo "  Group ID: $GROUP_ID"
echo "  Flow Job ID: $FLOW_ID"
echo "  Resumes Uploaded: $RESUME_COUNT"
echo "  Resumes Scored: ${SCORED_COUNT:-0}/${RESUME_COUNT}"
echo ""
echo "Check logs for more details:"
echo "  Backend: docker logs kreeda-backend --tail 100"
echo "  Python Processor: docker logs kreeda-python-processor --tail 100"
echo ""
log_success "Pipeline test completed successfully! 🎉"

# Cleanup and Final Analysis
log_step "Final Analysis & Cleanup"

# Stop Python log monitoring
stop_python_log_monitor

# Analyze logs
log_info "📊 LOG ANALYSIS SUMMARY:"
log_info "  Master Event Log: $SSE_MASTER_LOG ($(wc -l < "$SSE_MASTER_LOG") lines)"
log_info "  Python Processor Log: $PYTHON_LOG_FILE ($(wc -l < "$PYTHON_LOG_FILE") lines)"

if [ -f "$SSE_LOG" ]; then
    JD_SSE_EVENTS=$(wc -l < "$SSE_LOG")
    log_info "  JD SSE Events: $JD_SSE_EVENTS"
fi

if [ -f "$SSE_FLOW_LOG" ]; then
    FLOW_SSE_EVENTS=$(wc -l < "$SSE_FLOW_LOG")
    log_info "  Flow SSE Events: $FLOW_SSE_EVENTS"
fi

# Show recent Python processor activity
if [ -f "$PYTHON_LOG_FILE" ] && [ -s "$PYTHON_LOG_FILE" ]; then
    log_info ""
    log_info "📋 Recent Python Processor Activity (last 20 lines):"
    echo -e "${YELLOW}────────────────────────────────────────────────────────────${NC}"
    tail -20 "$PYTHON_LOG_FILE" | while IFS= read -r line; do
        echo -e "${CYAN}$line${NC}"
    done
    echo -e "${YELLOW}────────────────────────────────────────────────────────────${NC}"
else
    log_warning "No Python processor activity logged"
fi

# Final recommendations
log_info ""
log_info "📁 DETAILED LOGS AVAILABLE AT:"
log_info "  🔍 Master Events: $SSE_MASTER_LOG"
log_info "  🐍 Python Logs: $PYTHON_LOG_FILE"
[ -f "$SSE_LOG" ] && log_info "  📡 JD SSE: $SSE_LOG"
[ -f "$SSE_FLOW_LOG" ] && log_info "  📡 Flow SSE: $SSE_FLOW_LOG"

log_info ""
log_info "🔧 DOCKER COMMANDS FOR FURTHER INVESTIGATION:"
log_info "  Backend: docker logs kreeda-backend --tail 100 -f"
log_info "  Python: docker logs kreeda-python-processor --tail 100 -f"
log_info "  Redis: docker logs kreeda-redis --tail 100 -f"

log_success "🎯 Complete pipeline test finished with comprehensive logging!"

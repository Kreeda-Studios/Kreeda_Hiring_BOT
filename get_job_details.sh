#!/bin/bash

# Get Job Details by Job ID
# Usage: ./get_job_details.sh <job_id>
# Example: ./get_job_details.sh 65f1a2b3c4d5e6f7g8h9i0j1

API_URL="${API_BASE_URL:-https://hiringbot.kreedalabs.com}"
ENDPOINT="/api/jobs"

# Check if job ID is provided
if [ -z "$1" ]; then
    echo "❌ Error: Job ID is required"
    echo "Usage: ./get_job_details.sh <job_id>"
    echo ""
    echo "Example:"
    echo "  ./get_job_details.sh 65f1a2b3c4d5e6f7g8h9i0j1"
    exit 1
fi

JOB_ID="$1"

echo "🔍 Fetching job details for ID: $JOB_ID"
echo "📡 Connecting to: $API_URL$ENDPOINT/$JOB_ID"
echo ""

# Fetch the job data
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL$ENDPOINT/$JOB_ID")

# Extract HTTP code (last line)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
# Extract body (all lines except last)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" != "200" ]; then
    echo "❌ Error: HTTP $HTTP_CODE"
    echo "$BODY" | jq '.' 2>/dev/null || echo "$BODY"
    exit 1
fi

# Parse and display JSON, excluding embedding fields
echo "✅ Job Details (JSON format - embeddings excluded):"
echo ""
echo "$BODY" | jq 'del(.. | .embedding_hints?, .profile_embed?, .skills_embed?, .projects_embed?, .responsibilities_embed?, .overall_embed?, .negatives_embed?, .seniority_embed?)' 2>/dev/null || echo "$BODY"

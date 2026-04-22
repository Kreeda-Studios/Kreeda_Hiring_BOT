#!/bin/bash

# Get Resume Details by Resume ID
# Usage: ./get_resume_details.sh <resume_id>
# Example: ./get_resume_details.sh 65f1a2b3c4d5e6f7g8h9i0j1

API_URL="${API_BASE_URL:-http://localhost}"
ENDPOINT="/api/resumes"

# Check if resume ID is provided
if [ -z "$1" ]; then
    echo "❌ Error: Resume ID is required"
    echo "Usage: ./get_resume_details.sh <resume_id>"
    echo ""
    echo "Example:"
    echo "  ./get_resume_details.sh 65f1a2b3c4d5e6f7g8h9i0j1"
    exit 1
fi

RESUME_ID="$1"

echo "🔍 Fetching resume details for ID: $RESUME_ID"
echo "📡 Connecting to: $API_URL$ENDPOINT/$RESUME_ID"
echo ""

# Fetch the resume data
RESPONSE=$(curl -s -w "\n%{http_code}" "$API_URL$ENDPOINT/$RESUME_ID")

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
echo "✅ Resume Details (JSON format - embeddings excluded):"
echo ""
echo "$BODY" | jq 'del(.. | .embedding_hints?, .profile_embed?, .skills_embed?, .projects_embed?, .responsibilities_embed?, .overall_embed?, .negatives_embed?, .seniority_embed?)' 2>/dev/null || echo "$BODY"

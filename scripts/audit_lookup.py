#!/usr/bin/env python3
"""
Candidate Score Audit Lookup Helper

Usage:
  python audit_lookup.py --resume_id <RESUME_ID>
  python audit_lookup.py --job_id <JOB_ID>

Given a candidate or job ID, retrieves score metadata and outputs:
1. Pipeline Version (e.g. 1.2.0)
2. LLM & Embedding Models used (e.g. gpt-4o-mini)
3. Prompt Version Registry
4. Exact Timestamp when scored
"""

import sys
import os
import argparse
import requests
from pathlib import Path

# Add paths
script_dir = Path(__file__).parent
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))

try:
    from common.api_client import api
except ImportError:
    api = None

BACKEND_API_URL = (
    os.getenv('BACKEND_API_URL') or 
    os.getenv('NEXT_PUBLIC_API_URL') or 
    'http://localhost:3001/api'
).rstrip('/')


def lookup_resume_audit(resume_id: str):
    """Fetch audit metadata for a specific resume ID"""
    if api:
        try:
            res = api.post('/updates/resumes/batch', data={'resume_ids': [resume_id]})
            resumes = res.get('data', [])
        except Exception as e:
            print(f"❌ Failed to fetch resume via api_client: {e}")
            return
    else:
        url = f"{BACKEND_API_URL}/updates/resumes/batch"
        headers = {'Content-Type': 'application/json'}

        res = requests.post(url, json={'resume_ids': [resume_id]}, headers=headers)
        if res.status_code != 200:
            print(f"❌ Failed to fetch resume: {res.text}")
            return
        data = res.json()
        resumes = data.get('data', [])
    if not resumes:
        print(f"⚠️ Resume {resume_id} not found.")
        return

    resume = resumes[0]
    scores = resume.get('scores', {})
    meta = scores.get('pipeline_metadata', {})

    print(f"\n{'='*70}")
    print(f"🔍 AUDIT REPORT FOR RESUME: {resume_id}")
    print(f"{'='*70}")
    print(f"  📌 Candidate Name:   {resume.get('candidate_name', 'N/A')}")
    print(f"  🏆 Final Score:       {scores.get('composite_score', 0.0):.2f}")
    print(f"  🏷️ Pipeline Version:  {meta.get('pipeline_version', 'Legacy (Pre-1.2.0)')}")
    print(f"  🤖 LLM Model:        {meta.get('model_used', 'N/A')}")
    print(f"  🧠 Embedding Model:   {meta.get('embedding_model', 'N/A')}")
    print(f"  ⏱️ Processed At:     {meta.get('processed_at', 'N/A')}")
    
    prompts = meta.get('prompt_versions', {})
    if prompts:
        print(f"\n  📜 Active Prompt Registries:")
        for k, v in prompts.items():
            print(f"     - {k}: {v}")
    print(f"{'='*70}\n")


def main():
    parser = argparse.ArgumentParser(description="Candidate Score Audit Lookup")
    parser.add_argument("--resume_id", type=str, help="Resume ID to audit")
    args = parser.parse_args()

    if args.resume_id:
        lookup_resume_audit(args.resume_id)
    else:
        print("Please provide --resume_id <ID>")


if __name__ == "__main__":
    main()

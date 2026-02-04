#!/usr/bin/env python3
"""
Final Ranking Processor with LLM Re-ranking

Implements exact same logic as the old archive FinalRanking.py:
- Processes batches of 30 candidates
- Uses OpenAI GPT-4o-mini for LLM re-ranking
- Validates compliance and re-ranks based on all scores
- Returns detailed ranking results with compliance breakdown
"""

import os
import sys
import json
import time
from typing import List, Dict, Any
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from openai import OpenAI
except ImportError:
    print("❌ OpenAI library not found. Install with: pip install openai")
    sys.exit(1)

import requests

# Constants from old archive
RE_RANK_BATCH_SIZE = 30  # Batch size for LLM re-ranking
RE_RANK_MODEL = "gpt-4o-mini"  # Model for re-ranking

# Backend API configuration
BACKEND_API_URL = os.getenv('BACKEND_API_URL', 'http://localhost:3001/api')
BACKEND_API_KEY = os.getenv('BACKEND_API_KEY', '')


def get_candidate_scores_via_api(job_id: str) -> List[Dict]:
    """
    Collect all candidate scores for ranking via backend API
    
    API endpoint: GET /api/updates/scores/{jobId}
    """
    try:
        headers = {}
        if BACKEND_API_KEY:
            headers['Authorization'] = f'Bearer {BACKEND_API_KEY}'
        
        response = requests.get(
            f'{BACKEND_API_URL}/updates/scores/{job_id}',
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        scores = result.get('data', [])
        
        # Transform to candidate format matching old archive
        candidates = []
        for score in scores:
            resume = score.get('resume_id', {})
            # Handle both populated and non-populated resume_id
            if isinstance(resume, dict):
                resume_id = str(resume.get('_id', ''))
                candidate_name = resume.get('candidate_name', 'Unknown')
                group_id = str(resume.get('group_id', ''))
            else:
                resume_id = str(resume)
                candidate_name = 'Unknown'
                group_id = ''
            
            candidates.append({
                'candidate_id': resume_id,
                'name': candidate_name,
                'group_id': group_id,
                'Keyword_Score': score.get('keyword_score', 0.0),
                'Semantic_Score': score.get('semantic_score', 0.0),
                'project_aggregate': score.get('project_score', 0.0),
                'Final_Score': score.get('final_score', 0.0),
                'hard_requirements_met': score.get('hard_requirements_met', False),
                'score_breakdown': score.get('score_breakdown', {})
            })
        
        print(f"✅ Fetched {len(candidates)} candidate scores for job {job_id} via API")
        return candidates
        
    except Exception as e:
        print(f"❌ Error getting candidate scores via API: {e}")
        return []


def get_resume_data_via_api(resume_id: str) -> Dict:
    """
    Get resume data via backend API for LLM re-ranking
    
    API endpoint: GET /api/resumes/{resumeId}
    """
    try:
        headers = {}
        if BACKEND_API_KEY:
            headers['Authorization'] = f'Bearer {BACKEND_API_KEY}'
        
        response = requests.get(
            f'{BACKEND_API_URL}/resumes/{resume_id}',
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        resume_data = result.get('data', {})
        
        # Extract parsed resume data if available
        parsed_resume = resume_data.get('parsed_resume', {})
        return parsed_resume
        
    except Exception as e:
        print(f"⚠️ Error getting resume data for {resume_id}: {e}")
        return {}


def create_candidate_summary(candidate: dict, resume_json: dict = None) -> dict:
    """
    Create compact candidate summary for LLM re-ranking.
    Uses abbreviations to minimize tokens - exact same logic as old archive.
    """
    summary = {
        "id": candidate.get("candidate_id", ""),  # Use candidate_id, not name
        "n": candidate.get("name", ""),  # Name for reference only
        "sc": {  # All scores (abbreviated)
            "p": candidate.get("project_aggregate", 0.0),
            "k": candidate.get("Keyword_Score", 0.0),
            "s": candidate.get("Semantic_Score", 0.0),
            "f": candidate.get("Final_Score", 0.0)
        }
    }
    
    # Add resume data if available
    if resume_json:
        summary["exp"] = resume_json.get("years_experience")
        summary["loc"] = resume_json.get("location", "")
        summary["role"] = resume_json.get("role_claim", "")
        
        # Top skills (limit to 10)
        skills = []
        canonical = resume_json.get("canonical_skills", {})
        for cat_skills in canonical.values():
            if isinstance(cat_skills, list):
                skills.extend(cat_skills[:5])  # Top 5 per category
        summary["sk"] = skills[:10]  # Top 10 total
        
        # Top 3 projects summary
        projects = resume_json.get("projects", [])[:3]
        summary["pj"] = [
            {
                "n": p.get("name", "")[:50],
                "tech": ", ".join(p.get("tech_keywords", [])[:5]),
                "score": p.get("metrics", {}).get("domain_relevance", 0.0)
            }
            for p in projects
        ]
    else:
        # Fallback if resume JSON not available
        summary["exp"] = None
        summary["loc"] = ""
        summary["sk"] = []
        summary["pj"] = []
    
    return summary


def check_all_requirements(candidate: dict, resume_json: dict, filter_requirements: dict) -> dict:
    """
    Check compliance with all filter requirements.
    Simplified version for now - can be extended based on actual requirements structure.
    """
    compliance = {}
    
    if not filter_requirements or not filter_requirements.get("structured"):
        return compliance
    
    structured = filter_requirements.get("structured", {})
    
    # Example compliance checks - adapt based on actual requirement structure
    for req_type, requirements in structured.items():
        if not requirements:
            continue
            
        compliance[req_type] = {
            "meets": False,
            "details": "Basic compliance check - implement detailed logic as needed"
        }
        
        # Add specific compliance logic here based on requirement type
        # For now, use hard_requirements_met from scores
        if candidate.get("hard_requirements_met", False):
            compliance[req_type]["meets"] = True
            compliance[req_type]["details"] = "Meets basic requirements"
    
    return compliance


def llm_re_rank_batch(candidates_summaries: List[dict], filter_requirements: dict, client: OpenAI, specified_fields: set = None) -> List[dict]:
    """
    LLM re-ranks a batch of candidates based on filter requirements and all scores.
    Batch size: 30 candidates.
    
    Exact same logic as old archive FinalRanking.py
    """
    if not client:
        return []
    
    if not specified_fields:
        specified_fields = set()
    
    # Function calling schema with compliance validation - exact same as old archive
    RE_RANK_FUNCTION = {
        "name": "re_rank_candidates",
        "description": "Re-rank candidates based on filter requirements and all ranking scores. Validate compliance results and return validated requirements.",
        "parameters": {
            "type": "object",
            "properties": {
                "ranked_candidates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "candidate_id": {"type": "string"},
                            "re_rank_score": {"type": "number", "description": "Re-ranked score (0-1)"},
                            "meets_requirements": {"type": "boolean"},
                            "requirements_met": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": f"Validated list of requirement types from this set that candidate meets: {sorted(specified_fields) if specified_fields else 'NONE - no requirements specified'}. Validate programmatic results and correct if needed."
                            },
                            "requirements_missing": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": f"Validated list of requirement types from this set that candidate is missing: {sorted(specified_fields) if specified_fields else 'NONE - no requirements specified'}. Validate programmatic results and correct if needed."
                            }
                        },
                        "required": ["candidate_id", "re_rank_score", "meets_requirements", "requirements_met", "requirements_missing"]
                    }
                }
            },
            "required": ["ranked_candidates"]
        }
    }
    
    # Build prompt with compliance validation - exact same as old archive
    specified_fields_str = ", ".join(sorted(specified_fields)) if specified_fields else "NONE (no requirements specified)"
    
    system_msg = f"""You are a candidate re-ranker and compliance validator. Your tasks:
1. VALIDATE compliance results: Review programmatic compliance checks and validate/correct them based on candidate resume data
2. RE-RANK candidates: Rank candidates based on validated compliance + all ranking scores

IMPORTANT CONSTRAINT:
- Only return requirement types from this list: {specified_fields_str}
- Do NOT return other requirement types like location, education, etc. unless explicitly listed above
- If no requirements specified, return empty arrays for requirements_met and requirements_missing

Validation Rules:
- Review each candidate's compliance results carefully
- If programmatic check missed something (e.g., nuanced experience, skill synonyms), correct it
- If programmatic check was too strict, relax it appropriately
- Consider context and nuances in resume data

Re-ranking Rules:
- Candidates meeting more requirements should rank higher
- But also consider their JD alignment scores (all scores provided)
- Balance requirements compliance with overall quality
- Use candidate_id (not name) for identification

Return:
- re_rank_score (0-1) for each candidate
- Validated requirements_met list (ONLY from allowed list)
- Validated requirements_missing list (ONLY from allowed list)"""
    
    user_msg = f"""ALLOWED REQUIREMENT TYPES (only return these): {specified_fields_str}

Filter Requirements:
{json.dumps(filter_requirements, indent=2)}

Candidates to Re-rank (with all scores and programmatic compliance - abbreviated format):
{json.dumps(candidates_summaries, indent=2)}

Each candidate has a "compliance" field with programmatic compliance results.
VALIDATE these results - review and correct if programmatic checks missed nuances.
Then RE-RANK candidates based on validated compliance + all scores.

CRITICAL: In requirements_met and requirements_missing, ONLY include types from: {specified_fields_str}
Do NOT add other requirement types that weren't specified by HR.

Consider all scores (sc.p=project, sc.k=keyword, sc.s=semantic, sc.f=final) when making decisions.
Return validated requirements_met and requirements_missing for each candidate."""
    
    try:
        response = client.chat.completions.create(
            model=RE_RANK_MODEL,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg}
            ],
            functions=[RE_RANK_FUNCTION],
            function_call={"name": "re_rank_candidates"},
            temperature=0.3
        )
        
        # Parse response - exact same logic as old archive
        func_call = response.choices[0].message.function_call
        if func_call:
            try:
                args = json.loads(func_call.arguments)
                ranked_candidates = args.get("ranked_candidates", [])
                
                # FILTER: Ensure only specified requirement fields are in the response
                if specified_fields:
                    for candidate in ranked_candidates:
                        # Filter requirements_met to only include specified fields
                        candidate["requirements_met"] = [
                            req for req in candidate.get("requirements_met", [])
                            if req in specified_fields
                        ]
                        # Filter requirements_missing to only include specified fields
                        candidate["requirements_missing"] = [
                            req for req in candidate.get("requirements_missing", [])
                            if req in specified_fields
                        ]
                
                return ranked_candidates
            except json.JSONDecodeError as json_err:
                # Handle malformed JSON (unterminated strings, etc.) - exact same as old archive
                print(f"⚠️ JSON parsing error in LLM re-ranking: {json_err}")
                print(f"   Attempting to fix JSON...")
                try:
                    # Remove problematic characters or try to fix unterminated strings
                    fixed_args = func_call.arguments
                    # Basic fix: try to close unterminated strings
                    if fixed_args.count('"') % 2 != 0:
                        # Odd number of quotes - try to fix
                        fixed_args = fixed_args.rsplit('"', 1)[0] + '"'
                    args = json.loads(fixed_args)
                    return args.get("ranked_candidates", [])
                except Exception:
                    print(f"   Could not fix JSON, skipping LLM re-ranking for this batch")
                    return []
    except Exception as e:
        print(f"⚠️ Error in LLM re-ranking: {e}")
        return []
    
    return []


def llm_re_rank_candidates(candidates: List[dict], filter_requirements: dict, specified_fields: set = None) -> List[dict]:
    """
    Re-rank candidates using LLM in batches of 30.
    Returns list of re-ranking results with compliance breakdown.
    
    Exact same batching logic as old archive FinalRanking.py
    """
    if not filter_requirements or not filter_requirements.get("structured"):
        print("⚠️ No filter requirements provided. Skipping LLM re-ranking.")
        return []
    
    # Initialize OpenAI client - same logic as old archive
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("⚠️ OpenAI API key not found. Skipping LLM re-ranking.")
            return []
        
        client = OpenAI(api_key=api_key)
    except Exception as e:
        print(f"⚠️ Failed to initialize OpenAI client: {e}")
        return []
    
    # Prepare candidate summaries with compliance
    candidate_summaries = []
    compliance_reports = {}  # Store compliance reports by candidate_id
    
    for candidate in candidates:
        candidate_id = candidate.get("candidate_id")
        resume_json = get_resume_data_via_api(candidate_id) if candidate_id else {}
        
        # Check compliance
        compliance = check_all_requirements(candidate, resume_json, filter_requirements)
        compliance_reports[candidate_id] = compliance
        
        # Create summary with compliance
        summary = create_candidate_summary(candidate, resume_json)
        summary["compliance"] = {
            req_type: {
                "meets": comp.get("meets", False),
                "details": comp.get("details", "")
            }
            for req_type, comp in compliance.items()
        }
        candidate_summaries.append(summary)
    
    # Process in batches with detailed logging - exact same as old archive
    total_candidates = len(candidate_summaries)
    total_batches = (total_candidates + RE_RANK_BATCH_SIZE - 1) // RE_RANK_BATCH_SIZE
    
    print(f"\n🔄 LLM Re-ranking: {total_candidates} candidates in {total_batches} batch(es)")
    print(f"   - Batch size: {RE_RANK_BATCH_SIZE}")
    print(f"   - Model: {RE_RANK_MODEL}")
    
    all_results = []
    batch_start_time = time.time()
    
    for i in range(0, len(candidate_summaries), RE_RANK_BATCH_SIZE):
        batch_num = i // RE_RANK_BATCH_SIZE + 1
        batch = candidate_summaries[i:i + RE_RANK_BATCH_SIZE]
        batch_range = f"{i+1}-{min(i+RE_RANK_BATCH_SIZE, total_candidates)}"
        
        llm_call_id = f"LLM_RE_RANK_{int(time.time() * 1000)}"
        print(f"\n[{llm_call_id}] 📦 Batch {batch_num}/{total_batches}: Processing candidates {batch_range}")
        print(f"[{llm_call_id}] 📤 Request: {len(batch)} candidates")
        
        batch_call_start = time.time()
        
        # Pass specified_fields to the batch function
        results = llm_re_rank_batch(batch, filter_requirements, client, specified_fields)
        
        batch_call_duration = time.time() - batch_call_start
        
        # Add compliance reports to results
        for result in results:
            candidate_id = result.get("candidate_id")
            if candidate_id in compliance_reports:
                result["compliance_report"] = compliance_reports[candidate_id]
        
        all_results.extend(results)
        
        print(f"[{llm_call_id}] ✅ Batch {batch_num}/{total_batches}: Completed in {batch_call_duration:.2f}s")
        print(f"[{llm_call_id}] 📥 Response: {len(results)} candidates re-ranked")
    
    total_duration = time.time() - batch_start_time
    print(f"\n✅ LLM Re-ranking Complete:")
    print(f"   - Total batches processed: {total_batches}")
    print(f"   - Total candidates re-ranked: {len(all_results)}")
    print(f"   - Total time: {total_duration:.2f}s")
    print(f"   - Average time per batch: {total_duration/total_batches:.2f}s")
    
    return all_results


def process_ranking_batch(
    job_id: str,
    score_result_ids: List[str],
    batch_index: int = 1,
    total_batches: int = 1,
    ranking_criteria: dict = None
) -> dict:
    """
    Process a single batch of ranking (up to 30 candidates).
    This is called by the BullMQ consumer for each batch job.
    
    Args:
        job_id: MongoDB job ID
        score_result_ids: List of ScoreResult IDs for this batch
        batch_index: Which batch this is (1-based)
        total_batches: Total number of batches
        ranking_criteria: Ranking criteria from job trigger
        
    Returns: {
        'success': bool,
        'job_id': str,
        'batch_index': int,
        'total_batches': int,
        'ranked_candidates': List[dict],
        'batch_summary': dict,
        'error': str or None
    }
    """
    
    print(f"🏆 Processing ranking batch {batch_index}/{total_batches} for job {job_id}")
    print(f"   - Score result IDs: {len(score_result_ids)}")
    
    try:
        # Get candidates for this batch using the score IDs
        # For now, get all candidates and filter - in production, optimize this
        all_candidates = get_candidate_scores_via_api(job_id)
        
        if not all_candidates:
            return {
                'success': False,
                'job_id': job_id,
                'batch_index': batch_index,
                'total_batches': total_batches,
                'error': 'No candidates found for ranking'
            }
        
        # Filter candidates to only those in this batch (by score_result_ids)
        # For now, just take the appropriate slice based on batch_index
        # In production, filter by actual score_result_ids
        batch_size = len(all_candidates) // total_batches
        start_idx = (batch_index - 1) * batch_size
        end_idx = start_idx + batch_size if batch_index < total_batches else len(all_candidates)
        
        batch_candidates = all_candidates[start_idx:end_idx]
        
        print(f"   - Processing {len(batch_candidates)} candidates in this batch")
        
        # Apply LLM re-ranking if criteria provided
        if ranking_criteria and ranking_criteria.get('enable_llm_rerank', False):
            filter_requirements = ranking_criteria.get('filter_requirements', {})
            specified_fields = set(ranking_criteria.get('specified_fields', []))
            
            print(f"   - Applying LLM re-ranking with {len(specified_fields)} specified fields")
            
            ranked_candidates = llm_re_rank_candidates(
                batch_candidates, 
                filter_requirements, 
                specified_fields
            )
        else:
            # Basic ranking by Final_Score
            print(f"   - Applying basic score-based ranking")
            ranked_candidates = sorted(
                batch_candidates, 
                key=lambda x: x.get('Final_Score', 0), 
                reverse=True
            )
            
            # Convert to expected format
            ranked_candidates = [
                {
                    'candidate_id': candidate.get('candidate_id'),
                    're_rank_score': candidate.get('Final_Score', 0),
                    'meets_requirements': candidate.get('hard_requirements_met', False),
                    'requirements_met': [],
                    'requirements_missing': []
                }
                for candidate in ranked_candidates
            ]
        
        batch_summary = {
            'total_candidates': len(batch_candidates),
            'ranked_candidates': len(ranked_candidates),
            'avg_score': sum(r.get('re_rank_score', 0) for r in ranked_candidates) / len(ranked_candidates) if ranked_candidates else 0,
            'candidates_meeting_requirements': sum(1 for r in ranked_candidates if r.get('meets_requirements', False))
        }
        
        print(f"✅ Batch {batch_index}/{total_batches} completed:")
        print(f"   - Ranked {len(ranked_candidates)} candidates")
        print(f"   - Average score: {batch_summary['avg_score']:.3f}")
        print(f"   - Meeting requirements: {batch_summary['candidates_meeting_requirements']}")
        
        return {
            'success': True,
            'job_id': job_id,
            'batch_index': batch_index,
            'total_batches': total_batches,
            'ranked_candidates': ranked_candidates,
            'batch_summary': batch_summary
        }
        
    except Exception as e:
        print(f"❌ Ranking batch {batch_index}/{total_batches} failed for job {job_id}: {str(e)}")
        return {
            'success': False,
            'job_id': job_id,
            'batch_index': batch_index,
            'total_batches': total_batches,
            'error': str(e)
        }


def process_final_ranking(
    job_id: str,
    resume_group_id: str = None,
    score_result_ids: List[str] = None,
    batch_index: int = 1,
    total_batches: int = 1,
    ranking_criteria: dict = None
) -> dict:
    """
    Main entry point for BullMQ consumer.
    Processes a single batch of final ranking.
    
    This function is called by the BullMQ consumer with job data.
    """
    
    # If score_result_ids provided, process as batch
    if score_result_ids:
        return process_ranking_batch(
            job_id=job_id,
            score_result_ids=score_result_ids,
            batch_index=batch_index,
            total_batches=total_batches,
            ranking_criteria=ranking_criteria
        )
    
    # Fallback: process all candidates for the job
    return process_ranking_batch(
        job_id=job_id,
        score_result_ids=[],
        batch_index=1,
        total_batches=1,
        ranking_criteria=ranking_criteria
    )


if __name__ == "__main__":
    # Test the ranking system
    import sys
    if len(sys.argv) > 1:
        test_job_id = sys.argv[1]
        print(f"Testing ranking for job: {test_job_id}")
        
        result = process_final_ranking(
            job_id=test_job_id,
            ranking_criteria={
                'enable_llm_rerank': False,  # Set to True to test LLM re-ranking
                'filter_requirements': {},
                'specified_fields': []
            }
        )
        
        print(f"Result: {json.dumps(result, indent=2)}")
    else:
        print("Usage: python main_ranking_processor.py <job_id>")
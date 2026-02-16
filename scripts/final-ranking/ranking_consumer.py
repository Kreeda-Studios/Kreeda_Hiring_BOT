#!/usr/bin/env python3
"""
BullMQ Consumer for Ranking Processing

This script processes ranking jobs from the BullMQ 'ranking' queue.
Each job contains a batch of up to 30 resume IDs with score normalization parameters.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add parent directories to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent))

from main_ranking_processor import process_final_ranking


def process_ranking_job(job_data: dict) -> dict:
    """
    Process a ranking job from BullMQ.
    
    Expected job_data format:
    {
        "jobId": "697f8dd836bff27b67b85f2d",
        "resumeIds": ["resume1", "resume2", ...],
        "minKeywordScore": 0.15,
        "maxKeywordScore": 0.92,
        "minSemanticScore": 0.22,
        "maxSemanticScore": 0.88,
        "batchIndex": 1,
        "totalBatches": 3
    }
    
    Returns:
    {
        "success": true/false,
        "job_id": "...",
        "batch_index": 1,
        "total_batches": 3,
        "ranked_candidates": [...],
        "batch_summary": {...},
        "error": "..." (if failed)
    }
    """
    
    print(f"\n{'='*80}")
    print(f"📥 Received Ranking Job from BullMQ")
    print(f"{'='*80}")
    print(f"Job Data: {json.dumps(job_data, indent=2)}")
    print(f"{'='*80}\n")
    
    # Extract job parameters
    job_id = job_data.get('jobId')
    resume_ids = job_data.get('resumeIds', [])
    min_keyword_score = job_data.get('minKeywordScore', 0.0)
    max_keyword_score = job_data.get('maxKeywordScore', 1.0)
    min_semantic_score = job_data.get('minSemanticScore', 0.0)
    max_semantic_score = job_data.get('maxSemanticScore', 1.0)
    batch_index = job_data.get('batchIndex', 1)
    total_batches = job_data.get('totalBatches', 1)
    ranking_criteria = job_data.get('rankingCriteria', {})
    
    # Validate required parameters
    if not job_id:
        return {
            'success': False,
            'error': 'Missing required parameter: jobId'
        }
    
    if not resume_ids:
        return {
            'success': False,
            'error': 'Missing required parameter: resumeIds'
        }
    
    # Process the ranking batch
    try:
        result = process_final_ranking(
            job_id=job_id,
            resume_ids=resume_ids,
            min_keyword_score=min_keyword_score,
            max_keyword_score=max_keyword_score,
            min_semantic_score=min_semantic_score,
            max_semantic_score=max_semantic_score,
            batch_index=batch_index,
            total_batches=total_batches,
            ranking_criteria=ranking_criteria
        )
        
        return result
        
    except Exception as e:
        print(f"❌ Error processing ranking job: {e}")
        import traceback
        traceback.print_exc()
        
        return {
            'success': False,
            'job_id': job_id,
            'batch_index': batch_index,
            'total_batches': total_batches,
            'error': str(e)
        }


if __name__ == "__main__":
    # Test mode - process a sample job from command line
    if len(sys.argv) > 1:
        # Read job data from file or stdin
        job_data_json = sys.argv[1]
        
        try:
            job_data = json.loads(job_data_json)
        except json.JSONDecodeError:
            # Assume it's a file path
            with open(job_data_json, 'r') as f:
                job_data = json.load(f)
        
        result = process_ranking_job(job_data)
        
        print(f"\n{'='*80}")
        print(f"RESULT:")
        print(f"{'='*80}")
        print(json.dumps(result, indent=2))
        print(f"{'='*80}\n")
        
        sys.exit(0 if result.get('success') else 1)
    else:
        print("Usage:")
        print("  python ranking_consumer.py '<json_data>'")
        print("  python ranking_consumer.py job_data.json")
        print("\nExample JSON:")
        print(json.dumps({
            "jobId": "697f8dd836bff27b67b85f2d",
            "resumeIds": ["resume1", "resume2", "resume3"],
            "minKeywordScore": 0.15,
            "maxKeywordScore": 0.92,
            "minSemanticScore": 0.22,
            "maxSemanticScore": 0.88,
            "batchIndex": 1,
            "totalBatches": 1
        }, indent=2))
        sys.exit(1)

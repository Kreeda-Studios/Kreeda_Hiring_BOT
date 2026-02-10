#!/usr/bin/env python3

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add paths BEFORE imports
script_dir = Path(__file__).parent
parent_dir = script_dir.parent

if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from common.api_client import api, APIError
from common.job_logger import JobLogger
from common.bullmq_progress import ProgressTracker

from a_pdf_extractor import process_resume_file
from b_ai_parser import parse_resume_with_ai
from c_embedding_generator import generate_resume_embeddings
from d_hard_requirements_checker import check_hard_requirements
from e_keyword_scorer import calculate_keyword_scores
from f_semantic_scorer import calculate_semantic_scores
from g_project_scorer import calculate_project_scores
from h_composite_scorer import calculate_composite_score

class ResumeProcessingError(Exception):
    pass


def update_resume_status(resume_id: str, status: str, progress: int = None, error: str = None, job_id: str = None):
    """Update resume processing status in database"""
    try:
        payload = {
            'overall_processing_status': status
        }
        if progress is not None:
            payload['processing_progress'] = progress
        if error is not None:
            payload['processing_error'] = error
        if job_id is not None:
            payload['bullmq_job_id'] = job_id
        
        api.patch(f"/resumes/{resume_id}", data=payload)
    except Exception as e:
        print(f"⚠️ Failed to update resume status: {e}")


def update_job_resume_status(job_id: str, status: str, progress: int = None, error: str = None):
    """Update job's resume processing status"""
    try:
        payload = {
            'resume_processing_status': status
        }
        if progress is not None:
            payload['resume_processing_progress'] = progress
        if error is not None:
            payload['resume_processing_error'] = error
        
        api.patch(f"/jobs/{job_id}", data=payload)
    except Exception as e:
        print(f"⚠️ Failed to update job resume status: {e}")

def update_resume_embeddings(resume_id: str, section_embeddings: Dict[str, Any]) -> Dict:
    """Format resume embeddings for database update"""
    try:
        import numpy as np
        
        resume_embedding = {'model': 'text-embedding-3-small', 'dimension': 1536}
        
        for section in ['profile', 'skills', 'projects', 'responsibilities', 'education', 'overall']:
            if section in section_embeddings:
                emb_array = section_embeddings[section]
                if isinstance(emb_array, np.ndarray) and emb_array.size > 0:
                    if emb_array.ndim == 2:
                        emb_list = emb_array.tolist()
                    elif emb_array.ndim == 1:
                        emb_list = [emb_array.tolist()]
                    else:
                        emb_list = []
                    resume_embedding[section] = emb_list
                else:
                    resume_embedding[section] = []
        
        return {
            'resume_embedding': resume_embedding,
            'embedding_status': 'success'
        }
        
    except Exception as e:
        raise ResumeProcessingError(f"Error formatting embeddings: {e}")

async def process_resume_pipeline(job) -> Dict[str, Any]:
    """Process resume through complete pipeline with BullMQ progress tracking"""
    
    job_data = job.data
    resume_id = job_data.get('resume_id')
    job_id = job_data.get('job_id')
    index = job_data.get('index', 1)
    total = job_data.get('total', 1)
    
    logger = JobLogger.for_resume(resume_id, index, total)
    tracker = ProgressTracker(job)
    
    # Update resume status to processing
    update_resume_status(resume_id, 'processing', 0, job_id=job.id)
    
    try:
        # Fetch resume data
        await tracker.update(5, "fetching_resume", "Fetching resume data")
        logger.progress("Fetching resume data")
        
        resume_data = api.get(f"/updates/resume/{resume_id}")
        
        # Construct file path from job_id and filename
        job_id = resume_data.get('job_id')
        filename = resume_data.get('filename')
        
        if not filename:
            error_msg = f"Resume has no filename: {resume_id}"
            logger.fail(error_msg)
            await tracker.failed(error_msg, "InvalidDataError", "fetching_resume")
            return {'success': False, 'error': error_msg}
        
        # Path structure: /app/uploads/{job_id}/resumes/{filename}
        if job_id:
            resume_file_path = f"/app/uploads/{job_id}/resumes/{filename}"
        else:
            # Fallback to direct path if no job_id
            resume_file_path = f"/app/uploads/resumes/{filename}"
        
        if not os.path.exists(resume_file_path):
            error_msg = f"Resume file not found: {resume_file_path}"
            logger.fail(error_msg)
            await tracker.failed(error_msg, "FileNotFoundError", "fetching_resume")
            return {'success': False, 'error': error_msg}
        
        logger.progress(f"File located: {os.path.basename(resume_file_path)}")
        await tracker.update(8, "fetching_resume", "Resume file located")
        
        # Fetch job data
        await tracker.update(10, "fetching_job", "Fetching job data")
        jd_data = api.get(f"/updates/job/{job_id}")
        
        logger.progress(f"Processing: {os.path.basename(resume_file_path)}")
        await tracker.update(12, "starting", f"Starting resume processing")
        
        # Extract text from PDF
        await tracker.update(15, "extracting_text", "Extracting text from PDF")
        logger.progress("Extracting text from PDF")
        
        text_result = process_resume_file(resume_file_path)
        if not text_result.get('success'):
            error_msg = f"Text extraction failed: {text_result.get('error')}"
            logger.fail(error_msg)
            await tracker.failed(error_msg, "ExtractionError", "extracting_text")
            return {'success': False, 'error': error_msg}
        
        char_count = text_result.get('metadata', {}).get('characters', len(text_result.get('text', '')))
        logger.progress(f"Extracted {char_count} characters")
        await tracker.update(20, "extracting_text", f"Text extracted: {char_count} chars")
        
        # Parse with AI
        await tracker.update(25, "parsing", "Parsing resume with AI")
        logger.progress("Parsing resume with AI (1-2 minutes)")
        
        parse_result = await parse_resume_with_ai(text_result['text'], jd_data)
        if not parse_result.get('success'):
            error_msg = f"AI parsing failed: {parse_result.get('error')}"
            logger.fail(error_msg)
            await tracker.failed(error_msg, "AIParsingError", "parsing")
            return {'success': False, 'error': error_msg}
        
        parsed_resume = parse_result['parsed_data']
        # Save parsed resume using new API
        api.post("/updates/resume/parsed", data={
            'resume_id': resume_id,
            'parsed_content': parsed_resume
        })
        logger.progress(f"Parsed: {parsed_resume.get('name', 'Unknown')}")
        await tracker.update(40, "parsing", f"Resume parsed successfully")
        
        # Generate embeddings
        await tracker.update(45, "generating_embeddings", "Generating embeddings")
        logger.progress("Generating embeddings")
        
        embed_result = await generate_resume_embeddings(parsed_resume)
        if not embed_result.get('success'):
            error_msg = f"Embedding failed: {embed_result.get('error')}"
            logger.progress(f"Warning: {error_msg}")
            await tracker.update(55, "generating_embeddings", f"Warning: {error_msg}")
        else:
            section_embeddings = embed_result.get('section_embeddings', {})
            embedding_data = update_resume_embeddings(resume_id, section_embeddings)
            # Save embeddings using new API
            api.post("/updates/resume/embeddings", data={
                'resume_id': resume_id,
                'resume_embedding': embedding_data['resume_embedding']
            })
            logger.progress(f"Embeddings generated: {len(section_embeddings)} sections")
            await tracker.update(55, "generating_embeddings", "Embeddings generated")
        
        # Calculate scores
        await tracker.update(60, "scoring", "Calculating scores")
        logger.progress("Calculating scores")
        
        # Hard requirements check
        hard_req_result = check_hard_requirements(parsed_resume, jd_data)
        if not hard_req_result.get('success'):
            hard_req_result = {'meets_all_requirements': True, 'compliance_score': 1.0}
        logger.progress(f"Hard req: {'✅ Met' if hard_req_result.get('meets_all_requirements') else '❌ Not met'}")
        await tracker.update(65, "scoring", "Hard requirements checked")
        
        # Project scoring
        project_result = calculate_project_scores(parsed_resume, jd_data)
        if not project_result.get('success'):
            project_result = {'overall_score': 0.0}
        logger.progress(f"Project score: {project_result.get('overall_score', 0):.2f}")
        await tracker.update(70, "scoring", "Project scoring complete")
        
        # Keyword scoring
        keyword_result = calculate_keyword_scores(parsed_resume, jd_data)
        if not keyword_result.get('success'):
            keyword_result = {'overall_score': 0.0}
        logger.progress(f"Keyword score: {keyword_result.get('overall_score', 0):.2f}")
        await tracker.update(75, "scoring", "Keyword scoring complete")
        
        # Semantic scoring
        jd_embeddings = jd_data.get('jd_embedding', {})
        logger.progress(f"JD embeddings keys: {list(jd_embeddings.keys()) if jd_embeddings else 'None'}")
        logger.progress(f"JD skills embeddings count: {len(jd_embeddings.get('skills_embedding', [])) if jd_embeddings else 0}")
        
        semantic_result = calculate_semantic_scores(
            embed_result.get('section_embeddings', {}), 
            jd_embeddings
        )
        if not semantic_result.get('success'):
            semantic_result = {'overall_semantic_score': 0.0}
        logger.progress(f"Semantic score: {semantic_result.get('overall_semantic_score', 0):.2f}")
        await tracker.update(80, "scoring", "Semantic scoring complete")
        
        # Calculate final composite score
        await tracker.update(85, " composite_scoring", "Calculating final composite score")
        logger.progress("Calculating final composite score")
        
        composite_result = calculate_composite_score(
            project_result, keyword_result, semantic_result
        )
        if not composite_result.get('success'):
            composite_result = {'final_score': 0.0}
        
        final_score = composite_result.get('final_score', 0.0)
        logger.progress(f"Final score: {final_score:.2f}")
        await tracker.update(90, "composite_scoring", f"Final score: {final_score:.2f}")
        
        # Save scores to resume using new API
        await tracker.update(95, "saving_scores", "Saving scores to database")
        logger.progress("Saving scores to database")
        
        api.post("/updates/resume/scores", data={
            'resume_id': resume_id,
            'scores': {
                'hard_requirements': {
                    'meets_all_requirements': hard_req_result.get('meets_all_requirements', True),
                    'compliance_score': hard_req_result.get('compliance_score', 1.0),
                    'requirements_met': hard_req_result.get('requirements_met', []),
                    'requirements_missing': hard_req_result.get('requirements_missing', []),
                    'filter_reason': hard_req_result.get('filter_reason')
                },
                'project_score': project_result.get('overall_score', 0.0),
                'keyword_score': keyword_result.get('overall_score', 0.0),
                'semantic_score': semantic_result.get('overall_semantic_score', 0.0),
                'composite_score': composite_result.get('final_score', 0.0)
            }
        })
        
        api.post("/updates/resume/status", data={'resume_id': resume_id, 'status': 'completed'})
        
        # Update resume status to success
        update_resume_status(resume_id, 'success', 100)
        
        logger.complete(f"Completed: Score {final_score:.2f}")
        await tracker.complete(summary={
            'resumeId': resume_id,
            'jobId': job_id,
            'finalScore': final_score,
            'rankingTier': composite_result.get('ranking_tier', 'Poor')
        })
        
        return {
            'success': True,
            'final_score': composite_result.get('final_score', 0.0),
            'hard_requirements_passed': hard_req_result.get('meets_all_requirements', True),
            'resume_data': parsed_resume
        }
        
    except APIError as e:
        error_msg = f"API error: {e.message}"
        logger.fail(error_msg)
        api.post("/updates/resume/status", data={'resume_id': resume_id, 'status': 'failed'})
        update_resume_status(resume_id, 'failed', error=error_msg)
        await tracker.failed(error_msg, "APIError", "processing")
        return {'success': False, 'error': error_msg, 'final_score': 0.0}
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.fail(error_msg)
        print(f"📋 Full error traceback:\n{error_traceback}")
        api.post("/updates/resume/status", data={'resume_id': resume_id, 'status': 'failed'})
        update_resume_status(resume_id, 'failed', error=error_msg)
        await tracker.failed(str(e), type(e).__name__, "processing")
        return {'success': False, 'error': str(e), 'final_score': 0.0}

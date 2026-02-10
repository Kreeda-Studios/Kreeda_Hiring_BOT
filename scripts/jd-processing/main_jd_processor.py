#!/usr/bin/env python3
"""
Main JD Processing Orchestrator

Complete pipeline for processing job descriptions:
1. Fetch job from API
2. Extract text from PDF
3. AI parsing (JDGpt.py logic) - returns complete structured data
4. Save all data to database
5. Generate and save embeddings
"""

import sys
import os
from pathlib import Path

# Add paths BEFORE imports
script_dir = Path(__file__).parent
parent_dir = script_dir.parent

# Add to Python path
if str(script_dir) not in sys.path:
    sys.path.insert(0, str(script_dir))
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from common.api_client import api, APIError
from common.job_logger import JobLogger
from common.bullmq_progress import ProgressTracker

from a_pdf_text_extractor import extract_combined_text
from b_ai_jd_parser import process_jd_with_ai, format_jd_analysis_payload
from c_ai_embedding_generator import generate_and_format_embeddings
from d_compliance_parser import validate_and_format_compliances


def update_job_status(job_id: str, status: str, progress: int = None, error: str = None):
    """Update job processing status in database"""
    try:
        payload = {
            'jd_processing_status': status
        }
        if progress is not None:
            payload['jd_processing_progress'] = progress
        if error is not None:
            payload['jd_processing_error'] = error
        
        api.patch(f"/jobs/{job_id}", data=payload)
    except Exception as e:
        print(f"⚠️ Failed to update job status: {e}")


async def process_jd_complete(job) -> dict:
    """
    Complete JD processing pipeline
    
    Args:
        job: BullMQ job object
        
    Returns: {
        'success': bool,
        'job_id': str,
        'processing_stages': dict,
        'error': str or None
    }
    """
    job_id = job.data.get("jobId")
    logger = JobLogger.for_jd(job_id)
    tracker = ProgressTracker(job)
    
    # Update status to processing
    update_job_status(job_id, 'processing', 0)
    
    processing_stages = {
        'job_fetch': {'completed': False, 'error': None},
        'text_extraction': {'completed': False, 'error': None},
        'compliance_parsing': {'completed': False, 'error': None},
        'ai_parsing': {'completed': False, 'error': None},
        'save_analysis': {'completed': False, 'error': None},
        'embedding_generation': {'completed': False, 'error': None},
        'save_embeddings': {'completed': False, 'error': None},
    }
    
    try:
        # Step 1: Fetch job details from API
        await tracker.update(10, "fetching_job", "Fetching job details from database")
        logger.progress("Fetching job details from database")
        
        job_data = api.get(f"/updates/job/{job_id}")
        processing_stages['job_fetch']['completed'] = True
        
        logger.progress(f"Job loaded: {job_data.get('title', 'N/A')}")
        await tracker.update(20, "fetching_job", f"Job details loaded: {job_data.get('title', 'N/A')}")
        
        # Step 2: Extract and combine text
        await tracker.update(25, "extracting_text", "Extracting text from PDF and JD")
        logger.progress("Extracting text from PDF and JD")
        
        text_result = extract_combined_text(job_data)
        
        if not text_result.get('success'):
            error_msg = text_result.get('error', 'Text extraction failed')
            logger.fail(error_msg)
            processing_stages['text_extraction']['error'] = error_msg
            await tracker.failed(error_msg, "ExtractionError", "extracting_text")
            return {'success': False, 'job_id': job_id, 'processing_stages': processing_stages, 'error': error_msg}
        
        combined_text = text_result.get('text')
        sources = text_result.get('sources', [])
        processing_stages['text_extraction']['completed'] = True
        logger.progress(f"Extracted {text_result.get('char_count')} chars from: {', '.join(sources)}")
        await tracker.update(30, "extracting_text", f"Text extracted: {text_result.get('char_count')} characters")
        
        # Step 3: Parse mandatory and soft compliances
        await tracker.update(35, "parsing_compliance", "Parsing compliance requirements")
        logger.progress("Parsing compliance requirements")
        
        compliance_result = validate_and_format_compliances(job_data)
        updated_filter_requirements = compliance_result.get('filter_requirements')
        
        if compliance_result.get('success'):
            stats = compliance_result.get('stats', {})
            total = stats.get('total_count', 0)
            if total > 0:
                logger.progress(f"Parsed: {stats.get('mandatory_count')} mandatory, {stats.get('soft_count')} soft")
                await tracker.update(40, "parsing_compliance", f"Compliance parsed: {total} fields")
            else:
                logger.progress("No compliances to parse")
                await tracker.update(40, "parsing_compliance", "No compliances specified")
            processing_stages['compliance_parsing']['completed'] = True
        else:
            error_msg = compliance_result.get('error')
            logger.progress(f"Warning: {error_msg}")
            processing_stages['compliance_parsing']['error'] = error_msg
            await tracker.update(40, "parsing_compliance", f"Warning: {error_msg}")
        
        # Step 4: AI JD Parsing
        await tracker.update(45, "ai_parsing", "Processing JD with AI (1-2 minutes)")
        logger.progress("Parsing JD with GPT-4 (this may take 1-2 minutes)")
        
        ai_result = await process_jd_with_ai(combined_text)
        
        if not ai_result.get('success'):
            error_msg = ai_result.get('error', 'AI JD parsing failed')
            logger.fail(f"AI parsing failed: {error_msg}")
            processing_stages['ai_parsing']['error'] = error_msg
            await tracker.failed(error_msg, "AIParsingError", "ai_parsing")
            return {'success': False, 'job_id': job_id, 'processing_stages': processing_stages, 'error': error_msg}
        
        processing_stages['ai_parsing']['completed'] = True
        parsed_jd = ai_result.get('parsed_data', {})
        logger.progress(f"Parsed: {parsed_jd.get('role_title', 'N/A')} | {len(parsed_jd.get('required_skills', []))} skills")
        await tracker.update(60, "ai_parsing", "AI parsing completed")
        
        # Step 5: Save parsed data to DB using new API
        await tracker.update(65, "saving_analysis", "Saving parsed analysis to database")
        logger.progress("Saving parsed analysis to database")
        
        jd_analysis_payload = format_jd_analysis_payload(parsed_jd, updated_filter_requirements)
        
        api.post("/updates/jd/parsed", data={
            'job_id': job_id,
            'jd_analysis': jd_analysis_payload['jd_analysis']
        })
        processing_stages['save_analysis']['completed'] = True
        logger.progress("Parsed analysis saved to database")
        await tracker.update(70, "saving_analysis", "Parsed analysis saved")
        
        # Save compliance requirements if available
        if updated_filter_requirements:
            api.post("/updates/jd/compliance", data={
                'job_id': job_id,
                'filter_requirements': updated_filter_requirements
            })
            logger.progress("Compliance requirements saved")
        
        # Step 6: Generate embeddings
        await tracker.update(75, "generating_embeddings", "Generating embeddings")
        logger.progress("Generating embeddings")
        
        embeddings_result = await generate_and_format_embeddings(parsed_jd)
        
        if not embeddings_result.get('success'):
            error_msg = embeddings_result.get('error')
            logger.progress(f"Warning: {error_msg}")
            processing_stages['embedding_generation']['error'] = error_msg
            await tracker.update(85, "generating_embeddings", f"Warning: {error_msg}")
            sections_count = 0
        else:
            processing_stages['embedding_generation']['completed'] = True
            stats = embeddings_result.get('stats', {})
            sections_count = stats.get('sections_generated', 6)
            logger.progress(f"Generated {sections_count}/{stats.get('total_sections', 6)} embeddings")
            await tracker.update(85, "generating_embeddings", "Embeddings generated")
            
            # Step 7: Save embeddings using new API
            await tracker.update(90, "saving_embeddings", "Saving embeddings to database")
            logger.progress("Saving embeddings to database")
            
            api.post("/updates/jd/embeddings", data={
                'job_id': job_id,
                'jd_embedding': embeddings_result.get('embeddings_payload', {}).get('embeddings')
            })
            processing_stages['save_embeddings']['completed'] = True
            logger.progress("Embeddings saved to database")
            await tracker.update(95, "saving_embeddings", "Embeddings saved successfully")
        
        api.post("/updates/jd/status", data={'job_id': job_id, 'status': 'completed'})
        
        # Update status to success
        update_job_status(job_id, 'success', 100)
        
        logger.complete("JD processing completed successfully")
        await tracker.complete(summary={
            'jobId': job_id,
            'skillsExtracted': len(parsed_jd.get('required_skills', [])),
            'embeddingsGenerated': sections_count
        })
        
        return {
            'success': True,
            'job_id': job_id,
            'processing_stages': processing_stages
        }
        
    except APIError as e:
        logger.fail(f"API error: {e.message}")
        error_msg = f"API error: {e.message}"
        api.post("/updates/jd/status", data={'job_id': job_id, 'status': 'failed'})
        update_job_status(job_id, 'failed', error=error_msg)
        return {
            'success': False,
            'job_id': job_id, 
            'processing_stages': processing_stages,
            'error': error_msg
        }
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.fail(error_msg)
        print(f"📋 Full error traceback:\n{error_traceback}")
        api.post("/updates/jd/status", data={'job_id': job_id, 'status': 'failed'})
        update_job_status(job_id, 'failed', error=error_msg)
        return {
            'success': False,
            'job_id': job_id, 
            'processing_stages': processing_stages,
            'error': f"{type(e).__name__}: {str(e)}"
        }

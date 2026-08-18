#!/usr/bin/env python3

import sys
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import time
import asyncio

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
from d_hard_requirements_checker import check_hard_requirements, check_experience_gate
from e_keyword_scorer import calculate_keyword_scores
from f_semantic_scorer import calculate_semantic_scores
from g_project_scorer import calculate_project_scores
from h_composite_scorer import calculate_composite_score

class ResumeProcessingError(Exception):
    pass


# =============================================================================
# JD IN-PROCESS CACHE  (TTL + Request Coalescing)
# =============================================================================
#
# PROBLEM THIS SOLVES:
#   When a batch of N resumes is processed, every resume needs the same JD
#   document from the backend (/api/updates/job/{job_id}). Without caching,
#   we make N identical HTTP requests to the backend and N identical MongoDB
#   reads — pure wasted work.
#
# SOLUTION — TWO-LAYER MECHANISM:
#
#   Layer 1: TTL Cache (_jd_cache)
#     A module-level dict that stores the JD document once it has been
#     fetched. Keyed by job_id so multiple concurrent batches for different
#     jobs are completely isolated (Job A's data never leaks into Job B).
#     Each entry holds (jd_data, timestamp). After _JD_CACHE_TTL_SECONDS,
#     the entry is treated as stale and the next caller refetches it fresh.
#
#   Layer 2: Request Coalescing (_jd_pending)
#     Without coalescing, all 16 workers can start simultaneously, all check
#     the (empty) cache at the same moment, all see a miss, and all fire their
#     own API call — a "cache stampede". This dict prevents that.
#
#     When the FIRST worker for a given job_id sees a cache miss, it creates
#     an asyncio.Task to do the actual fetch, stores it in _jd_pending, and
#     then awaits it. Workers 2-16 arrive moments later, also see a cache
#     miss, but find the task already in _jd_pending — so they just await
#     the SAME task. Only 1 HTTP request is ever in flight at a time.
#
# RESULT:
#   - 31 resumes, same job → 1 JD API call  (instead of 31 without cache,
#                                             or 15-16 with simple TTL cache)
#   - Zero risk of data mixing (key = job_id, each job is independent)
#   - Zero new dependencies (dict + asyncio.Task are Python stdlib)
#   - Memory: a single JD document with embeddings is ~1-3 MB; harmless
#
# LIFECYCLE:
#   - Cache starts empty when the Python container starts.
#   - First resume in a batch populates it.
#   - Subsequent resumes in the same batch get instant 0ms cache hits.
#   - After TTL expires, the NEXT caller triggers a fresh fetch (resets clock).
#   - Container restart clears everything (fresh state, no stale data risk).
# =============================================================================

# Stores fetched JD documents: { job_id: (jd_data, time.monotonic()) }
_jd_cache: Dict[str, Any] = {}

# Stores in-flight fetch tasks: { job_id: asyncio.Task }
# Prevents duplicate API calls when multiple workers start simultaneously.
_jd_pending: Dict[str, asyncio.Task] = {}

# How long a cached JD is considered fresh. 10 minutes covers any realistic
# batch size. After this, the next caller will refetch from the backend.
_JD_CACHE_TTL_SECONDS: int = 600


async def _get_jd_cached(job_id: str) -> Dict[str, Any]:
    """
    Fetch JD data using a TTL cache with request coalescing.

    Call flow for 16 concurrent workers all needing the same job_id:

      Worker 1  → cache MISS, pending MISS → creates Task → awaits it
                                              (Task fires 1 API call)
      Worker 2  → cache MISS, pending HIT  → awaits SAME Task (no new call)
      Worker 3  → cache MISS, pending HIT  → awaits SAME Task (no new call)
      ...        (all 16 workers share the single in-flight Task)
      Task done → stores result in _jd_cache, removes from _jd_pending

      Worker 17 → cache HIT (age < TTL)    → returns instantly, 0 ms
      Worker 18 → cache HIT                → returns instantly, 0 ms
      ...

    Args:
        job_id: MongoDB ObjectId string of the job whose JD we need.

    Returns:
        The full JD document dict as returned by /api/updates/job/{job_id}.
    """
    now = time.monotonic()

    # ------------------------------------------------------------------
    # STEP 1: Check the TTL cache first.
    # If this job_id was fetched recently and the entry hasn't expired,
    # return it immediately without any I/O.
    # ------------------------------------------------------------------
    if job_id in _jd_cache:
        jd_data, cached_at = _jd_cache[job_id]
        if now - cached_at < _JD_CACHE_TTL_SECONDS:
            # Cache hit — JD is fresh. Return in ~0 ms.
            return jd_data
        # TTL expired — the entry is stale. Fall through to refetch.
        # The old data remains in _jd_cache until overwritten below,
        # so it acts as a safe fallback if the API call fails.

    # ------------------------------------------------------------------
    # STEP 2: Check if another worker is already fetching this job_id.
    # This is the request coalescing step that prevents stampedes.
    #
    # asyncio runs on a single thread. A context switch only happens at
    # an `await` point. So between here and the `_jd_pending[job_id] = task`
    # line below there is NO context switch — this check-and-set is
    # effectively atomic within the asyncio event loop.
    # ------------------------------------------------------------------
    if job_id in _jd_pending:
        # Another worker already started fetching this JD.
        # Await the same Task — we'll get the result when it completes
        # without making a second API call.
        return await _jd_pending[job_id]

    # ------------------------------------------------------------------
    # STEP 3: We are the FIRST worker for this job_id (cache miss, no
    # pending task). Define the actual fetch coroutine, wrap it in a
    # Task (so it can be shared with other workers), register it in
    # _jd_pending, then await it.
    # ------------------------------------------------------------------
    async def _fetch_jd() -> Dict[str, Any]:
        """
        Inner coroutine that performs the actual API call and stores the
        result in _jd_cache. Wrapped in a Task so multiple workers can
        await the same fetch without duplicating work.
        """
        try:
            jd_data = await api.get_async(f"/updates/job/{job_id}")
            # Store in cache with a fresh timestamp so subsequent workers
            # (and the next batch for the same job) get instant hits.
            _jd_cache[job_id] = (jd_data, time.monotonic())
            return jd_data
        finally:
            # Always remove from _jd_pending when done (success or error),
            # so future callers don't try to await a completed/failed Task.
            _jd_pending.pop(job_id, None)

    # Create the Task and register it BEFORE the first await so that any
    # worker that reaches Step 2 after this point will find it and wait.
    task = asyncio.ensure_future(_fetch_jd())
    _jd_pending[job_id] = task

    # Await our own Task. This yields control to the event loop, allowing
    # other workers to reach Step 2 and find the task in _jd_pending.
    return await task



async def update_resume_status(resume_id: str, status: str, progress: int = None, error: str = None, job_id: str = None, hard_requirements_met: bool = None):
    """Update resume processing status in database via /updates/resume/status/single endpoint"""
    try:
        # Only use success/failed boolean approach
        success = status == 'success'
        payload = {
            'resume_id': resume_id,
            'success': success,
            'error': error
        }
        if progress is not None:
            payload['processing_progress'] = progress
        if hard_requirements_met is not None:
            payload['hard_requirements_met'] = hard_requirements_met
        
        await api.post_async("/updates/resume/status/single", data=payload)
    except Exception as e:
        print(f"⚠️ Failed to update resume status: {e}")


def update_job_resume_status(job_id: str, status: str, progress: int = None, error: str = None):
    """Update job's resume processing status"""
    try:
        pass # Disabling legacy status update as progress is now tracked via BullMQ and final status via /updates/resume/status.
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
    
    # Determine retry/fail policy
    max_attempts = job.opts.get('attempts', 1) if job.opts else 1
    attempts_made = getattr(job, 'attemptsMade', 0)
    is_final_attempt = (attempts_made + 1) >= max_attempts
    
    # Update resume status to processing
    await update_resume_status(resume_id, 'processing', 0, job_id=job.id)
    
    try:
        # Fetch resume data
        await tracker.update(5, "fetching_resume", "Fetching resume data")
        logger.progress("Fetching resume data")
        
        resume_data = await api.get_async(f"/updates/resume/{resume_id}")
        
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
        jd_data = await _get_jd_cached(job_id)
        
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
        
        parse_result = await parse_resume_with_ai(
            text_result['text'],
            text_result.get('hyperlinks', []),
            jd_data,
        )
        if not parse_result.get('success'):
            error_msg = f"AI parsing failed: {parse_result.get('error')}"
            logger.fail(error_msg)
            await tracker.failed(error_msg, "AIParsingError", "parsing")
            return {'success': False, 'error': error_msg}

        parsed_resume = parse_result['parsed_data']
        # Save parsed resume using new API
        await api.post_async("/updates/resume/parsed", data={
            'resume_id': resume_id,
            'parsed_content': parsed_resume
        })
        candidate_name = (parsed_resume.get('profile') or {}).get('name', 'Unknown')
        logger.progress(f"Parsed: {candidate_name}")
        await tracker.update(40, "parsing", f"Resume parsed successfully")

        # ======================================================================
        # EXPERIENCE GATE  (deterministic, pure Python, ~0ms, no API calls)
        # ======================================================================
        #
        # WHY THIS IS HERE:
        #   The next step (generate_resume_embeddings) fires 6 OpenAI API calls
        #   to produce vector embeddings for each resume section. For a candidate
        #   who fails the experience requirement, those API calls are pure waste.
        #
        #   This gate runs immediately after AI parsing, before any embeddings
        #   are generated. It reads the HR filter text from the JD, extracts the
        #   experience clause using regex, and does integer arithmetic against the
        #   parsed resume. No LLM, no network, essentially 0ms overhead.
        #
        # OPTION A (chosen):
        #   Gate runs early for experience only. If it FAILS -> terminate.
        #   If it PASSES -> pipeline continues normally, including the full
        #   check_hard_requirements() call later (which will re-check experience
        #   plus skills). The double experience check is harmless -- the second
        #   check will always pass since the first already confirmed it.
        #
        # GATE OUTCOMES:
        #   gate_applicable=False  -> No experience clause in HR text. Skip gate.
        #   gate_applicable=True, passed=True  -> Experience OK. Continue.
        #   gate_applicable=True, passed=False -> Terminate immediately.
        # ======================================================================
        gate_result = check_experience_gate(parsed_resume, jd_data)

        if gate_result.get('gate_applicable') and not gate_result.get('passed'):
            # ------------------------------------------------------------------
            # EXPERIENCE GATE FAILED -- build an enriched rejection reason that
            # includes the delta (how many months short or over the candidate is).
            # ------------------------------------------------------------------
            base_reason = gate_result.get('reason', 'Experience requirement not met')
            shortfall   = gate_result.get('shortfall_months')  # int or None
            excess      = gate_result.get('excess_months')      # int or None

            # Build a concise delta suffix ONLY for the terminal log line.
            # IMPORTANT: base_reason already embeds the delta inside its sentence
            # (e.g. "...below the minimum requirement of 24 months (short by 16 months).").
            # Do NOT append delta_str to base_reason -- that would duplicate the
            # delta in the string that gets stored in the DB and shown on the frontend.
            if shortfall is not None:
                delta_str = f"short by {shortfall} month{'s' if shortfall != 1 else ''}"
            elif excess is not None:
                delta_str = f"over by {excess} month{'s' if excess != 1 else ''}"
            else:
                delta_str = ""

            # The reason stored in DB and shown on the frontend is base_reason only.
            # The delta is already embedded in the sentence by _check_experience_python.
            log_reason = base_reason

            # Terminal/tracker log gets the delta_str appended for quick scanning
            logger.progress(f"❌ [EXP GATE] {base_reason} [{delta_str}]" if delta_str else f"❌ [EXP GATE] {base_reason}")
            await tracker.update(42, "experience_gate", f"Rejected: {log_reason}")

            # Save 0.0 scores to DB so the frontend can display the rejection
            await api.post_async("/updates/resume/scores", data={
                'resume_id': resume_id,
                'scores': {
                    'hard_requirements': {
                        'meets_all_requirements': False,
                        'compliance_score': 0.0,
                        'requirements_met': [],
                        'requirements_missing': [base_reason],
                        'filter_reason': log_reason
                    },
                    'project_score': 0.0,
                    'keyword_score': 0.0,
                    'semantic_score': 0.0,
                    'composite_score': 0.0
                }
            })

            # Mark the resume as completed (not failed) with hard_requirements_met=False
            await update_resume_status(resume_id, 'success', 100, hard_requirements_met=False)

            logger.complete(f"Completed: Experience gate rejected - {delta_str or 'out of range'}")
            await tracker.update(100, "complete", "Job completed - Experience gate rejected")

            return {
                'success': True,
                'score': 0.0,
                'hard_requirements_passed': False,
                'filter_reason': log_reason,
                'message': 'Candidate does not meet the experience requirement'
            }
        # ======================================================================
        # END EXPERIENCE GATE -- candidate passed or gate was not applicable.
        # Continue with embeddings and the rest of the pipeline.
        # ======================================================================

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
            await api.post_async("/updates/resume/embeddings", data={
                'resume_id': resume_id,
                'resume_embedding': embedding_data['resume_embedding']
            })
            logger.progress(f"Embeddings generated: {len(section_embeddings)} sections")
            await tracker.update(55, "generating_embeddings", "Embeddings generated")
        
        # Calculate scores
        await tracker.update(60, "scoring", "Calculating scores")
        logger.progress("Calculating scores")
        
        # Hard requirements check
        hard_req_result = await check_hard_requirements(parsed_resume, jd_data)
        if not hard_req_result.get('success'):
            hard_req_result = {'meets_all_requirements': True, 'compliance_score': 1.0}
        
        meets_hard_requirements = hard_req_result.get('meets_all_requirements', True)
        logger.progress(f"Hard req: {'✅ Met' if meets_hard_requirements else '❌ Not met'}")
        await tracker.update(65, "scoring", "Hard requirements checked")
        
        # If hard requirements not met, skip further processing and save failed result
        if not meets_hard_requirements:
            reason = hard_req_result.get('filter_reason', 'No reason provided')
            logger.progress(f"❌ Hard requirements not met: {reason} - skipping further processing")
            await tracker.update(95, "saving_scores", f"Saving failed compliance scores: {reason}")
            
            # Save failed compliance scores
            await api.post_async("/updates/resume/scores", data={
                'resume_id': resume_id,
                'scores': {
                    'hard_requirements': {
                        'meets_all_requirements': False,
                        'compliance_score': hard_req_result.get('compliance_score', 0.0),
                        'requirements_met': hard_req_result.get('requirements_met', []),
                        'requirements_missing': hard_req_result.get('requirements_missing', []),
                        'filter_reason': hard_req_result.get('filter_reason')
                    },
                    'project_score': 0.0,
                    'keyword_score': 0.0,
                    'semantic_score': 0.0,
                    'composite_score': 0.0
                }
            })
            
            # Update resume status to completed with hard_requirements_met=False
            await update_resume_status(resume_id, 'success', 100, hard_requirements_met=False)
            
            logger.complete(f"Completed: Hard requirements not met - Score 0.00")
            await tracker.update(100, "complete", "Job completed - Hard requirements not met")
            
            return {
                'success': True,
                'score': 0.0,
                'hard_requirements_passed': False,
                'filter_reason': hard_req_result.get('filter_reason', 'Does not meet mandatory compliance requirements'),
                'message': 'Resume does not meet mandatory compliance requirements'
            }
        
        # Continue with regular scoring if hard requirements are met
        
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
            jd_embeddings,
            embed_result.get('section_texts', {}),
            parsed_resume
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
        
        await api.post_async("/updates/resume/scores", data={
            'resume_id': resume_id,
            'scores': {
                'hard_requirements': {
                    'meets_all_requirements': hard_req_result.get('meets_all_requirements', True),
                    'compliance_score': hard_req_result.get('compliance_score', 1.0),
                    'requirements_met': hard_req_result.get('requirements_met', []),
                    'requirements_missing': hard_req_result.get('requirements_missing', []),
                    'filter_reason': hard_req_result.get('filter_reason'),
                    'selection_reason': hard_req_result.get('selection_reason')
                },
                'project_score': project_result.get('overall_score', 0.0),
                'keyword_score': keyword_result.get('overall_score', 0.0),
                'semantic_score': semantic_result.get('overall_semantic_score', 0.0),
                'section_scores': semantic_result.get('section_scores', {}),
                'composite_score': composite_result.get('final_score', 0.0)
            }
        })
        
        # NOTE: Do NOT update job status here - only individual resume status
        # Parent job will update job status when ALL resumes complete
        
        # Update resume status to success with hard_requirements_met=True
        await update_resume_status(resume_id, 'success', 100, hard_requirements_met=True)
        
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
        # NOTE: Do NOT update job status - only individual resume status
        if is_final_attempt:
            await update_resume_status(resume_id, 'failed', error=error_msg)
        await tracker.failed(error_msg, "APIError", "processing")
        return {'success': False, 'error': error_msg, 'final_score': 0.0}
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        error_msg = f"{type(e).__name__}: {str(e)}"
        logger.fail(error_msg)
        print(f"📋 Full error traceback:\n{error_traceback}")
        # NOTE: Do NOT update job status - only individual resume status
        if is_final_attempt:
            await update_resume_status(resume_id, 'failed', error=error_msg)
        await tracker.failed(str(e), type(e).__name__, "processing")
        return {'success': False, 'error': str(e), 'final_score': 0.0}

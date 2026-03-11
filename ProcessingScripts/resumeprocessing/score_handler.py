"""
Score Job Processing Handler
==============================
One BullMQ job = one (JD, Resume) evaluation pair (ScorePair document).

Flow:
  1. Mark pair as 'processing'
  2. GET /api/score/job-data/{scorePairId}  →  { jdData, resumeData }
  3. CandidateEvaluator.evaluate_async(resumeData, jdData)
  4. POST /api/score/update-result  →  { scorePairId, result }
     (backend saves scores, increments parent ScoreRun counts, finalises run if done)

Called by main.py worker for every job on the 'score-processing' queue.

Job Data:
    { "scorePairId": "MongoDB ObjectId string" }
"""

import logging
from typing import Any, Dict

from openai import AsyncOpenAI
from .score_processor import CandidateEvaluator
from .api_client import (
    update_score_pair_status,
    update_score_result,
    fetch_score_job_data,
    notify_score_pair_failed,
)

logger = logging.getLogger(__name__)


async def process_score_job(job: Any, job_token: str) -> Dict[str, Any]:
    """
    Process a single scoring job (one JD + one Resume pair).

    Args:
        job:       BullMQ Job object  (job.data = { scorePairId })
        job_token: BullMQ job token

    Returns:
        Dict with success status and metadata.

    Raises:
        Exception: BullMQ will retry on failure.
    """
    job_id        = job.id
    job_data      = job.data
    score_pair_id = job_data.get('scorePairId')

    logger.info("=" * 60)
    logger.info(f"🏆 Score Job {job_id} — ScorePair: {score_pair_id}")
    logger.info("=" * 60)

    if not score_pair_id:
        raise ValueError(f"Missing scorePairId in job data: {job_data}")

    try:
        # ── Step 1: Mark processing ──────────────────────────────────────
        logger.info("📝 Step 1/4: Marking as 'processing'")
        await update_score_pair_status(score_pair_id, 'processing')

        # ── Step 2: Fetch JD + resume data ───────────────────────────────
        logger.info("📥 Step 2/4: Fetching job data")
        payload = await fetch_score_job_data(score_pair_id)

        jd_data     = payload.get('jdData', {})
        resume_data = payload.get('resumeData', {})

        logger.info(f"   JD data keys:     {list(jd_data.keys())}")
        logger.info(f"   Resume data keys: {list(resume_data.keys())}")

        # ── Step 3: Evaluate the pair ────────────────────────────────────
        logger.info("🤖 Step 3/4: Evaluating pair with AI")
        import os
        aclient   = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        evaluator = CandidateEvaluator(async_llm_client=aclient)

        result = await evaluator.evaluate_async(resume_data, jd_data)
        logger.info(f"   ✅ Overall score: {result.get('overall_score')}")

        # ── Step 4: Save result (marks pair 'completed' + updates parent run) ──
        logger.info("💾 Step 4/4: Saving result")
        await update_score_result(score_pair_id, result)

        logger.info(f"🎉 Score job {job_id} finished successfully")
        return {'success': True, 'scorePairId': score_pair_id, 'overallScore': result.get('overall_score')}

    except Exception as exc:
        error_msg = str(exc)
        logger.error(f"❌ Score job {job_id} failed: {error_msg}", exc_info=True)
        await notify_score_pair_failed(score_pair_id, error_msg)
        raise


logger = logging.getLogger(__name__)

"""
Resume, JD & Score Processing Package
=======================================
Contains all processing logic for resumes, job descriptions, and candidate scoring.

For engineers working on this package:
- processor.py:       Resume AI extraction logic
- jd_processor.py:    JD AI extraction logic
- score_processor.py: Candidate evaluation engine (CandidateEvaluator)
- api_client.py:      Backend API communication functions
- s3_handler.py:      S3/MinIO file download and cleanup
- job_handler.py:     Resume job flow (BullMQ worker)
- jd_handler.py:      JD job flow (BullMQ worker)
- score_handler.py:   Scoring job flow (BullMQ worker)
- test_local.py:      Local testing utilities

Usage in main.py:
    from resumeprocessing.job_handler import process_resume_job
    from resumeprocessing.jd_handler import process_jd_job
    from resumeprocessing.score_handler import process_score_job
"""

# Resume processing exports
from .processor import process_single_resume_file

# JD processing exports
from .jd_processor import process_single_jd_file

# Score processing exports
from .score_processor import CandidateEvaluator

# S3 operations
from .s3_handler import download_from_s3, cleanup_temp_file

# API operations — resume
from .api_client import (
    update_resume_status,
    send_extracted_data,
    notify_processing_failed,
    # JD
    update_jd_status,
    send_jd_extracted_data,
    notify_jd_processing_failed,
    # Score
    update_score_pair_status,
    update_score_result,
    fetch_score_job_data,
    notify_score_pair_failed,
)

__all__ = [
    # Resume processing
    'process_single_resume_file',

    # JD processing
    'process_single_jd_file',

    # S3 operations
    'download_from_s3',
    'cleanup_temp_file',

    # API operations — resume
    'update_resume_status',
    'send_extracted_data',
    'notify_processing_failed',

    # API operations — JD
    'update_jd_status',
    'send_jd_extracted_data',
    'notify_jd_processing_failed',

    # Score processing
    'CandidateEvaluator',

    # API operations — Score
    'update_score_pair_status',
    'update_score_result',
    'fetch_score_job_data',
    'notify_score_pair_failed',
]

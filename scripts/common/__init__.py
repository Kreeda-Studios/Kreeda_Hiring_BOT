"""
Common utilities for Kreeda Hiring Bot scripts

This package provides shared utilities for:
- BullMQ progress tracking
- Job logging
- API clients
- Error handling
"""

from .bullmq_progress import (
    ProgressTracker,
    ParentProgressTracker,
    update_progress,
    complete_job,
    fail_job
)

from .job_logger import (
    JobLogger,
    log_jd_progress,
    log_resume_progress,
    log_ranking_progress
)

from .api_client import (
    api,
    APIClient,
    APIError,
    get_job,
    update_job,
    get_resume,
    update_resume,
    save_score,
    get_scores
)

__all__ = [
    # Progress tracking
    "ProgressTracker",
    "ParentProgressTracker",
    "update_progress",
    "complete_job",
    "fail_job",
    # Logging
    "JobLogger",
    "log_jd_progress",
    "log_resume_progress",
    "log_ranking_progress",
    # API client
    "api",
    "APIClient",
    "APIError",
    "get_job",
    "update_job",
    "get_resume",
    "update_resume",
    "save_score",
    "get_scores"
]

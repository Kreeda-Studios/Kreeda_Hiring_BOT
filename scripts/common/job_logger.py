"""
Job Logger Module

Simple, clean logger for JD, Resume, and Ranking processing.
Uses consistent formatting with emojis for visual distinction.

Usage:
    from common.job_logger import JobLogger
    
    # For JD Processing
    logger = JobLogger.for_jd(job_id="673abc123")
    logger.progress("Extracting PDF content")
    logger.complete("Processing finished")
    logger.fail("API timeout error")
    
    # For Resume Processing
    logger = JobLogger.for_resume(resume_id="789xyz", index=1, total=87)
    logger.progress("Parsing resume")
    logger.complete("Resume scored")
    logger.fail("Extraction failed")
    
    # For Ranking Processing
    logger = JobLogger.for_ranking(job_id="673abc123", batch=1, total=3)
    logger.progress("Re-ranking with GPT-4")
    logger.complete("Batch ranked")
    logger.fail("LLM error")
"""

import logging
from typing import Optional
from datetime import datetime

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%H:%M:%S'
)

EMOJI_PROGRESS = "⚙️"   # Progress/Update
EMOJI_COMPLETE = "✅"   # Complete/Success
EMOJI_FAIL = "❌"       # Fail/Error


class JobLogger:
    """
    Clean logger for job processing with consistent formatting.
    
    Three formats:
    - JD: [Job Id] Message
    - Resume: [1/n][Resume Id] Message
    - Ranking: [1/n][Job Id] Message
    """
    
    def __init__(self, job_type: str, **context):
        """
        Initialize logger with job type and context.
        
        Args:
            job_type: Type of job ('jd', 'resume', 'ranking')
            **context: Context data (job_id, resume_id, index, total, etc.)
        """
        self.job_type = job_type
        self.context = context
        self.logger = logging.getLogger(f'job.{job_type}')
    
    @classmethod
    def for_jd(cls, job_id: str) -> 'JobLogger':
        """
        Create logger for JD processing.
        
        Format: ⚙️  [Job Id] Message
        
        Args:
            job_id: MongoDB Job ID
        """
        return cls('jd', job_id=job_id)
    
    @classmethod
    def for_resume(cls, resume_id: str, index: int, total: int) -> 'JobLogger':
        """
        Create logger for Resume processing.
        
        Format: ⚙️  [1/n][Resume Id] Message
        
        Args:
            resume_id: MongoDB Resume ID
            index: Current resume index (1-based)
            total: Total resumes in batch
        """
        return cls('resume', resume_id=resume_id, index=index, total=total)
    
    @classmethod
    def for_ranking(cls, job_id: str, batch: int, total: int) -> 'JobLogger':
        """
        Create logger for Ranking processing.
        
        Format: ⚙️  [1/n][Job Id] Message
        
        Args:
            job_id: MongoDB Job ID
            batch: Current batch number (1-based)
            total: Total batches
        """
        return cls('ranking', job_id=job_id, batch=batch, total=total)
    
    def _format_prefix(self) -> str:
        """Generate prefix based on job type"""
        if self.job_type == 'jd':
            # Format: [Job Id]
            return f"[{self.context['job_id'][:12]}...]"
        
        elif self.job_type == 'resume':
            # Format: [1/n][Resume Id]
            index = self.context['index']
            total = self.context['total']
            resume_id = self.context['resume_id'][:12]
            return f"[{index}/{total}][{resume_id}...]"
        
        elif self.job_type == 'ranking':
            # Format: [1/n][Job Id]
            batch = self.context['batch']
            total = self.context['total']
            job_id = self.context['job_id'][:12]
            return f"[{batch}/{total}][{job_id}...]"
        
        return ""
    
    def progress(self, message: str) -> None:
        """
        Log progress/update message.
        
        Args:
            message: Progress message
        """
        prefix = self._format_prefix()
        self.logger.info(f"{EMOJI_PROGRESS}  {prefix} {message}")
    
    def complete(self, message: str = "Processing complete") -> None:
        """
        Log completion message.
        
        Args:
            message: Completion message
        """
        prefix = self._format_prefix()
        self.logger.info(f"{EMOJI_COMPLETE}  {prefix} {message}")
    
    def fail(self, message: str) -> None:
        """
        Log failure/error message.
        
        Args:
            message: Error message
        """
        prefix = self._format_prefix()
        self.logger.error(f"{EMOJI_FAIL}  {prefix} {message}")


# Convenience functions for quick usage
def log_jd_progress(job_id: str, message: str) -> None:
    """Quick JD progress log"""
    logger = JobLogger.for_jd(job_id)
    logger.progress(message)


def log_resume_progress(resume_id: str, index: int, total: int, message: str) -> None:
    """Quick Resume progress log"""
    logger = JobLogger.for_resume(resume_id, index, total)
    logger.progress(message)


def log_ranking_progress(job_id: str, batch: int, total: int, message: str) -> None:
    """Quick Ranking progress log"""
    logger = JobLogger.for_ranking(job_id, batch, total)
    logger.progress(message)

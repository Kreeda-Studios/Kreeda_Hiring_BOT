"""
BullMQ Progress Tracker Module

Clean, standardized progress tracking for BullMQ jobs.
Handles progress updates, completion, and failure reporting.

Usage:
    from common.bullmq_progress import ProgressTracker
    
    # Initialize with job
    tracker = ProgressTracker(job)
    
    # Update progress
    tracker.update(
        percent=25,
        step="extracting_text",
        message="Extracting PDF content"
    )
    
    # Mark complete
    tracker.complete(
        duration=15000,
        summary={"skillsExtracted": 25}
    )
    
    # Mark failed
    tracker.failed(
        error="API timeout",
        error_type="APIError",
        step="ai_parsing"
    )
"""

from datetime import datetime, timezone
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Clean BullMQ progress tracker.
    
    Automatically pushes standardized progress updates to BullMQ jobs.
    """
    
    def __init__(self, job: Any):
        """
        Initialize progress tracker.
        
        Args:
            job: BullMQ job object with updateProgress() and updateData() methods
        """
        self.job = job
        self.start_time = datetime.now(timezone.utc)
        self._last_percent = 0
        
    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        return datetime.now(timezone.utc).isoformat()
    
    def _get_duration(self) -> int:
        """Get duration since start in milliseconds."""
        delta = datetime.now(timezone.utc) - self.start_time
        return int(delta.total_seconds() * 1000)
    
    async def update(
        self,
        percent: int,
        step: str,
        message: Optional[str] = None,
        stage: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Update job progress.
        
        Args:
            percent: Progress percentage (0-100)
            step: Current step identifier (e.g., "extracting_text")
            message: Optional human-readable message
            stage: Optional stage identifier
            metadata: Optional additional data
        """
        # Validate percent
        if not 0 <= percent <= 100:
            logger.warning(f"Invalid percent value: {percent}. Must be 0-100.")
            percent = max(0, min(100, percent))
        
        # Build progress object
        progress = {
            "percent": percent,
            "step": step,
            "timestamp": self._get_timestamp()
        }
        
        if message:
            progress["message"] = message
        
        if stage:
            progress["stage"] = stage
            
        if metadata:
            progress["metadata"] = metadata
        
        try:
            # Push to BullMQ
            await self.job.updateProgress(progress)
            self._last_percent = percent
            
            # Log progress
            log_msg = f"Progress: {percent}% - {step}"
            if message:
                log_msg += f" - {message}"
            logger.info(log_msg)
            
        except Exception as e:
            logger.error(f"Failed to update progress: {e}", exc_info=True)
    
    async def complete(
        self,
        duration: Optional[int] = None,
        summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Mark job as complete.
        
        Args:
            duration: Optional custom duration in ms (auto-calculated if not provided)
            summary: Optional job-specific summary data
        
        Returns:
            Completion object
        """
        completion = {
            "success": True,
            "step": "complete",
            "timestamp": self._get_timestamp(),
            "duration": duration if duration is not None else self._get_duration()
        }
        
        if summary:
            completion["summary"] = summary
        
        try:
            # Update to 100% progress
            await self.update(
                percent=100,
                step="complete",
                message="Job completed successfully"
            )
            
            # Update job data with completion info
            await self.job.updateData({
                **self.job.data,
                "completion": completion
            })
            
            logger.info(
                f"Job completed - Duration: {completion['duration']}ms"
            )
            
            return completion
            
        except Exception as e:
            logger.error(f"Failed to mark completion: {e}", exc_info=True)
            return completion
    
    async def failed(
        self,
        error: str,
        error_type: Optional[str] = None,
        step: Optional[str] = None,
        retryable: bool = False,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Mark job as failed.
        
        Args:
            error: Error message
            error_type: Optional error type (e.g., "APIError", "ValidationError")
            step: Optional step where failure occurred
            retryable: Whether the job can be retried
            metadata: Optional additional error context
        
        Returns:
            Failure object
        """
        failure = {
            "error": error,
            "timestamp": self._get_timestamp(),
            "step": step or "unknown",
            "duration": self._get_duration()
        }
        
        if error_type:
            failure["errorType"] = error_type
        
        if retryable:
            failure["retryable"] = True
            
        if metadata:
            failure["metadata"] = metadata
        
        try:
            # Update job data with failure info
            await self.job.updateData({
                **self.job.data,
                "failure": failure
            })
            
            logger.error(
                f"Job failed - {error_type or 'Error'}: {error} "
                f"(step: {failure['step']})"
            )
            
            return failure
            
        except Exception as e:
            logger.error(f"Failed to mark failure: {e}", exc_info=True)
            return failure
    
    async def update_with_stage(
        self,
        stage_name: str,
        stage_percent: int,
        total_stages: int,
        current_stage: int,
        message: Optional[str] = None
    ) -> None:
        """
        Update progress with stage-based calculation.
        
        Useful for multi-stage jobs where you want to calculate
        overall progress based on current stage.
        
        Args:
            stage_name: Name of current stage
            stage_percent: Progress within current stage (0-100)
            total_stages: Total number of stages
            current_stage: Current stage number (1-based)
            message: Optional message
        
        Example:
            # Stage 2 of 4, 50% through current stage
            await tracker.update_with_stage(
                stage_name="ai_parsing",
                stage_percent=50,
                total_stages=4,
                current_stage=2,
                message="Parsing with GPT-4"
            )
            # Overall progress will be: ((2-1) * 100 + 50) / 4 = 37.5%
        """
        # Calculate overall progress
        stage_weight = 100 / total_stages
        overall_percent = int(
            ((current_stage - 1) * stage_weight) + 
            (stage_percent * stage_weight / 100)
        )
        
        await self.update(
            percent=overall_percent,
            step=stage_name,
            message=message,
            stage=f"{current_stage}/{total_stages}",
            metadata={
                "stagePercent": stage_percent,
                "currentStage": current_stage,
                "totalStages": total_stages
            }
        )


class ParentProgressTracker(ProgressTracker):
    """
    Progress tracker for parent jobs that orchestrate child jobs.
    
    Tracks child job completion and calculates aggregate progress.
    """
    
    def __init__(self, job: Any, total_children: int):
        """
        Initialize parent progress tracker.
        
        Args:
            job: BullMQ job object
            total_children: Total number of child jobs
        """
        super().__init__(job)
        self.total_children = total_children
        self.completed_children = 0
        self.failed_children = 0
    
    async def child_completed(
        self,
        child_index: int,
        child_summary: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Mark a child job as completed.
        
        Args:
            child_index: 1-based index of completed child
            child_summary: Optional summary from child job
        """
        self.completed_children += 1
        
        # Calculate progress
        percent = int((self.completed_children / self.total_children) * 100)
        
        await self.update(
            percent=percent,
            step="processing_children",
            message=f"Completed {self.completed_children}/{self.total_children}",
            metadata={
                "completedChildren": self.completed_children,
                "totalChildren": self.total_children,
                "childIndex": child_index,
                "childSummary": child_summary
            }
        )
    
    async def child_failed(
        self,
        child_index: int,
        error: str
    ) -> None:
        """
        Mark a child job as failed.
        
        Args:
            child_index: 1-based index of failed child
            error: Error message from child
        """
        self.failed_children += 1
        
        logger.warning(
            f"Child {child_index}/{self.total_children} failed: {error}"
        )
        
        # Update metadata to track failures
        await self.job.updateData({
            **self.job.data,
            "failedChildren": self.failed_children,
            "lastFailure": {
                "childIndex": child_index,
                "error": error,
                "timestamp": self._get_timestamp()
            }
        })
    
    async def complete_parent(
        self,
        summary: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Complete parent job with child statistics.
        
        Args:
            summary: Optional additional summary data
        
        Returns:
            Completion object
        """
        parent_summary = {
            "totalChildren": self.total_children,
            "completedChildren": self.completed_children,
            "failedChildren": self.failed_children,
            "successRate": (
                self.completed_children / self.total_children * 100
                if self.total_children > 0 else 0
            )
        }
        
        if summary:
            parent_summary.update(summary)
        
        return await self.complete(summary=parent_summary)


# Convenience functions for quick usage
async def update_progress(
    job: Any,
    percent: int,
    step: str,
    message: Optional[str] = None
) -> None:
    """
    Quick progress update without creating tracker instance.
    
    Args:
        job: BullMQ job object
        percent: Progress percentage (0-100)
        step: Current step identifier
        message: Optional message
    """
    tracker = ProgressTracker(job)
    await tracker.update(percent, step, message)


async def complete_job(
    job: Any,
    summary: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Quick job completion without creating tracker instance.
    
    Args:
        job: BullMQ job object
        summary: Optional summary data
    
    Returns:
        Completion object
    """
    tracker = ProgressTracker(job)
    return await tracker.complete(summary=summary)


async def fail_job(
    job: Any,
    error: str,
    error_type: Optional[str] = None,
    step: Optional[str] = None
) -> Dict[str, Any]:
    """
    Quick job failure without creating tracker instance.
    
    Args:
        job: BullMQ job object
        error: Error message
        error_type: Optional error type
        step: Optional step where failure occurred
    
    Returns:
        Failure object
    """
    tracker = ProgressTracker(job)
    return await tracker.failed(error, error_type, step)

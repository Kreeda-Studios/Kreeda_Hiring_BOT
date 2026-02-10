import { useState, useEffect, useCallback } from 'react';

interface JobProcessingStatus {
  id: string;
  title: string;
  status: 'draft' | 'active' | 'completed' | 'archived';
  locked: boolean;
  jd_processing: {
    status: 'pending' | 'processing' | 'success' | 'failed';
    progress: number;
    error?: string;
    job_id?: string;
  };
  resume_processing: {
    status: 'pending' | 'processing' | 'success' | 'failed';
    progress: number;
    error?: string;
    parent_job_id?: string;
    total_resumes: number;
    processing_count: number;
    completed_count: number;
    failed_count: number;
  };
}

interface ResumeProcessingStatus {
  id: string;
  filename: string;
  original_name: string;
  status: 'pending' | 'processing' | 'success' | 'failed';
  progress: number;
  error?: string;
  job_id?: string;
}

interface JobStatusData {
  job: JobProcessingStatus;
  resumes: ResumeProcessingStatus[];
}

export function useJobStatus(jobId: string) {
  const [statusData, setStatusData] = useState<JobStatusData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!jobId) return;

    try {
      setLoading(true);
      setError(null);

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api';
      const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/status`);
      
      if (!response.ok) {
        throw new Error('Failed to fetch job status');
      }
      
      const result = await response.json();
      
      if (result.success) {
        setStatusData(result.data);
      } else {
        throw new Error(result.error || 'Failed to fetch job status');
      }
    } catch (err) {
      console.error('Failed to fetch job status:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch status');
    } finally {
      setLoading(false);
    }
  }, [jobId]);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Utility functions
  const isJDProcessingInProgress = () => {
    return statusData?.job.jd_processing.status === 'processing';
  };

  const isResumeProcessingInProgress = () => {
    return statusData?.job.resume_processing.status === 'processing';
  };

  const canUploadResumes = () => {
    return !isResumeProcessingInProgress();
  };

  const canStartJDProcessing = () => {
    return !statusData?.job.locked && statusData?.job.jd_processing.status !== 'processing';
  };

  const canStartResumeProcessing = () => {
    return statusData?.job.locked && 
           statusData?.job.jd_processing.status === 'success' &&
           statusData?.job.resume_processing.status !== 'processing' &&
           statusData?.job.resume_processing.total_resumes > 0;
  };

  return {
    statusData,
    loading,
    error,
    refetch: fetchStatus,
    // Utility functions
    isJDProcessingInProgress,
    isResumeProcessingInProgress,
    canUploadResumes,
    canStartJDProcessing,
    canStartResumeProcessing,
  };
}
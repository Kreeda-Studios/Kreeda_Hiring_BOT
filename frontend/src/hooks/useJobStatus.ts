import { useState, useEffect, useCallback } from 'react';

interface Job {
  _id: string;
  title: string;
  description?: string;
  status: string;
  locked: boolean;
  jd_file_path?: string;
  createdAt: string;
  updatedAt: string;
}

interface Resume {
  _id: string;
  filename: string;
  original_name: string;
  status: string;
  job_id: string;
}

interface JobStatusData {
  job: Job;
  resumes: Resume[];
  resumeCount: number;
}

export function useJobStatus(jobId: string) {
  const [statusData, setStatusData] = useState<JobStatusData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    if (!jobId) return;

    try {
      console.log('📡 [useJobStatus] Polling status for:', jobId);
      setLoading(true);
      setError(null);

      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL!;
      
      // Fetch job and resumes in parallel
      const [jobResponse, resumesResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/jobs/${jobId}`),
        fetch(`${API_BASE_URL}/resumes?job_id=${jobId}`)
      ]);
      
      if (!jobResponse.ok) {
        throw new Error('Failed to fetch job');
      }
      
      const jobResult = await jobResponse.json();
      const resumesResult = resumesResponse.ok ? await resumesResponse.json() : { data: [], count: 0 };
      
      if (jobResult.success) {
        console.log('✅ [useJobStatus] Status fetched:', jobResult.data.status);
        setStatusData({
          job: jobResult.data,
          resumes: resumesResult.data || [],
          resumeCount: resumesResult.count || 0
        });
      } else {
        throw new Error(jobResult.error || 'Failed to fetch job');
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

  // Utility functions based on actual job status
  const isJDProcessingInProgress = () => {
    const status = statusData?.job.status;
    return status === 'jd_processing_started';
  };

  const isResumeProcessingInProgress = () => {
    const status = statusData?.job.status;
    return status === 'resume_processing_started';
  };

  const canUploadResumes = () => {
    const status = statusData?.job.status;
    // Only allow upload when status is exactly 'jd_processing_completed'
    return status === 'jd_processing_completed';
  };

  const canStartJDProcessing = () => {
    const status = statusData?.job.status;
    return !statusData?.job.locked && status !== 'jd_processing_started';
  };

  const canStartResumeProcessing = () => {
    const status = statusData?.job.status;
    const hasResumes = (statusData?.resumeCount || 0) > 0;
    
    // Only allow processing when status is exactly 'jd_processing_completed'
    return status === 'jd_processing_completed' && hasResumes;
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
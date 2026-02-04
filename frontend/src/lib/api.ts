const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api';

async function fetchAPI<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  const response = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  
  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Request failed' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }
  
  return response.json();
}

// Jobs API
export const jobsAPI = {
  getAll: () => fetchAPI<{ success: boolean; data: any[]; count: number }>('/jobs'),
  
  getById: (id: string) => fetchAPI<{ success: boolean; data: any }>(`/jobs/${id}`),
  
  create: (data: { title: string; description?: string; jd_text?: string }) =>
    fetchAPI<{ success: boolean; data: any }>('/jobs', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  
  update: (id: string, data: any) =>
    fetchAPI<{ success: boolean; data: any }>(`/jobs/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  uploadJD: async (jobId: string, file: File) => {
    const formData = new FormData();
    formData.append('jd_pdf', file);
    
    const response = await fetch(`${API_BASE_URL}/jobs/${jobId}/upload-jd`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'JD upload failed' }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }
    
    return response.json();
  },

  linkResumeGroups: (jobId: string, resumeGroupIds: string[]) =>
    fetchAPI<{ success: boolean; data: any }>(`/jobs/${jobId}/resume-groups`, {
      method: 'PUT',
      body: JSON.stringify({ resume_group_ids: resumeGroupIds }),
    }),
  
  delete: (id: string) =>
    fetchAPI<{ success: boolean; message: string }>(`/jobs/${id}`, { method: 'DELETE' }),
};

// Resume Groups API
export const resumeGroupsAPI = {
  getAll: () =>
    fetchAPI<{ success: boolean; data: any[]; count: number }>('/resume-groups'),

  getByJob: (jobId: string) =>
    fetchAPI<{ success: boolean; data: any[]; count: number }>(`/resume-groups?job_id=${jobId}`),
  
  create: (data: { name: string; job_ids?: string[]; source?: string }) =>
    fetchAPI<{ success: boolean; data: any }>('/resume-groups', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  uploadResumes: async (groupId: string, files: File[], jobId?: string) => {
    const formData = new FormData();
    if (jobId) formData.append('job_id', jobId);
    files.forEach(file => formData.append('resumes', file));
    
    const response = await fetch(`${API_BASE_URL}/resume-groups/${groupId}/upload`, {
      method: 'POST',
      body: formData,
    });
    
    if (!response.ok) {
      const error = await response.json().catch(() => ({ error: 'Upload failed' }));
      throw new Error(error.error || `HTTP ${response.status}`);
    }
    
    return response.json();
  },
  
  delete: (id: string) =>
    fetchAPI<{ success: boolean; message: string }>(`/resume-groups/${id}`, { method: 'DELETE' }),
};

// Resumes API
export const resumesAPI = {
  getAll: () =>
    fetchAPI<{ success: boolean; data: any[]; count: number }>('/resumes'),

  getByGroup: (groupId: string) =>
    fetchAPI<{ success: boolean; data: any[]; count: number }>(`/resumes?group_id=${groupId}`),
  
  getById: (id: string) =>
    fetchAPI<{ success: boolean; data: any }>(`/resumes/${id}`),
  
  create: (data: { title: string; description?: string }) =>
    fetchAPI<{ success: boolean; data: any }>('/resumes', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  update: (id: string, data: Partial<any>) =>
    fetchAPI<{ success: boolean; data: any }>(`/resumes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  
  delete: (id: string) =>
    fetchAPI<{ success: boolean; message: string }>(`/resumes/${id}`, { method: 'DELETE' }),
};

// Processing API
export const processingAPI = {
  processJD: (jobId: string) =>
    fetchAPI<{ success: boolean; data: any; message: string }>(`/process/jd/${jobId}`, {
      method: 'POST',
    }),

  processResumes: (jobId: string) =>
    fetchAPI<{ success: boolean; data: any; message: string }>(`/process/resumes/${jobId}`, {
      method: 'POST',
    }),

  processRanking: (jobId: string) =>
    fetchAPI<{ success: boolean; data: any; message: string }>(`/process/ranking/${jobId}`, {
      method: 'POST',
    }),
  
  getStatus: (jobId: string) =>
    fetchAPI<{ 
      success: boolean; 
      data: {
        jobId: string;
        counts: {
          jd: {
            total: number;
            active: number;
            completed: number;
            failed: number;
          };
          resumes: {
            total: number;
            active: number;
            waiting: number;
            completed: number;
            failed: number;
          };
          ranking: {
            total: number;
            active: number;
            completed: number;
            failed: number;
          };
        };
        activeProgress: any;
      }
    }>(`/status/job/${jobId}/status`),
  
  getFlowStatus: (flowId: string) =>
    fetchAPI<{ success: boolean; data: any }>(`/status/flow/${flowId}/status`),
  
  getScores: (params?: { jobId?: string; resumeId?: string }) => {
    const queryParams = new URLSearchParams();
    if (params?.jobId) queryParams.append('job_id', params.jobId);
    if (params?.resumeId) queryParams.append('resume_id', params.resumeId);
    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';
    
    return fetchAPI<{ success: boolean; data: any[]; count: number }>(`/scores${queryString}`);
  },
  
  getScoresByJob: (jobId: string) =>
    fetchAPI<{ 
      success: boolean; 
      data: {
        _id: string;
        job_id: string;
        resume_id: {
          _id: string;
          filename: string;
          candidate_name?: string;
        };
        project_score: number;
        keyword_score: number;
        semantic_score: number;
        final_score: number;
        recalculated_llm_score: number;
        hard_requirements_met: boolean;
        rank?: number;
        adjusted_score?: number;
        score_breakdown?: any;
        createdAt: string;
        updatedAt: string;
      }[]; 
      count: number;
    }>(`/scores/job/${jobId}`),
  
  getRankings: (jobId: string) =>
    fetchAPI<any[]>(`/jobs/${jobId}/rankings`),
};

// Queue API
export const queueAPI = {
  getStats: () =>
    fetchAPI<{ success: boolean; stats: any }>('/queue/stats'),
  
  pause: (queueName: string) =>
    fetchAPI<{ success: boolean; message: string }>(`/queue/${queueName}/pause`, { method: 'POST' }),
  
  resume: (queueName: string) =>
    fetchAPI<{ success: boolean; message: string }>(`/queue/${queueName}/resume`, { method: 'POST' }),
};

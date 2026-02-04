// Job Data Types for BullMQ

export interface JDProcessingJobData {
  jobId: string;
}

export interface ResumeProcessingJobData {
  resumeId: string;
  jobId: string;
  resumeGroupId: string;
  fileName: string;
  filePath: string;
  fileContent?: string;
}

// Resume Group Flow Job (Parent Job)
export interface ResumeGroupFlowJobData {
  jobId: string;
  resumeGroupId: string;
  totalResumes: number;
}

export interface ScoringJobData {
  resumeId: string;
  jobId: string;
  resumeGroupId: string;
  scoringType: 'keyword' | 'semantic' | 'project' | 'final';
  parsedResume?: any;
  jobRequirements?: any;
}

export interface RankingJobData {
  jobId: string;
  resumeGroupId: string;
  scoreResults: string[]; // Array of scoreResult IDs
  batchIndex?: number; // Which batch this is (1, 2, 3...)
  totalBatches?: number; // Total number of batches
  rankingCriteria?: {
    // Legacy weights for compatibility
    weightKeyword?: number;
    weightSemantic?: number; 
    weightProject?: number;
    requireHardRequirements?: boolean;
    // New LLM re-ranking criteria
    enable_llm_rerank?: boolean;
    filter_requirements?: {
      structured?: any;
    };
    specified_fields?: string[];
  };
}

// Ranking Flow Job (Parent Job)
export interface RankingFlowJobData {
  jobId: string;
  totalScores: number;
  totalBatches: number;
}

// Job Status Types
export type JobStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'cancelled';

// Job Result Types
export interface JobResult {
  success: boolean;
  message: string;
  data?: any;
  error?: string;
  processingTime?: number;
}
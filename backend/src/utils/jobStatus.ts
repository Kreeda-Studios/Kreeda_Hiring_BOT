/**
 * Job Status Level Utilities
 * Provides level-based status checking to prevent operations when job is at higher processing levels
 */

export type JobStatus = 
  | 'draft' 
  | 'jd_processing_started' 
  | 'jd_processing_failed' 
  | 'jd_processing_completed' 
  | 'resume_processing_started' 
  | 'resume_processing_failed' 
  | 'resume_processing_completed' 
  | 'ranking_started' 
  | 'ranking_failed'
  | 'ranking_completed';

// Status levels - higher number means more advanced in the workflow
// Failed statuses stay at same level as started to block progression but allow retry
export const STATUS_LEVELS: Record<JobStatus, number> = {
  'draft': 0,
  'jd_processing_started': 1,
  'jd_processing_failed': 1, // Same level as started - blocks resume operations
  'jd_processing_completed': 2, // Only completed status allows resume operations
  'resume_processing_started': 3,
  'resume_processing_failed': 3, // Same level as started - blocks ranking
  'resume_processing_completed': 4, // Only completed status allows ranking
  'ranking_started': 5,
  'ranking_failed': 5, // Same level as started - allows retry
  'ranking_completed': 6
};

// Operation requirement type
interface OperationRequirement {
  maxLevel?: number;
  requiredLevel?: number;
  allowedStatuses?: JobStatus[];
  description: string;
}

// Operation requirements - what level is needed for each operation
export const OPERATION_REQUIREMENTS: Record<string, OperationRequirement> = {
  // Can upload JD until JD processing completes successfully
  JD_UPLOAD: { maxLevel: 1, description: 'JD upload' },
  
  // Can upload resumes only after JD completes successfully, before ranking starts
  RESUME_UPLOAD: { requiredLevel: 2, maxLevel: 3, description: 'Resume upload' },
  
  // Can update job details until JD processing starts (including after failure)
  JOB_UPDATE: { maxLevel: 0, description: 'Job update' },
  
  // Can delete job until JD processing completes successfully
  JOB_DELETE: { maxLevel: 1, description: 'Job deletion' },
  
  // Can process JD if draft or failed (retry allowed)
  JD_PROCESSING: { maxLevel: 1, allowedStatuses: ['draft', 'jd_processing_failed'], description: 'JD processing' },
  
  // Can process resumes only if JD completed successfully, and resume not started/failed can retry
  RESUME_PROCESSING: { requiredLevel: 2, maxLevel: 3, allowedStatuses: ['jd_processing_completed', 'resume_processing_failed'], description: 'Resume processing' },
  
  // Can start ranking only if resumes completed successfully
  RANKING: { requiredLevel: 4, maxLevel: 4, allowedStatuses: ['resume_processing_completed'], description: 'Ranking' }
};

/**
 * Check if an operation is allowed based on current job status
 */
export function isOperationAllowed(
  currentStatus: JobStatus, 
  operation: keyof typeof OPERATION_REQUIREMENTS
): { allowed: boolean; reason?: string } {
  const currentLevel = STATUS_LEVELS[currentStatus];
  const requirement = OPERATION_REQUIREMENTS[operation];
  
  // Check specific allowed statuses first (for processing operations that allow retries)
  if (requirement.allowedStatuses) {
    if (!requirement.allowedStatuses.includes(currentStatus)) {
      return {
        allowed: false,
        reason: `${requirement.description} is not allowed in current status: ${currentStatus}. Allowed statuses: ${requirement.allowedStatuses.join(', ')}`
      };
    }
    return { allowed: true };
  }
  
  // Check if there's a required minimum level
  if (requirement.requiredLevel !== undefined && currentLevel < requirement.requiredLevel) {
    const requiredStatusExamples = Object.entries(STATUS_LEVELS)
      .filter(([_, level]) => level >= requirement.requiredLevel!)
      .map(([status]) => status)
      .slice(0, 2);
    
    return {
      allowed: false,
      reason: `${requirement.description} requires job to reach a successful completion stage first. Current: ${currentStatus}. Required: ${requiredStatusExamples.join(' or ')}`
    };
  }
  
  // Check if current level exceeds maximum allowed level
  if (requirement.maxLevel && currentLevel > requirement.maxLevel) {
    return {
      allowed: false,
      reason: `Cannot perform ${requirement.description} - job has progressed beyond this stage. Current: ${currentStatus}`
    };
  }
  
  return { allowed: true };
}

/**
 * Get the next logical status for a successful operation
 */
export function getNextStatus(currentStatus: JobStatus, operation: string): JobStatus {
  switch (operation) {
    case 'JD_PROCESSING_START':
      return 'jd_processing_started';
    case 'JD_PROCESSING_COMPLETE':
      return 'jd_processing_completed';
    case 'JD_PROCESSING_FAIL':
      return 'jd_processing_failed';
    case 'RESUME_PROCESSING_START':
      return 'resume_processing_started';
    case 'RESUME_PROCESSING_COMPLETE':
      return 'resume_processing_completed';
    case 'RESUME_PROCESSING_FAIL':
      return 'resume_processing_failed';
    case 'RANKING_START':
      return 'ranking_started';
    case 'RANKING_COMPLETE':
      return 'ranking_completed';
    case 'RANKING_FAIL':
      return 'ranking_failed';
    default:
      return currentStatus;
  }
}
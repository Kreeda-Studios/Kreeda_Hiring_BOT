// Design system constants for consistent styling across the platform

// ==================== STATUS COLORS ====================

export const JOB_STATUS_CONFIG = {
  draft: {
    label: "Draft",
    color: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300",
    icon: "circle",
  },
  active: {
    label: "Active",
    color: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
    icon: "loader",
  },
  completed: {
    label: "Completed",
    color: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    icon: "check-circle",
  },
  archived: {
    label: "Archived",
    color: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
    icon: "file-check",
  },
} as const;

export const RESUME_STATUS_CONFIG = {
  pending: {
    label: "Pending",
    color: "bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
  },
  processing: {
    label: "Processing",
    color: "bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300",
  },
  complete: {
    label: "Complete",
    color: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
  },
  failed: {
    label: "Failed",
    color: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
  },
} as const;

// ==================== SCORE COLORS ====================

export const getScoreColor = (score: number): string => {
  if (score >= 0.8) return "text-green-600 dark:text-green-400";
  if (score >= 0.6) return "text-emerald-600 dark:text-emerald-400";
  if (score >= 0.4) return "text-amber-600 dark:text-amber-400";
  if (score >= 0.2) return "text-orange-600 dark:text-orange-400";
  return "text-red-600 dark:text-red-400";
};

export const getScoreBgColor = (score: number): string => {
  if (score >= 0.8) return "bg-green-500";
  if (score >= 0.6) return "bg-emerald-500";
  if (score >= 0.4) return "bg-amber-500";
  if (score >= 0.2) return "bg-orange-500";
  return "bg-red-500";
};

// ==================== COMPLIANCE COLORS ====================

export const COMPLIANCE_CONFIG = {
  full: {
    label: "All Requirements Met",
    color: "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300",
    icon: "check-circle",
  },
  partial: {
    label: "Partial Compliance",
    color: "bg-amber-100 text-amber-700 dark:bg-amber-900 dark:text-amber-300",
    icon: "alert-circle",
  },
  none: {
    label: "Requirements Missing",
    color: "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300",
    icon: "x-circle",
  },
} as const;

// ==================== LAYOUT CONSTANTS ====================

export const SIDEBAR_WIDTH = 280;
export const SIDEBAR_WIDTH_COLLAPSED = 68;
export const HEADER_HEIGHT = 64;
export const PAGE_PADDING = 24;

// ==================== ANIMATION CONSTANTS ====================

export const TRANSITION_DEFAULT = "transition-all duration-200 ease-in-out";
export const TRANSITION_FAST = "transition-all duration-150 ease-in-out";
export const TRANSITION_SLOW = "transition-all duration-300 ease-in-out";

// ==================== UPLOAD CONSTANTS ====================

export const MAX_FILE_SIZE = 5 * 1024 * 1024; // 5MB per file
export const MAX_JD_FILE_SIZE = 10 * 1024 * 1024; // 10MB for JD
export const BATCH_SIZE = 20; // Files per batch
export const ALLOWED_FILE_TYPES = ["application/pdf"];

export const UPLOAD_LIMITS = {
  MAX_FILE_SIZE_MB: 5,
  MAX_FILES_PER_BATCH: 20,
  ALLOWED_TYPES: ["application/pdf"],
} as const;

export const RESUME_SOURCES = [
  { value: "upload", label: "Manual Upload" },
  { value: "email", label: "Email Import" },
  { value: "api", label: "API Integration" },
] as const;

export const SCORE_COLORS = {
  EXCELLENT: { threshold: 80, class: "bg-green-500/10 text-green-600" },
  GOOD: { threshold: 65, class: "bg-blue-500/10 text-blue-600" },
  AVERAGE: { threshold: 50, class: "bg-amber-500/10 text-amber-600" },
  POOR: { threshold: 0, class: "bg-red-500/10 text-red-600" },
} as const;

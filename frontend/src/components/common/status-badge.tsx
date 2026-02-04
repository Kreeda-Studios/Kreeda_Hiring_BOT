import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Circle,
  Loader2,
  FileCheck,
  BarChart3,
  CheckCircle2,
  XCircle,
  AlertCircle,
} from "lucide-react";
import type { JobStatus, ResumeStatus } from "@/lib/types";
import { JOB_STATUS_CONFIG, RESUME_STATUS_CONFIG } from "@/lib/constants";

interface JobStatusBadgeProps {
  status: JobStatus;
  className?: string;
}

const JobStatusIcons = {
  circle: Circle,
  loader: Loader2,
  "file-check": FileCheck,
  "bar-chart": BarChart3,
  "check-circle": CheckCircle2,
  "x-circle": XCircle,
} as const;

export function JobStatusBadge({ status, className }: JobStatusBadgeProps) {
  const config = JOB_STATUS_CONFIG[status as keyof typeof JOB_STATUS_CONFIG];
  const Icon = JobStatusIcons[config.icon as keyof typeof JobStatusIcons];

  return (
    <Badge
      variant="secondary"
      className={cn(config.color, "gap-1.5 font-medium", className)}
    >
      <Icon
        className={cn(
          "h-3.5 w-3.5",
          status === "active" && "animate-spin"
        )}
      />
      {config.label}
    </Badge>
  );
}

interface ResumeStatusBadgeProps {
  status: ResumeStatus;
  className?: string;
}

export function ResumeStatusBadge({ status, className }: ResumeStatusBadgeProps) {
  const config = RESUME_STATUS_CONFIG[status as keyof typeof RESUME_STATUS_CONFIG];

  return (
    <Badge
      variant="secondary"
      className={cn(config.color, "font-medium", className)}
    >
      {config.label}
    </Badge>
  );
}

interface ComplianceBadgePropsWithCount {
  met: number;
  total: number;
  isCompliant?: never;
  className?: string;
}

interface ComplianceBadgePropsWithBoolean {
  isCompliant: boolean;
  met?: never;
  total?: never;
  className?: string;
}

type ComplianceBadgeProps = ComplianceBadgePropsWithCount | ComplianceBadgePropsWithBoolean;

export function ComplianceBadge(props: ComplianceBadgeProps) {
  const { className } = props;
  
  let isCompliant: boolean;
  let label: string;
  
  if ('isCompliant' in props && props.isCompliant !== undefined) {
    isCompliant = props.isCompliant;
    label = isCompliant ? "Compliant" : "Non-Compliant";
  } else if ('met' in props && 'total' in props) {
    const percentage = props.total > 0 ? (props.met / props.total) * 100 : 0;
    isCompliant = percentage >= 100;
    label = `${props.met}/${props.total}`;
  } else {
    isCompliant = false;
    label = "Unknown";
  }
  
  const color = isCompliant
    ? "bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300"
    : "bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300";
  const Icon = isCompliant ? CheckCircle2 : XCircle;

  return (
    <Badge variant="secondary" className={cn(color, "gap-1.5 font-medium", className)}>
      <Icon className="h-3.5 w-3.5" />
      {label}
    </Badge>
  );
}

"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { EmptyState } from "@/components/common";
import { processingAPI, jobsAPI } from "@/lib/api";
import {
  Activity,
  CheckCircle2,
  Clock,
  Loader2,
  AlertCircle,
  FileText,
  Users,
  Trophy,
  RefreshCw,
} from "lucide-react";
import { Button } from "@/components/ui/button";

interface ProgressSectionProps {
  jobId: string;
}

interface ProcessingStatus {
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

interface ActivityLog {
  id: string;
  type: string;
  message: string;
  timestamp: string;
}

export function ProgressSection({ jobId }: ProgressSectionProps) {
  const [status, setStatus] = useState<ProcessingStatus | null>(null);
  const [job, setJob] = useState<any>(null);
  const [activityLog, setActivityLog] = useState<ActivityLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchStatus = async () => {
    try {
      const [statusRes, jobRes] = await Promise.all([
        processingAPI.getStatus(jobId),
        jobsAPI.getById(jobId),
      ]);

      if (statusRes.success) {
        setStatus(statusRes.data);
      }
      
      if (jobRes.success) {
        setJob(jobRes.data);
      }

      // Clear fake activity log since we don't have real event tracking yet
      setActivityLog([]);
    } catch (error) {
      console.error('Error fetching status:', error);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    fetchStatus();
    
    // Poll for updates every 10 seconds if processing
    const interval = setInterval(fetchStatus, 10000);
    return () => clearInterval(interval);
  }, [jobId]);

  const handleRefresh = () => {
    setRefreshing(true);
    fetchStatus();
  };

  // Calculate progress percentages
  const jdProgress = (status?.counts?.jd?.completed ?? 0) > 0 ? 100 : 
                     (status?.counts?.jd?.active ?? 0) > 0 ? 50 : 0;
  const resumeProgress = (status?.counts?.resumes?.total ?? 0) > 0 
    ? Math.round(((status?.counts?.resumes?.completed ?? 0) / (status?.counts?.resumes?.total ?? 1)) * 100)
    : 0;
  const rankingProgress = (status?.counts?.ranking?.total ?? 0) > 0
    ? Math.round(((status?.counts?.ranking?.completed ?? 0) / (status?.counts?.ranking?.total ?? 1)) * 100)
    : 0;
    
  const overallProgress = Math.round((jdProgress + resumeProgress + rankingProgress) / 3);

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin mr-2" />
          <span>Loading progress...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Overall Progress */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Activity className="h-5 w-5" />
                Processing Progress
              </CardTitle>
              <CardDescription>
                Overall progress: {overallProgress}% complete
              </CardDescription>
            </div>
            <Button 
              variant="outline" 
              size="sm"
              onClick={handleRefresh}
              disabled={refreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          <Progress value={overallProgress} className="h-2" />
          
          {/* Stage Progress */}
          <div className="grid gap-4 md:grid-cols-3">
            {/* JD Processing */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium flex items-center gap-2">
                  <FileText className="h-4 w-4" />
                  JD Processing
                </span>
                <Badge variant={jdProgress === 100 ? "default" : "secondary"}>
                  {jdProgress === 100 ? "Complete" : "Pending"}
                </Badge>
              </div>
              <Progress value={jdProgress} className="h-1" />
            </div>
            
            {/* Resume Processing */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium flex items-center gap-2">
                  <Users className="h-4 w-4" />
                  Resume Processing
                </span>
                <Badge variant={resumeProgress === 100 ? "default" : resumeProgress > 0 ? "outline" : "secondary"}>
                  {resumeProgress === 100 ? "Complete" : resumeProgress > 0 ? "Processing" : "Pending"}
                </Badge>
              </div>
              <Progress value={resumeProgress} className="h-1" />
              {status && (status.counts?.resumes?.total ?? 0) > 0 && (
                <p className="text-xs text-muted-foreground">
                  {status.counts.resumes.completed}/{status.counts.resumes.total} completed
                </p>
              )}
            </div>
            
            {/* Ranking */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium flex items-center gap-2">
                  <Trophy className="h-4 w-4" />
                  Ranking
                </span>
                <Badge variant={rankingProgress === 100 ? "default" : rankingProgress > 0 ? "outline" : "secondary"}>
                  {rankingProgress === 100 ? "Complete" : rankingProgress > 0 ? "Processing" : "Pending"}
                </Badge>
              </div>
              <Progress value={rankingProgress} className="h-1" />
              {status && (status.counts?.ranking?.total ?? 0) > 0 && (
                <p className="text-xs text-muted-foreground">
                  {status.counts.ranking.completed}/{status.counts.ranking.total} completed
                </p>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Activity Log */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Activity Log</CardTitle>
          <CardDescription>Recent processing events</CardDescription>
        </CardHeader>
        <CardContent>
          {activityLog.length === 0 ? (
            <EmptyState
              icon={<Activity className="h-6 w-6" />}
              title="No recent activity"
              description="Processing events and logs will be tracked here in future updates."
            />
          ) : (
            <div className="space-y-4">
              {activityLog.map((log) => (
                <div key={log.id} className="flex gap-3">
                  <div className="shrink-0 mt-1">
                    <ActivityIcon type={log.type} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">{log.message}</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(log.timestamp).toLocaleString()}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function ActivityIcon({ type }: { type: string }) {
  switch (type) {
    case "jd_complete":
      return (
        <div className="rounded-full bg-green-500/10 p-1.5">
          <FileText className="h-3 w-3 text-green-500" />
        </div>
      );
    case "resume_batch":
      return (
        <div className="rounded-full bg-blue-500/10 p-1.5">
          <Loader2 className="h-3 w-3 text-blue-500" />
        </div>
      );
    case "resume_complete":
      return (
        <div className="rounded-full bg-green-500/10 p-1.5">
          <CheckCircle2 className="h-3 w-3 text-green-500" />
        </div>
      );
    case "ranking_start":
      return (
        <div className="rounded-full bg-purple-500/10 p-1.5">
          <Trophy className="h-3 w-3 text-purple-500" />
        </div>
      );
    default:
      return (
        <div className="rounded-full bg-muted p-1.5">
          <Activity className="h-3 w-3 text-muted-foreground" />
        </div>
      );
  }
}

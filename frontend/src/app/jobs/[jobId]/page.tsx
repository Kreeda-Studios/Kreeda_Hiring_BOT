"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { PageContainer, JobStatusBadge, EmptyState } from "@/components/common";
import {
  ArrowLeft,
  FileText,
  Users,
  Activity,
  Trophy,
  Settings,
  MoreVertical,
  Loader2,
  Play,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { Job } from "@/lib/types";
import { JDSection } from "./components/jd-section";
import { ResumesSection } from "./components/resumes-section";
import { ProgressSection } from "./components/progress-section";
import { ResultsSection } from "./components/results-section";
import { jobsAPI } from "@/lib/api";

interface JobDetailPageProps {
  params: Promise<{ jobId: string }>;
}

export default function JobDetailPage({ params }: JobDetailPageProps) {
  const { jobId } = use(params);
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("jd");

  useEffect(() => {
    async function fetchJob() {
      try {
        setLoading(true);
        const response = await jobsAPI.getById(jobId);
        if (response.success) {
          setJob(response.data);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load job");
      } finally {
        setLoading(false);
      }
    }
    fetchJob();
  }, [jobId]);

  if (loading) {
    return (
      <PageContainer>
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </PageContainer>
    );
  }

  if (error || !job) {
    return (
      <PageContainer>
        <EmptyState
          icon={<FileText className="h-8 w-8" />}
          title="Job not found"
          description={error || "The job you're looking for doesn't exist."}
          action={
            <Button asChild>
              <Link href="/jobs">Back to Jobs</Link>
            </Button>
          }
        />
      </PageContainer>
    );
  }



  return (
    <PageContainer>
      {/* Back button */}
      <div className="mb-6">
        <Button variant="ghost" size="sm" asChild>
          <Link href="/jobs">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Jobs
          </Link>
        </Button>
      </div>

      {/* Job Header */}
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4 mb-8">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold tracking-tight">{job.title}</h1>
            <JobStatusBadge status={job.status} />
          </div>
          {job.description && (
            <p className="text-muted-foreground max-w-2xl">{job.description}</p>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Process Button */}
          <Button asChild>
            <Link href={`/jobs/${jobId}/process`}>
              <Play className="h-4 w-4 mr-2" />
              Start Processing
            </Link>
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem className="text-destructive">
                Delete Job
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-3 lg:w-auto lg:inline-grid">
          <TabsTrigger value="jd" className="gap-2">
            <FileText className="h-4 w-4" />
            <span className="hidden sm:inline">Job Description</span>
            <span className="sm:hidden">JD</span>
          </TabsTrigger>
          <TabsTrigger value="resumes" className="gap-2">
            <Users className="h-4 w-4" />
            <span className="hidden sm:inline">Resumes</span>
            <span className="sm:hidden">Resumes</span>
          </TabsTrigger>
          {/* <TabsTrigger value="progress" className="gap-2">
            <Activity className="h-4 w-4" />
            <span className="hidden sm:inline">Progress</span>
            <span className="sm:hidden">Progress</span>
          </TabsTrigger> */}
          <TabsTrigger value="results" className="gap-2">
            <Trophy className="h-4 w-4" />
            <span className="hidden sm:inline">Results</span>
            <span className="sm:hidden">Results</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="jd">
          <JDSection job={job} jobId={jobId} onJobUpdate={setJob} />
        </TabsContent>

        <TabsContent value="resumes">
          <ResumesSection jobId={jobId} />
        </TabsContent>
{/* 
        <TabsContent value="progress">
          <ProgressSection jobId={jobId} />
        </TabsContent> */}

        <TabsContent value="results">
          <ResultsSection jobId={jobId} />
        </TabsContent>
      </Tabs>
    </PageContainer>
  );
}

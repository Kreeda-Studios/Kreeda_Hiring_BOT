"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
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
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
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
  const router = useRouter();
  const { jobId } = use(params);
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("jd");
  const [deleting, setDeleting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);

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

  const handleDeleteJob = async () => {
    if (deleting) return;

    try {
      setDeleting(true);
      await jobsAPI.delete(jobId);
      setShowDeleteDialog(false);
      router.push("/jobs");
      router.refresh();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to delete job";
      setError(message);
      window.alert(message);
    } finally {
      setDeleting(false);
    }
  };

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
            <Button asChild className="cursor-pointer">
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
        <Button variant="ghost" size="sm" asChild className="px-0 cursor-pointer h-auto py-1 -mx-2">
          <Link href="/jobs" className="flex items-center gap-2">
            <ArrowLeft className="h-4 w-4" />
            <span>Back to Jobs</span>
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
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon" className="cursor-pointer">
                <MoreVertical className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                className="text-destructive cursor-pointer"
                onClick={() => {
                  setShowDeleteDialog(true);
                }}
                onSelect={() => {
                  setShowDeleteDialog(true);
                }}
                disabled={deleting}
              >
                {deleting ? "Deleting..." : "Delete Job"}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid w-full grid-cols-3 lg:w-auto lg:inline-grid">
          <TabsTrigger value="jd" className="gap-2 cursor-pointer">
            <FileText className="h-4 w-4" />
            <span className="hidden sm:inline">Job Description</span>
            <span className="sm:hidden">JD</span>
          </TabsTrigger>
          <TabsTrigger value="resumes" className="gap-2 cursor-pointer">
            <Users className="h-4 w-4" />
            <span className="hidden sm:inline">Resumes</span>
            <span className="sm:hidden">Resumes</span>
          </TabsTrigger>
          <TabsTrigger value="results" className="gap-2 cursor-pointer">
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

        <TabsContent value="results">
          <ResultsSection jobId={jobId} />
        </TabsContent>
      </Tabs>

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete This Job?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete this job, all related resumes, all scores, and stored files. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting} className="cursor-pointer">Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                void handleDeleteJob();
              }}
              className="bg-destructive hover:bg-destructive/90 cursor-pointer"
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete Job"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageContainer>
  );
}

"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import { PageContainer, JobStatusBadge, EmptyState } from "@/components/common";
import { Briefcase, Plus, Search, Loader2, Trash2 } from "lucide-react";
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
import { jobsAPI } from "@/lib/api";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedJobs, setSelectedJobs] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [deleting, setDeleting] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const JOBS_PER_PAGE = 12;

  useEffect(() => {
    async function fetchJobs() {
      try {
        setLoading(true);
        const response = await jobsAPI.getAll();
        if (response.success) {
          setJobs(response.data);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load jobs");
      } finally {
        setLoading(false);
      }
    }
    fetchJobs();
  }, []);

  const filteredJobs = jobs.filter((job) => {
    return (
      job.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      job.description?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  });

  // Pagination
  const totalPages = Math.ceil(filteredJobs.length / JOBS_PER_PAGE);
  const startIdx = (currentPage - 1) * JOBS_PER_PAGE;
  const paginatedJobs = filteredJobs.slice(startIdx, startIdx + JOBS_PER_PAGE);

  // Selection handlers
  const toggleSelectJob = (jobId: string) => {
    const newSelected = new Set(selectedJobs);
    if (newSelected.has(jobId)) {
      newSelected.delete(jobId);
    } else {
      newSelected.add(jobId);
    }
    setSelectedJobs(newSelected);
  };

  const toggleSelectAll = () => {
    if (selectedJobs.size === paginatedJobs.length && paginatedJobs.length > 0) {
      setSelectedJobs(new Set());
    } else {
      setSelectedJobs(new Set(paginatedJobs.map(j => j._id)));
    }
  };

  const handleDeleteSelected = async () => {
    if (selectedJobs.size === 0) {
      return;
    }

    setDeleting(true);
    try {
      for (const jobId of selectedJobs) {
        await jobsAPI.delete(jobId);
      }
      
      // Remove deleted jobs from state
      setJobs(jobs.filter(j => !selectedJobs.has(j._id)));
      setSelectedJobs(new Set());
      setShowDeleteDialog(false);
      
      // Reset to first page if current page is empty
      if (currentPage > totalPages) {
        setCurrentPage(Math.max(1, totalPages));
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      alert(`Failed to delete jobs: ${message}`);
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

  if (error) {
    return (
      <PageContainer>
        <EmptyState
          icon={<Briefcase className="h-8 w-8" />}
          title="Failed to load jobs"
          description={error}
          action={
            <Button onClick={() => window.location.reload()} className="cursor-pointer">
              Try again
            </Button>
          }
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      {/* Search Bar - Top Row */}
      <div className="flex justify-center mb-4">
        <div className="w-full max-w-sm">
          {/* <label classNam e="text-sm font-medium text-muted-foreground mb-2 block text-center">Search</label> */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search jobs..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setCurrentPage(1); // Reset to first page on search
              }}
              className="pl-9"
            />
          </div>
        </div>
      </div>

      {/* Actions - Bottom Row */}
      <div className="flex gap-2 mb-6 items-center justify-between">
        <div>
          {selectedJobs.size > 0 && (
            <Button 
              variant="destructive" 
              size="sm"
              onClick={() => setShowDeleteDialog(true)}
              disabled={deleting}
              className="cursor-pointer"
            >
              <Trash2 className="h-4 w-4 mr-2" />
              {deleting ? "Deleting..." : `Delete Selected (${selectedJobs.size})`}
            </Button>
          )}
        </div>

        <Button asChild className="cursor-pointer">
          <Link href="/jobs/new">
            <Plus className="mr-2 h-4 w-4" />
            Create New Job
          </Link>
        </Button>
      </div>

      {/* Jobs List */}
      {filteredJobs.length === 0 ? (
        <div className="flex justify-between items-center py-12 border rounded-lg px-6">
          <div className="flex flex-col gap-2">
            <h2 className="text-2xl font-bold">{searchQuery ? "No matching jobs" : "No jobs yet"}</h2>
            <p className="text-muted-foreground">
              {searchQuery
                ? "Try adjusting your search criteria."
                : "Create your first job to start screening resumes with AI."}
            </p>
          </div>
          <Button asChild className="cursor-pointer flex-shrink-0">
            <Link href="/jobs/new">
              <Plus className=" h-4 w-4" />
              Create New Job
            </Link>
          </Button>
        </div>
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 mb-6">
            {paginatedJobs.map((job) => (
              <JobCard 
                key={job._id} 
                job={job} 
                isSelected={selectedJobs.has(job._id)}
                onSelect={() => toggleSelectJob(job._id)}
              />
            ))}
          </div>

          {/* Pagination - Always show */}
          <div className="flex items-center justify-center gap-2 mt-6">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="cursor-pointer"
            >
              Previous
            </Button>
            
            <div className="flex items-center gap-1">
              {Array.from({ length: totalPages }, (_, i) => i + 1).map(page => (
                <Button
                  key={page}
                  variant={currentPage === page ? "default" : "outline"}
                  size="sm"
                  onClick={() => setCurrentPage(page)}
                  className="cursor-pointer"
                >
                  {page}
                </Button>
              ))}
            </div>
            
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="cursor-pointer"
            >
              Next
            </Button>
          </div>
        </>
      )}

      <AlertDialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Selected Jobs?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete {selectedJobs.size} job(s), all related resumes, all scores, and stored files. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={deleting} className="cursor-pointer">
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                void handleDeleteSelected();
              }}
              className="bg-destructive hover:bg-destructive/90 cursor-pointer"
              disabled={deleting}
            >
              {deleting ? "Deleting..." : "Delete Jobs"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </PageContainer>
  );
}

interface JobCardProps {
  job: Job;
  isSelected: boolean;
  onSelect: () => void;
}

function JobCard({ job, isSelected, onSelect }: JobCardProps) {
  return (
    <Card className="hover:border-primary/50 transition-colors flex flex-col py-2 min-h-32 gap-1">
      {/* Top Row: Checkbox and Status Badge */}
      <div className="flex items-center justify-between px-3 gap-2">
        <Checkbox
          checked={isSelected}
          onCheckedChange={onSelect}
          className="cursor-pointer flex-shrink-0"
        />
        <div className="flex-1" />
        <JobStatusBadge status={job.status} />
      </div>

      {/* Content: Title and Description */}
      <Link href={`/jobs/${job._id}`} className="flex-1 cursor-pointer px-3 gap-1 min-w-0 flex flex-col justify-start">
        <CardTitle className="text-base font-semibold truncate w-full">
          {job.title.charAt(0).toUpperCase() + job.title.slice(1)}
        </CardTitle>
        <p className="text-sm text-muted-foreground line-clamp-2 w-full break-words whitespace-normal">
          {job.description ? job.description.charAt(0).toUpperCase() + job.description.slice(1) : ''}
        </p>
      </Link>
    </Card>
  );
}

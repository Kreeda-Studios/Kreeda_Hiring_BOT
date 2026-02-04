"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PageHeader, PageContainer, JobStatusBadge, EmptyState } from "@/components/common";
import { Briefcase, Plus, Search, Loader2 } from "lucide-react";
import type { Job } from "@/lib/types";
import { jobsAPI } from "@/lib/api";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");

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
            <Button onClick={() => window.location.reload()}>
              Try again
            </Button>
          }
        />
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <PageHeader
        title="Jobs"
        description="Manage your hiring processes and view candidate pipelines."
      >
        <Button asChild>
          <Link href="/jobs/new">
            <Plus className="mr-2 h-4 w-4" />
            Create Job
          </Link>
        </Button>
      </PageHeader>

      {/* Search Bar Only */}
      <div className="flex flex-col sm:flex-row gap-4 mb-6">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search jobs..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Jobs List */}
      {filteredJobs.length === 0 ? (
        <EmptyState
          icon={<Briefcase className="h-8 w-8" />}
          title={searchQuery ? "No matching jobs" : "No jobs yet"}
          description={
            searchQuery
              ? "Try adjusting your search criteria."
              : "Create your first job to start screening resumes with AI."
          }
          action={
            <Button asChild>
              <Link href="/jobs/new">
                <Plus className="mr-2 h-4 w-4" />
                Create Job
              </Link>
            </Button>
          }
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredJobs.map((job) => (
            <JobCard key={job._id} job={job} />
          ))}
        </div>
      )}
    </PageContainer>
  );
}

interface JobCardProps {
  job: Job;
}

function JobCard({ job }: JobCardProps) {
  return (
    <Link href={`/jobs/${job._id}`}>
      <Card className="hover:border-primary/50 transition-colors h-full">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div className="space-y-1 min-w-0">
              <CardTitle className="text-base font-semibold truncate">
                {job.title}
              </CardTitle>
              {job.description && (
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {job.description}
                </p>
              )}
            </div>
            <JobStatusBadge status={job.status} />
          </div>
        </CardHeader>
      </Card>
    </Link>
  );
}

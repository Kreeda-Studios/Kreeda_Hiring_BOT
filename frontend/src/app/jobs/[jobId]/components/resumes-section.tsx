"use client";

import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { EmptyState, ResumeStatusBadge } from "@/components/common";
import {
  Users,
  Upload,
  FileText,
  Loader2,
  Play,
  AlertTriangle,
  CheckCircle2,
  FileUp,
} from "lucide-react";
import type { Resume, ResumeStatus } from "@/lib/types";
import { jobsAPI, resumesAPI, processingAPI } from "@/lib/api";
import { useJobStatus } from "@/hooks/useJobStatus";

interface ResumesSectionProps {
  jobId: string;
}

export function ResumesSection({ jobId }: ResumesSectionProps) {
  // Use status hook for real-time tracking
  const { 
    statusData, 
    isResumeProcessingInProgress, 
    canUploadResumes, 
    canStartResumeProcessing, 
    refetch: refetchStatus 
  } = useJobStatus(jobId);
  
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchResumes();
  }, [jobId]);

  // Update processing state based on status
  useEffect(() => {
    const processingState = isResumeProcessingInProgress();
    setProcessing(processingState);
  }, [isResumeProcessingInProgress]);

  const fetchResumes = async () => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('📂 [Resumes] Fetching resumes for job:', jobId);
      const resumesRes = await resumesAPI.getByJob(jobId);
      if (resumesRes.success) {
        setResumes(resumesRes.data);
        console.log('📂 [Resumes] Loaded resumes:', resumesRes.data.length);
      } else {
        setError("Failed to load resumes. Please try again.");
      }
    } catch (error) {
      console.error("Failed to load resume data:", error);
      setError("Failed to load resume data. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    // Check if upload is allowed
    if (!canUploadResumes()) {
      setError("Cannot upload resumes while resume processing is in progress. Please wait for current processing to complete.");
      return;
    }

    // Filter for PDF files only
    const pdfFiles = Array.from(files).filter(file => file.type === 'application/pdf');
    
    if (pdfFiles.length === 0) {
      setError("Please select PDF files only.");
      return;
    }

    if (pdfFiles.length !== files.length) {
      setError(`Only PDF files are allowed. ${pdfFiles.length} valid PDF files selected, ${files.length - pdfFiles.length} files skipped.`);
    }

    // Show info for large uploads
    if (pdfFiles.length > 50) {
      console.log(`📤 [Bulk Upload] Processing ${pdfFiles.length} resumes - this may take a moment...`);
    }

    setUploading(true);
    setError(null);
    setUploadSuccess(null);

    try {
      console.log('📤 [Upload] Uploading to job ID:', jobId);
      const response = await jobsAPI.uploadResumes(jobId, pdfFiles);
      
      if (response.success) {
        const uploadCount = pdfFiles.length;
        if (uploadCount > 100) {
          setUploadSuccess(`🎉 Successfully uploaded ${uploadCount} resumes! Large batch processing initiated.`);
        } else {
          setUploadSuccess(`Successfully uploaded ${uploadCount} resume(s)`);
        }
        // Refresh the resume list and status
        await fetchResumes();
        refetchStatus();
      } else {
        setError(response.message || "Upload failed");
      }
    } catch (error) {
      console.error("Upload error:", error);
      setError(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleProcessResumes = async () => {
    if (resumes.length === 0) return;
    
    // Check if processing is allowed
    if (!canStartResumeProcessing()) {
      setError("Cannot start resume processing. Please ensure JD is processed first and no other processing is in progress.");
      return;
    }
    
    setProcessing(true);
    setError(null);
    
    try {
      const response = await processingAPI.processResumes(jobId);
      if (response.success) {
        console.log('Resume processing started:', response.message);
        // Refresh status to get updated processing state
        refetchStatus();
      } else {
        setError(response.message || "Failed to start processing");
      }
    } catch (error) {
      console.error("Failed to start resume processing:", error);
      setError(error instanceof Error ? error.message : "Failed to start processing");
    } finally {
      // Keep processing true while status is processing
      if (!isResumeProcessingInProgress()) {
        setProcessing(false);
      }
    }
  };

  const getResumeStatus = (resume: Resume): ResumeStatus => {
    if (resume.parsing_status === "complete") return "complete";
    if (resume.parsing_status === "failed" || resume.extraction_status === "failed") return "failed";
    if (resume.parsing_status === "processing" || resume.extraction_status === "processing") return "processing";
    return "pending";
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Error Display */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="h-4 w-4" />
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {/* Success Message */}
      {uploadSuccess && (
        <Alert className="border-green-200 bg-green-50">
          <CheckCircle2 className="h-4 w-4 text-green-600" />
          <AlertDescription className="text-green-700">{uploadSuccess}</AlertDescription>
        </Alert>
      )}

      {/* Upload & Management Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5" />
              Resume Management
            </div>
          </CardTitle>
          <CardDescription>
            Upload and manage resumes for this job
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
            {/* Upload Section */}
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div className="space-y-1">
                <h4 className="font-medium">Bulk Upload Resume PDFs</h4>
                <p className="text-sm text-muted-foreground">
                  Select multiple PDF files (supports hundreds at once)
                </p>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={uploading || !canUploadResumes()}
                >
                  {uploading ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <FileUp className="h-4 w-4 mr-2" />
                  )}
                  {uploading ? 'Uploading...' : 'Select PDFs'}
                </Button>
                {!canUploadResumes() && (
                  <p className="text-xs text-orange-600">
                    Upload locked during processing
                  </p>
                )}
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileUpload}
                  accept=".pdf"
                  multiple
                  className="hidden"
                />
              </div>
            </div>

            {/* Resume Stats */}
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold">{resumes.length}</div>
                <div className="text-sm text-muted-foreground">Total Resumes</div>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {resumes.filter(r => r.parsing_status === "complete").length}
                </div>
                <div className="text-sm text-muted-foreground">Processed</div>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold text-blue-600">
                  {resumes.filter(r => r.parsing_status === "pending" || r.extraction_status === "pending").length}
                </div>
                <div className="text-sm text-muted-foreground">Pending</div>
              </div>
            </div>

            {/* Process Button */}
            {resumes.length > 0 && (
              <div className="space-y-3 pt-4 border-t">
                <div className="flex justify-center">
                  <Button
                    onClick={handleProcessResumes}
                    disabled={!canStartResumeProcessing() || processing}
                    className="w-full max-w-md"
                    size="lg"
                  >
                    {processing ? (
                      <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                    ) : (
                      <Play className="mr-2 h-5 w-5" />
                    )}
                    {processing ? 'Processing Resumes...' : 'Start Resume Processing'}
                  </Button>
                </div>
                
                {/* Status Messages */}
                {statusData && (
                  <div className="text-center space-y-1">
                    {statusData.job.jd_processing.status !== 'success' && (
                      <p className="text-xs text-orange-600">
                        ⚠️ JD must be processed before resume processing can start
                      </p>
                    )}
                    {statusData.job.resume_processing.status === 'processing' && (
                      <p className="text-xs text-blue-600">
                        🔄 Processing {statusData.job.resume_processing.completed_count} / {statusData.job.resume_processing.total_resumes} resumes 
                        ({statusData.job.resume_processing.progress}%)
                      </p>
                    )}
                    {statusData.job.resume_processing.status === 'success' && (
                      <p className="text-xs text-green-600">
                        ✅ All resumes processed successfully
                      </p>
                    )}
                    {statusData.job.resume_processing.status === 'failed' && (
                      <p className="text-xs text-red-600">
                        ❌ Resume processing failed: {statusData.job.resume_processing.error}
                      </p>
                    )}
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

      {/* Resumes List */}
      {resumes.length > 0 ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Uploaded Resumes ({resumes.length})
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Filename</TableHead>
                  <TableHead>Candidate</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Uploaded</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {resumes.map((resume) => (
                  <TableRow key={resume._id}>
                    <TableCell className="font-medium">
                      {resume.filename}
                    </TableCell>
                    <TableCell>
                      {resume.candidate_name || "Not extracted"}
                    </TableCell>
                    <TableCell>
                      <ResumeStatusBadge status={getResumeStatus(resume)} />
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {new Date(resume.createdAt).toLocaleDateString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      ) : (
        <EmptyState
          icon={<Users className="h-8 w-8" />}
          title="No resumes uploaded yet"
          description="Upload PDF resumes to get started with candidate evaluation"
          action={
            <Button
              onClick={() => fileInputRef.current?.click()}
              className="mt-4"
            >
              <Upload className="mr-2 h-4 w-4" />
              Upload First Resume
            </Button>
          }
        />
      )}
    </div>
  );
}
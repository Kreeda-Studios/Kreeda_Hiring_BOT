"use client";

import { useState, useEffect, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
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

  // Batch upload state
  const [uploadProgress, setUploadProgress] = useState<{
    currentBatch: number;
    totalBatches: number;
    uploadedCount: number;
    totalFiles: number;
    failedCount: number;
  } | null>(null);

  // Progress tracking - initialize with resume count
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingPhase, setProcessingPhase] = useState<string>('not_started');
  const [processingStats, setProcessingStats] = useState(() => ({ 
    total: resumes.length, 
    completed: 0, 
    failed: 0 
  }));
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchResumes();
  }, [jobId]);

  // Update processing state and progress based on status
  useEffect(() => {
    const processingState = isResumeProcessingInProgress();
    const currentStatus = statusData?.job.status;
    setProcessing(processingState);
    
    // Always update total with current resume count
    const currentTotal = resumes.length;
    
    // Set progress based on job status
    if (currentStatus === 'resume_processing_completed' || 
        currentStatus === 'ranking_started' ||
        currentStatus === 'ranking_completed') {
      // Resume processing already completed - show 100% and STOP all polling
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      setProcessingProgress(100);
      setProcessingStats({ 
        total: currentTotal, 
        completed: currentTotal, 
        failed: 0 
      });
    } else if (processingState) {
      // Currently processing - start polling ONLY if not already polling
      if (!progressIntervalRef.current) {
        fetchProgress();
        progressIntervalRef.current = setInterval(fetchProgress, 3000);
      }
    } else {
      // Not processing - STOP any polling and reset
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
        progressIntervalRef.current = null;
      }
      if (currentStatus === 'jd_processing_completed' || currentStatus === 'draft') {
        setProcessingProgress(0);
        setProcessingStats({ total: currentTotal, completed: 0, failed: 0 });
      }
    }
  }, [isResumeProcessingInProgress, statusData?.job.status]);

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (progressIntervalRef.current) {
        clearInterval(progressIntervalRef.current);
      }
    };
  }, []);

  const fetchProgress = async () => {
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL!;
      const response = await fetch(`${API_BASE_URL}/progress/resumes/${jobId}`);
      const result = await response.json();
      
      if (result.success && result.data) {
        // Use overall_progress which combines resume (0-70%) and ranking (70-95%)
        setProcessingProgress(result.data.overall_progress || 0);
        setProcessingPhase(result.data.phase || 'not_started');
        
        // Use resume_stats for display
        const resumeStats = result.data.resume_stats || {};
        setProcessingStats({
          total: resumeStats.total || 0,
          completed: resumeStats.completed || 0,
          failed: resumeStats.failed || 0
        });
        
        // Check if fully completed (100%)
        const isCompleted = result.data.phase === 'completed' || result.data.overall_progress >= 100;
        
        if (isCompleted) {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          // Delay refresh slightly to ensure polling is fully stopped
          setTimeout(() => {
            refetchStatus(); // Refresh job status
            fetchResumes(); // Refresh resume list
          }, 500);
        }
      }
    } catch (error) {
      console.error('Failed to fetch resume progress:', error);
    }
  };

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

    setUploading(true);
    setError(null);
    setUploadSuccess(null);

    try {
      // Use chunked upload for better memory management
      const BATCH_SIZE = 5; // Upload 5 files at a time
      const batches: File[][] = [];
      
      // Split files into batches
      for (let i = 0; i < pdfFiles.length; i += BATCH_SIZE) {
        batches.push(pdfFiles.slice(i, i + BATCH_SIZE));
      }

      console.log(`📤 [Chunked Upload] Uploading ${pdfFiles.length} files in ${batches.length} batches`);

      let totalUploaded = 0;
      let totalFailed = 0;

      // Upload batches sequentially
      for (let i = 0; i < batches.length; i++) {
        const batch = batches[i];
        
        // Update progress
        setUploadProgress({
          currentBatch: i + 1,
          totalBatches: batches.length,
          uploadedCount: totalUploaded,
          totalFiles: pdfFiles.length,
          failedCount: totalFailed
        });

        try {
          console.log(`📤 [Batch ${i + 1}/${batches.length}] Uploading ${batch.length} files...`);
          const response = await jobsAPI.uploadResumes(jobId, batch);
          
          if (response.success) {
            totalUploaded += batch.length;
            console.log(`✅ [Batch ${i + 1}/${batches.length}] Success: ${batch.length} files uploaded`);
          } else {
            totalFailed += batch.length;
            console.error(`❌ [Batch ${i + 1}/${batches.length}] Failed:`, response);
          }
        } catch (batchError) {
          totalFailed += batch.length;
          console.error(`❌ [Batch ${i + 1}/${batches.length}] Error:`, batchError);
        }

        // Small delay between batches to prevent overwhelming the server
        if (i < batches.length - 1) {
          await new Promise(resolve => setTimeout(resolve, 500));
        }
      }

      // Final progress update
      setUploadProgress({
        currentBatch: batches.length,
        totalBatches: batches.length,
        uploadedCount: totalUploaded,
        totalFiles: pdfFiles.length,
        failedCount: totalFailed
      });

      // Show results
      if (totalFailed === 0) {
        setUploadSuccess(`🎉 Successfully uploaded all ${totalUploaded} resume(s)!`);
      } else if (totalUploaded > 0) {
        setUploadSuccess(`⚠️ Uploaded ${totalUploaded} resume(s), ${totalFailed} failed. Please retry failed files.`);
      } else {
        setError(`Failed to upload ${totalFailed} resume(s). Please try again.`);
      }

      // Refresh the resume list and status
      if (totalUploaded > 0) {
        await fetchResumes();
        refetchStatus();
      }
    } catch (error) {
      console.error("Upload error:", error);
      setError(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setUploading(false);
      setUploadProgress(null);
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
    // Check if resume was filtered out due to hard requirements
    if (resume.scores?.hard_requirements?.meets_all_requirements === false) {
      return "filtered";
    }
    
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

      {/* Upload Progress */}
      {uploadProgress && (
        <Card className="border-blue-500/50 bg-blue-50">
          <CardContent className="pt-6 space-y-3">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                <Loader2 className="h-5 w-5 animate-spin text-blue-600" />
                <span className="font-semibold text-base text-blue-900">
                  Uploading Resumes... (Batch {uploadProgress.currentBatch}/{uploadProgress.totalBatches})
                </span>
              </div>
              <span className="font-bold text-lg text-blue-900 tabular-nums">
                {uploadProgress.uploadedCount}/{uploadProgress.totalFiles}
              </span>
            </div>
            <Progress 
              value={(uploadProgress.uploadedCount / uploadProgress.totalFiles) * 100} 
              className="h-2.5" 
            />
            <div className="flex justify-between text-sm text-blue-800">
              <span>Current batch: {uploadProgress.currentBatch} of {uploadProgress.totalBatches}</span>
              <span>Uploaded: {uploadProgress.uploadedCount} | Failed: {uploadProgress.failedCount}</span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Resume Processing Progress Bar - Top Position */}
      {resumes.length > 0 && (
        <Card className={processingProgress === 100 ? 'border-green-500/50 bg-green-500/10' : processing ? 'border-primary/50 bg-primary/10' : 'border-muted'}>
          <CardContent className="pt-6 space-y-3">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                {processingProgress === 100 ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : processing ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : (
                  <FileText className="h-5 w-5 text-muted-foreground" />
                )}
                <span className="font-semibold text-base">
                  {processingProgress === 100 
                    ? 'All Processing Complete' 
                    : processingPhase === 'ranking' 
                    ? 'Ranking Candidates...' 
                    : processing 
                    ? 'Processing Resumes...' 
                    : 'Resume Processing Status'}
                </span>
                {processingPhase === 'ranking' && (
                  <Badge variant="outline" className="ml-2">Ranking Phase (70-95%)</Badge>
                )}
                {processingPhase === 'resume_processing' && (
                  <Badge variant="outline" className="ml-2">Resume Phase (0-70%)</Badge>
                )}
              </div>
              <span className="font-bold text-lg tabular-nums">{processingProgress}%</span>
            </div>
            <Progress value={processingProgress} className="h-2.5" />
            <div className="flex justify-between text-sm">
              <span className="text-muted-foreground">Total Resumes: <span className="font-medium text-foreground">{processingStats.total}</span></span>
              <span className="text-muted-foreground">Completed: <span className="font-medium text-green-500">{processingStats.completed}</span></span>
              <span className="text-muted-foreground">Failed: <span className="font-medium text-destructive">{processingStats.failed}</span></span>
            </div>
          </CardContent>
        </Card>
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
                  Select multiple PDF files - uploads in batches of 5 for optimal performance
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
            <div className="grid grid-cols-4 gap-4">
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold">{resumes.length}</div>
                <div className="text-sm text-muted-foreground">Total Resumes</div>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold text-green-600">
                  {resumes.filter(r => r.parsing_status === "complete" && r.scores?.hard_requirements?.meets_all_requirements !== false).length}
                </div>
                <div className="text-sm text-muted-foreground">Processed</div>
              </div>
              <div className="text-center p-3 bg-muted rounded-lg">
                <div className="text-2xl font-bold text-orange-600">
                  {resumes.filter(r => r.scores?.hard_requirements?.meets_all_requirements === false).length}
                </div>
                <div className="text-sm text-muted-foreground">Filtered Out</div>
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
                    {statusData.job.status !== 'jd_processing_completed' && (
                      <p className="text-xs text-orange-600">
                        ⚠️ JD must be processed before resume processing can start
                      </p>
                    )}
                    {statusData.job.status === 'resume_processing_started' && (
                      <p className="text-xs text-blue-600">
                        🔄 Processing resumes...
                      </p>
                    )}
                    {statusData.job.status === 'resume_processing_completed' && (
                      <p className="text-xs text-green-600">
                        ✅ All resumes processed successfully
                      </p>
                    )}
                    {statusData.job.status === 'resume_processing_failed' && (
                      <p className="text-xs text-red-600">
                        ❌ Resume processing failed. Please try again.
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
                      <div className="flex items-center gap-2">
                        <ResumeStatusBadge status={getResumeStatus(resume)} />
                        {resume.scores?.hard_requirements?.meets_all_requirements === false && (
                          <div className="group relative">
                            <AlertTriangle className="h-4 w-4 text-orange-500 cursor-help" />
                            <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 px-3 py-2 bg-black text-white text-xs rounded whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity z-10">
                              {resume.scores.hard_requirements.filter_reason || "Does not meet mandatory requirements"}
                              <div className="absolute top-full left-1/2 transform -translate-x-1/2 border-4 border-transparent border-t-black"></div>
                            </div>
                          </div>
                        )}
                      </div>
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
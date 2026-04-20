"use client";

import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { FileText, Loader2, CheckCircle2, FileUp, Play, AlertTriangle } from "lucide-react";
import type { Job } from "@/lib/types";
import { processingAPI, jobsAPI, resumeGroupsAPI } from "@/lib/api";
import { useJobStatus } from "@/hooks/useJobStatus";

interface ProgressUpdate {
  stage: string;
  percent: number;
  message: string;
  timestamp: string;
}

interface JDSectionProps {
  job: Job;
  jobId: string;
  onJobUpdate?: (updatedJob: Job) => void;
}

export function JDSection({ job, jobId, onJobUpdate }: JDSectionProps) {
  // Use status hook for real-time tracking
  const { statusData, isJDProcessingInProgress, canStartJDProcessing, refetch: refetchStatus } = useJobStatus(jobId);
  
  const [isLocked, setIsLocked] = useState(job.locked || false);
  const [showWarningDialog, setShowWarningDialog] = useState(false);

  const [jd_pdf_filename, setJdPdfFilename] = useState(job.jd_pdf_filename || "");
  const [jdText, setJdText] = useState(job.jd_text || "");
  const [mandatoryCompliances, setMandatoryCompliances] = useState(
    job.filter_requirements?.mandatory_compliances?.raw_prompt || ""
  );
  const [softCompliances, setSoftCompliances] = useState(
    job.filter_requirements?.soft_compliances?.raw_prompt || ""
  );

  const [isProcessing, setIsProcessing] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const hasJDPDF = !!job.jd_pdf_filename;
  const hasJDText = !!job.jd_text;

  // Progress tracking
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingMessage, setProcessingMessage] = useState("");
  const progressIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Update locked state when job or status changes
  useEffect(() => {
    const locked = job.locked || statusData?.job.locked || false;
    setIsLocked(locked);
  }, [job.locked, statusData?.job.locked]);

  // Update processing state and progress based on status
  useEffect(() => {
    const processing = isJDProcessingInProgress();
    const currentStatus = statusData?.job.status || job.status;
    setIsProcessing(processing);
    
    // Set progress based on job status
    if (currentStatus === 'jd_processing_completed' || 
        currentStatus === 'resume_processing_started' ||
        currentStatus === 'resume_processing_completed' ||
        currentStatus === 'resume_processing_failed' ||
        currentStatus === 'ranking_started' ||
        currentStatus === 'ranking_completed') {
      // JD already completed - show 100%
      setProcessingProgress(100);
      setProcessingMessage("JD Processing Complete");
    } else if (processing) {
      // Currently processing - start polling
      if (!progressIntervalRef.current) {
        fetchProgress();
        progressIntervalRef.current = setInterval(fetchProgress, 3000);
      }
    } else if (currentStatus === 'draft') {
      // Not started yet
      setProcessingProgress(0);
      setProcessingMessage("Ready to process");
    }
    
    // Stop polling when processing completes
    if (!processing && progressIntervalRef.current) {
      clearInterval(progressIntervalRef.current);
      progressIntervalRef.current = null;
    }
  }, [statusData?.job.status, job.status]);

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
      const response = await fetch(`${API_BASE_URL}/progress/jd/${jobId}`);
      const result = await response.json();
      
      if (result.success && result.data) {
        setProcessingProgress(result.data.progress || 0);
        setProcessingMessage(result.data.progress_details?.message || result.data.state || "Processing...");
        
        // If completed, stop polling
        if (result.data.state === 'completed' || result.data.state === 'failed') {
          if (progressIntervalRef.current) {
            clearInterval(progressIntervalRef.current);
            progressIntervalRef.current = null;
          }
          refetchStatus(); // Refresh job status
        }
      }
    } catch (error) {
      console.error('Failed to fetch JD progress:', error);
    }
  };

  // PDF upload handler
  const handlePDFUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    
    // Validation
    if (file.type !== 'application/pdf') {
      setUploadError('Please select a PDF file');
      setUploadSuccess(null);
      return;
    }
    
    // Clear previous messages
    setUploadError(null);
    setUploadSuccess(null);
    setIsUploading(true);
    
    try {
      const response = await jobsAPI.uploadJD(jobId, file);
      if (response.success && response.data.filename) {
        // Update local state with the uploaded filename
        const filename = response.data.filename;
        console.log('📄 [Upload] Setting filename in state:', filename);
        setJdPdfFilename(filename);
        setUploadSuccess(`PDF uploaded successfully: ${filename}`);
        setUploadError(null);
        
        // Update parent component if callback provided
        if (onJobUpdate) {
          const updatedJob = { ...job, jd_pdf_filename: filename };
          onJobUpdate(updatedJob);
        }
        
        // Clear success message after 5 seconds
        setTimeout(() => setUploadSuccess(null), 5000);
      }
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : 'Failed to upload PDF');
      setUploadSuccess(null);
    } finally {
      setIsUploading(false);
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  // Process JD handler: Show warning first
  const handleProcessClick = () => {
    if (isLocked) {
      console.warn('⚠️ [Process] Job is locked, cannot process');
      return;
    }
    console.log('⚠️ [Process] Showing warning dialog');
    setShowWarningDialog(true);
  };

  // Actual processing after confirmation
  const handleProcessConfirm = async () => {
    console.log('🚀 [Process] Starting JD processing...');
    setShowWarningDialog(false);
    setIsProcessing(true);
    setProcessingProgress(0); // Reset progress
    setProcessingMessage("Starting JD processing...");
    
    try {
      // Save JD and compliance data first
      console.log('💾 [Process] Saving JD data...');
      const updateResponse = await jobsAPI.update(jobId, {
        jd_pdf_filename,
        jd_text: jdText,
        mandatory_compliances: mandatoryCompliances,
        soft_compliances: softCompliances
      });
      if (!updateResponse.success) {
        throw new Error('Failed to save JD data before processing.');
      }
      console.log('✅ [Process] JD data saved successfully');
      
      // Create/replace resume group for this job
      console.log('📁 [Process] Creating resume group...');
      try {
        const resumeGroupResponse = await resumeGroupsAPI.create({
          name: `${job.title} - Resume Group`,
          job_ids: [jobId],
          source: 'upload'
        });
        if (resumeGroupResponse.success) {
          console.log('✅ [Process] Resume group created:', resumeGroupResponse.data._id);
          
          // Attach the resume group to the job using PATCH
          console.log('🔗 [Process] Attaching resume group to job...');
          try {
            const patchResponse = await fetch(`${process.env.NEXT_PUBLIC_API_URL!}/jobs/${jobId}`, {
              method: 'PATCH',
              headers: {
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                resume_groups: [resumeGroupResponse.data]
              })
            });
            
            if (patchResponse.ok) {
              console.log('✅ [Process] Resume group attached to job successfully');
            } else {
              console.warn('⚠️ [Process] Failed to attach resume group to job');
            }
          } catch (jobUpdateError) {
            console.warn('⚠️ [Process] Failed to attach resume group to job:', jobUpdateError);
          }
        }
      } catch (groupError) {
        console.warn('⚠️ [Process] Resume group creation failed, continuing with JD processing:', groupError);
      }
      
      // Now trigger JD processing
      console.log('⚙️ [Process] Triggering JD processing queue...');
      const processResponse = await processingAPI.processJD(jobId);
      if (!processResponse.success) {
        throw new Error(processResponse.message || 'Failed to start JD processing');
      }
      console.log('✅ [Process] JD processing queued:', processResponse.data);
      
      // Check if job is now locked
      if (processResponse.data.locked) {
        console.log('🔒 [Process] Job is now locked');
        setIsLocked(true);
      }
      
      // SSE subscription will handle the rest via useEffect
      
      // Refresh status after short delay to get updated BullMQ job ID
      setTimeout(() => {
        refetchStatus();
      }, 1000);
    } catch (error) {
      console.error('❌ [Process] Error:', error);
      setUploadError(error instanceof Error ? error.message : 'Failed to process JD');
      setIsProcessing(false);
      setProcessingProgress(0);
      setProcessingMessage("");
    }
  };

  return (
    <div className="space-y-6">
      {/* JD Processing Progress - Top Position */}
      {(hasJDPDF || hasJDText) && (
        <Card className={processingProgress === 100 ? 'border-green-500/50 bg-green-500/10' : isProcessing ? 'border-primary/50 bg-primary/10' : 'border-muted'}>
          <CardContent className="pt-6 space-y-3">
            <div className="flex justify-between items-center">
              <div className="flex items-center gap-2">
                {processingProgress === 100 ? (
                  <CheckCircle2 className="h-5 w-5 text-green-500" />
                ) : isProcessing ? (
                  <Loader2 className="h-5 w-5 animate-spin text-primary" />
                ) : (
                  <FileText className="h-5 w-5 text-muted-foreground" />
                )}
                <span className="font-semibold text-base">
                  {processingProgress === 100 ? 'JD Processing Complete' : isProcessing ? 'Processing Job Description' : 'JD Processing Status'}
                </span>
              </div>
              <span className="font-bold text-lg tabular-nums">{processingProgress}%</span>
            </div>
            <Progress value={processingProgress} className="h-2.5" />
            {processingMessage && (
              <p className="text-sm text-muted-foreground">{processingMessage}</p>
            )}
          </CardContent>
        </Card>
      )}

      {/* JD PDF Section */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Job Description PDF
                {job.status === 'active' && hasJDPDF && (
                  <Badge variant="secondary" className="bg-green-100 text-green-700">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Processed
                  </Badge>
                )}
              </CardTitle>
              <CardDescription>
                {jd_pdf_filename ? (
                  <span className="flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-600" />
                    <span className="font-medium text-green-700">PDF ready: {jd_pdf_filename}</span>
                  </span>
                ) : (
                  "Upload a PDF file for the job description."
                )}
              </CardDescription>
            </div>
            {!isLocked && (
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                >
                  {isUploading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <FileUp className="h-4 w-4" />
                  )}
                  {isUploading ? 'Uploading...' : 'Upload PDF'}
                </Button>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handlePDFUpload}
                  accept=".pdf"
                  className="hidden"
                />
              </div>
            )}
          </div>
          {uploadError && (
            <div className="flex items-center gap-2 text-red-600 text-sm mt-2 p-2 bg-red-50 rounded">
              <AlertTriangle className="h-4 w-4" />
              {uploadError}
            </div>
          )}
          {uploadSuccess && (
            <div className="flex items-center gap-2 text-green-600 text-sm mt-2 p-2 bg-green-50 rounded">
              <CheckCircle2 className="h-4 w-4" />
              {uploadSuccess}
            </div>
          )}
        </CardHeader>
      </Card>

      {/* JD Text Section - always editable, no edit button */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <FileText className="h-5 w-5" />
            Job Description Text
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="jd-text">Job Description Text</Label>
            <Textarea
              id="jd-text"
              placeholder="Paste the complete job description here..."
              value={jdText}
              onChange={e => !isLocked && setJdText(e.target.value)}
              rows={15}
              className="font-mono text-sm"
              disabled={isLocked}
            />
            <p className="text-xs text-muted-foreground">
              Include responsibilities, requirements, qualifications, and any other relevant details.
            </p>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle className="h-5 w-5" />
            Compliance Requirements
          </CardTitle>
          <CardDescription>
            Define mandatory and soft compliance requirements for candidate filtering
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col md:flex-row gap-6">
            <div className="flex-1 space-y-2">
              <Label htmlFor="mandatory-compliance">
                Mandatory Compliance Requirements
              </Label>
              <Textarea
                id="mandatory-compliance"
                placeholder="e.g., Must have Python, Machine Learning, minimum 3 years experience..."
                value={mandatoryCompliances}
                onChange={e => !isLocked && setMandatoryCompliances(e.target.value)}
                rows={4}
                className="resize-none"
                disabled={isLocked}
              />
              <p className="text-xs text-muted-foreground">
                Candidates must meet ALL mandatory requirements to pass initial screening.
              </p>
            </div>
            <div className="flex-1 space-y-2">
              <Label htmlFor="soft-compliance">
                Soft Compliance Requirements (Preferred)
              </Label>
              <Textarea
                id="soft-compliance"
                placeholder="e.g., Preferred skills: TensorFlow, PyTorch, AWS, Docker, Kubernetes..."
                value={softCompliances}
                onChange={e => !isLocked && setSoftCompliances(e.target.value)}
                rows={4}
                className="resize-none"
                disabled={isLocked}
              />
              <p className="text-xs text-muted-foreground">
                Nice-to-have requirements that improve candidate scoring but are not mandatory.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="pt-6">
          <Button
            onClick={handleProcessClick}
            disabled={!canStartJDProcessing() || (!jd_pdf_filename && !jdText) || isProcessing}
            className="w-full"
          >
            {isProcessing ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Play className="mr-2 h-4 w-4" />
            )}
            {isProcessing ? 'Processing JD...' : isLocked ? 'JD Processed' : 'Process JD'}
          </Button>
          
          {/* Status Messages */}
          {statusData?.job.status === 'jd_processing_completed' && (
            <p className="text-xs text-green-600 mt-2 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" />
              JD processing completed successfully. Job is now locked.
            </p>
          )}
          {statusData?.job.status === 'jd_processing_failed' && (
            <p className="text-xs text-red-600 mt-2 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              JD processing failed. Please try again.
            </p>
          )}
          {isLocked && statusData?.job.status === 'jd_processing_completed' && (
            <p className="text-xs text-orange-600 mt-2 flex items-center gap-1">
              <AlertTriangle className="h-3 w-3" />
              Job is locked. JD has been processed and cannot be modified.
            </p>
          )}
          {(!jd_pdf_filename && !jdText) && (
            <p className="text-xs text-muted-foreground mt-2 text-center">
              <span className="text-red-500 font-medium">Note:</span> Please upload a JD PDF or enter JD text before processing.
            </p>
          )}
        </CardContent>
      </Card>
      
      {/* Warning Dialog before processing */}
      <AlertDialog open={showWarningDialog} onOpenChange={setShowWarningDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
              Warning: Job Will Be Locked
            </AlertDialogTitle>
            <AlertDialogDescription className="space-y-3 text-left">
              <p>Once you start processing, this job will be <strong>locked</strong> and you will <strong>NOT</strong> be able to:</p>
              <ul className="list-disc list-inside space-y-1 ml-2">
                <li>Upload a different JD PDF</li>
                <li>Modify the JD text</li>
                <li>Change mandatory compliance requirements</li>
                <li>Change soft compliance requirements</li>
              </ul>
              <p className="font-semibold text-foreground mt-4">Are you sure you want to proceed with processing?</p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={handleProcessConfirm} className="bg-orange-600 hover:bg-orange-700">
              Yes, Process & Lock
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

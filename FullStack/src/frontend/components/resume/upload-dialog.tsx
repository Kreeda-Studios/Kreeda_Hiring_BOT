/**
 * Upload Dialog Component
 * Modal for uploading multiple resumes
 */

'use client';

import { useState, useRef } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/frontend/components/ui/dialog';
import { Button } from '@/frontend/components/ui/button';
import { Upload, X, FileText, Loader2 } from 'lucide-react';

interface UploadDialogProps {
  onUploadComplete: () => void;
}

interface FileWithProgress {
  file: File;
  progress: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export function UploadDialog({ onUploadComplete }: UploadDialogProps) {
  const [open, setOpen] = useState(false);
  const [files, setFiles] = useState<FileWithProgress[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (selectedFiles: FileList | null) => {
    if (!selectedFiles) return;

    const newFiles = Array.from(selectedFiles)
      .filter(file => 
        file.type === 'application/pdf' || 
        file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      )
      .map(file => ({
        file,
        progress: 'pending' as const,
      }));

    setFiles(prev => [...prev, ...newFiles]);
  };

  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const uploadFiles = async () => {
    for (let i = 0; i < files.length; i++) {
      if (files[i].progress !== 'pending') continue;

      // Update status to uploading
      setFiles(prev => prev.map((f, idx) => 
        idx === i ? { ...f, progress: 'uploading' as const } : f
      ));

      try {
        const formData = new FormData();
        formData.append('file', files[i].file);

        const response = await fetch('/api/resume/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error('Upload failed');
        }

        // Update status to success
        setFiles(prev => prev.map((f, idx) => 
          idx === i ? { ...f, progress: 'success' as const } : f
        ));

      } catch (error) {
        // Update status to error
        setFiles(prev => prev.map((f, idx) => 
          idx === i ? { 
            ...f, 
            progress: 'error' as const,
            error: error instanceof Error ? error.message : 'Upload failed'
          } : f
        ));
      }
    }

    // Wait a moment then close and notify
    setTimeout(() => {
      onUploadComplete();
      setFiles([]);
      setOpen(false);
    }, 1000);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const getStatusColor = (progress: FileWithProgress['progress']) => {
    switch (progress) {
      case 'uploading': return 'text-blue-500';
      case 'success': return 'text-green-500';
      case 'error': return 'text-red-500';
      default: return 'text-muted-foreground';
    }
  };

  const getStatusIcon = (progress: FileWithProgress['progress']) => {
    switch (progress) {
      case 'uploading': return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'success': return <FileText className="h-4 w-4" />;
      case 'error': return <X className="h-4 w-4" />;
      default: return <FileText className="h-4 w-4" />;
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Upload className="h-4 w-4 mr-2" />
          Upload Resumes
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Upload Resumes</DialogTitle>
          <DialogDescription>
            Select PDF or DOCX files to upload. Multiple files can be uploaded at once.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          {/* Drop Zone */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
              isDragging 
                ? 'border-primary bg-primary/5' 
                : 'border-muted hover:border-primary/50'
            }`}
          >
            <Upload className="h-8 w-8 mx-auto mb-4 text-muted-foreground" />
            <p className="text-sm text-muted-foreground mb-2">
              Drag and drop files here, or click to browse
            </p>
            <p className="text-xs text-muted-foreground">
              Supports PDF and DOCX files
            </p>
          </div>

          <input
            ref={fileInputRef}
            type="file"
            multiple
            accept=".pdf,.docx"
            onChange={(e) => handleFileSelect(e.target.files)}
            className="hidden"
          />

          {/* File List */}
          {files.length > 0 && (
            <div className="space-y-2 max-h-[300px] overflow-y-auto">
              {files.map((fileItem, index) => (
                <div
                  key={index}
                  className="flex items-center justify-between p-3 bg-muted/50 rounded-lg"
                >
                  <div className="flex items-center gap-3 flex-1 min-w-0">
                    <div className={getStatusColor(fileItem.progress)}>
                      {getStatusIcon(fileItem.progress)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">
                        {fileItem.file.name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {(fileItem.file.size / 1024 / 1024).toFixed(2)} MB
                      </p>
                      {fileItem.error && (
                        <p className="text-xs text-red-500">{fileItem.error}</p>
                      )}
                    </div>
                  </div>
                  {fileItem.progress === 'pending' && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(index)}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => {
                setFiles([]);
                setOpen(false);
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={uploadFiles}
              disabled={files.length === 0 || files.some(f => f.progress === 'uploading')}
            >
              {files.some(f => f.progress === 'uploading') ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                `Upload ${files.length} file${files.length !== 1 ? 's' : ''}`
              )}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

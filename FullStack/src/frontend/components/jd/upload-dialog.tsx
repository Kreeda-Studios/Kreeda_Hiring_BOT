/**
 * JD Upload Dialog Component
 * Modal for uploading a single Job Description PDF
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

interface JDUploadDialogProps {
  onUploadComplete: () => void;
}

interface FileWithProgress {
  file: File;
  progress: 'pending' | 'uploading' | 'success' | 'error';
  error?: string;
}

export function JDUploadDialog({ onUploadComplete }: JDUploadDialogProps) {
  const [open, setOpen] = useState(false);
  const [files, setFiles] = useState<FileWithProgress[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (selectedFiles: FileList | null) => {
    if (!selectedFiles) return;

    const newFiles = Array.from(selectedFiles)
      .filter(
        (file) =>
          file.type === 'application/pdf' ||
          file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      )
      .map((file) => ({ file, progress: 'pending' as const }));

    setFiles((prev) => [...prev, ...newFiles]);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
  };

  const uploadFiles = async () => {
    for (let i = 0; i < files.length; i++) {
      if (files[i].progress !== 'pending') continue;

      setFiles((prev) =>
        prev.map((f, idx) =>
          idx === i ? { ...f, progress: 'uploading' as const } : f
        )
      );

      try {
        const formData = new FormData();
        formData.append('file', files[i].file);

        const response = await fetch('/api/jd/upload', {
          method: 'POST',
          body: formData,
        });

        if (!response.ok) {
          throw new Error('Upload failed');
        }

        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i ? { ...f, progress: 'success' as const } : f
          )
        );
      } catch (error) {
        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i
              ? {
                  ...f,
                  progress: 'error' as const,
                  error: error instanceof Error ? error.message : 'Upload failed',
                }
              : f
          )
        );
      }
    }

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
      case 'success':   return 'text-green-500';
      case 'error':     return 'text-red-500';
      default:          return 'text-muted-foreground';
    }
  };

  const getStatusIcon = (progress: FileWithProgress['progress']) => {
    switch (progress) {
      case 'uploading': return <Loader2 className="h-4 w-4 animate-spin" />;
      case 'success':   return <FileText className="h-4 w-4" />;
      case 'error':     return <X className="h-4 w-4" />;
      default:          return <FileText className="h-4 w-4" />;
    }
  };

  const hasPending = files.some((f) => f.progress === 'pending');

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Upload className="h-4 w-4 mr-2" />
          Upload JD
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>Upload Job Description</DialogTitle>
          <DialogDescription>
            Select a PDF or DOCX file containing the job description to upload and process.
          </DialogDescription>
        </DialogHeader>

        {/* Drop Zone */}
        <div
          className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
            isDragging
              ? 'border-primary bg-primary/5'
              : 'border-muted-foreground/25 hover:border-primary/50'
          }`}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onClick={() => fileInputRef.current?.click()}
        >
          <Upload className="h-10 w-10 mx-auto mb-3 text-muted-foreground" />
          <p className="text-sm font-medium">
            Drag & drop or click to select a JD file
          </p>
          <p className="text-xs text-muted-foreground mt-1">PDF or DOCX</p>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.docx"
            multiple
            className="hidden"
            onChange={(e) => handleFileSelect(e.target.files)}
          />
        </div>

        {/* File List */}
        {files.length > 0 && (
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {files.map((item, index) => (
              <div
                key={index}
                className="flex items-center justify-between p-2 rounded-lg border bg-muted/30"
              >
                <div className={`flex items-center gap-2 flex-1 min-w-0 ${getStatusColor(item.progress)}`}>
                  {getStatusIcon(item.progress)}
                  <span className="text-sm truncate">{item.file.name}</span>
                </div>
                {item.progress === 'pending' && (
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0 ml-2 shrink-0"
                    onClick={(e) => { e.stopPropagation(); removeFile(index); }}
                  >
                    <X className="h-3 w-3" />
                  </Button>
                )}
                {item.error && (
                  <span className="text-xs text-red-500 ml-2">{item.error}</span>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <Button variant="outline" onClick={() => { setFiles([]); setOpen(false); }}>
            Cancel
          </Button>
          <Button onClick={uploadFiles} disabled={!hasPending}>
            Upload
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

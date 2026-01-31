'use client';

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Upload, FileText, CheckCircle, Loader2, X, AlertCircle, Mail, Video, Mic, MessageCircle, Briefcase } from "lucide-react";
import { useState, useCallback, useEffect } from "react";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/contexts/AuthContext";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

interface JobPosition {
  id: string;
  title: string;
  department?: string;
  is_active?: boolean;
}

interface UploadResult {
  success: boolean;
  message: string;
  candidates_created: number;
  interviews_scheduled: number;
  candidates: Array<{
    candidate_id: string;
    full_name: string;
    email: string;
    phone?: string;
    skills?: string[];
  }>;
  interviews: Array<{
    interview_id: string;
    candidate_id: string;
    candidate_name: string;
    candidate_email: string;
    status: string;
  }>;
  failed_files: string[];
}

const MAX_FILES = 10;
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const MAX_ZIP_SIZE = 50 * 1024 * 1024; // 50MB
const SUPPORTED_TYPES = ['.pdf', '.doc', '.docx', '.zip'];

export function FileUploadDemo() {
  const { user } = useAuth();
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [jobPositions, setJobPositions] = useState<JobPosition[]>([]);
  const [loadingJobPositions, setLoadingJobPositions] = useState(false);

  // Top-level selections (before upload)
  const [selectedJobPositionId, setSelectedJobPositionId] = useState<string>('');
  const [selectedMode, setSelectedMode] = useState<'audio' | 'video' | 'chat'>('chat');

  // Fetch job positions on mount for the current organization
  useEffect(() => {
    const fetchJobPositions = async () => {
      if (!user?.organizationId) return;
      setLoadingJobPositions(true);
      try {
        const response: any = await apiClient.getJobPositions(user.organizationId);
        const data = response?.success ? response.data : response;
        if (data?.job_positions) {
          setJobPositions(data.job_positions.filter((jp: JobPosition) => jp.is_active !== false));
        }
      } catch (error) {
        console.error('Failed to fetch job positions:', error);
      } finally {
        setLoadingJobPositions(false);
      }
    };
    fetchJobPositions();
  }, [user?.organizationId]);

  const validateFile = (file: File): string | null => {
    const fileExt = '.' + file.name.split('.').pop()?.toLowerCase();

    if (!SUPPORTED_TYPES.includes(fileExt)) {
      return `File type ${fileExt} not supported. Supported: PDF, DOC, DOCX, ZIP`;
    }

    const isZip = fileExt === '.zip';
    const maxSize = isZip ? MAX_ZIP_SIZE : MAX_FILE_SIZE;

    if (file.size > maxSize) {
      const maxSizeMB = Math.round(maxSize / (1024 * 1024));
      return `File size exceeds ${maxSizeMB}MB limit`;
    }

    return null;
  };

  const handleFileSelect = (files: FileList | null) => {
    if (!files) return;

    const fileArray = Array.from(files);
    const totalFiles = selectedFiles.length + fileArray.length;

    if (totalFiles > MAX_FILES) {
      setUploadError(`Maximum ${MAX_FILES} files allowed. You selected ${fileArray.length} additional files.`);
      return;
    }

    const validFiles: File[] = [];
    const errors: string[] = [];

    fileArray.forEach((file) => {
      const error = validateFile(file);
      if (error) {
        errors.push(`${file.name}: ${error}`);
      } else {
        validFiles.push(file);
      }
    });

    if (errors.length > 0) {
      setUploadError(errors.join('\n'));
    } else {
      setUploadError(null);
      setSelectedFiles((prev) => [...prev, ...validFiles]);
    }
  };

  const removeFile = (index: number) => {
    setSelectedFiles((prev) => prev.filter((_, i) => i !== index));
    setUploadError(null);
  };

  const onDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const onDragEnter = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const onDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const onDrop = useCallback((e: React.DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);
    handleFileSelect(e.dataTransfer.files);
  }, [selectedFiles]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
  };

  const handleUpload = async () => {
    if (selectedFiles.length === 0) return;
    if (!selectedJobPositionId) {
      setUploadError('Please select a job position before uploading.');
      return;
    }
    if (!user?.organizationId) {
      setUploadError('Organization not found. Please log in again.');
      return;
    }

    setIsUploading(true);
    setUploadError(null);

    try {
      console.log(`Uploading ${selectedFiles.length} file(s) with job_position_id=${selectedJobPositionId}, mode=${selectedMode}`);

      const response = await apiClient.uploadResumeForParsing(selectedFiles, {
        organization_id: user.organizationId,
        job_position_id: selectedJobPositionId,
        mode: selectedMode,
      });

      console.log("Upload response:", response);

      // Handle both response formats
      const responseData = response?.success !== undefined ? response : { success: true, data: response };

      if (!responseData.success && !responseData.data) {
        throw new Error((responseData as any).error || "Failed to upload and process resumes");
      }

      const data = responseData.data || responseData;

      // Backend returns: candidates_saved (count), files (array with extracted info)
      // Each saved candidate also gets an interview created automatically
      const candidatesSaved = data.candidates_saved || data.candidates_created || 0;
      const filesProcessed = data.files_processed || 0;

      // Build candidates list from files array (backend returns processed file details)
      const candidatesList = (data.files || data.candidates || [])
        .filter((f: any) => f.status === 'processed' && f.id)
        .map((f: any) => ({
          candidate_id: f.id,
          full_name: f.extracted_name || 'Unknown',
          email: f.extracted_emails?.[0] || '',
          skills: f.extracted_skills || [],
        }));

      setUploadResult({
        success: true,
        message: (responseData as any).message || `Processed ${filesProcessed} resume(s). ${candidatesSaved} candidate(s) created.`,
        candidates_created: candidatesSaved,
        interviews_scheduled: candidatesSaved, // each candidate gets an interview
        candidates: candidatesList,
        interviews: candidatesList.map((c: any) => ({
          interview_id: '',
          candidate_id: c.candidate_id,
          candidate_name: c.full_name,
          candidate_email: c.email,
          status: 'scheduled',
        })),
        failed_files: (data.files || [])
          .filter((f: any) => f.status === 'failed')
          .map((f: any) => f.filename),
      });
      setUploadSuccess(true);

      console.log(`Upload complete: ${candidatesSaved} candidates created, files processed: ${filesProcessed}`);

    } catch (error: any) {
      console.error("Upload error:", error);
      setUploadError(error.message || "Upload failed. Please try again.");
      setUploadSuccess(false);
    } finally {
      setIsUploading(false);
    }
  };

  const resetForm = () => {
    setSelectedFiles([]);
    setUploadResult(null);
    setUploadSuccess(false);
    setUploadError(null);
  };

  const selectedJobPosition = jobPositions.find(jp => jp.id === selectedJobPositionId);

  return (
    <div className="w-full rounded-xl border border-border bg-card p-6 shadow-sm">
      <div className="mb-4 space-y-1">
        <h3 className="text-lg font-medium text-white">Upload Candidate Resume(s)</h3>
        <p className="text-sm text-white/70">
          Select a job position, choose interview mode, then upload resumes to create interviews automatically.
        </p>
      </div>

      {/* Step 1: Job Position Selection */}
      <div className="mb-4 space-y-3">
        <div>
          <label className="text-sm font-medium text-white block mb-2">
            <Briefcase className="h-4 w-4 inline mr-1" />
            Job Position <span className="text-red-400">*</span>
          </label>
          <Select
            value={selectedJobPositionId}
            onValueChange={setSelectedJobPositionId}
            disabled={uploadSuccess}
          >
            <SelectTrigger className="w-full bg-white/10 border-white/20 text-white">
              <SelectValue placeholder={loadingJobPositions ? "Loading positions..." : "Select a job position"} />
            </SelectTrigger>
            <SelectContent>
              {jobPositions.length === 0 ? (
                <SelectItem value="none" disabled>
                  {loadingJobPositions ? "Loading..." : "No job positions found. Create one first."}
                </SelectItem>
              ) : (
                jobPositions.map((position) => (
                  <SelectItem key={position.id} value={position.id}>
                    {position.title}{position.department ? ` (${position.department})` : ''}
                  </SelectItem>
                ))
              )}
            </SelectContent>
          </Select>
          {!selectedJobPositionId && jobPositions.length > 0 && (
            <p className="text-xs text-yellow-400/70 mt-1">Required: Select the job position for these candidates</p>
          )}
          {jobPositions.length === 0 && !loadingJobPositions && (
            <p className="text-xs text-red-400/70 mt-1">No job positions available. Please create one from the Job Positions tab first.</p>
          )}
        </div>

        {/* Interview Mode Selection */}
        <div>
          <label className="text-sm font-medium text-white block mb-2">Interview Mode</label>
          <div className="flex flex-wrap gap-2">
            {([
              { value: 'chat' as const, label: 'Chat', icon: MessageCircle },
              { value: 'audio' as const, label: 'Audio', icon: Mic },
              { value: 'video' as const, label: 'Video', icon: Video },
            ]).map(({ value, label, icon: Icon }) => (
              <button
                key={value}
                type="button"
                onClick={() => setSelectedMode(value)}
                disabled={uploadSuccess}
                className={`inline-flex items-center gap-1.5 rounded-full border px-4 py-1.5 text-sm transition ${
                  selectedMode === value
                    ? 'border-blue-400 bg-blue-500/20 text-blue-100'
                    : 'border-white/20 bg-white/5 text-white/70 hover:bg-white/10'
                }`}
              >
                <Icon className="h-4 w-4" />
                <span>{label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* File Input */}
      <Input
        type="file"
        accept=".pdf,.doc,.docx,.zip"
        multiple
        className="hidden"
        id="file-upload-input"
        onChange={(e) => handleFileSelect(e.target.files)}
      />

      {/* Upload Area */}
      {selectedFiles.length === 0 && !uploadSuccess ? (
        <div
          onClick={() => {
            if (!selectedJobPositionId) {
              setUploadError('Please select a job position first.');
              return;
            }
            document.getElementById('file-upload-input')?.click();
          }}
          onDragOver={onDragOver}
          onDragEnter={onDragEnter}
          onDragLeave={onDragLeave}
          onDrop={onDrop}
          className={`flex h-40 cursor-pointer flex-col items-center justify-center gap-3 rounded-lg border-2 border-dashed transition-colors ${
            !selectedJobPositionId
              ? 'border-white/10 bg-white/[0.02] opacity-60'
              : isDragging
                ? 'border-blue-400/60 bg-blue-500/10'
                : 'border-white/15 bg-white/5 hover:bg-white/10'
          }`}
        >
          <div className="rounded-full bg-black/40 p-3">
            <Upload className="h-5 w-5 text-white/80" />
          </div>
          <div className="text-center">
            <p className="text-sm font-medium text-white">
              {selectedJobPositionId ? 'Click to select files' : 'Select a job position first'}
            </p>
            <p className="text-xs text-white/60">or drag and drop resumes here</p>
            <p className="text-xs text-white/50 mt-1">Supports: PDF, DOC, DOCX, ZIP (up to {MAX_FILES} files)</p>
          </div>
        </div>
      ) : !uploadSuccess ? (
        <div className="space-y-4">
          {/* Selected Job Position Badge */}
          {selectedJobPosition && (
            <div className="flex items-center gap-2 text-xs text-blue-300 bg-blue-500/10 border border-blue-500/20 rounded-lg px-3 py-2">
              <Briefcase className="h-3.5 w-3.5" />
              <span>Job: <strong>{selectedJobPosition.title}</strong></span>
              <span className="mx-1 text-white/30">|</span>
              <span>Mode: <strong className="capitalize">{selectedMode}</strong></span>
            </div>
          )}

          {/* Selected Files List */}
          <div className="space-y-2">
            {selectedFiles.map((file, index) => (
              <div
                key={index}
                className="flex items-center gap-4 rounded-lg border border-white/10 bg-white/5 p-4"
              >
                <div className="rounded-md bg-white/10 p-2">
                  <FileText className="h-6 w-6 text-white" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-white text-sm font-medium truncate">{file.name}</div>
                  <div className="text-xs text-white/60">{formatFileSize(file.size)}</div>
                  {file.name.toLowerCase().endsWith('.zip') && (
                    <div className="text-xs text-blue-400 mt-1">ZIP archive - will extract and process all resumes</div>
                  )}
                </div>
                <Button
                  size="sm"
                  variant="destructive"
                  onClick={() => removeFile(index)}
                  className="flex-shrink-0"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            ))}
          </div>

          {/* Upload Button */}
          <div className="flex items-center justify-between">
            <div className="text-xs text-white/60">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? 's' : ''} selected
              {selectedFiles.length >= MAX_FILES && (
                <span className="text-yellow-400 ml-2">(Maximum reached)</span>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                onClick={() => document.getElementById('file-upload-input')?.click()}
                variant="outline"
                size="sm"
                disabled={selectedFiles.length >= MAX_FILES}
                className="border-white/20 text-white hover:bg-white/10"
              >
                Add More
              </Button>
              <Button
                onClick={handleUpload}
                disabled={isUploading || selectedFiles.length === 0 || !selectedJobPositionId}
                className="bg-blue-600 hover:bg-blue-700"
              >
                {isUploading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Uploading & Creating Interviews...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Upload & Start Interview{selectedFiles.length !== 1 ? 's' : ''}
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      {/* Error Display */}
      {uploadError && (
        <div className="mt-4 bg-red-500/10 border border-red-500/30 rounded-lg p-3 flex items-start gap-2">
          <AlertCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <p className="text-sm text-red-400 font-medium">Error</p>
            <pre className="text-xs text-red-300 mt-1 whitespace-pre-wrap">{uploadError}</pre>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setUploadError(null)}
            className="text-red-400 hover:text-red-300"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Upload Results */}
      {uploadSuccess && uploadResult && (
        <div className="mt-4 space-y-4">
          {/* Success Summary */}
          <div className="bg-green-500/10 border border-green-500/30 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle className="h-5 w-5 text-green-400" />
              <span className="text-sm font-semibold text-green-300">Upload Complete</span>
            </div>
            <p className="text-sm text-white/80 mb-3">{uploadResult.message}</p>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="bg-white/5 rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-white">{uploadResult.candidates_created}</div>
                <div className="text-white/60">Candidate{uploadResult.candidates_created !== 1 ? 's' : ''} Created</div>
              </div>
              <div className="bg-white/5 rounded-lg p-2 text-center">
                <div className="text-lg font-bold text-white">{uploadResult.interviews_scheduled}</div>
                <div className="text-white/60">Interview{uploadResult.interviews_scheduled !== 1 ? 's' : ''} Scheduled</div>
              </div>
            </div>
          </div>

          {/* Failed Files */}
          {uploadResult.failed_files.length > 0 && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3">
              <p className="text-sm font-medium text-red-400 mb-2">Failed Files</p>
              {uploadResult.failed_files.map((file, i) => (
                <div key={i} className="text-xs text-red-300">{file}</div>
              ))}
            </div>
          )}

          {/* Created Candidates & Interviews */}
          {uploadResult.interviews.length > 0 && (
            <div className="bg-white/5 border border-white/10 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-white mb-3">Scheduled Interviews</h4>
              <div className="space-y-2">
                {uploadResult.interviews.map((interview, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-white/5 rounded-lg border border-white/10">
                    <CheckCircle className="h-4 w-4 text-green-400 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-white font-medium truncate">
                        {interview.candidate_name || 'Unknown'}
                      </div>
                      <div className="text-xs text-white/60 truncate">
                        {interview.candidate_email || 'No email'}
                      </div>
                    </div>
                    <div className="text-xs text-blue-300 bg-blue-500/10 rounded-full px-2 py-0.5">
                      {interview.status || 'scheduled'}
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-white/50 mt-3">
                <Mail className="h-3 w-3 inline mr-1" />
                Invitation emails have been sent to candidates.
              </p>
            </div>
          )}

          {/* Candidates without interviews */}
          {uploadResult.candidates.length > 0 && uploadResult.interviews.length === 0 && (
            <div className="bg-white/5 border border-white/10 rounded-lg p-4">
              <h4 className="text-sm font-semibold text-white mb-3">Created Candidates</h4>
              <div className="space-y-2">
                {uploadResult.candidates.map((candidate, i) => (
                  <div key={i} className="flex items-center gap-3 p-3 bg-white/5 rounded-lg border border-white/10">
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-white font-medium truncate">
                        {candidate.full_name || 'Unknown'}
                      </div>
                      <div className="text-xs text-white/60 truncate">
                        {candidate.email || 'No email'}
                      </div>
                    </div>
                    {candidate.skills && candidate.skills.length > 0 && (
                      <div className="text-xs text-white/50 truncate max-w-[150px]">
                        {candidate.skills.slice(0, 3).join(', ')}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Start Over Button */}
          <Button
            onClick={resetForm}
            variant="outline"
            className="w-full border-white/20 text-white hover:bg-white/10"
          >
            Upload More Resumes
          </Button>
        </div>
      )}
    </div>
  );
}

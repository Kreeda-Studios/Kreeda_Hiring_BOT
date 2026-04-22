"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState, ComplianceBadge } from "@/components/common";
import { SCORE_COLORS, getScoreColor } from "@/lib/constants";
import { processingAPI, resumesAPI } from "@/lib/api";
import {
  Trophy,
  Search,
  Download,
  ArrowUpDown,
  ExternalLink,
  User,
  FileText,
  Star,
  Filter,
  Loader2,
  RefreshCw,
} from "lucide-react";
import type { RankedCandidate } from "@/lib/types";

interface ScoreData {
  _id: string;
  job_id: string;
  resume_id: {
    _id: string;
    filename: string;
    candidate_name?: string;
  };
  contact?: {
    email?: string;
    phone?: string;
    profile?: string;
  };
  location?: string;
  years_experience?: number;
  project_score: number;
  keyword_score: number;
  semantic_score: number;
  final_score: number;
  recalculated_llm_score: number;
  hard_requirements_met: boolean;
  scores?: {
    hard_requirements?: {
      meets_all_requirements: boolean;
      compliance_score: number;
      requirements_met: string[];
      requirements_missing: string[];
      filter_reason?: string;
    };
  };
  rank?: number;
  adjusted_score?: number;
  score_breakdown?: any;
  createdAt: string;
  updatedAt: string;
}

interface ResultsSectionProps {
  jobId: string;
}

const sortOptions = [
  { value: "final_score", label: "Final Score" },
  { value: "rank", label: "Rank" },
  { value: "keyword_score", label: "Keyword Score" },
  { value: "semantic_score", label: "Semantic Score" },
  { value: "project_score", label: "Project Score" },
  { value: "recalculated_llm_score", label: "LLM Score" },
];

export function ResultsSection({ jobId }: ResultsSectionProps) {
  const [scores, setScores] = useState<ScoreData[]>([]);
  const [rankings, setRankings] = useState<RankedCandidate[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [sortBy, setSortBy] = useState("final_score");
  const [filterCompliant, setFilterCompliant] = useState<"all" | "compliant" | "non-compliant">("all");

  // Selection state
  const [selectedResumes, setSelectedResumes] = useState<Set<string>>(new Set());
  const [downloadingBulk, setDownloadingBulk] = useState(false);
  const [expandedFiltered, setExpandedFiltered] = useState<Set<string>>(new Set());

  // Convert scores to rankings for display
  const convertScoresToRankings = (scoreData: ScoreData[]): RankedCandidate[] => {
    return scoreData
      .sort((a, b) => b.final_score - a.final_score) // Sort by final_score descending
      .map((score, index) => ({
        rank: index + 1,
        resume_id: score.resume_id._id,
        candidate_name: score.resume_id.candidate_name ||
          score.resume_id.filename?.replace(/\.(pdf|doc|docx)$/i, '') ||
          `Candidate ${index + 1}`,
        email: score.contact?.email || '',
        phone: score.contact?.phone || '',
        profile: score.contact?.profile || '',
        location: score.location || '',
        years_experience: score.years_experience || 0,
        final_score: score.final_score,
        keyword_score: score.keyword_score,
        semantic_score: score.semantic_score,
        project_score: score.project_score,
        compliance_score: score.recalculated_llm_score,
        is_compliant: score.hard_requirements_met,
        filter_reason: score.scores?.hard_requirements?.filter_reason,
        compliance_status: {
          hard_compliance: score.hard_requirements_met,
          soft_compliance_score: score.recalculated_llm_score,
          requirements_met: score.scores?.hard_requirements?.requirements_met || [],
          requirements_missing: score.scores?.hard_requirements?.requirements_missing || [],
        },
        group_name: undefined,
      }));
  };

  const fetchScores = async () => {
    try {
      setLoading(true);
      const response = await processingAPI.getScoresByJob(jobId);

      if (response.success && response.data) {
        console.log('Fetched scores:', response.data);
        setScores(response.data);
        const convertedRankings = convertScoresToRankings(response.data);
        setRankings(convertedRankings);
      } else {
        console.log('No scores found for job:', jobId);
        setScores([]);
        setRankings([]);
      }
    } catch (error) {
      console.error('Error fetching scores:', error);
      setScores([]);
      setRankings([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const fetchRankings = fetchScores; // Alias for compatibility

  useEffect(() => {
    fetchScores();
    // Reset selection when tab/jobId changes
    setSelectedResumes(new Set());
  }, [jobId]);

  const handleRefresh = () => {
    setRefreshing(true);
    // Reset checkbox selections when refreshing
    setSelectedResumes(new Set());
    fetchScores();
  };

  const handleProcessRanking = async () => {
    setProcessing(true);
    try {
      const response = await processingAPI.processRanking(jobId);
      if (response.success) {
        // Wait a bit then refresh rankings
        setTimeout(() => {
          handleRefresh();
        }, 2000);
      }
    } catch (error) {
      console.error("Failed to process ranking:", error);
    } finally {
      setProcessing(false);
    }
  };

  // Separate candidates into filtered (hard requirements failed) and valid rankings
  const validRankings = rankings.filter(candidate => candidate.final_score > 0.0 || candidate.is_compliant);
  const filteredOutCandidates = rankings.filter(candidate => candidate.final_score === 0.0 && !candidate.is_compliant);

  const filteredRankings = validRankings
    .filter((candidate) => {
      const matchesSearch = candidate.candidate_name
        .toLowerCase()
        .includes(searchQuery.toLowerCase());
      const matchesCompliance =
        filterCompliant === "all" ||
        (filterCompliant === "compliant" && candidate.is_compliant) ||
        (filterCompliant === "non-compliant" && !candidate.is_compliant);
      return matchesSearch && matchesCompliance;
    })
    .sort((a, b) => {
      const key = sortBy as keyof RankedCandidate;
      if (typeof a[key] === "number" && typeof b[key] === "number") {
        return sortBy === "rank"
          ? (a[key] as number) - (b[key] as number)
          : (b[key] as number) - (a[key] as number);
      }
      return 0;
    });

  // Selection handlers
  const toggleSelectAll = () => {
    if (selectedResumes.size === filteredRankings.length && filteredRankings.length > 0) {
      setSelectedResumes(new Set());
    } else {
      setSelectedResumes(new Set(filteredRankings.map(r => r.resume_id)));
    }
  };

  const toggleSelectResume = (resumeId: string) => {
    const newSelection = new Set(selectedResumes);
    if (newSelection.has(resumeId)) {
      newSelection.delete(resumeId);
    } else {
      newSelection.add(resumeId);
    }
    setSelectedResumes(newSelection);
  };

  const handleBulkDownload = async () => {
    if (selectedResumes.size === 0) {
      alert('Please select resumes to download');
      return;
    }

    setDownloadingBulk(true);
    try {
      const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL!;
      const response = await fetch(`${API_BASE_URL}/resumes/bulk-download`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          resumeIds: Array.from(selectedResumes)
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to download resumes');
      }

      // Get the blob and download it
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resumes-${new Date().toISOString().split('T')[0]}.zip`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      window.URL.revokeObjectURL(url);

      // Clear selection after download
      setSelectedResumes(new Set());
    } catch (error) {
      console.error('Error downloading resumes:', error);
      alert('Failed to download resumes. Please try again.');
    } finally {
      setDownloadingBulk(false);
    }
  };


  const handleExportCSV = () => {
    if (filteredRankings.length === 0) {
      alert('No data to export');
      return;
    }

    // CSV with contact details first, then scores
    const headers = ['Rank', 'Name', 'Phone', 'Email', 'Profile/LinkedIn', 'Final Score', 'Keyword', 'Semantic', 'Project'];
    const rows = filteredRankings.map(r => [
      r.rank,
      r.candidate_name,
      r.phone || '',
      r.email || '',
      r.profile || '',
      r.final_score.toFixed(1),
      r.keyword_score.toFixed(1),
      r.semantic_score.toFixed(1),
      r.project_score.toFixed(1)
    ]);

    const csvContent = [headers, ...rows].map(row => row.join(',')).join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `rankings-${jobId}-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
  };

  if (loading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin mr-2" />
          <span>Loading rankings...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Rankings Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <Trophy className="h-5 w-5" />
                Final Scores & Rankings
              </CardTitle>
              <CardDescription>
                Showing {validRankings.length} ranked candidates
                {filteredOutCandidates.length > 0 && (
                  <span className="text-orange-600">
                    {' '}• {filteredOutCandidates.length} filtered out
                  </span>
                )}
                {' '}from Score API (Job ID: {jobId})
              </CardDescription>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleRefresh}
                disabled={refreshing}
                className="cursor-pointer"              >
                <RefreshCw className={` h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              {selectedResumes.size > 0 && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleBulkDownload}
                  disabled={downloadingBulk}
                  className="cursor-pointer"
                >
                  {downloadingBulk ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Download className="h-4 w-4 mr-2" />
                  )}
                  Download Selected ({selectedResumes.size})
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={handleExportCSV} className="cursor-pointer">
                <Download className="h-4 w-4 mr-2" />
                Export CSV
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Filters */}
          <div className="flex flex-col md:flex-row gap-4 mb-6">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search candidates..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>
            <Select value={sortBy} onValueChange={setSortBy}>
              <SelectTrigger className="w-45">
                <ArrowUpDown className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Sort by" />
              </SelectTrigger>
              <SelectContent>
                {sortOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {/*
            <Select 
              value={filterCompliant} 
              onValueChange={(v) => setFilterCompliant(v as "all" | "compliant" | "non-compliant")}
            >
              <SelectTrigger className="w-45">
                <Filter className="h-4 w-4 mr-2" />
                <SelectValue placeholder="Filter" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Candidates</SelectItem>
                <SelectItem value="compliant">Compliant Only</SelectItem>
                <SelectItem value="non-compliant">Non-Compliant</SelectItem>
              </SelectContent>
            </Select>
            */}
          </div>

          {/* Table */}
          {filteredRankings.length === 0 ? (
            <EmptyState
              icon={<Trophy className="h-6 w-6" />}
              title="No scored candidates found"
              description={scores.length === 0
                ? "No scores found for this job. Candidates need to be processed first."
                : "No candidates match your current filters."}
            />
          ) : (
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-12">
                      <Checkbox
                        checked={selectedResumes.size === filteredRankings.length && filteredRankings.length > 0}
                        onCheckedChange={toggleSelectAll}
                        aria-label="Select all"
                      />
                    </TableHead>
                    <TableHead className="w-16">Rank</TableHead>
                    <TableHead>Candidate</TableHead>
                    <TableHead>Email</TableHead>
                    <TableHead>Phone</TableHead>
                    <TableHead className="text-center">Final</TableHead>
                    <TableHead className="text-center">Keyword</TableHead>
                    <TableHead className="text-center">Semantic</TableHead>
                    <TableHead className="text-center">Project</TableHead>
                    <TableHead className="text-center">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRankings.map((candidate) => (
                    <TableRow key={candidate.resume_id}>
                      <TableCell>
                        <Checkbox
                          checked={selectedResumes.has(candidate.resume_id)}
                          onCheckedChange={() => toggleSelectResume(candidate.resume_id)}
                          aria-label={`Select ${candidate.candidate_name}`}
                        />
                      </TableCell>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {candidate.rank <= 3 && (
                            <Trophy className={`h-4 w-4 ${candidate.rank === 1 ? 'text-yellow-500' :
                                candidate.rank === 2 ? 'text-gray-400' :
                                  'text-amber-600'
                              }`} />
                          )}
                          <span className="font-medium">{candidate.rank}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div>
                          <p className="font-medium">{candidate.candidate_name}</p>
                        </div>
                      </TableCell>
                      <TableCell>
                        {candidate.email ? (
                          <a href={`mailto:${candidate.email}`} className="text-sm text-blue-600 hover:underline">
                            {candidate.email}
                          </a>
                        ) : (
                          <span className="text-xs text-muted-foreground">N/A</span>
                        )}
                      </TableCell>
                      <TableCell>
                        {candidate.phone ? (
                          <span className="text-sm">{candidate.phone}</span>
                        ) : (
                          <span className="text-xs text-muted-foreground">N/A</span>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <span className={`font-bold ${getScoreColor(candidate.final_score / 100)}`}>
                          {candidate.final_score.toFixed(1)}
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        <span className={getScoreColor(candidate.keyword_score / 100)}>
                          {candidate.keyword_score.toFixed(1)}
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        <span className={getScoreColor(candidate.semantic_score / 100)}>
                          {candidate.semantic_score.toFixed(1)}
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        <span className={getScoreColor(candidate.project_score / 100)}>
                          {candidate.project_score.toFixed(1)}
                        </span>
                      </TableCell>
                      {/* <TableCell className="text-center">
                        <ComplianceBadge isCompliant={candidate.is_compliant} />
                      </TableCell> */}
                      <TableCell className="text-center">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => resumesAPI.openResume(candidate.resume_id)}
                          title="View Resume"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Filtered Out Candidates Section */}
      {filteredOutCandidates.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Filter className="h-5 w-5 text-orange-500" />
              Filtered Out Candidates
            </CardTitle>
            <CardDescription>
              {filteredOutCandidates.length} candidate{filteredOutCandidates.length !== 1 ? 's' : ''} were filtered out due to not meeting mandatory compliance requirements.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Candidate</TableHead>
                    <TableHead>Reason</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredOutCandidates.map((candidate) => (
                    <TableRow key={candidate.resume_id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
                            Filtered
                          </Badge>
                          <span className="font-medium">{candidate.candidate_name}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        <span className="text-sm text-muted-foreground">
                          Does not meet mandatory compliance requirements
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button 
                          variant="ghost" 
                          size="sm"
                          onClick={() => resumesAPI.openResume(candidate.resume_id)}
                          title="View Resume"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

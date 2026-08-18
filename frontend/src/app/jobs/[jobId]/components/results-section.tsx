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
  Sparkles,
} from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
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
  filter_reason?: string;
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
      .sort((a, b) => b.final_score - a.final_score)
      .map((score, index) => {
        const secScores = (score as any).scores?.section_scores || score.score_breakdown?.section_scores || {};
        const rawSkills = secScores.skills !== undefined ? secScores.skills : score.keyword_score;
        const rawEdu = secScores.education !== undefined ? secScores.education : score.semantic_score;
        const rawExp = secScores.responsibilities !== undefined ? secScores.responsibilities : score.semantic_score;

        const backendReason = (score.scores?.hard_requirements as any)?.selection_reason || (score as any).selection_reason;
        
        // Build dynamic 1-liner selection reason based on actual strengths if backend reason is generic
        let reason = backendReason;
        if (!reason || reason.includes("Matched mandatory compliance criteria")) {
          const pPct = Math.round(score.project_score > 1 ? score.project_score : score.project_score * 100);
          const sPct = Math.round(rawSkills > 1 ? rawSkills : rawSkills * 100);
          const ePct = Math.round(rawExp > 1 ? rawExp : rawExp * 100);

          const strengths = [];
          if (sPct >= 50) strengths.push("matched required skills");
          if (pPct >= 50) strengths.push("strong project execution");
          if (ePct >= 40) strengths.push("relevant work experience");

          if (strengths.length > 0) {
            reason = `Selected due to ${strengths.join(", ")}.`;
          } else {
            reason = `Candidate met all mandatory requirements and matched key job profile criteria.`;
          }
        }

        return {
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
          skills_score: rawSkills,
          education_score: rawEdu,
          experience_score: rawExp,
          evidence: (secScores as any).evidence || {},
          compliance_score: score.recalculated_llm_score,
          is_compliant: score.hard_requirements_met,
          filter_reason: score.filter_reason || "Reason not specified",
          selection_reason: reason,
          compliance_status: {
            hard_compliance: score.hard_requirements_met,
            soft_compliance_score: score.recalculated_llm_score,
            requirements_met: score.scores?.hard_requirements?.requirements_met || [],
            requirements_missing: score.scores?.hard_requirements?.requirements_missing || [],
          },
          group_name: undefined,
        };
      });
  };

  const formatPercent = (val: number | undefined): string => {
    if (val === undefined || val === null || isNaN(val)) return "0%";
    const pct = val > 1 ? val : val * 100;
    return `${Math.round(pct)}%`;
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
        setScores([]);
        setRankings([]);
      }
    } catch (error) {
      console.error('Error fetching scores:', error);
      setScores([]);
      setRankings([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchScores();
    setRefreshing(false);
  };

  useEffect(() => {
    fetchScores();
  }, [jobId]);

  const validRankings = rankings.filter(r => r.is_compliant);
  const filteredOutCandidates = rankings.filter(r => !r.is_compliant);

  const filteredRankings = validRankings.filter((candidate) => {
    const matchesSearch =
      candidate.candidate_name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      candidate.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      candidate.location.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSearch;
  });

  const toggleSelectAll = () => {
    if (selectedResumes.size === filteredRankings.length) {
      setSelectedResumes(new Set());
    } else {
      setSelectedResumes(new Set(filteredRankings.map(r => r.resume_id)));
    }
  };

  const toggleSelectResume = (resumeId: string) => {
    const next = new Set(selectedResumes);
    if (next.has(resumeId)) {
      next.delete(resumeId);
    } else {
      next.add(resumeId);
    }
    setSelectedResumes(next);
  };

  const handleBulkDownload = async () => {
    if (selectedResumes.size === 0) return;
    try {
      setDownloadingBulk(true);
      await resumesAPI.downloadBulkResumes(Array.from(selectedResumes));
    } catch (error) {
      console.error('Error downloading resumes:', error);
    } finally {
      setDownloadingBulk(false);
    }
  };

  const handleExportCSV = () => {
    const headers = ['Rank', 'Name', 'Email', 'Phone', 'Location', 'Overall Score', 'Skills Score', 'Project Score', 'Experience Score'];
    const rows = filteredRankings.map(r => [
      r.rank,
      `"${r.candidate_name}"`,
      `"${r.email}"`,
      `"${r.phone}"`,
      `"${r.location}"`,
      formatPercent(r.final_score),
      formatPercent(r.skills_score),
      formatPercent(r.project_score),
      formatPercent(r.experience_score)
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
          </div>

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
                    <TableHead className="text-center">Overall Score</TableHead>
                    <TableHead className="text-center">Skills Score</TableHead>
                    <TableHead className="text-center">Project Score</TableHead>
                    <TableHead className="text-center">Experience Score</TableHead>
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
                          className="cursor-pointer"
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
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium">{candidate.candidate_name}</span>
                          {candidate.selection_reason && (
                            <TooltipProvider>
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <span className="inline-flex items-center justify-center p-1 rounded-full bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-950 dark:text-green-300 cursor-pointer transition-colors">
                                    <Sparkles className="h-3.5 w-3.5" />
                                  </span>
                                </TooltipTrigger>
                                <TooltipContent side="right" className="max-w-xs text-xs">
                                  <p className="font-semibold text-green-400 mb-1">Selection Reason</p>
                                  <p>{candidate.selection_reason}</p>
                                </TooltipContent>
                              </Tooltip>
                            </TooltipProvider>
                          )}
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
                        <span className={`font-bold ${getScoreColor(candidate.final_score > 1 ? candidate.final_score / 100 : candidate.final_score)}`}>
                          {formatPercent(candidate.final_score)}
                        </span>
                      </TableCell>
                      <TableCell className="text-center">
                        {candidate.evidence?.skills?.length ? (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className={`cursor-pointer underline decoration-dotted underline-offset-4 ${getScoreColor((candidate.skills_score || 0) > 1 ? (candidate.skills_score || 0) / 100 : (candidate.skills_score || 0))}`}>
                                  {formatPercent(candidate.skills_score)}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-xs text-xs">
                                <p className="font-semibold text-blue-400 mb-1">⚡ Skills Evidence Quotes</p>
                                <ul className="list-disc pl-3 space-y-1">
                                  {candidate.evidence.skills.map((q, i) => (
                                    <li key={i}>"{q}"</li>
                                  ))}
                                </ul>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        ) : (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className={`cursor-pointer ${getScoreColor((candidate.skills_score || 0) > 1 ? (candidate.skills_score || 0) / 100 : (candidate.skills_score || 0))}`}>
                                  {formatPercent(candidate.skills_score)}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-xs text-xs">
                                <p className="text-muted-foreground">No explicit skills section extracted from resume.</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        {candidate.evidence?.projects?.length ? (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className={`cursor-pointer underline decoration-dotted underline-offset-4 ${getScoreColor(candidate.project_score > 1 ? candidate.project_score / 100 : candidate.project_score)}`}>
                                  {formatPercent(candidate.project_score)}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-xs text-xs">
                                <p className="font-semibold text-indigo-400 mb-1">🚀 Project Evidence Quotes</p>
                                <ul className="list-disc pl-3 space-y-1">
                                  {candidate.evidence.projects.map((q, i) => (
                                    <li key={i}>"{q}"</li>
                                  ))}
                                </ul>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        ) : (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className={`cursor-pointer ${getScoreColor(candidate.project_score > 1 ? candidate.project_score / 100 : candidate.project_score)}`}>
                                  {formatPercent(candidate.project_score)}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-xs text-xs">
                                <p className="text-muted-foreground">No dedicated project section extracted from resume.</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        {(candidate.evidence?.experience?.length || candidate.evidence?.responsibilities?.length) ? (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className={`cursor-pointer underline decoration-dotted underline-offset-4 ${getScoreColor((candidate.experience_score || 0) > 1 ? (candidate.experience_score || 0) / 100 : (candidate.experience_score || 0))}`}>
                                  {formatPercent(candidate.experience_score)}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-xs text-xs">
                                <p className="font-semibold text-emerald-400 mb-1">💼 Experience Evidence Quotes</p>
                                <ul className="list-disc pl-3 space-y-1">
                                  {(candidate.evidence.experience || candidate.evidence.responsibilities || []).map((q, i) => (
                                    <li key={i}>"{q}"</li>
                                  ))}
                                </ul>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        ) : (
                          <TooltipProvider>
                            <Tooltip>
                              <TooltipTrigger asChild>
                                <span className={`cursor-pointer ${getScoreColor((candidate.experience_score || 0) > 1 ? (candidate.experience_score || 0) / 100 : (candidate.experience_score || 0))}`}>
                                  {formatPercent(candidate.experience_score)}
                                </span>
                              </TooltipTrigger>
                              <TooltipContent side="top" className="max-w-xs text-xs">
                                <p className="text-muted-foreground">No explicit work experience section extracted from resume.</p>
                              </TooltipContent>
                            </Tooltip>
                          </TooltipProvider>
                        )}
                      </TableCell>
                      <TableCell className="text-center">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => resumesAPI.openResume(candidate.resume_id)}
                          title="View Resume"
                          className="cursor-pointer"
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
                          {candidate.filter_reason || "Did not meet mandatory requirements"}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => resumesAPI.openResume(candidate.resume_id)}
                          title="View Resume"
                          className="cursor-pointer"
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

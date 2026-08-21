"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Checkbox } from "@/components/ui/checkbox";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
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
  AlertTriangle,
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
      is_overqualified?: boolean;
    };
  };
  is_overqualified?: boolean;
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
  const [showOverqualified, setShowOverqualified] = useState(true);
  const [expandedFiltered, setExpandedFiltered] = useState<Set<string>>(new Set());
  const [selectedPerfect, setSelectedPerfect] = useState<Set<string>>(new Set());
  const [selectedOQ, setSelectedOQ] = useState<Set<string>>(new Set());
  const [selectedFiltered, setSelectedFiltered] = useState<Set<string>>(new Set());

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
          is_overqualified: score.scores?.hard_requirements?.is_overqualified || (score as any).is_overqualified || false,
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

  const renderFormattedSelectionReason = (reason: string) => {
    if (!reason) return null;
    let clean = reason
      .replace(/^Candidate met all mandatory requirements:\s*/i, '')
      .replace(/^Passed compliance checks:\s*/i, '');
      
    const parts = clean.split(';').map(p => p.trim()).filter(Boolean);
    
    return (
      <div className="space-y-1.5 text-xs max-w-sm">
        <p className="font-bold text-green-700 border-b border-green-200 pb-1 flex items-center gap-1">
          <Sparkles className="h-3.5 w-3.5 text-green-600" />
          Selection & Compliance Overview
        </p>
        <ul className="list-disc pl-3.5 space-y-1 text-black font-medium">
          {parts.map((part, idx) => (
            <li key={idx}>
              {part}
            </li>
          ))}
        </ul>
      </div>
    );
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

  const searchFilter = (candidate: RankedCandidate) => {
    const query = searchQuery.toLowerCase();
    return (
      (candidate.candidate_name || '').toLowerCase().includes(query) ||
      (candidate.email || '').toLowerCase().includes(query) ||
      (candidate.location || '').toLowerCase().includes(query)
    );
  };

  const perfectMatchRankings = rankings
    .filter(r => r.is_compliant && !r.is_overqualified)
    .filter(searchFilter)
    .map((r, index) => ({ ...r, rank: index + 1 }));

  const overqualifiedRankings = rankings
    .filter(r => r.is_compliant && r.is_overqualified)
    .filter(searchFilter)
    .map((r, index) => ({ ...r, rank: index + 1 }));

  const filteredOutCandidates = rankings.filter(r => !r.is_compliant).filter(searchFilter);
  
  const filteredRankings = [...perfectMatchRankings, ...overqualifiedRankings];



  const handleExportCSV = () => {
    const headers = ['Rank', 'Name', 'Email', 'Phone', 'Location', 'Overall', 'Skills', 'Projects', 'Experience'];
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

  const handleBulkDownload = async (resumeIds: string[]) => {
    if (resumeIds.length === 0) return;
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/resumes/bulk-download`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resumeIds }),
      });
      if (!response.ok) throw new Error('Download failed');
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `resumes-${new Date().toISOString().split('T')[0]}.zip`;
      a.click();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Bulk download error:', error);
    }
  };

  const renderRankedTable = (
    title: string,
    candidates: RankedCandidate[],
    icon: React.ReactNode,
    titleColorClass: string = "",
    selected: Set<string>,
    setSelected: React.Dispatch<React.SetStateAction<Set<string>>>
  ) => {
    const allIds = candidates.map(c => c.resume_id);
    const allSelected = allIds.length > 0 && allIds.every(id => selected.has(id));
    const someSelected = allIds.some(id => selected.has(id)) && !allSelected;

    const toggleAll = () => {
      if (allSelected) {
        setSelected(prev => { const next = new Set(prev); allIds.forEach(id => next.delete(id)); return next; });
      } else {
        setSelected(prev => new Set([...prev, ...allIds]));
      }
    };

    const toggleOne = (id: string) => {
      setSelected(prev => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id); else next.add(id);
        return next;
      });
    };

    const selectedInSection = allIds.filter(id => selected.has(id));
    return (
      <div className="space-y-4">
        {candidates.length === 0 ? (
          <EmptyState
            icon={icon}
            title={`No ${title.toLowerCase()} candidates`}
            description={`None of the candidates fell into the ${title} category based on your filters.`}
          />
        ) : (
          <div className="space-y-3">
            {/* Download toolbar */}
            <div className="flex items-center gap-2 justify-end">
              <Button
                variant="outline"
                size="sm"
                className="cursor-pointer"
                disabled={selectedInSection.length === 0}
                onClick={() => handleBulkDownload(selectedInSection)}
              >
                <Download className="h-4 w-4 mr-1" />
                Download Selected ({selectedInSection.length})
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="cursor-pointer"
                onClick={() => handleBulkDownload(allIds)}
              >
                <Download className="h-4 w-4 mr-1" />
                Download All ({allIds.length})
              </Button>
            </div>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                <TableHead className="w-10">
                  <Checkbox
                    checked={allSelected}
                    data-state={someSelected ? 'indeterminate' : undefined}
                    onCheckedChange={toggleAll}
                    aria-label="Select all"
                  />
                </TableHead>
                <TableHead className="w-16">Rank</TableHead>
                <TableHead>Candidate</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead className="text-center whitespace-nowrap">Overall</TableHead>
                <TableHead className="text-center whitespace-nowrap">Skills</TableHead>
                <TableHead className="text-center whitespace-nowrap">Projects</TableHead>
                <TableHead className="text-center whitespace-nowrap">Experience</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {candidates.map((candidate) => (
                <TableRow key={candidate.resume_id}>
                  <TableCell>
                    <Checkbox
                      checked={selected.has(candidate.resume_id)}
                      onCheckedChange={() => toggleOne(candidate.resume_id)}
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
                    <div className="flex items-center gap-1.5 whitespace-nowrap">
                      <button
                        onClick={() => resumesAPI.openResume(candidate.resume_id)}
                        className="font-medium text-foreground hover:underline cursor-pointer flex items-center gap-1 text-left"
                        title="Click to view resume PDF"
                      >
                        <span>{candidate.candidate_name}</span>
                        <ExternalLink className="h-3.5 w-3.5 text-muted-foreground opacity-70 hover:opacity-100" />
                      </button>
                      {candidate.selection_reason && (
                        <TooltipProvider>
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span className="inline-flex items-center justify-center p-1 rounded-full bg-green-50 text-green-700 hover:bg-green-100 dark:bg-green-950 dark:text-green-300 cursor-pointer transition-colors">
                                <Sparkles className="h-3.5 w-3.5" />
                              </span>
                            </TooltipTrigger>
                            <TooltipContent side="right" className="p-3 bg-white text-black border border-gray-200 shadow-md">
                              {renderFormattedSelectionReason(candidate.selection_reason)}
                            </TooltipContent>
                          </Tooltip>
                        </TooltipProvider>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    {candidate.email ? (
                      <a href={`mailto:${candidate.email}`} title={candidate.email} className="text-sm text-blue-600 hover:underline max-w-[160px] truncate block">
                        {candidate.email}
                      </a>
                    ) : (
                      <span className="text-xs text-muted-foreground">N/A</span>
                    )}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">
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
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
        </div>
        )}
      </div>
    );
  };

  const renderFilteredTable = (
    candidates: RankedCandidate[],
    selected: Set<string>,
    setSelected: React.Dispatch<React.SetStateAction<Set<string>>>
  ) => {
    const allIds = candidates.map(c => c.resume_id);
    const allSelected = allIds.length > 0 && allIds.every(id => selected.has(id));
    const someSelected = allIds.some(id => selected.has(id)) && !allSelected;

    const toggleAll = () => {
      if (allSelected) {
        setSelected(prev => { const next = new Set(prev); allIds.forEach(id => next.delete(id)); return next; });
      } else {
        setSelected(prev => new Set([...prev, ...allIds]));
      }
    };

    const toggleOne = (id: string) => {
      setSelected(prev => {
        const next = new Set(prev);
        if (next.has(id)) next.delete(id); else next.add(id);
        return next;
      });
    };

    const selectedInSection = allIds.filter(id => selected.has(id));
    return (
      <div className="space-y-4 mt-6">
        {candidates.length === 0 ? (
          <EmptyState
            icon={<AlertTriangle className="h-6 w-6" />}
            title="No filtered out candidates"
            description="All candidates met the mandatory requirements."
          />
        ) : (
          <div className="space-y-3">
            {/* Download toolbar */}
            <div className="flex items-center gap-2 justify-end">
              <Button
                variant="outline"
                size="sm"
                className="cursor-pointer"
                disabled={selectedInSection.length === 0}
                onClick={() => handleBulkDownload(selectedInSection)}
              >
                <Download className="h-4 w-4 mr-1" />
                Download Selected ({selectedInSection.length})
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="cursor-pointer"
                onClick={() => handleBulkDownload(allIds)}
              >
                <Download className="h-4 w-4 mr-1" />
                Download All ({allIds.length})
              </Button>
            </div>
          <div className="rounded-md border">
            <Table>
              <TableHeader>
              <TableRow>
                <TableHead className="w-10">
                  <Checkbox
                    checked={allSelected}
                    data-state={someSelected ? 'indeterminate' : undefined}
                    onCheckedChange={toggleAll}
                    aria-label="Select all filtered"
                  />
                </TableHead>
                <TableHead>Candidate</TableHead>
                <TableHead>Reason</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {candidates.map((candidate) => (
                <TableRow key={candidate.resume_id}>
                  <TableCell>
                    <Checkbox
                      checked={selected.has(candidate.resume_id)}
                      onCheckedChange={() => toggleOne(candidate.resume_id)}
                      aria-label={`Select ${candidate.candidate_name}`}
                    />
                  </TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
                        Filtered
                      </Badge>
                      <button
                        onClick={() => resumesAPI.openResume(candidate.resume_id)}
                        className="font-medium text-foreground hover:underline cursor-pointer flex items-center gap-1 text-left"
                        title="Click to view resume PDF"
                      >
                        <span>{candidate.candidate_name}</span>
                        <ExternalLink className="h-3.5 w-3.5 text-muted-foreground opacity-70 hover:opacity-100" />
                      </button>
                    </div>
                  </TableCell>
                  <TableCell>
                    <span className="text-sm text-muted-foreground">
                      {candidate.filter_reason || "Did not meet mandatory requirements"}
                    </span>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          </div>
        </div>
        )}
      </div>
    );
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
                Showing {perfectMatchRankings.length} ranked candidates
                {(filteredOutCandidates.length + overqualifiedRankings.length) > 0 && (
                  <span className="text-orange-600">
                    {' '}• {filteredOutCandidates.length + overqualifiedRankings.length} filtered out
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

          {filteredRankings.length === 0 && filteredOutCandidates.length === 0 ? (
            <EmptyState
              icon={<Trophy className="h-6 w-6" />}
              title="No scored candidates found"
              description={scores.length === 0
                ? "No scores found for this job. Candidates need to be processed first."
                : "No candidates match your current filters."}
            />
          ) : (
            <Tabs defaultValue="perfect-match" className="w-full">
              <TabsList className="grid w-full grid-cols-2 mb-6">
                <TabsTrigger value="perfect-match" className="flex items-center gap-2">
                  <Trophy className="h-4 w-4 text-yellow-500" />
                  Perfect Match ({perfectMatchRankings.length})
                </TabsTrigger>
                <TabsTrigger value="filtered-out" className="flex items-center gap-2">
                  <Filter className="h-4 w-4 text-orange-500" />
                  Filtered Out ({filteredOutCandidates.length + overqualifiedRankings.length})
                </TabsTrigger>
              </TabsList>
              
              <TabsContent value="perfect-match">
                {renderRankedTable("Perfect Match", perfectMatchRankings, <Trophy className="h-5 w-5 text-yellow-500" />, "", selectedPerfect, setSelectedPerfect)}
              </TabsContent>
              
              <TabsContent value="filtered-out">
                {overqualifiedRankings.length > 0 && (
                  <div className="mb-8 border-b pb-6">
                    <div className="flex items-center justify-between mb-4">
                      <div className="flex flex-col">
                        <h3 className="text-lg font-medium flex items-center gap-2">
                          <Star className="h-5 w-5 text-purple-500" />
                          Overqualified Candidates
                        </h3>
                        <p className="text-sm text-muted-foreground">
                          Candidates whose experience exceeds the required range but who pass all mandatory skill checks.
                        </p>
                      </div>
                      <Button 
                        variant="outline" 
                        onClick={() => setShowOverqualified(!showOverqualified)}
                        className="cursor-pointer"
                      >
                        {showOverqualified ? "Hide Overqualified" : `Show Overqualified (${overqualifiedRankings.length})`}
                      </Button>
                    </div>
                    
                    {showOverqualified && (
                      <div className="mt-4">
                        {renderRankedTable("Overqualified", overqualifiedRankings, <Star className="h-5 w-5 text-purple-500" />, "text-purple-700", selectedOQ, setSelectedOQ)}
                      </div>
                    )}
                  </div>
                )}

                {renderFilteredTable(filteredOutCandidates, selectedFiltered, setSelectedFiltered)}
              </TabsContent>
            </Tabs>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

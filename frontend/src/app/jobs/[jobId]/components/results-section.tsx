"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
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
import { processingAPI } from "@/lib/api";
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
  project_score: number;
  keyword_score: number;
  semantic_score: number;
  final_score: number;
  recalculated_llm_score: number;
  hard_requirements_met: boolean;
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
        final_score: score.final_score,
        keyword_score: score.keyword_score,
        semantic_score: score.semantic_score,
        project_score: score.project_score,
        compliance_score: score.recalculated_llm_score,
        is_compliant: score.hard_requirements_met,
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
  }, [jobId]);

  const handleRefresh = () => {
    setRefreshing(true);
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

  const filteredRankings = rankings
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


  const handleExportCSV = () => {
    if (filteredRankings.length === 0) {
      alert('No data to export');
      return;
    }
    
    const headers = ['Rank', 'Name', 'Final Score', 'Keyword', 'Semantic', 'Project', 'Compliant', 'Group'];
    const rows = filteredRankings.map(r => [
      r.rank,
      r.candidate_name,
      r.final_score.toFixed(1),
      r.keyword_score.toFixed(1),
      r.semantic_score.toFixed(1),
      r.project_score.toFixed(1),
      r.is_compliant ? 'Yes' : 'No',
      r.group_name || 'N/A'
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
                Showing {scores.length} scored candidates from Score API (Job ID: {jobId})
              </CardDescription>
            </div>
            <div className="flex gap-2">
              {rankings.length === 0 && (
                <Button
                  variant="default"
                  size="sm"
                  onClick={handleProcessRanking}
                  disabled={processing}
                >
                  {processing ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-2" />
                  ) : (
                    <Trophy className="h-4 w-4 mr-2" />
                  )}
                  {processing ? 'Processing...' : 'Process Ranking'}
                </Button>
              )}
              <Button 
                variant="outline" 
                size="sm"
                onClick={handleRefresh}
                disabled={refreshing}
              >
                <RefreshCw className={`h-4 w-4 mr-2 ${refreshing ? 'animate-spin' : ''}`} />
                Refresh
              </Button>
              <Button variant="outline" size="sm" onClick={handleExportCSV}>
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
                    <TableHead className="w-16">Rank</TableHead>
                    <TableHead>Candidate</TableHead>
                    <TableHead className="text-right">Final</TableHead>
                    <TableHead className="text-right">Keyword</TableHead>
                    <TableHead className="text-right">Semantic</TableHead>
                    <TableHead className="text-right">Project</TableHead>
                    {/* <TableHead className="text-center">Status</TableHead> */}
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredRankings.map((candidate) => (
                    <TableRow key={candidate.resume_id}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {candidate.rank <= 3 && (
                            <Trophy className={`h-4 w-4 ${
                              candidate.rank === 1 ? 'text-yellow-500' :
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
                          <p className="text-xs text-muted-foreground">{candidate.group_name}</p>
                        </div>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={`font-bold ${getScoreColor(candidate.final_score / 100)}`}>
                          {candidate.final_score.toFixed(1)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={getScoreColor(candidate.keyword_score / 100)}>
                          {candidate.keyword_score.toFixed(1)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={getScoreColor(candidate.semantic_score / 100)}>
                          {candidate.semantic_score.toFixed(1)}
                        </span>
                      </TableCell>
                      <TableCell className="text-right">
                        <span className={getScoreColor(candidate.project_score / 100)}>
                          {candidate.project_score.toFixed(1)}
                        </span>
                      </TableCell>
                      {/* <TableCell className="text-center">
                        <ComplianceBadge isCompliant={candidate.is_compliant} />
                      </TableCell> */}
                      <TableCell className="text-right">
                        <Button variant="ghost" size="sm">
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
    </div>
  );
}

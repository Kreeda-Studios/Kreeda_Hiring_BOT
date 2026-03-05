/**
 * Preview Panel Component
 * Shows resume preview with tabs for PDF and Analysis
 */

'use client';

import { useEffect, useState, useMemo } from 'react';
import { X, Loader2 } from 'lucide-react';
import { Button } from '@/frontend/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/frontend/components/ui/tabs';
import { PDFViewer } from './pdf-viewer';

interface PreviewPanelProps {
  resumeId: string;
  onClose: () => void;
}

interface ResumeData {
  resume: any;
  fileUrl: string;
}

export function PreviewPanel({ resumeId, onClose }: PreviewPanelProps) {
  const [data, setData] = useState<ResumeData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchResume = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const response = await fetch(`/api/resume/${resumeId}`);
        
        if (!response.ok) {
          throw new Error('Failed to fetch resume');
        }

        const result = await response.json();
        setData(result.data);
      } catch (err) {
        console.error('Error fetching resume:', err);
        setError(err instanceof Error ? err.message : 'Failed to load resume');
      } finally {
        setLoading(false);
      }
    };

    fetchResume();
  }, [resumeId]);

  // Memoize the file URL to prevent unnecessary re-renders
  const fileUrl = useMemo(() => data?.fileUrl || '', [data?.fileUrl]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-background">
        <div className="text-center space-y-2">
          <p className="text-red-500">{error}</p>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    );
  }

  if (!data) {
    return null;
  }

  return (
    <div className="h-full flex flex-col bg-background overflow-hidden">
      <Tabs defaultValue="analysis" className="h-full flex flex-col">
        {/* Browser-style Tabs Header */}
        <div className="flex items-center border-b bg-muted/30 shrink-0">
          <TabsList className="h-12 rounded-none border-0 bg-transparent p-0">
            <TabsTrigger 
              value="analysis" 
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-background px-6 h-12"
            >
              📊 Analysis
            </TabsTrigger>
            <TabsTrigger 
              value="preview" 
              className="rounded-none border-b-2 border-transparent data-[state=active]:border-primary data-[state=active]:bg-background px-6 h-12"
            >
              📄 Preview
            </TabsTrigger>
          </TabsList>
          <div className="flex-1"></div>
          <Button variant="ghost" size="sm" onClick={onClose} className="mr-2">
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Tab Content Area */}
        <div className="flex-1 overflow-hidden">
          <TabsContent value="preview" className="h-full m-0">
            {data.resume.fileType === 'pdf' ? (
              <PDFViewer url={fileUrl} />
            ) : (
              <div className="flex items-center justify-center h-full">
                <p className="text-muted-foreground">
                  DOCX preview not yet supported. 
                  <a 
                    href={fileUrl} 
                    target="_blank" 
                    rel="noopener noreferrer"
                    className="text-primary hover:underline ml-1"
                  >
                    Download file
                  </a>
                </p>
              </div>
            )}
          </TabsContent>

          <TabsContent value="analysis" className="h-full m-0 p-6 overflow-auto">
            <div className="space-y-6">
              {/* Header */}
              <div>
                <h3 className="text-lg font-semibold mb-2">Resume Analysis</h3>
                <p className="text-sm text-muted-foreground mb-4">
                  Detailed analysis and extracted information
                </p>
              </div>

              {/* Processing Status */}
              {(data.resume.status === 'uploaded' || data.resume.status === 'processing') && (
                <div className="rounded-lg bg-muted/50 p-4 text-center">
                  <p className="text-sm text-muted-foreground">
                    Resume is being processed. Detailed analysis will appear here once complete.
                  </p>
                </div>
              )}

              {/* Show all extracted data only when completed */}
              {data.resume.status === 'completed' && (
                <>
                  {/* Profile Information */}
                  {data.resume.profile && (
                    <div className="space-y-2">
                      <h4 className="font-medium text-base">
                        👤 Profile Information
                      </h4>
                      <div className="rounded-md border bg-card p-4 space-y-2">
                        {data.resume.profile.name && (
                          <div className="flex flex-col sm:flex-row sm:gap-2">
                            <span className="font-medium text-sm min-w-[120px]">Name:</span>
                            <span className="text-sm">{data.resume.profile.name}</span>
                          </div>
                        )}
                        {data.resume.profile.email && (
                          <div className="flex flex-col sm:flex-row sm:gap-2">
                            <span className="font-medium text-sm min-w-[120px]">Email:</span>
                            <span className="text-sm">{data.resume.profile.email}</span>
                          </div>
                        )}
                        {data.resume.profile.contact && (
                          <div className="flex flex-col sm:flex-row sm:gap-2">
                            <span className="font-medium text-sm min-w-[120px]">Contact:</span>
                            <span className="text-sm">{data.resume.profile.contact}</span>
                          </div>
                        )}
                        {data.resume.profile.location && (
                          <div className="flex flex-col sm:flex-row sm:gap-2">
                            <span className="font-medium text-sm min-w-[120px]">Location:</span>
                            <span className="text-sm">{data.resume.profile.location}</span>
                          </div>
                        )}
                        {data.resume.profile.linkedin && (
                          <div className="flex flex-col sm:flex-row sm:gap-2">
                            <span className="font-medium text-sm min-w-[120px]">LinkedIn:</span>
                            <a href={data.resume.profile.linkedin} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline break-all">
                              {data.resume.profile.linkedin}
                            </a>
                          </div>
                        )}
                        {data.resume.profile.github && (
                          <div className="flex flex-col sm:flex-row sm:gap-2">
                            <span className="font-medium text-sm min-w-[120px]">GitHub:</span>
                            <a href={data.resume.profile.github} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline break-all">
                              {data.resume.profile.github}
                            </a>
                          </div>
                        )}
                        {data.resume.profile.leetcode && (
                          <div className="flex flex-col sm:flex-row sm:gap-2">
                            <span className="font-medium text-sm min-w-[120px]">LeetCode:</span>
                            <a href={data.resume.profile.leetcode} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline break-all">
                              {data.resume.profile.leetcode}
                            </a>
                          </div>
                        )}
                        {data.resume.profile.hackerrank && (
                          <div className="flex flex-col sm:flex-row sm:gap-2">
                            <span className="font-medium text-sm min-w-[120px]">HackerRank:</span>
                            <a href={data.resume.profile.hackerrank} target="_blank" rel="noopener noreferrer" className="text-sm text-primary hover:underline break-all">
                              {data.resume.profile.hackerrank}
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Domain & Confidence */}
                  {data.resume.domain && (
                    <div className="space-y-2">
                      <h4 className="font-medium text-base">
                        🎯 Domain Classification
                      </h4>
                      <div className="rounded-md border bg-card p-4">
                        <div className="flex items-center justify-between text-sm">
                          <span className="font-medium">{data.resume.domain}</span>
                          {data.resume.domainConfidence && (
                            <span className="text-muted-foreground">
                              Confidence: {(data.resume.domainConfidence * 100).toFixed(0)}%
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  )}

                  {/* Skills */}
                  {data.resume.skills && (
                    <div className="space-y-2">
                      <h4 className="font-medium text-base">
                        💼 Skills
                      </h4>
                      <div className="rounded-md border bg-card p-4 space-y-3">
                        {data.resume.skills.provided && data.resume.skills.provided.length > 0 && (
                          <div>
                            <p className="text-sm font-medium mb-2">Provided Skills:</p>
                            <div className="flex flex-wrap gap-2">
                              {data.resume.skills.provided.map((skill: string, idx: number) => (
                                <span key={idx} className="px-2 py-1 bg-muted text-xs rounded-md">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {data.resume.skills.inferred && data.resume.skills.inferred.length > 0 && (
                          <div>
                            <p className="text-sm font-medium mb-2">Inferred Skills:</p>
                            <div className="flex flex-wrap gap-2">
                              {data.resume.skills.inferred.map((skill: string, idx: number) => (
                                <span key={idx} className="px-2 py-1 bg-muted text-xs rounded-md">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                        {data.resume.skills.softSkills && data.resume.skills.softSkills.length > 0 && (
                          <div>
                            <p className="text-sm font-medium mb-2">Soft Skills:</p>
                            <div className="flex flex-wrap gap-2">
                              {data.resume.skills.softSkills.map((skill: string, idx: number) => (
                                <span key={idx} className="px-2 py-1 bg-muted text-xs rounded-md">
                                  {skill}
                                </span>
                              ))}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Experience */}
                  {data.resume.experience && data.resume.experience.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="font-medium text-base">
                        💼 Work Experience
                      </h4>
                      
                      {/* Experience Summary */}
                      {data.resume.experienceSummary && (
                        <div className="rounded-md border bg-muted/50 p-3">
                          <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                            {data.resume.experienceSummary.totalFullTime > 0 && (
                              <div>
                                <span className="font-medium">Full Time:</span>{' '}
                                <span>{data.resume.experienceSummary.totalFullTime} months</span>
                                <span className="ml-1">
                                  ({Math.floor(data.resume.experienceSummary.totalFullTime / 12)}y {data.resume.experienceSummary.totalFullTime % 12}m)
                                </span>
                              </div>
                            )}
                            {data.resume.experienceSummary.totalInternship > 0 && (
                              <div>
                                <span className="font-medium">Internship:</span>{' '}
                                <span>{data.resume.experienceSummary.totalInternship} months</span>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Experience Details */}
                      <div className="space-y-3">
                        {data.resume.experience.map((exp: any, idx: number) => (
                          <div key={idx} className="rounded-md border bg-card p-4 space-y-2">
                            {/* Company and Employment Type */}
                            <div className="flex justify-between items-start gap-2">
                              <h5 className="font-semibold text-base">{exp.company || 'Company Not Specified'}</h5>
                              {exp.employmentType && (
                                <span className="text-xs px-2 py-1 bg-muted text-muted-foreground rounded-md whitespace-nowrap">
                                  {exp.employmentType}
                                </span>
                              )}
                            </div>

                            {/* Role */}
                            <p className="text-sm text-foreground">{exp.role || 'Role Not Specified'}</p>

                            {/* Duration */}
                            {(exp.startDate || exp.endDate) && (
                              <p className="text-sm text-muted-foreground">
                                {exp.startDate ? new Date(exp.startDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'N/A'} 
                                {' - '}
                                {exp.endDate ? new Date(exp.endDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'Present'}
                              </p>
                            )}

                            {/* Skills Used */}
                            {exp.skillsUsed && exp.skillsUsed.length > 0 && (
                              <div>
                                <p className="text-xs text-muted-foreground mb-1.5">Skills:</p>
                                <div className="flex flex-wrap gap-1.5">
                                  {exp.skillsUsed.map((skill: string, i: number) => (
                                    <span key={i} className="px-2 py-0.5 bg-muted text-xs rounded">
                                      {skill}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Achievements */}
                            {exp.achievements && exp.achievements.length > 0 && (
                              <ul className="space-y-1 text-sm text-muted-foreground">
                                {exp.achievements.map((achievement: string, i: number) => (
                                  <li key={i} className="flex items-start gap-2">
                                    <span className="mt-1.5">•</span>
                                    <span className="flex-1">{achievement}</span>
                                  </li>
                                ))}
                              </ul>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Projects */}
                  {data.resume.projects && data.resume.projects.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="font-medium text-base">
                        🚀 Projects
                      </h4>
                      <div className="space-y-3">
                        {data.resume.projects.map((project: any, idx: number) => (
                          <div key={idx} className="rounded-md border bg-card p-4 space-y-2">
                            {/* Project Title and Domain */}
                            <div className="flex items-start justify-between gap-2">
                              <h5 className="font-semibold text-base">
                                {project.title || 'Untitled Project'}
                              </h5>
                              {project.domain && (
                                <span className="text-xs px-2 py-1 bg-muted text-muted-foreground rounded-md whitespace-nowrap">
                                  {project.domain}
                                </span>
                              )}
                            </div>

                            {/* Description */}
                            {project.description && (
                              <p className="text-sm text-muted-foreground">
                                {project.description}
                              </p>
                            )}

                            {/* Links */}
                            {(project.demoLink || project.codeLink) && (
                              <div className="flex flex-wrap gap-2">
                                {project.demoLink && (
                                  <a 
                                    href={project.demoLink} 
                                    target="_blank" 
                                    rel="noopener noreferrer" 
                                    className="text-xs text-primary hover:underline"
                                  >
                                    🔗 Demo
                                  </a>
                                )}
                                {project.codeLink && (
                                  <a 
                                    href={project.codeLink} 
                                    target="_blank" 
                                    rel="noopener noreferrer" 
                                    className="text-xs text-primary hover:underline"
                                  >
                                    💻 Code
                                  </a>
                                )}
                              </div>
                            )}

                            {/* Skills Used */}
                            {project.skillsUsed && project.skillsUsed.length > 0 && (
                              <div>
                                <p className="text-xs text-muted-foreground mb-1.5">Technologies:</p>
                                <div className="flex flex-wrap gap-1.5">
                                  {project.skillsUsed.map((skill: string, i: number) => (
                                    <span key={i} className="px-2 py-0.5 bg-muted text-xs rounded">
                                      {skill}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}

                            {/* Metrics */}
                            {project.metrics && (
                              <div className="pt-2 border-t">
                                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                                  {project.metrics.difficulty !== undefined && (
                                    <div className="text-xs">
                                      <span className="text-muted-foreground">Difficulty: </span>
                                      <span className="font-medium">{project.metrics.difficulty}/10</span>
                                    </div>
                                  )}
                                  {project.metrics.complexity !== undefined && (
                                    <div className="text-xs">
                                      <span className="text-muted-foreground">Complexity: </span>
                                      <span className="font-medium">{project.metrics.complexity}/10</span>
                                    </div>
                                  )}
                                  {project.metrics.domainRelevance !== undefined && (
                                    <div className="text-xs">
                                      <span className="text-muted-foreground">Relevance: </span>
                                      <span className="font-medium">{project.metrics.domainRelevance}/10</span>
                                    </div>
                                  )}
                                  {project.metrics.impact !== undefined && (
                                    <div className="text-xs">
                                      <span className="text-muted-foreground">Impact: </span>
                                      <span className="font-medium">{(project.metrics.impact * 10).toFixed(1)}/10</span>
                                    </div>
                                  )}
                                </div>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Education */}
                  {data.resume.education && data.resume.education.length > 0 && (
                    <div className="space-y-3">
                      <h4 className="font-medium text-base">
                        🎓 Education
                      </h4>
                      <div className="space-y-3">
                        {data.resume.education.map((edu: any, idx: number) => (
                          <div key={idx} className="rounded-md border bg-card p-4 space-y-2">
                            {/* College/University */}
                            <h5 className="font-semibold text-base">
                              {edu.college || 'Institution Not Specified'}
                            </h5>

                            {/* Degree */}
                            <p className="text-sm text-foreground">
                              {edu.degree || 'Degree Not Specified'}
                            </p>

                            {/* Department */}
                            {edu.department && (
                              <p className="text-sm text-muted-foreground">
                                {edu.department}
                              </p>
                            )}

                            {/* Duration and Grade */}
                            <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                              {(edu.startDate || edu.endDate) && (
                                <span>
                                  {edu.startDate ? new Date(edu.startDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'N/A'}
                                  {' - '}
                                  {edu.endDate ? new Date(edu.endDate).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) : 'Present'}
                                </span>
                              )}
                              {edu.grade && (
                                <span>
                                  Grade: <span className="font-medium">{edu.grade}</span>
                                </span>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Certifications */}
                  {data.resume.certifications && data.resume.certifications.length > 0 && (
                    <div className="space-y-2">
                      <h4 className="font-medium text-base">
                        📜 Certifications
                      </h4>
                      <div className="rounded-md border bg-card p-4">
                        <ul className="space-y-2">
                          {data.resume.certifications.map((cert: any, idx: number) => (
                            <li key={idx} className="text-sm flex items-start gap-2">
                              <span className="mt-1">•</span>
                              <span className="flex-1">
                                {typeof cert === 'string' ? cert : cert.title}
                                {cert.url && (
                                  <a href={cert.url} target="_blank" rel="noopener noreferrer" className="ml-2 text-primary hover:underline text-xs">
                                    🔗 View
                                  </a>
                                )}
                              </span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  )}

                  {/* Achievements */}
                  {data.resume.achievements && (
                    <div className="space-y-2">
                      <h4 className="font-medium text-base">
                        🏆 Achievements
                      </h4>
                      <div className="rounded-md border bg-card p-4 space-y-3">
                        {/* Handle both array format and object format */}
                        {Array.isArray(data.resume.achievements) ? (
                          <ul className="space-y-2">
                            {data.resume.achievements.map((achievement: string, idx: number) => (
                              <li key={idx} className="text-sm flex items-start gap-2">
                                <span className="mt-1">•</span>
                                <span className="flex-1">{achievement}</span>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <>
                            {data.resume.achievements.awards && data.resume.achievements.awards.length > 0 && (
                              <div>
                                <p className="text-sm font-medium mb-2">Awards:</p>
                                <ul className="space-y-1">
                                  {data.resume.achievements.awards.map((award: string, idx: number) => (
                                    <li key={idx} className="text-sm flex items-start gap-2 ml-2">
                                      <span className="mt-1">•</span>
                                      <span className="flex-1">{award}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {data.resume.achievements.hackathons && data.resume.achievements.hackathons.length > 0 && (
                              <div>
                                <p className="text-sm font-medium mb-2">Hackathons:</p>
                                <ul className="space-y-1">
                                  {data.resume.achievements.hackathons.map((hackathon: string, idx: number) => (
                                    <li key={idx} className="text-sm flex items-start gap-2 ml-2">
                                      <span className="mt-1">•</span>
                                      <span className="flex-1">{hackathon}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {data.resume.achievements.researchPapers && data.resume.achievements.researchPapers.length > 0 && (
                              <div>
                                <p className="text-sm font-medium mb-2">Research Papers:</p>
                                <ul className="space-y-1">
                                  {data.resume.achievements.researchPapers.map((paper: string, idx: number) => (
                                    <li key={idx} className="text-sm flex items-start gap-2 ml-2">
                                      <span className="mt-1">•</span>
                                      <span className="flex-1">{paper}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                            {data.resume.achievements.other && data.resume.achievements.other.length > 0 && (
                              <div>
                                <p className="text-sm font-medium mb-2">Other:</p>
                                <ul className="space-y-1">
                                  {data.resume.achievements.other.map((item: string, idx: number) => (
                                    <li key={idx} className="text-sm flex items-start gap-2 ml-2">
                                      <span className="mt-1">•</span>
                                      <span className="flex-1">{item}</span>
                                    </li>
                                  ))}
                                </ul>
                              </div>
                            )}
                          </>
                        )}
                      </div>
                    </div>
                  )}

                  {/* Processing Metadata */}
                  <div className="space-y-2">
                    <h4 className="font-medium text-base">
                      ℹ️ Processing Information
                    </h4>
                    <div className="rounded-md border bg-card p-4 space-y-1 text-sm">
                      <p>
                        <span className="font-medium">Status:</span>{' '}
                        <span className="capitalize">
                          {data.resume.status}
                        </span>
                      </p>
                      <p>
                        <span className="font-medium">Uploaded:</span>{' '}
                        {new Date(data.resume.uploadedAt).toLocaleString()}
                      </p>
                      {data.resume.processedAt && (
                        <p>
                          <span className="font-medium">Processed:</span>{' '}
                          {new Date(data.resume.processedAt).toLocaleString()}
                        </p>
                      )}
                    </div>
                  </div>
                </>
              )}

              {/* Error State */}
              {data.resume.status === 'failed' && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                  <p className="text-sm text-red-800">
                    <span className="font-medium">Processing failed:</span>{' '}
                    {data.resume.processingError || 'Unknown error'}
                  </p>
                </div>
              )}
            </div>
          </TabsContent>
        </div>
      </Tabs>
    </div>
  );
}

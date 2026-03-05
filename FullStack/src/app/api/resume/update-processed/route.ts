/**
 * Resume Processed Data Update API Route
 * POST /api/resume/update-processed
 * 
 * Updates a resume with AI-extracted data
 * Called by the worker after successful resume processing
 */

import { NextRequest, NextResponse } from 'next/server';
import { connectToDatabase } from '@/backend/config/database';
import { Resume } from '@/backend/models';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { resumeId, extractedData } = body;

    // Validate required fields
    if (!resumeId || !extractedData) {
      return NextResponse.json(
        { error: 'resumeId and extractedData are required' },
        { status: 400 }
      );
    }

    // Connect to database
    await connectToDatabase();

    // Prepare update data - map from AI format to database schema
    const updateData: any = {};

    // Profile information
    if (extractedData.profile) {
      updateData.profile = {
        name: extractedData.profile.name || undefined,
        contact: extractedData.profile.contact || undefined,
        email: extractedData.profile.email || undefined,
        linkedin: extractedData.profile.linkedin || undefined,
        github: extractedData.profile.github || undefined,
        leetcode: extractedData.profile.leetcode || undefined,
        hackerrank: extractedData.profile.hackerrank || undefined,
        location: extractedData.profile.location || undefined,
      };
    }

    // Domain
    if (extractedData.domain) {
      updateData.domain = extractedData.domain;
    }

    // Domain Confidence
    if (extractedData.confidence !== undefined && extractedData.confidence !== null) {
      updateData.domainConfidence = extractedData.confidence;
    }

    // Skills
    if (extractedData.skills) {
      updateData.skills = {
        provided: extractedData.skills.provided || [],
        inferred: extractedData.skills.inferred || [],
        softSkills: extractedData.skills.soft_skills || [],
      };
    }

    // Experience Summary
    if (extractedData.experience) {
      updateData.experienceSummary = {
        totalFullTime: extractedData.experience.total_full_time_experience || 0,
        totalInternship: extractedData.experience.total_internship_experience_in_months || 0,
      };

      // Experience details
      if (extractedData.experience.details && Array.isArray(extractedData.experience.details)) {
        updateData.experience = extractedData.experience.details.map((exp: any) => {
          // Helper to validate and parse dates
          const parseDate = (dateStr: any) => {
            if (!dateStr) return undefined;
            if (typeof dateStr === 'string' && dateStr.toLowerCase() === 'present') return 'present';
            const date = new Date(dateStr);
            return !isNaN(date.getTime()) ? date : undefined;
          };

          return {
            company: exp.company || 'Unknown',
            role: exp.role || 'Unknown',
            startDate: parseDate(exp.start),
            endDate: parseDate(exp.end),
            employmentType: exp.employment_type || 'Full Time',
            skillsUsed: [], // Can be inferred from impact if needed
            achievements: exp.impact || [],
          };
        });
      }
    }

    // Projects
    if (extractedData.projects && Array.isArray(extractedData.projects)) {
      updateData.projects = extractedData.projects.map((proj: any) => ({
        title: proj.title || 'Untitled Project',
        domain: extractedData.domain || undefined,
        skillsUsed: [], // Can be extracted from description if available
        demoLink: proj.demo_link || undefined,
        codeLink: proj.code_link || undefined,
        description: undefined,
        metrics: proj.metric_ai ? {
          impact: proj.metric_ai.impact || undefined,
          difficulty: proj.metric_ai.difficulty || undefined,
          complexity: proj.metric_ai.complexity || undefined,
          domainRelevance: proj.metric_ai.domain_relevance || undefined,
        } : undefined,
      }));
    }

    // Education
    if (extractedData.educations && Array.isArray(extractedData.educations)) {
      // Helper to validate and parse dates
      const parseDate = (dateStr: any) => {
        if (!dateStr) return undefined;
        if (typeof dateStr === 'string' && dateStr.toLowerCase() === 'present') return 'present';
        const date = new Date(dateStr);
        return !isNaN(date.getTime()) ? date : undefined;
      };

      updateData.education = extractedData.educations
        .filter((edu: any) => edu.college && edu.degree && edu.department)
        .map((edu: any) => ({
          startDate: parseDate(edu.start),
          endDate: parseDate(edu.end),
          college: edu.college,
          degree: edu.degree,
          department: edu.department,
          grade: edu.grade || undefined,
        }));
    }

    // Certifications
    if (extractedData.certifications && Array.isArray(extractedData.certifications)) {
      updateData.certifications = extractedData.certifications
        .filter((cert: any) => cert && typeof cert === 'string')
        .map((cert: string) => ({
          title: cert,
          url: undefined,
          skills: [],
          issuedDate: undefined,
          expiryDate: undefined,
        }));
    }

    // Achievements
    if (extractedData.achievements && Array.isArray(extractedData.achievements)) {
      updateData.achievements = {
        hackathons: [],
        researchPapers: [],
        awards: extractedData.achievements,
        other: [],
      };
    }

    // Update the resume
    const updatedResume = await Resume.findByIdAndUpdate(
      resumeId,
      { $set: updateData },
      { new: true, runValidators: true }
    );

    if (!updatedResume) {
      return NextResponse.json(
        { error: 'Resume not found' },
        { status: 404 }
      );
    }

    return NextResponse.json({
      success: true,
      data: {
        resumeId: updatedResume._id,
        profile: updatedResume.profile,
        domain: updatedResume.domain,
        experienceSummary: updatedResume.experienceSummary,
      },
      message: 'Resume data updated successfully',
    });

  } catch (error) {
    console.error('Error updating resume data:', error);
    return NextResponse.json(
      {
        error: 'Failed to update resume data',
        details: error instanceof Error ? error.message : 'Unknown error',
      },
      { status: 500 }
    );
  }
}

// OPTIONS for CORS
export async function OPTIONS() {
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    },
  });
}

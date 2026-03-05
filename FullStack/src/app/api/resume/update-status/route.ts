/**
 * Resume Status Update API Route
 * POST /api/resume/update-status
 * 
 * Updates the processing status of a resume
 * Called by the worker during resume processing lifecycle
 */

import { NextRequest, NextResponse } from 'next/server';
import { ResumeService } from '@/backend/services/resume.service';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { resumeId, status, error } = body;

    // Validate required fields
    if (!resumeId || !status) {
      return NextResponse.json(
        { error: 'resumeId and status are required' },
        { status: 400 }
      );
    }

    // Validate status value
    const validStatuses = ['uploaded', 'processing', 'completed', 'failed'];
    if (!validStatuses.includes(status)) {
      return NextResponse.json(
        { error: `Invalid status. Must be one of: ${validStatuses.join(', ')}` },
        { status: 400 }
      );
    }

    // Update resume status
    const updatedResume = await ResumeService.updateResumeStatus(
      resumeId,
      status,
      error
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
        status: updatedResume.status,
        processedAt: updatedResume.processedAt,
      },
    });

  } catch (error) {
    console.error('Error updating resume status:', error);
    return NextResponse.json(
      {
        error: 'Failed to update resume status',
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

/**
 * JD Status Update API Route
 * POST /api/jd/update-status
 *
 * Updates the processing status of a JD.
 * Called by the Python worker during the JD processing lifecycle.
 */

import { NextRequest, NextResponse } from 'next/server';
import { JDService } from '@/backend/services/jd.service';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { jdId, status, error } = body;

    if (!jdId || !status) {
      return NextResponse.json(
        { error: 'jdId and status are required' },
        { status: 400 }
      );
    }

    const validStatuses = ['uploaded', 'processing', 'completed', 'failed'];
    if (!validStatuses.includes(status)) {
      return NextResponse.json(
        { error: `Invalid status. Must be one of: ${validStatuses.join(', ')}` },
        { status: 400 }
      );
    }

    const updatedJD = await JDService.updateJDStatus(jdId, status, error);

    if (!updatedJD) {
      return NextResponse.json({ error: 'JD not found' }, { status: 404 });
    }

    return NextResponse.json({
      success: true,
      data: {
        jdId: updatedJD._id,
        status: updatedJD.status,
        processedAt: updatedJD.processedAt,
      },
    });

  } catch (error) {
    console.error('Error updating JD status:', error);
    return NextResponse.json(
      { error: 'Failed to update JD status', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

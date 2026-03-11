/**
 * JD Processed Data Update API Route
 * POST /api/jd/update-processed
 *
 * Called by the Python worker after successful JD processing.
 * Saves AI-extracted data and marks the JD as completed.
 */

import { NextRequest, NextResponse } from 'next/server';
import { JDService } from '@/backend/services/jd.service';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { jdId, extractedData } = body;

    if (!jdId || !extractedData) {
      return NextResponse.json(
        { error: 'jdId and extractedData are required' },
        { status: 400 }
      );
    }

    const updatedJD = await JDService.updateJDExtractedData(jdId, extractedData);

    if (!updatedJD) {
      return NextResponse.json({ error: 'JD not found' }, { status: 404 });
    }

    return NextResponse.json({
      success: true,
      data: {
        jdId: updatedJD._id,
        status: updatedJD.status,
        processedAt: updatedJD.processedAt,
        extractedData: updatedJD.extractedData,
      },
    });

  } catch (error) {
    console.error('Error updating JD processed data:', error);
    return NextResponse.json(
      { error: 'Failed to update JD processed data', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

/**
 * Fetch Scoring Job Data
 * GET /api/score/job-data/[runId]
 *
 * The [runId] segment is actually a ScorePair ID (kept as-is to avoid
 * renaming the folder). Called by the Python worker at the start of a job.
 * Returns { jdData, resumeData } for the specific pair.
 */

import { NextRequest, NextResponse } from 'next/server';
import { ScoreService } from '@/backend/services/score.service';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ runId: string }> }
) {
  try {
    const { runId: scorePairId } = await params;
    if (!scorePairId) {
      return NextResponse.json({ error: 'scorePairId is required' }, { status: 400 });
    }

    const data = await ScoreService.getJobData(scorePairId);
    if (!data) {
      return NextResponse.json({ error: 'Score pair, JD, or Resume not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true, data });
  } catch (error) {
    console.error('Error fetching score job data:', error);
    return NextResponse.json(
      { error: 'Failed to fetch job data', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

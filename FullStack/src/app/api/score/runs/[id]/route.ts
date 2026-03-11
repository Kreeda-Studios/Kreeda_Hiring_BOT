/**
 * Get Single Score Run
 * GET /api/score/runs/[id]
 */

import { NextRequest, NextResponse } from 'next/server';
import { ScoreService } from '@/backend/services/score.service';

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params;
    if (!id) {
      return NextResponse.json({ error: 'Score run ID is required' }, { status: 400 });
    }

    const result = await ScoreService.getScoreRunById(id);
    if (!result) {
      return NextResponse.json({ error: 'Score run not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true, data: result });
  } catch (error) {
    console.error('Error fetching score run:', error);
    return NextResponse.json(
      { error: 'Failed to fetch score run', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

/**
 * Create Score Run
 * POST /api/score/run
 * Body: { jdId: string; resumeIds: string[] }
 *
 * Creates one parent ScoreRun + one ScorePair per resume, then
 * enqueues each pair as an independent job.
 */

import { NextRequest, NextResponse } from 'next/server';
import { ScoreService } from '@/backend/services/score.service';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { jdId, resumeIds } = body;

    if (!jdId || !resumeIds || !Array.isArray(resumeIds) || resumeIds.length === 0) {
      return NextResponse.json(
        { error: 'jdId and a non-empty resumeIds array are required' },
        { status: 400 }
      );
    }

    const { run, pairs } = await ScoreService.createScoreRun({ jdId, resumeIds });

    return NextResponse.json({
      success: true,
      data: {
        scoreRunId:   run._id,
        jdFileName:   run.jdFileName,
        pairsCreated: pairs.length,
        pairs: pairs.map((p) => ({
          scorePairId:    p._id,
          resumeId:       p.resumeId,
          resumeFileName: p.resumeFileName,
          candidateName:  p.candidateName,
          status:         p.status,
          createdAt:      p.createdAt,
        })),
      },
    });
  } catch (error) {
    console.error('Error creating score run:', error);
    return NextResponse.json(
      { error: 'Failed to create score run', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}

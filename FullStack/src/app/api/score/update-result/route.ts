/**
 * Save Score Result
 * POST /api/score/update-result
 *
 * Called by the Python worker after evaluating a single (JD, Resume) pair.
 * Body: { scorePairId: string; result: { ...scores, missingSkills, strengths, concerns } }
 * On error path: { scorePairId: string; error: string }
 */

import { NextRequest, NextResponse } from 'next/server';
import { ScoreService } from '@/backend/services/score.service';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { scorePairId, result, error: workerError } = body;

    if (!scorePairId) {
      return NextResponse.json(
        { error: 'scorePairId is required' },
        { status: 400 }
      );
    }

    // Error path — mark the pair as failed
    if (workerError && !result) {
      const updated = await ScoreService.markPairFailed(scorePairId, workerError);
      if (!updated) return NextResponse.json({ error: 'Score pair not found' }, { status: 404 });
      return NextResponse.json({ success: true });
    }

    if (!result) {
      return NextResponse.json({ error: 'result payload is required' }, { status: 400 });
    }

    const updated = await ScoreService.updatePairResult(scorePairId, {
      candidateName:        result.candidate_name,
      overallScore:         result.overall_score,
      skillMatch:           result.skill_match,
      experienceMatch:      result.experience_match,
      techStackMatch:       result.tech_stack_match,
      projectRelevance:     result.project_relevance,
      responsibilityMatch:  result.responsibility_match,
      impactStrength:       result.impact_strength,
      educationMatch:       result.education_match,
      criticalSkillGapScore: result.critical_skill_gap_score,
      missingSkills: result.missing_skills ?? [],
      strengths:     result.strengths ?? [],
      concerns:      result.concerns ?? [],
    });

    if (!updated) {
      return NextResponse.json({ error: 'Score pair not found' }, { status: 404 });
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Error updating score result:', error);
    return NextResponse.json(
      { error: 'Failed to update score result', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}


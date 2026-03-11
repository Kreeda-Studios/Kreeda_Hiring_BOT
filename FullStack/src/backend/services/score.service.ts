/**
 * Score Service
 *
 * ScoreRun (parent): 1 document per submission — holds the JD and aggregate counts.
 * ScorePair (child): 1 document per (JD, Resume) pair — holds individual scores.
 *
 * createScoreRun()  → creates 1 ScoreRun + N ScorePairs + enqueues N jobs.
 * getScoreRuns()    → paginated list of parent runs.
 * getScoreRunById() → parent run + all its pairs.
 * updatePairStatus()  → mark a pair as processing / failed.
 * updatePairResult()  → save AI scores to a pair, update parent run counts.
 * getJobData()      → everything a worker needs for one pair.
 */

import mongoose from 'mongoose';
import { ScoreRun, ScorePair, Resume, JD } from '../models';
import type { IScoreRun } from '../models/scoreRun';
import type { IScorePair } from '../models/scorePair';
import { scoreQueue } from '../config/bullmq';
import { connectToDatabase } from '../config/database';

// ─── Public interfaces ────────────────────────────────────────────────────────

export interface CreateScoreRunData {
  jdId: string;
  resumeIds: string[];
}

export interface ScoreResultUpdate {
  candidateName?: string;
  overallScore?: number;
  skillMatch?: number;
  experienceMatch?: number;
  techStackMatch?: number;
  projectRelevance?: number;
  responsibilityMatch?: number;
  impactStrength?: number;
  educationMatch?: number;
  criticalSkillGapScore?: number;
  missingSkills?: string[];
  strengths?: string[];
  concerns?: string[];
}

// ─── Service ──────────────────────────────────────────────────────────────────

export class ScoreService {
  /**
   * Create one ScoreRun (parent) + one ScorePair per resume, then enqueue each pair.
   */
  static async createScoreRun(data: CreateScoreRunData): Promise<{
    run: IScoreRun;
    pairs: IScorePair[];
  }> {
    await connectToDatabase();

    const jd = await JD.findById(data.jdId);
    if (!jd) throw new Error('JD not found');

    const jdFileName = jd.originalFileName || jd.fileName;

    // Resolve resume metadata in one query
    const resumeDocs = await Resume.find(
      { _id: { $in: data.resumeIds } },
      { originalFileName: 1, fileName: 1, profile: 1 }
    );

    const resumeMap = new Map(
      resumeDocs.map((r) => [
        r._id.toString(),
        {
          fileName:      r.originalFileName || r.fileName,
          candidateName: (r.profile as { name?: string } | undefined)?.name,
        },
      ])
    );

    // Create the parent ScoreRun
    const run = await ScoreRun.create({
      jdId:          new mongoose.Types.ObjectId(data.jdId),
      jdFileName,
      totalResumes:  data.resumeIds.length,
      completedCount: 0,
      failedCount:   0,
      status:        'queued',
    });

    // Create one ScorePair per resume
    const pairDocs = data.resumeIds.map((rid) => {
      const meta = resumeMap.get(rid) ?? { fileName: rid, candidateName: undefined };
      return {
        scoreRunId:     run._id,
        jdId:           new mongoose.Types.ObjectId(data.jdId),
        resumeId:       new mongoose.Types.ObjectId(rid),
        resumeFileName: meta.fileName,
        candidateName:  meta.candidateName,
        status:         'queued' as const,
        missingSkills:  [],
        strengths:      [],
        concerns:       [],
      };
    });

    const pairs = await ScorePair.insertMany(pairDocs);

    // Enqueue one job per pair
    await Promise.all(
      pairs.map((pair) =>
        scoreQueue.add(
          'score-pair',
          { scorePairId: pair._id.toString() },
          { attempts: 2, backoff: { type: 'exponential', delay: 3000 } }
        )
      )
    );

    return { run: run as unknown as IScoreRun, pairs: pairs as unknown as IScorePair[] };
  }

  /**
   * Paginated list of parent ScoreRuns, newest first.
   */
  static async getScoreRuns(
    page: number,
    limit: number
  ): Promise<{ runs: IScoreRun[]; total: number; totalPages: number }> {
    await connectToDatabase();

    const total      = await ScoreRun.countDocuments();
    const totalPages = Math.ceil(total / limit);
    const skip       = (page - 1) * limit;

    const runs = await ScoreRun.find()
      .sort({ createdAt: -1 })
      .skip(skip)
      .limit(limit);

    return { runs, total, totalPages };
  }

  /**
   * Get one ScoreRun (parent) and all its ScorePairs.
   */
  static async getScoreRunById(id: string): Promise<{
    run: IScoreRun;
    pairs: IScorePair[];
  } | null> {
    await connectToDatabase();

    const run = await ScoreRun.findById(id);
    if (!run) return null;

    const pairs = await ScorePair.find({ scoreRunId: id }).sort({ createdAt: 1 });

    return { run, pairs };
  }

  /**
   * Mark a pair as processing (called when job starts).
   * Also flips the parent run status to 'processing' on the first call.
   */
  static async updatePairStatus(
    pairId: string,
    status: 'queued' | 'processing' | 'completed' | 'failed',
    error?: string
  ): Promise<IScorePair | null> {
    await connectToDatabase();

    const update: Record<string, unknown> = { status };
    if (status === 'completed' || status === 'failed') update.completedAt = new Date();
    if (error) update.errorMessage = error;

    const pair = await ScorePair.findByIdAndUpdate(pairId, update, { new: true });
    if (!pair) return null;

    // Flip parent run to 'processing' as soon as any pair starts
    if (status === 'processing') {
      await ScoreRun.findByIdAndUpdate(pair.scoreRunId, { status: 'processing' });
    }

    return pair;
  }

  /**
   * Save the AI evaluation result for a pair.
   * Increments completedCount / failedCount on the parent run and
   * marks the parent 'completed' or 'failed' when all pairs are done.
   */
  static async updatePairResult(
    pairId: string,
    result: ScoreResultUpdate
  ): Promise<IScorePair | null> {
    await connectToDatabase();

    const set: Record<string, unknown> = {
      status:      'completed',
      completedAt: new Date(),
    };

    if (result.candidateName         !== undefined) set.candidateName         = result.candidateName;
    if (result.overallScore          !== undefined) set.overallScore          = result.overallScore;
    if (result.skillMatch            !== undefined) set.skillMatch            = result.skillMatch;
    if (result.experienceMatch       !== undefined) set.experienceMatch       = result.experienceMatch;
    if (result.techStackMatch        !== undefined) set.techStackMatch        = result.techStackMatch;
    if (result.projectRelevance      !== undefined) set.projectRelevance      = result.projectRelevance;
    if (result.responsibilityMatch   !== undefined) set.responsibilityMatch   = result.responsibilityMatch;
    if (result.impactStrength        !== undefined) set.impactStrength        = result.impactStrength;
    if (result.educationMatch        !== undefined) set.educationMatch        = result.educationMatch;
    if (result.criticalSkillGapScore !== undefined) set.criticalSkillGapScore = result.criticalSkillGapScore;
    if (result.missingSkills !== undefined) set.missingSkills = result.missingSkills;
    if (result.strengths     !== undefined) set.strengths     = result.strengths;
    if (result.concerns      !== undefined) set.concerns      = result.concerns;

    const pair = await ScorePair.findByIdAndUpdate(pairId, { $set: set }, { new: true });
    if (!pair) return null;

    // Increment parent completed count and maybe finalize
    await this.maybeFinishRun(pair.scoreRunId.toString(), 'completed');

    return pair;
  }

  /**
   * Record a failed pair result and potentially finalize the parent run.
   */
  static async markPairFailed(pairId: string, errorMessage: string): Promise<IScorePair | null> {
    await connectToDatabase();

    const pair = await ScorePair.findByIdAndUpdate(
      pairId,
      { status: 'failed', errorMessage, completedAt: new Date() },
      { new: true }
    );
    if (!pair) return null;

    await this.maybeFinishRun(pair.scoreRunId.toString(), 'failed');

    return pair;
  }

  /**
   * Increment the appropriate counter on the parent run.
   * If completed + failed == total, mark the run done.
   */
  private static async maybeFinishRun(
    runId: string,
    outcome: 'completed' | 'failed'
  ): Promise<void> {
    const inc =
      outcome === 'completed'
        ? { $inc: { completedCount: 1 } }
        : { $inc: { failedCount: 1 } };

    const run = await ScoreRun.findByIdAndUpdate(runId, inc, { new: true });
    if (!run) return;

    const done = run.completedCount + run.failedCount;
    if (done >= run.totalResumes) {
      const finalStatus = run.failedCount === run.totalResumes ? 'failed' : 'completed';
      await ScoreRun.findByIdAndUpdate(runId, {
        status:      finalStatus,
        completedAt: new Date(),
      });
    }
  }

  /**
   * Fetch everything a Python worker needs in order to score one pair.
   */
  static async getJobData(scorePairId: string): Promise<{
    jdData: Record<string, unknown>;
    resumeData: Record<string, unknown>;
  } | null> {
    await connectToDatabase();

    const pair = await ScorePair.findById(scorePairId);
    if (!pair) return null;

    const [jd, resume] = await Promise.all([
      JD.findById(pair.jdId),
      Resume.findById(pair.resumeId),
    ]);

    if (!jd || !resume) return null;

    return {
      jdData:     (jd.extractedData as Record<string, unknown>) ?? {},
      resumeData: {
        profile:           resume.profile,
        domain:            resume.domain,
        skills:            resume.skills,
        experienceSummary: resume.experienceSummary,
        experience:        resume.experience,
        projects:          resume.projects,
        education:         resume.education,
        certifications:    resume.certifications,
        achievements:      resume.achievements,
      },
    };
  }
}

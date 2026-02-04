import { Router, Request, Response } from 'express';
import { sseService } from '../services/sseService';

const router = Router();

/**
 * SSE endpoint for job progress updates
 * GET /api/sse/jobs/:jobId/progress
 */
router.get('/jobs/:jobId/progress', (req: Request, res: Response) => {
  const { jobId } = req.params;

  if (!jobId) {
    res.status(400).json({ error: 'Job ID is required' });
    return;
  }

  console.log(`📡 New SSE connection request for job: ${jobId}`);

  // Add client and keep connection open
  sseService.addClient(jobId, res);
});

/**
 * SSE endpoint for Flow parent job progress (alias for clarity)
 * GET /api/sse/flow/:parentJobId/progress
 */
router.get('/flow/:parentJobId/progress', (req: Request, res: Response) => {
  const { parentJobId } = req.params;

  if (!parentJobId) {
    res.status(400).json({ error: 'Parent job ID is required' });
    return;
  }

  console.log(`📡 New SSE connection request for Flow job: ${parentJobId}`);

  // Add client and keep connection open (uses same service as regular jobs)
  sseService.addClient(parentJobId, res);
});

/**
 * Get SSE service stats (for debugging)
 * GET /api/sse/stats
 */
router.get('/stats', (req: Request, res: Response) => {
  res.json({
    totalConnections: sseService.getTotalClientCount(),
  });
});

export default router;

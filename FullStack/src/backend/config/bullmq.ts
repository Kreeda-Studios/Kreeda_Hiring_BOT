/**
 * BullMQ Queue Configuration
 */

import { Queue, QueueOptions } from 'bullmq';
import { redis } from './redis';

const queueOptions: QueueOptions = {
  connection: redis,
};

export const resumeQueue = new Queue('resume-processing', queueOptions);

export const queues = {
  resume: resumeQueue,
};

export default queues;

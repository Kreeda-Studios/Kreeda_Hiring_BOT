
import { Queue, QueueOptions } from 'bullmq';
import { redis } from './redis';

const queueOptions: QueueOptions = {
  connection: redis,
};

export const resumeQueue = new Queue('resume-processing', queueOptions);
export const jdQueue = new Queue('jd-processing', queueOptions);
export const scoreQueue = new Queue('score-processing', queueOptions);

export const queues = {
  resume: resumeQueue,
  jd: jdQueue,
  score: scoreQueue,
};

export default queues;

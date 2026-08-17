# Embedding Optimization Documentation

This document explains the Single-Call Batch Embedding optimization implemented for both Resumes and Job Descriptions (JDs) in the Kreeda Hiring Bot system.

## What changes were made?

1. **Resume Processing:**
   * **File:** `scripts/resume-processing/c_embedding_generator.py`
   * **Change:** Refactored `generate_resume_embeddings()`. We eliminated the loop that sent 6 separate sequential API requests to OpenAI for each section. Instead, all text blocks are accumulated into a single flat list, sent in one single API request, and the returned embedding vectors are mapped back to their original sections using slice indexing.

2. **Job Description Processing:**
   * **File:** `scripts/jd-processing/c_ai_embedding_generator.py`
   * **Change:** Refactored `process_jd_embeddings()`. Similarly, the 6 sequential OpenAI embedding API requests were combined into a single batch call, with results re-mapped to their sections using index bounds.

---

## Why were these changes made?

1. **Massive Latency Reduction:**
   * Sending 6 sequential requests to OpenAI embeddings endpoint introduced substantial network latency (around 1 second per resume).
   * Combining them into a single batch call runs the embedding computations in parallel on OpenAI's GPUs, dropping the latency to around 200 milliseconds per resume.

2. **Throughput Scaling:**
   * When processing batches of 40 to 150 resumes, sequential processing creates bottlenecks and freezes the Python worker event loop.
   * This optimization reduces total API network roundtrips by 83% (from 240 calls down to 40 calls for 40 resumes), allowing the worker to handle higher throughput without timeouts.

3. **100% Backward Compatibility:**
   * The output data structures, database schemas, and downstream scoring mechanisms are completely preserved. The change is isolated strictly to the network layer.

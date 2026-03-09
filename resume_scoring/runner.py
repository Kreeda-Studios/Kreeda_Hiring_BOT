import os
import json
import asyncio
from typing import List, Dict, Any
from evaluation_engine import CandidateEvaluator, EvaluationResult

# Use the client provided by the OpenAI library
from openai import AsyncOpenAI

async def process_resumes():
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))
    
    # Initialize the client. Make sure OPENAI_API_KEY is in your environment variables.
    client = AsyncOpenAI()
    evaluator = CandidateEvaluator(async_llm_client=client)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    jd_dir = os.path.join(base_dir, "JD")
    resumes_dir = os.path.join(base_dir, "resumes")
    output_dir = os.path.join(base_dir, "output_json")

    # Find the first JD in the JD folder
    jd_files = [f for f in os.listdir(jd_dir) if f.endswith(".json")]
    if not jd_files:
        print("No JD found in the JD folder. Please add one.")
        return
    
    jd_path = os.path.join(jd_dir, jd_files[0])
    with open(jd_path, "r", encoding="utf-8") as f:
        jd_data = json.load(f)
        
    print(f"Loaded JD: {jd_files[0]}")

    # Find all resumes
    resume_files = [f for f in os.listdir(resumes_dir) if f.endswith(".json")]
    if not resume_files:
        print("No resumes found in the resumes folder. Please add some.")
        return

    print(f"Found {len(resume_files)} resumes to evaluate.")

    for resume_file in resume_files:
        resume_path = os.path.join(resumes_dir, resume_file)
        print(f"Evaluating {resume_file}...")
        
        with open(resume_path, "r", encoding="utf-8") as f:
            resume_data = json.load(f)
            
        try:
            # Score the resume asynchronously
            result = await evaluator.evaluate_async(resume_data, jd_data)
            
            # Save the result
            output_file = os.path.join(output_dir, f"evaluated_{resume_file}")
            with open(output_file, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=4)
                
            print(f"Successfully evaluated and saved to {output_file}")
            
        except Exception as e:
            print(f"Failed to evaluate {resume_file}: {e}")

if __name__ == "__main__":
    asyncio.run(process_resumes())

"""
Score Processor
===============
Houses the AI team's CandidateEvaluator (preserved verbatim).

Usage in score_handler.py:
    from .score_processor import CandidateEvaluator
    evaluator = CandidateEvaluator(async_llm_client=AsyncOpenAI(...))
    result = await evaluator.evaluate_async(resume_data, jd_data)
"""

import json
import logging
from typing import Dict, Any, List
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# PYDANTIC MODELS FOR STRUCTURED LLM OUTPUT
# ---------------------------------------------------------------------------

class EvaluationResult(BaseModel):
    """
    Pydantic model defining the expected structured output from the LLM.
    The LLM will evaluate the resume against the JD and provide these metrics.
    All scores must be floats between 0.0 and 1.0.
    """
    candidate_name: str = Field(description="Name of the candidate (if provided, else empty).")
    skill_match: float = Field(ge=0.0, le=1.0, description="Score comparing resume skills with JD required and preferred skills.")
    experience_match: float = Field(ge=0.0, le=1.0, description="Score comparing candidate experience with JD requirements.")
    tech_stack_match: float = Field(ge=0.0, le=1.0, description="Score matching technologies, frameworks, tools, etc.")
    project_relevance: float = Field(ge=0.0, le=1.0, description="Score evaluating how well projects demonstrate required skills.")
    responsibility_match: float = Field(ge=0.0, le=1.0, description="Score comparing past responsibilities against JD core duties.")
    impact_strength: float = Field(ge=0.0, le=1.0, description="Score evaluating measurable achievements and real-world impact.")
    education_match: float = Field(ge=0.0, le=1.0, description="Score matching candidate education with JD requirements.")
    critical_skill_gap_score: float = Field(ge=0.0, le=1.0, description="Score representing the severity of missing REQUIRED skills. If required skills are empty, use PREFERRED skills and TECH STACK. 1.0 means no crucial gaps, 0.0 means critical failure.")
    
    missing_skills: List[str] = Field(description="List of skills highly required by JD but missing in the resume. If required skills are empty, base this on preferred skills and tech stack.")
    strengths: List[str] = Field(description="List of key candidate strengths relevant to the JD.")
    concerns: List[str] = Field(description="List of concerns or red flags regarding the candidate's fit.")


# ---------------------------------------------------------------------------
# EVALUATION ENGINE
# ---------------------------------------------------------------------------

class CandidateEvaluator:
    """
    Candidate Evaluation Engine.
    Takes Resume JSON and JD JSON, calls an LLM to evaluate the match,
    and returns a structured EvaluationResult along with the calculated overall score.
    """
    
    # Define exact weights as per the system requirements
    WEIGHTS = {
        "skill_match": 0.30,
        "responsibility_match": 0.20,
        "experience_match": 0.15,
        "tech_stack_match": 0.10,
        "project_relevance": 0.10,
        "impact_strength": 0.10,
        "education_match": 0.03,
        "critical_skill_gap_score": 0.02
    }

    def __init__(self, async_llm_client: Any):
        """
        Initialize the evaluator with an async LLM client.
        :param async_llm_client: e.g., AsyncOpenAI() client instance
        """
        self.client = async_llm_client

    def _build_evaluation_prompt(self, resume_data: Dict[str, Any], jd_data: Dict[str, Any]) -> str:
        """
        Builds the system prompt asking the LLM to act as an expert technical recruiter 
        and evaluate the candidate strictly.
        """
        prompt = f"""
You are an expert AI Technical Recruiter and Systems Engineer.
Your task is to comprehensively evaluate a candidate's Resume JSON against a Job Description (JD) JSON.

You must output your evaluation strictly as a JSON object matching the provided schema.

SCORING RULES (CRITICAL):
All scores MUST be a float between 0.0 and 1.0.
0.0 = Complete mismatch / No evidence
0.5 = Partial match / Weak evidence
1.0 = Perfect match / Exceptional evidence

EVALUATION CRITERIA:
1. skill_match: Compare resume skills (provided + inferred) with JD required and preferred skills.
2. experience_match: Compare candidate experience months with JD minimum and maximum experience.
3. tech_stack_match: Compare candidate technologies with the JD tech stack (languages, frameworks, etc.).
4. project_relevance: Evaluate how well the candidate's projects demonstrate relevant skills required by the job.
5. responsibility_match: Compare resume experience responsibilities with JD responsibilities.
6. impact_strength: Evaluate the strength of measurable achievements and real-world impact in the resume (metrics, numbers, scale).
7. education_match: Evaluate whether the candidate's education aligns with JD education requirements.
8. critical_skill_gap_score: Evaluate the severity of missing REQUIRED skills. If the JD's 'required' skills array is empty, you MUST default to evaluating gaps based on 'preferred' skills and core 'tech_stack' items instead. (1.0 = no gap, 0.0 = completely missing critical core skills).
IMPORTANT FOR missing_skills: If 'required' skills in JD are empty, output the most crucial 'preferred' skills and 'tech_stack' elements that are missing.

### RESUME DATA:
{json.dumps(resume_data, indent=2)}

### JOB DESCRIPTION DATA:
{json.dumps(jd_data, indent=2)}

Carefully analyze both inputs and generate the structured evaluation JSON.
"""
        return prompt

    def calculate_overall_score(self, eval_result: EvaluationResult) -> float:
        """
        Calculates the normalized overall score based on the predefined weights.
        The LLM computes the sub-scores; Python computes the exact weighted average
        to ensure mathematical determinism and prevent LLM hallucination on math.
        """
        score = (
            eval_result.skill_match * self.WEIGHTS["skill_match"] +
            eval_result.responsibility_match * self.WEIGHTS["responsibility_match"] +
            eval_result.experience_match * self.WEIGHTS["experience_match"] +
            eval_result.tech_stack_match * self.WEIGHTS["tech_stack_match"] +
            eval_result.project_relevance * self.WEIGHTS["project_relevance"] +
            eval_result.impact_strength * self.WEIGHTS["impact_strength"] +
            eval_result.education_match * self.WEIGHTS["education_match"] +
            eval_result.critical_skill_gap_score * self.WEIGHTS["critical_skill_gap_score"]
        )
        return round(score, 3)

    # -----------------------------------------------------------------------
    # MODULAR ACCESSORS (For pipeline clarity & extending modular validation)
    # -----------------------------------------------------------------------
    
    def get_skill_match(self, result: EvaluationResult) -> float:
        return result.skill_match

    def get_experience_match(self, result: EvaluationResult) -> float:
        return result.experience_match

    def get_tech_stack_match(self, result: EvaluationResult) -> float:
        return result.tech_stack_match

    def get_project_relevance(self, result: EvaluationResult) -> float:
        return result.project_relevance

    def get_responsibility_match(self, result: EvaluationResult) -> float:
        return result.responsibility_match

    def get_impact_strength(self, result: EvaluationResult) -> float:
        return result.impact_strength

    def get_education_match(self, result: EvaluationResult) -> float:
        return result.education_match

    def get_critical_skill_gap(self, result: EvaluationResult) -> float:
        return result.critical_skill_gap_score

    async def evaluate_async(self, resume_json: Dict[str, Any], jd_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main evaluation function.
        Calls the LLM asynchronously, validates the structure via Pydantic,
        calculates the overall score deterministically in Python, 
        and returns the final JSON response.
        """
        prompt = self._build_evaluation_prompt(resume_json, jd_json)
        
        try:
            # We are using gpt-5-mini as requested.
            # Note: For embedding requirements, 'text-embedding-3-small' would be utilized 
            # if we added vector-based similarity matching (e.g. comparing responsibility strings 
            # before passing to LLM). Here, the LLM parses the exact text directly in the prompt.
            response = await self.client.beta.chat.completions.parse(
                model="gpt-5-mini", # Using gpt-5-mini as specified
                messages=[
                    {"role": "system", "content": "You are a technical hiring evaluation engine."},
                    {"role": "user", "content": prompt}
                ],
                response_format=EvaluationResult
            )
            
            # The parsed Pydantic object
            eval_result: EvaluationResult = response.choices[0].message.parsed
            
            # Calculate deterministic overall score in Python
            overall_score = self.calculate_overall_score(eval_result)
            
            # Construct final Output JSON
            final_output = eval_result.model_dump()
            final_output["overall_score"] = overall_score
            
            return final_output

        except Exception as e:
            # Handle potential API or parsing errors gracefully
            print(f"Error during evaluation: {e}")
            raise

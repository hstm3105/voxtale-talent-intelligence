import os
from google.genai import types
from models import JDRequirements, ResumeProfile, ResumeDocument, FitAssessment
from pipeline.jd_extractor import get_genai_client, generate_content_safe
from pipeline.security import wrap_untrusted_text, SECURITY_SYSTEM_INSTRUCTION
from database import get_validated_feedback
from utils.logger import logger

def evaluate_fit(jd: JDRequirements, profile: ResumeProfile, doc: ResumeDocument) -> FitAssessment:
    """Evaluates candidate fit against JD requirements statelessly using Gemini in JSON mode."""
    # Handle empty/garbled resume fast path
    if profile.is_empty_or_garbled or doc.extraction_status == "unreadable_file":
        return FitAssessment(
            score_0_100=0,
            key_strengths=["None identified"],
            key_gaps=["Document is empty, unreadable, or missing text"],
            rationale="Unable to evaluate candidate fit due to unreadable or missing document content.",
            is_overqualified=False,
            has_data_quality_concern=False,
            data_quality_note=""
        )

    client = get_genai_client()
    wrapped_text = wrap_untrusted_text(doc.raw_text)

    # Section 6 Bonus: Retrieve validated recruiter feedback for few-shot context
    feedback_items = get_validated_feedback(limit=3)
    feedback_context = ""
    if feedback_items:
        feedback_context = "\nHISTORICAL RECRUITER CORRECTIONS & PREFERENCES (Learn from past recruiter guidance):\n"
        for fb in feedback_items:
            feedback_context += (
                f"- Candidate '{fb['candidate_name']}': System model decided {fb['original_decision']} (Score {fb['original_score']}), "
                f"but Recruiter corrected to '{fb['corrected_decision']}'. Recruiter rationale: {fb['feedback_notes']}\n"
            )

    prompt = f"""You are a senior technical recruiter evaluating a candidate against a target Job Description.

TARGET JOB REQUIREMENTS:
- Role Title: {jd.role_title}
- Seniority Level: {jd.seniority_level}
- Required Minimum Experience: {jd.min_years_experience} years
- Must-Have Skills: {', '.join(jd.must_have_skills)}
- Nice-to-Have Skills: {', '.join(jd.nice_to_have_skills)}
- Key Responsibilities: {'; '.join(jd.key_responsibilities)}

CANDIDATE STRUCTURED PROFILE:
- Extracted Name: {profile.candidate_name}
- Total Experience: {profile.total_years_experience} years
- Extracted Skills: {', '.join(profile.skills)}
- Summary: {profile.summary}
{feedback_context}
CANDIDATE RAW RESUME DATA:
{wrapped_text}

INSTRUCTIONS FOR EVALUATION:
1. Assign an objective overall fit score from 0 to 100 based strictly on how well the candidate matches the must-have requirements, experience, and key duties.
2. Identify 2 to 3 concrete, JD-specific candidate key_strengths (e.g. specific skills, relevant tools, domain achievements).
3. Identify 2 to 3 concrete, JD-specific candidate key_gaps or missing requirements (e.g. missing mandatory skill, insufficient years of experience, missing degree).
4. Provide a clear rationale (1 to 3 concise sentences) that a recruiter can read directly.
5. Set is_overqualified to true ONLY IF the candidate vastly exceeds the role's required seniority level or experience (e.g. VP applying for Junior Analyst).
6. Set has_data_quality_concern to true ONLY if something about this resume made your evaluation meaningfully less reliable in a way not covered by the other checks — for example the resume is written in a different language than the job description, the formatting is so unconventional that extraction confidence is low, or the document doesn't appear to be a resume at all. If true, give a specific one-sentence data_quality_note.
"""

    try:
        response = generate_content_safe(
            client=client,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SECURITY_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=FitAssessment,
                temperature=0.0
            )
        )
        fit = FitAssessment.model_validate_json(response.text)
        
        # Ensure score is strictly between 0 and 100
        fit.score_0_100 = max(0, min(100, fit.score_0_100))
        
        logger.info(f"Evaluated '{profile.candidate_name}' ({doc.filename}) | Score: {fit.score_0_100} | Overqualified: {fit.is_overqualified} | Quality Concern: {fit.has_data_quality_concern}")
        return fit
    except Exception as e:
        logger.error(f"Fit evaluation failed for {doc.filename}: {e}")
        if "API_KEY_INVALID" in str(e) or "INVALID_ARGUMENT" in str(e):
            raise ValueError("The provided GEMINI_API_KEY is invalid or unauthorized. Please verify your key at https://aistudio.google.com/app/apikey.")
        
        err_msg = f"Automated evaluation failed due to a technical error and could not be completed. This resume requires manual review. Error: {str(e)}"
        return FitAssessment(
            score_0_100=0,
            key_strengths=["Evaluation failed due to technical error"],
            key_gaps=["Evaluation API error"],
            rationale=err_msg,
            is_overqualified=False,
            has_data_quality_concern=True,
            data_quality_note=err_msg
        )

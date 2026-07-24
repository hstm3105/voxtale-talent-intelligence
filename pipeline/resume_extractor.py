import os
from google.genai import types
from models import ResumeProfile, ResumeDocument
from pipeline.jd_extractor import get_genai_client, generate_content_safe
from pipeline.security import wrap_untrusted_text, SECURITY_SYSTEM_INSTRUCTION
from utils.logger import logger
from utils.text_helpers import get_word_count

def extract_resume_profile(doc: ResumeDocument) -> ResumeProfile:
    """Extracts structured candidate profile from resume text using Gemini in JSON mode."""
    # Check if raw text is empty or near-empty before calling LLM
    word_count = get_word_count(doc.raw_text)
    if word_count < 35 or doc.extraction_status == "unreadable_file":
        logger.warning(f"Resume {doc.filename} has insufficient text ({word_count} words). Flagging as insufficient_information.")
        return ResumeProfile(
            candidate_name=doc.filename.rsplit(".", 1)[0].replace("_", " ").title(),
            email=None,
            phone=None,
            total_years_experience=0.0,
            skills=[],
            work_history=[],
            education=[],
            summary="Insufficient or near-empty text",
            is_empty_or_garbled=True
        )

    client = get_genai_client()
    wrapped_text = wrap_untrusted_text(doc.raw_text)

    prompt = f"""Extract candidate information from the resume text provided below into the structured schema.
If the candidate name cannot be explicitly found, use the file name '{doc.filename}'.
If the resume text is garbled, corrupt, or missing essential professional details (e.g. fewer than 35-40 words or lacking work history), set is_empty_or_garbled to true.

{wrapped_text}
"""

    try:
        response = generate_content_safe(
            client=client,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=SECURITY_SYSTEM_INSTRUCTION,
                response_mime_type="application/json",
                response_schema=ResumeProfile,
                temperature=0.0
            )
        )
        profile = ResumeProfile.model_validate_json(response.text)
        
        # Fallback candidate name if blank/unknown
        if not profile.candidate_name or profile.candidate_name.lower() in ["unknown candidate", "unknown", "n/a", ""]:
            profile.candidate_name = doc.filename.rsplit(".", 1)[0].replace("_", " ").title()

        # Flag sparse resumes lacking essential details (< 40 words with zero work history entries)
        if word_count < 40 and len(profile.work_history) == 0 and len(profile.skills) <= 2:
            logger.warning(f"Resume {doc.filename} lacks essential work history/details ({word_count} words). Setting is_empty_or_garbled=True.")
            profile.is_empty_or_garbled = True

        logger.info(f"Extracted profile for '{profile.candidate_name}' ({doc.filename})")
        return profile
    except Exception as e:
        logger.error(f"Failed to extract structured profile for {doc.filename}: {e}")
        if "API_KEY_INVALID" in str(e) or "INVALID_ARGUMENT" in str(e):
            raise ValueError("The provided GEMINI_API_KEY is invalid or unauthorized. Please verify your key at https://aistudio.google.com/app/apikey.")
        return ResumeProfile(
            candidate_name=doc.filename.rsplit(".", 1)[0].replace("_", " ").title(),
            is_empty_or_garbled=True,
            summary=f"Extraction error: {str(e)}"
        )

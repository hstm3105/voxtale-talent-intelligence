from models import ResumeDocument, ResumeProfile, FitAssessment, EvaluationResult
from config import SHORTLIST_THRESHOLD, MAYBE_THRESHOLD
from utils.text_helpers import format_list_to_string
from utils.logger import logger

def make_decision(
    doc: ResumeDocument,
    profile: ResumeProfile,
    fit: FitAssessment,
    is_injection: bool,
    injection_reason: str,
    is_duplicate: bool,
    target_role: str = "Target Role"
) -> EvaluationResult:
    """Deterministic, rules-based engine mapping score and flags to final recruiter decision."""

    candidate_name = profile.candidate_name or doc.filename.rsplit(".", 1)[0].replace("_", " ").title()
    score = fit.score_0_100
    email = profile.email if profile.email else "N/A"
    phone = profile.phone if profile.phone else "N/A"

    # Determine Flags and Decision according to strict priority rules
    if doc.extraction_status == "unreadable_file":
        flags = "unreadable_file"
        decision = "Needs Manual Review"
        rationale = f"File could not be read or text extracted cleanly. {doc.extraction_error or ''}".strip()
        score = 0

    elif profile.is_empty_or_garbled or doc.raw_text.strip() == "":
        flags = "insufficient_information"
        decision = "Needs Manual Review"
        rationale = "Resume contains insufficient, garbled, or missing information to evaluate."
        score = 0

    elif is_injection:
        flags = "possible_prompt_injection"
        decision = "Needs Manual Review"
        rationale = (
            f"Possible prompt injection detected ({injection_reason}). Candidate content evaluated on merits: "
            f"{fit.rationale}"
        )

    elif is_duplicate:
        flags = "duplicate_submission"
        decision = "Needs Manual Review"
        rationale = f"Duplicate submission detected across candidate pool. Original fit rationale: {fit.rationale}"

    elif fit.is_overqualified:
        flags = "overqualified"
        decision = "Needs Manual Review"
        rationale = f"Candidate appears significantly overqualified for the position scope. Fit rationale: {fit.rationale}"

    elif fit.has_data_quality_concern:
        flags = "other"
        decision = "Needs Manual Review"
        score = fit.score_0_100
        if fit.rationale and "Automated evaluation failed due to a technical error" in fit.rationale:
            rationale = fit.rationale
        else:
            rationale = f"Data quality concern flagged for manual review: {fit.data_quality_note}. Fit rationale: {fit.rationale}"

    else:
        flags = "none"
        if score >= SHORTLIST_THRESHOLD:
            decision = "Shortlist"
        elif score >= MAYBE_THRESHOLD:
            decision = "Maybe"
        else:
            decision = "Reject"
        rationale = fit.rationale

    # Format strengths and gaps for CSV cell compliance
    strengths_str = format_list_to_string(fit.key_strengths, default="No specific key strengths highlighted")
    gaps_str = format_list_to_string(fit.key_gaps, default="No major qualification gaps identified")

    result = EvaluationResult(
        resume_filename=doc.filename,
        candidate_name=candidate_name,
        target_role=target_role,
        decision=decision,
        score_0_100=score,
        key_strengths=strengths_str,
        key_gaps=gaps_str,
        flags=flags,
        rationale=rationale,
        email=email,
        phone=phone
    )

    logger.info(f"Final Decision for '{doc.filename}' ({candidate_name}): [{decision}] | Score: {score} | Flags: {flags}")
    return result

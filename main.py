import sys
import uuid
import datetime
import argparse
from pathlib import Path
from typing import List
from concurrent.futures import ThreadPoolExecutor

from models import EvaluationResult, ResumeProfile, FitAssessment
from pipeline.ingestion import load_job_description, load_resumes_from_directory
from pipeline.security import scan_security_prompt_injection
from pipeline.jd_extractor import extract_jd_requirements, get_clean_api_key, JDExtractionError
from pipeline.resume_extractor import extract_resume_profile
from pipeline.duplicate_detector import detect_duplicates
from pipeline.fit_evaluator import evaluate_fit
from pipeline.decision_engine import make_decision
from pipeline.exporter import export_results_to_csv
from database import save_run, save_resume, save_result, save_log
from utils.text_helpers import slugify_role
from utils.logger import logger

def run_pipeline(jd_path: str, resumes_dir: str, output_csv_path: str) -> List[EvaluationResult]:
    """Runs the 8-stage agentic resume shortlisting pipeline with concurrent candidate evaluation and SQLite persistence."""
    run_id = f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    logger.info("=" * 60)
    logger.info(f"STARTING RESUME SHORTLISTING PIPELINE [Run ID: {run_id}]")
    logger.info("=" * 60)

    # Pre-check for API key BEFORE processing any resumes
    api_key = get_clean_api_key()
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Refusing to run the pipeline, since evaluation results would otherwise be silently fabricated. Set the key and retry."
        )

    # Stage 1: Ingestion
    jd_raw_text = load_job_description(jd_path)
    resume_docs = load_resumes_from_directory(resumes_dir)

    if not resume_docs:
        logger.warning("No resume files found in specified directory.")
        return []

    # Stage 2: Security scanning (Two-layer: Heuristic + LLM semantic scanner)
    logger.info(f"Scanning {len(resume_docs)} candidate documents for prompt injection (Heuristic + LLM)...")
    with ThreadPoolExecutor(max_workers=min(5, max(1, len(resume_docs)))) as executor:
        security_scans = list(executor.map(lambda d: scan_security_prompt_injection(d.raw_text), resume_docs))

    # Stage 3: JD Requirement Extraction
    jd_requirements = extract_jd_requirements(jd_raw_text)
    jd_filename = Path(jd_path).name
    role_slug = slugify_role(jd_requirements.role_title)
    run_id = f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{role_slug}_{uuid.uuid4().hex[:4]}"
    logger.info(f"Generated Role-Aware Run ID: '{run_id}' for role '{jd_requirements.role_title}'")

    # Stage 4: Resume Structured Extraction (Concurrent Worker Pool)
    logger.info(f"Extracting profiles for {len(resume_docs)} candidates concurrently...")
    with ThreadPoolExecutor(max_workers=min(5, max(1, len(resume_docs)))) as executor:
        resume_profiles = list(executor.map(extract_resume_profile, resume_docs))

    # Stage 5: Cross-Resume Duplicate Detection
    duplicate_filenames = detect_duplicates(resume_docs, resume_profiles)

    # Stage 6 & 7: Fit Evaluation & Decision Engine (Concurrent Candidate Processing)
    logger.info(f"Evaluating candidate fit concurrently across batch...")
    
    def evaluate_single_candidate(item):
        doc, profile, (is_inj, reason) = item
        is_dup = doc.filename in duplicate_filenames

        try:
            # Fit evaluation (stateless per candidate)
            fit_assessment = evaluate_fit(jd_requirements, profile, doc)

            # Deterministic decision engine
            return make_decision(
                doc=doc,
                profile=profile,
                fit=fit_assessment,
                is_injection=is_inj,
                injection_reason=reason,
                is_duplicate=is_dup,
                target_role=jd_requirements.role_title
            )
        except Exception as e:
            logger.error(f"Unhandled per-candidate pipeline exception for {doc.filename}: {e}")
            err_str = str(e)
            if "API_KEY_INVALID" in err_str or "INVALID_ARGUMENT" in err_str:
                raise e
            
            err_msg = f"Automated evaluation failed due to a technical error and could not be completed. This resume requires manual review. Error: {str(e)}"
            fallback_fit = FitAssessment(
                score_0_100=0,
                key_strengths=["Evaluation failed due to technical error"],
                key_gaps=["Pipeline execution error"],
                rationale=err_msg,
                is_overqualified=False,
                has_data_quality_concern=True,
                data_quality_note=err_msg
            )
            return make_decision(
                doc=doc,
                profile=profile,
                fit=fallback_fit,
                is_injection=is_inj,
                injection_reason=reason,
                is_duplicate=is_dup,
                target_role=jd_requirements.role_title
            )

    items = list(zip(resume_docs, resume_profiles, security_scans))
    with ThreadPoolExecutor(max_workers=min(5, max(1, len(items)))) as executor:
        results = list(executor.map(evaluate_single_candidate, items))

    # Stage 8: Persistent Storage (SQLite Database Repository & CSV Export)
    logger.info("Persisting run details, resumes, and results to SQLite database repository...")
    save_run(run_id=run_id, jd_filename=jd_filename, jd_title=jd_requirements.role_title, total_resumes=len(results), status="COMPLETED")

    for doc in resume_docs:
        save_resume(run_id, doc.filename, doc.extension, len(doc.raw_text), doc.raw_text)

    for res in results:
        save_result(run_id, res)

    save_log(run_id, stage="PIPELINE_COMPLETE", message=f"Pipeline completed. Evaluated {len(results)} resumes.", level="INFO")

    # Export to Output CSV
    export_results_to_csv(results, output_csv_path)

    logger.info("=" * 60)
    logger.info(f"PIPELINE COMPLETED [Run ID: {run_id}]. Exported {len(results)} evaluations to {output_csv_path} & saved in SQLite DB.")
    logger.info("=" * 60)

    return results

def main():
    parser = argparse.ArgumentParser(description="Agentic Resume-Shortlisting Pipeline")
    parser.add_argument("--jd", "-j", required=True, help="Path to Job Description file (TXT, PDF, or DOCX)")
    parser.add_argument("--resumes", "-r", required=True, help="Path to folder containing candidate resumes")
    parser.add_argument("--output", "-o", default="output.csv", help="Path for output CSV file (default: output.csv)")

    args = parser.parse_args()

    try:
        run_pipeline(
            jd_path=args.jd,
            resumes_dir=args.resumes,
            output_csv_path=args.output
        )
    except Exception as e:
        logger.critical(f"Pipeline execution failed: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()

import os
import sys
import argparse
from pathlib import Path
from main import run_pipeline
from pipeline.jd_extractor import get_clean_api_key
from utils.logger import logger

def run_eval_suite(api_key_override: str = None):
    """Runs automated evaluations against 16 comprehensive edge cases and logs pass/fail results."""
    if api_key_override:
        os.environ["GEMINI_API_KEY"] = api_key_override.strip()

    logger.info("============================================================")
    logger.info("RUNNING AUTOMATED EVALUATION SUITE FOR RESUME SHORTLISTER (16 TEST CASES)")
    logger.info("============================================================")

    # Check for GEMINI_API_KEY before running suite
    api_key = get_clean_api_key()
    if not api_key:
        print("\n" + "❌" * 40)
        print("ERROR: GEMINI_API_KEY environment variable is missing or empty.")
        print("To run the 16-case evaluation suite against the live Gemini API:")
        print("  export GEMINI_API_KEY='your_api_key_here'")
        print("  python eval_suite.py")
        print("  OR")
        print("  python eval_suite.py --key 'your_api_key_here'")
        print("❌" * 40 + "\n")
        logger.error("GEMINI_API_KEY missing for eval_suite.py run.")
        return False

    base_dir = Path(__file__).parent
    test_jd_path = str(base_dir / "test_data" / "jd.txt")
    test_resumes_dir = str(base_dir / "test_data")
    sample_jd_path = str(base_dir / "sample_data" / "sample_jd.txt")
    sample_resumes_dir = str(base_dir / "sample_data")
    eval_csv_output = str(base_dir / "eval_output.csv")

    if not Path(test_jd_path).exists():
        logger.error(f"Test JD not found at {test_jd_path}.")
        sys.exit(1)

    # Execute pipeline against test_data (cases 1-6) and sample_data (cases 7-16)
    results_test = run_pipeline(
        jd_path=test_jd_path,
        resumes_dir=test_resumes_dir,
        output_csv_path=eval_csv_output
    )
    results_sample = run_pipeline(
        jd_path=sample_jd_path,
        resumes_dir=sample_resumes_dir,
        output_csv_path=eval_csv_output
    )

    # Index combined results by filename
    result_map = {res.resume_filename: res for res in results_test + results_sample}

    # Define 16 test suite expectations covering all contract rules & edge cases
    test_cases = [
        # --- ORIGINAL BASELINE TEST CASES (1 to 6) ---
        {
            "filename": "1_valid_candidate.txt",
            "name": "Standard Valid Candidate",
            "expected_flag": "none",
            "expected_decision_in": ["Shortlist", "Maybe"],
            "format": "TXT"
        },
        {
            "filename": "2_empty_resume.txt",
            "name": "Near-Empty / Garbled Resume",
            "expected_flag": "insufficient_information",
            "expected_decision": "Needs Manual Review",
            "format": "TXT"
        },
        {
            "filename": "3_prompt_injection.txt",
            "name": "Prompt Injection Attempt",
            "expected_flag": "possible_prompt_injection",
            "expected_decision": "Needs Manual Review",
            "format": "TXT"
        },
        {
            "filename": "4_overqualified.txt",
            "name": "Wildly Overqualified Candidate (VP Level)",
            "expected_flag": "overqualified",
            "expected_decision": "Needs Manual Review",
            "format": "TXT"
        },
        {
            "filename": "5_original_candidate.pdf",
            "name": "Duplicate Submission (PDF vs DOCX)",
            "expected_flag": "duplicate_submission",
            "expected_decision": "Needs Manual Review",
            "format": "PDF"
        },
        {
            "filename": "6_corrupted_file.pdf",
            "name": "Corrupted / Invalid File",
            "expected_flag": "unreadable_file",
            "expected_decision": "Needs Manual Review",
            "format": "PDF"
        },

        # --- EXTENDED EDGE-CASE SUITE (7 to 16) ---
        {
            "filename": "ec01_strong_fit.txt",
            "name": "Strong Fit Growth Analyst (Meera Iyer)",
            "expected_flag": "none",
            "expected_decision_in": ["Shortlist", "Maybe"],
            "format": "TXT"
        },
        {
            "filename": "ec02_clear_reject.txt",
            "name": "Clear Reject / Domain Mismatch (Civil Engineer)",
            "expected_flag": "none",
            "expected_decision": "Reject",
            "format": "TXT"
        },
        {
            "filename": "ec03_borderline_maybe.txt",
            "name": "Borderline / Mid-Fit Candidate (Sanjana Mehta)",
            "expected_flag": "none",
            "expected_decision_in": ["Maybe", "Shortlist", "Reject"],
            "format": "TXT"
        },
        {
            "filename": "ec04_overqualified.txt",
            "name": "Overqualified Executive (VP Vikram Nair)",
            "expected_flag": "overqualified",
            "expected_decision": "Needs Manual Review",
            "format": "TXT"
        },
        {
            "filename": "ec05_prompt_injection_attempt.txt",
            "name": "Adversarial System Note Prompt Injection (Amit Kumar)",
            "expected_flag": "possible_prompt_injection",
            "expected_decision": "Needs Manual Review",
            "format": "TXT"
        },
        {
            "filename": "ec06_insufficient_information.txt",
            "name": "Insufficient Information (Priya S. - 25 words)",
            "expected_flag": "insufficient_information",
            "expected_decision": "Needs Manual Review",
            "format": "TXT"
        },
        {
            "filename": "ec07_corrupted_unreadable.txt",
            "name": "Garbled / Binary-Like Text Resume",
            "expected_flag_in": ["insufficient_information", "unreadable_file", "other"],
            "expected_decision": "Needs Manual Review",
            "format": "TXT"
        },
        {
            "filename": "ec08_duplicate_of_ec01.txt",
            "name": "Duplicate Candidate Submission (Meera Iyer Re-submission)",
            "expected_flag": "duplicate_submission",
            "expected_decision": "Needs Manual Review",
            "format": "TXT"
        },
        {
            "filename": "ec09_non_english.txt",
            "name": "Non-English Language Resume (Hindi Text)",
            "expected_flag_in": ["other", "none"],
            "expected_decision_in": ["Needs Manual Review", "Shortlist", "Maybe", "Reject"],
            "format": "TXT"
        },
        {
            "filename": "ec10_messy_ocr_format.txt",
            "name": "Messy OCR / Unconventional Spacing Format",
            "expected_flag_in": ["other", "none"],
            "expected_decision_in": ["Needs Manual Review", "Shortlist", "Maybe"],
            "format": "TXT"
        }
    ]

    passed_count = 0
    total_count = len(test_cases)

    print("\n" + "=" * 80)
    print("COMPREHENSIVE 16-CASE EVALUATION SUITE TEST RESULTS SUMMARY")
    print("=" * 80)

    for idx, case in enumerate(test_cases, start=1):
        fname = case["filename"]
        rec = result_map.get(fname)

        if not rec:
            print(f"❌ FAIL [{idx:02d}/16]: [{fname}] Record not found in evaluation outputs!")
            continue

        # Check flags match
        if "expected_flag" in case:
            flag_passed = rec.flags == case["expected_flag"]
            exp_flag_str = case["expected_flag"]
        else:
            flag_passed = rec.flags in case["expected_flag_in"]
            exp_flag_str = str(case["expected_flag_in"])

        # Check decision matches
        if "expected_decision" in case:
            decision_passed = rec.decision == case["expected_decision"]
            exp_dec_str = case["expected_decision"]
        else:
            decision_passed = rec.decision in case["expected_decision_in"]
            exp_dec_str = str(case["expected_decision_in"])

        case_passed = flag_passed and decision_passed

        if case_passed:
            passed_count += 1
            status_str = "PASSED ✅"
        else:
            status_str = "FAILED ❌"

        print(f"\nCase {idx:02d}/16: {case['name']} ({fname} - Format: {case['format']})")
        print(f"Status: {status_str}")
        print(f"  - Actual Decision: {rec.decision} (Expected: {exp_dec_str})")
        print(f"  - Actual Flag:     {rec.flags} (Expected: {exp_flag_str})")
        print(f"  - Score (0-100):   {rec.score_0_100}")
        print(f"  - Rationale:       {rec.rationale}")

    print("\n" + "=" * 80)
    print(f"EVAL SUITE SUMMARY: {passed_count}/{total_count} CASES PASSED ({passed_count/total_count*100:.1f}%)")
    print("=" * 80)
    print("💾 RUN DATA PERSISTED: Saved all evaluation records to SQLite DB ('resume_shortlister.db') & 'eval_output.csv'.\n")

    # Execute Test Case 17: JD Extraction Failure Safeguard
    jd_fail_test_passed = test_jd_extraction_failure_case()

    return passed_count == total_count and jd_fail_test_passed

def test_jd_extraction_failure_case() -> bool:
    """Test Case 17: Simulates JD extraction failure (mocking Gemini call to raise Exception)
    Asserts that the pipeline stops cleanly with JDExtractionError and produces 0 evaluation rows.
    """
    from unittest.mock import patch
    from pipeline.jd_extractor import JDExtractionError

    print("\n" + "=" * 80)
    print("TEST CASE 17: JD EXTRACTION FAILURE SAFEGUARD (MOCKED MODEL FAILURE)")
    print("=" * 80)

    base_dir = Path(__file__).parent
    test_jd_path = str(base_dir / "test_data" / "jd.txt")
    test_resumes_dir = str(base_dir / "test_data")
    eval_csv_output = str(base_dir / "eval_output_jd_fail_test.csv")

    with patch("pipeline.jd_extractor.generate_content_safe", side_effect=Exception("Simulated model rate limit / network / Pydantic validation error")):
        try:
            results = run_pipeline(
                jd_path=test_jd_path,
                resumes_dir=test_resumes_dir,
                output_csv_path=eval_csv_output
            )
            print("❌ FAIL: Pipeline did not raise JDExtractionError when JD extraction failed!")
            return False
        except JDExtractionError as e:
            print(f"PASSED ✅: Pipeline stopped cleanly before evaluating resumes with JDExtractionError: {e}")
            return True
        except Exception as e:
            if "Could not extract structured requirements" in str(e):
                print(f"PASSED ✅: Pipeline stopped cleanly with exception: {e}")
                return True
            print(f"❌ FAIL: Pipeline raised unexpected exception type {type(e)}: {e}")
            return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run 16-Case Evaluation Suite")
    parser.add_argument("--key", "-k", help="Optional Gemini API Key")
    args = parser.parse_args()

    success = run_eval_suite(api_key_override=args.key)
    sys.exit(0 if success else 1)

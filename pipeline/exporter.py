import csv
from typing import List
from models import EvaluationResult
from config import CSV_HEADER
from utils.logger import logger

def export_results_to_csv(results: List[EvaluationResult], output_csv_path: str) -> None:
    """Exports pipeline evaluation results to CSV strictly adhering to contract header and column order."""
    logger.info(f"Writing {len(results)} evaluation results to CSV at: {output_csv_path}")

    with open(output_csv_path, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
        
        # Write exact CSV header
        writer.writerow(CSV_HEADER)

        # Write each candidate row
        for res in results:
            writer.writerow([
                res.resume_filename,
                res.candidate_name,
                getattr(res, "target_role", "Target Role"),
                res.decision,
                res.score_0_100,
                res.key_strengths,
                res.key_gaps,
                res.flags,
                res.rationale
            ])

    logger.info("CSV export completed successfully.")

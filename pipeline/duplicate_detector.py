from typing import List, Set
from models import ResumeDocument, ResumeProfile
from config import SIMILARITY_THRESHOLD
from utils.logger import logger
from utils.text_helpers import normalize_text, calculate_jaccard_similarity

def detect_duplicates(documents: List[ResumeDocument], profiles: List[ResumeProfile]) -> Set[str]:
    """Scans all documents and profiles in the batch to find duplicates.
    Returns a set of filenames identified as duplicate submissions.
    """
    logger.info("Scanning batch for duplicate submissions...")
    duplicate_filenames: Set[str] = set()

    n = len(documents)
    for i in range(n):
        doc_i = documents[i]
        prof_i = profiles[i]
        
        # Skip documents already flagged as duplicates or unreadable
        if doc_i.filename in duplicate_filenames or doc_i.extraction_status == "unreadable_file":
            continue

        name_i = normalize_text(prof_i.candidate_name)
        email_i = prof_i.email.strip().lower() if prof_i.email else ""
        phone_i = prof_i.phone.strip() if prof_i.phone else ""
        text_i = doc_i.raw_text

        for j in range(i + 1, n):
            doc_j = documents[j]
            prof_j = profiles[j]
            
            if doc_j.filename in duplicate_filenames or doc_j.extraction_status == "unreadable_file":
                continue

            name_j = normalize_text(prof_j.candidate_name)
            email_j = prof_j.email.strip().lower() if prof_j.email else ""
            phone_j = prof_j.phone.strip() if prof_j.phone else ""
            text_j = doc_j.raw_text

            is_duplicate = False
            reason = ""

            # Check 1: Exact email match (non-empty)
            if email_i and email_j and email_i == email_j:
                is_duplicate = True
                reason = f"Matching email '{email_i}'"

            # Check 2: Exact phone match (non-empty)
            elif phone_i and phone_j and phone_i == phone_j:
                is_duplicate = True
                reason = f"Matching phone '{phone_i}'"

            # Check 3: Candidate name match AND text similarity > 0.6
            elif name_i and name_j and name_i == name_j and name_i not in ["unknown candidate", ""]:
                sim = calculate_jaccard_similarity(text_i, text_j)
                if sim > 0.4:
                    is_duplicate = True
                    reason = f"Matching candidate name '{prof_i.candidate_name}' with similarity {sim:.2f}"

            # Check 4: High text content similarity (> 0.85 Jaccard 4-gram)
            else:
                sim = calculate_jaccard_similarity(text_i, text_j)
                if sim >= SIMILARITY_THRESHOLD:
                    is_duplicate = True
                    reason = f"High content text similarity score ({sim:.2f} >= {SIMILARITY_THRESHOLD})"

            if is_duplicate:
                logger.warning(f"Duplicate detected: '{doc_j.filename}' is a duplicate of '{doc_i.filename}' ({reason})")
                duplicate_filenames.add(doc_j.filename)

    return duplicate_filenames

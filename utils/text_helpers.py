import re
from typing import Set

def normalize_text(text: str) -> str:
    """Normalizes text by converting to lowercase and stripping extra whitespace and non-alphanumeric chars."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def get_word_count(text: str) -> int:
    """Returns number of words in text."""
    normalized = normalize_text(text)
    return len(normalized.split()) if normalized else 0

def get_character_ngrams(text: str, n: int = 4) -> Set[str]:
    """Generates set of character n-grams from normalized text."""
    cleaned = normalize_text(text)
    if len(cleaned) < n:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i+n] for i in range(len(cleaned) - n + 1)}

def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Computes Jaccard similarity coefficient between two text documents using 4-grams."""
    ngrams1 = get_character_ngrams(text1, n=4)
    ngrams2 = get_character_ngrams(text2, n=4)
    
    if not ngrams1 or not ngrams2:
        return 0.0
        
    intersection = len(ngrams1.intersection(ngrams2))
    union = len(ngrams1.union(ngrams2))
    
    return intersection / union if union > 0 else 0.0

def format_list_to_string(items: list, default: str = "None specified") -> str:
    """Formats a list of strings into a semicolon-delimited string for CSV cell compatibility."""
    if not items:
        return default
    clean_items = [str(item).strip().rstrip(';') for item in items if str(item).strip()]
    if not clean_items:
        return default
    return "; ".join(clean_items)

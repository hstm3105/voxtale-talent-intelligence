import os
import time
import re
from typing import Any
from google import genai
from google.genai import types
from models import JDRequirements
from config import get_current_model_name, GEMINI_API_KEY
from utils.logger import logger

def get_clean_api_key() -> str:
    """Gets and sanitizes the API key from config or environment."""
    key = GEMINI_API_KEY or os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or ""
    return key.strip().strip("'").strip('"')

def get_genai_client() -> genai.Client:
    """Initializes and returns the Gemini API client."""
    api_key = get_clean_api_key()
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY or GOOGLE_API_KEY environment variable is missing. "
            "Please set GEMINI_API_KEY before running the pipeline."
        )
    return genai.Client(api_key=api_key)

def is_rate_limit_error(e: Exception) -> bool:
    """Checks if an exception is a 429 / RESOURCE_EXHAUSTED rate limit error."""
    err_str = str(e).lower()
    return "resource_exhausted" in err_str or "429" in err_str or "quota" in err_str or "retrydelay" in err_str

def parse_retry_delay(e: Exception, default_delay: float = 15.0) -> float:
    """Parses suggested retry delay from exception string or returns default."""
    err_str = str(e)
    match = re.search(r'retry[_-]?delay[\'"]?\s*[:=]\s*[\'"]?(\d+(?:\.\d+)?)', err_str, re.IGNORECASE)
    if match:
        try:
            delay = float(match.group(1))
            return max(1.0, min(60.0, delay))
        except ValueError:
            pass
    return default_delay

def generate_content_safe(client: genai.Client, contents: str, config: types.GenerateContentConfig = None) -> Any:
    """Executes Gemini API call with automatic 429 rate-limit retry logic (up to 2 retries)."""
    model_name = get_current_model_name()
    logger.info(f"Calling Gemini API with selected model: '{model_name}'...")
    
    max_retries = 2
    for attempt in range(max_retries + 1):
        try:
            return client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config
            )
        except Exception as e:
            err_str = str(e)
            if "API_KEY_INVALID" in err_str or "INVALID_ARGUMENT" in err_str:
                # Do not retry invalid API keys
                raise e

            if is_rate_limit_error(e) and attempt < max_retries:
                delay = parse_retry_delay(e, default_delay=15.0)
                logger.warning(
                    f"429 Rate Limit encountered (RESOURCE_EXHAUSTED). Retrying attempt {attempt + 1}/{max_retries} "
                    f"in {delay:.1f}s... Error details: {e}"
                )
                time.sleep(delay)
            else:
                raise e

def validate_gemini_api_key(api_key: str) -> tuple[bool, str]:
    """Validates if a Gemini API key is active and authorized."""
    if not api_key or not api_key.strip():
        return False, "API Key is empty."
    clean_key = api_key.strip().strip("'").strip('"')
    model_name = get_current_model_name()
    try:
        client = genai.Client(api_key=clean_key)
        resp = generate_content_safe(client, contents="test")
        return True, f"API Key is valid and authorized for model '{model_name}'!"
    except Exception as e:
        err_str = str(e)
        if "API_KEY_INVALID" in err_str or "INVALID_ARGUMENT" in err_str:
            return False, "Invalid API key string. Please check your API key at Google AI Studio (https://aistudio.google.com/app/apikey)."
        return False, f"API Key Validation Error: {err_str}"

def extract_jd_requirements(jd_text: str) -> JDRequirements:
    """Dynamically extracts structured job requirements from raw JD text using Gemini."""
    model_name = get_current_model_name()
    logger.info(f"Extracting structured requirements from Job Description using model '{model_name}'...")
    
    client = get_genai_client()

    prompt = f"""You are an expert HR analyst. Analyze the following Job Description text and extract structured job requirements.
Reason generically about the text provided — do not assume any specific role type or skill list.

Job Description Text:
{jd_text}
"""

    try:
        response = generate_content_safe(
            client=client,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=JDRequirements,
                temperature=0.0
            )
        )
        extracted = JDRequirements.model_validate_json(response.text)
        logger.info(f"Successfully extracted JD requirements for role: '{extracted.role_title}' using '{model_name}'")
        return extracted
    except Exception as e:
        logger.error(f"Error during JD requirement extraction with model '{model_name}': {e}")
        if "API_KEY_INVALID" in str(e) or "INVALID_ARGUMENT" in str(e):
            raise ValueError("The provided GEMINI_API_KEY is invalid or unauthorized. Please verify your key at https://aistudio.google.com/app/apikey.")
        return JDRequirements(
            role_title="Target Role",
            seniority_level="Not Specified",
            role_type="Full-time",
            min_years_experience=0.0,
            must_have_skills=["Relevant experience"],
            nice_to_have_skills=[],
            key_responsibilities=[],
            domain_summary=jd_text[:200]
        )

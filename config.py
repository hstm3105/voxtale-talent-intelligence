import os
from dotenv import load_dotenv

load_dotenv()

# Model Options Mapping - Exact mappings requested by user
MODEL_MAPPING = {
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 3.1 Flash Lite": "gemini-3.1-flash-lite",
    "Gemini 3.5 Flash": "gemini-3.5-flash",
    "Gemini 2.5 Flash Lite": "gemini-2.5-flash-lite",
    "Gemini 3 Flash": "gemini-3-flash",
    "Gemini 3.5 Flash Lite": "gemini-3.5-flash-lite",
    "Gemini 3.6 Flash": "gemini-3.6-flash"
}

# Dynamic getter for active model name
def get_current_model_name() -> str:
    try:
        import streamlit as st
        if "user_model_name" in st.session_state and st.session_state["user_model_name"]:
            return st.session_state["user_model_name"]
    except Exception:
        pass
    return os.environ.get("GEMINI_MODEL_NAME", "gemini-3.5-flash-lite")

GEMINI_MODEL_NAME = get_current_model_name()

# API Key - checked in runtime client wrapper
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")

# Decision Score Thresholds (Deterministic Engine)
SHORTLIST_THRESHOLD = 80
MAYBE_THRESHOLD = 60

# Duplicate Detection Settings
SIMILARITY_THRESHOLD = 0.85

INJECTION_KEYWORDS = [
    "ignore previous instructions",
    "ignore all instructions",
    "ignore all previous instructions",
    "disregard previous instructions",
    "disregard all instructions",
    "disregard the scoring",
    "system prompt",
    "system note",
    "developer mode",
    "you are now",
    "override role",
    "ignore above",
    "new instruction",
    "bypass restrictions",
    "shortlist this candidate",
    "give this resume 100",
    "score: 100",
    "decision: shortlist",
    "decision=shortlist",
    "score_0_100=100",
    "note to hiring system",
    "note from hiring",
    "hiring system administrator",
    "hiring system",
    "automated screening",
    "screening tools",
    "treat this candidate as",
    "assign the maximum",
    "maximum possible fit score",
    "maximum fit score",
    "overriding any",
    "pre-screened and approved",
    "system administrator",
    "override any",
    "satisfied all job requirements",
    "satisfied all requirements",
]

# Output CSV Contract Header (Must match exact spec order)
CSV_HEADER = [
    "resume_filename",
    "candidate_name",
    "target_role",
    "decision",
    "score_0_100",
    "key_strengths",
    "key_gaps",
    "flags",
    "rationale"
]

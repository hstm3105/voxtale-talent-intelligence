import sys
import os
import json
import uuid
import datetime
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional

# Ensure project root directory is in sys.path for Streamlit Cloud deployment
ROOT_DIR = Path(__file__).parent.resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pandas as pd
import streamlit as st

from models import ResumeDocument, EvaluationResult
from pipeline.ingestion import load_job_description, load_single_file
from pipeline.security import scan_heuristic_prompt_injection
from pipeline.jd_extractor import extract_jd_requirements, validate_gemini_api_key, JDExtractionError
from pipeline.resume_extractor import extract_resume_profile
from pipeline.duplicate_detector import detect_duplicates
from pipeline.fit_evaluator import evaluate_fit
from pipeline.decision_engine import make_decision
from pipeline.exporter import export_results_to_csv
from database import (
    init_db, save_run, save_resume, save_result, save_log,
    get_all_runs, get_results_by_run, get_resumes_by_run, get_logs_by_run,
    save_feedback, approve_feedback, get_pending_feedback, get_all_feedback, get_validated_feedback,
    get_all_roles_with_candidates, get_shortlisted_candidates_by_role
)
from sheets_sync import export_to_google_sheets, generate_excel_for_sheets
from email_sender import send_results_email, DEFAULT_RECIPIENT_EMAIL, sanitize_str
from config import CSV_HEADER, MODEL_MAPPING, get_current_model_name
from pipeline.ui_components import render_confidence_ring, render_chip, build_candidate_html_table, render_kpi_card, render_skill_tags

# Page Configuration - Executive Sidebar Enabled Layout
st.set_page_config(
    page_title="VoxTale - Agentic Resume Shortlister",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Global Theme & CSS Design System (Exact Values per Specification)
CUSTOM_CSS = """
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Sans:ital,wght@0,600;1,600&family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">

<style>
    /* Exact Color Tokens */
    :root {
        --canvas-bg: #0B0B10;
        --surface-bg: #14141C;
        --raised-bg: #1C1C28;
        --border-hairline: #26262F;
        --text-primary: #F2F1F7;
        --text-secondary: #8E8CA3;
        --text-muted: #5C5A6E;
        --brand-accent: #6E62F5;
        --brand-accent-hover: #7C71F7;
        --shortlist-color: #34D399;
        --reject-color: #FB7185;
        --maybe-color: #FBBF24;
        --review-color: #A78BFA;
    }

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: var(--text-primary);
        background-color: var(--canvas-bg);
        font-size: 0.92rem;
    }

    .stApp {
        background-color: var(--canvas-bg) !important;
    }

    /* Streamlit Native Header & Container Padding Fix (Prevents Status Pill Clipping) */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 3.5rem !important;
    }

    .block-container {
        padding-top: 3.75rem !important;
        padding-bottom: 2rem;
        max-width: 95%;
    }

    /* Typography Hierarchy */
    h1, h2, h3, h4, h5, h6, .heading-font {
        font-family: 'Instrument Sans', sans-serif !important;
        font-weight: 600 !important;
        color: var(--text-primary) !important;
        letter-spacing: -0.02em !important;
    }

    h1 { font-size: 1.7rem !important; }
    h2 { font-size: 1.25rem !important; }
    h3 { font-size: 1.05rem !important; }
    h4 { font-size: 0.95rem !important; }

    .mono-font, code, pre, [data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace !important;
    }

    /* Sidebar Navigation List & Feature Buttons */
    section[data-testid="stSidebar"] {
        background-color: var(--canvas-bg) !important;
        border-right: 1px solid var(--border-hairline) !important;
        padding-top: 1.2rem;
        width: 17.5rem !important;
        min-width: 17.5rem !important;
    }

    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"] {
        background: transparent !important;
        border: 1px solid transparent !important;
        border-left: 3px solid transparent !important;
        border-radius: 8px !important;
        color: #8E8CA3 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.81rem !important;
        font-weight: 500 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 7px 10px !important;
        margin-bottom: 3px !important;
        white-space: nowrap !important;
        transition: all 0.18s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }

    section[data-testid="stSidebar"] div.stButton > button[kind="secondary"]:hover {
        background: rgba(255, 255, 255, 0.04) !important;
        color: #F2F1F7 !important;
        border-left: 3px solid rgba(110, 98, 245, 0.5) !important;
        transform: translateX(2px) !important;
    }

    section[data-testid="stSidebar"] div.stButton > button[kind="primary"] {
        background: rgba(110, 98, 245, 0.14) !important;
        border: 1px solid rgba(110, 98, 245, 0.25) !important;
        border-left: 3px solid #6E62F5 !important;
        border-radius: 8px !important;
        color: #F2F1F7 !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.81rem !important;
        font-weight: 600 !important;
        text-align: left !important;
        justify-content: flex-start !important;
        padding: 7px 10px !important;
        margin-bottom: 3px !important;
        white-space: nowrap !important;
        box-shadow: 0 2px 8px rgba(110, 98, 245, 0.15) !important;
    }

    /* Native Cards (Upload Dropzones & Panels) */
    div[data-testid="stContainerBorderParent"] {
        border-color: var(--border-hairline) !important;
        background-color: var(--surface-bg) !important;
        border-radius: 14px !important;
        padding: 22px !important;
    }

    /* File Uploader Dropzone Styling */
    div[data-testid="stFileUploader"] section {
        background-color: var(--surface-bg) !important;
        border: 1.5px dashed var(--border-hairline) !important;
        border-radius: 14px !important;
        transition: all 0.2s ease !important;
    }

    div[data-testid="stFileUploader"] section:hover {
        border: 1.5px solid var(--brand-accent) !important;
        background-color: var(--raised-bg) !important;
    }

    /* Primary CTA Button */
    div.stButton > button[kind="primary"] {
        background-color: var(--brand-accent) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 10px !important;
        font-family: 'Instrument Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 8px 18px !important;
        box-shadow: 0 4px 12px rgba(110, 98, 245, 0.3) !important;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    div.stButton > button[kind="primary"]:hover {
        background-color: var(--brand-accent-hover) !important;
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 16px rgba(110, 98, 245, 0.45) !important;
    }
    div.stButton > button[kind="primary"]:active {
        transform: scale(0.97) !important;
    }

    /* Secondary Action Button (Outlined / Ghost) */
    div.stButton > button[kind="secondary"] {
        background-color: transparent !important;
        color: var(--text-primary) !important;
        border: 1px solid var(--border-hairline) !important;
        border-radius: 10px !important;
        font-family: 'Inter', sans-serif !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button[kind="secondary"]:hover {
        background-color: var(--raised-bg) !important;
        border-color: var(--brand-accent) !important;
        color: var(--brand-accent) !important;
    }

    /* Green Approval Action Button */
    .btn-approve-green > button {
        background-color: transparent !important;
        color: var(--shortlist-color) !important;
        border: 1px solid var(--shortlist-color) !important;
        border-radius: 8px !important;
        font-family: 'Instrument Sans', sans-serif !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        transition: all 0.2s ease !important;
    }
    .btn-approve-green > button:hover {
        background-color: var(--shortlist-color) !important;
        color: #0B0B10 !important;
        box-shadow: 0 4px 12px rgba(52, 211, 153, 0.3) !important;
    }

    /* Email Preview Card */
    .email-preview-card {
        border: 1px dashed rgba(110, 98, 245, 0.4);
        background: rgba(110, 98, 245, 0.03);
        padding: 20px;
        border-radius: 12px;
        font-size: 0.9rem;
    }

    /* Custom Metric Pair */
    .stat-label { font-size: 0.78rem; color: var(--text-secondary); }
    .stat-val { font-size: 0.84rem; font-weight: 600; color: var(--text-primary); font-family: 'JetBrains Mono', monospace; }
</style>
"""

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
st.session_state["app_theme"] = "dark"

# Initialize Database Schema
init_db()

# Native Settings Pop-Up Dialog Modal
@st.dialog("Settings", width="medium")
def open_settings_modal():
    st.markdown("<p style='font-size: 0.88rem; color: #8E8CA3;'>Configure Gemini foundation model API keys, Google Sheets sync, and SMTP email credentials.</p>", unsafe_allow_html=True)
    
    tab_m1, tab_m2, tab_m3 = st.tabs(["API & Model", "Google Sheets Sync", "SMTP Email Settings"])
    
    with tab_m1:
        st.markdown("#### Gemini Foundation Model Settings")
        current_api_key = st.session_state.get("user_gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
        api_key_tab = st.text_input(
            "Gemini API Key",
            type="password",
            value=current_api_key,
            key="modal_api_key_in"
        )
        if api_key_tab:
            st.session_state["user_gemini_api_key"] = api_key_tab.strip().strip("'").strip('"')
            os.environ["GEMINI_API_KEY"] = api_key_tab.strip().strip("'").strip('"')

        if st.button("Validate API Key Connection", key="modal_validate_key_btn", use_container_width=True):
            active_key = st.session_state.get("user_gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
            is_valid, msg = validate_gemini_api_key(active_key)
            if is_valid:
                st.success(msg)
            else:
                st.error(msg)

        model_options = list(MODEL_MAPPING.keys())
        current_env_model = st.session_state.get("user_model_name") or os.environ.get("GEMINI_MODEL_NAME", "gemini-3.5-flash-lite")
        curr_index = 0
        for idx, (label, val) in enumerate(MODEL_MAPPING.items()):
            if val == current_env_model:
                curr_index = idx
                break

        sel_model = st.selectbox("Selected Foundation Model", model_options, index=curr_index, key="modal_model_sel")
        st.session_state["user_model_name"] = MODEL_MAPPING[sel_model]
        os.environ["GEMINI_MODEL_NAME"] = MODEL_MAPPING[sel_model]

    with tab_m2:
        st.markdown("#### Google Sheets Sync Configuration")
        st.markdown("<p style='font-size: 0.85rem; color: #8E8CA3;'>Upload or paste your Google Service Account JSON key for live spreadsheet sync.</p>", unsafe_allow_html=True)
        
        g_file_tab = st.file_uploader("Upload google_credentials.json", type=["json"], key="modal_g_json_file")
        g_text_tab = st.text_area("Or Paste Service Account JSON Key", height=90, key="modal_g_json_text")
        g_sheet_url_tab = st.text_input("Target Sheet URL / ID (Optional)", placeholder="https://docs.google.com/spreadsheets/d/...", key="modal_sheet_url")

        parsed_sa = None
        if g_file_tab:
            try:
                parsed_sa = json.loads(g_file_tab.getvalue().decode("utf-8"))
                st.success("Loaded Service Account JSON file!")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
        elif g_text_tab.strip():
            try:
                parsed_sa = json.loads(g_text_tab.strip())
                st.success("Loaded Service Account JSON text!")
            except Exception as e:
                st.error(f"Invalid JSON: {e}")

        if parsed_sa:
            st.session_state["service_account_dict"] = parsed_sa
            st.info(f"Service Account Email: `{parsed_sa.get('client_email', 'N/A')}`")

        if g_sheet_url_tab.strip():
            st.session_state["target_sheet_url"] = g_sheet_url_tab.strip()

    with tab_m3:
        st.markdown("#### SMTP Email Server Credentials")
        st.text_input("Recipient / Recruiter Email", value=DEFAULT_RECIPIENT_EMAIL, key="modal_recip_email")
        s_email = st.text_input("Sender Email (Gmail)", value=os.environ.get("SENDER_EMAIL", ""), key="modal_sender_email")
        s_pass = st.text_input("Sender App Password", type="password", value=os.environ.get("SENDER_APP_PASSWORD", ""), key="modal_sender_pass")
        if s_email:
            os.environ["SENDER_EMAIL"] = s_email
        if s_pass:
            os.environ["SENDER_APP_PASSWORD"] = s_pass

    st.markdown("---")
    _, m_btn, _ = st.columns([1, 1.4, 1])
    with m_btn:
        if st.button("Save & Close Settings", type="primary", use_container_width=True):
            st.rerun()

# Initialize Navigation Session State
if "active_nav_screen" not in st.session_state:
    st.session_state["active_nav_screen"] = "Run Shortlisting Pipeline"

# Fetch Live System Metrics for Sidebar Badges
past_runs = get_all_runs()
shortlisted_cands_all = get_shortlisted_candidates_by_role("All Roles")
pending_feedback = get_pending_feedback()
feedback_count = len(get_all_feedback())

# Component 1: Feature-Oriented Executive Sidebar Navigation
st.sidebar.markdown("""
<div style="padding: 4px 0 10px 0;">
    <div style="font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; color: #5C5A6E; font-family: 'Inter', sans-serif; margin-bottom: 8px;">
        CORE WORKFLOWS
    </div>
</div>
""", unsafe_allow_html=True)

# Feature 1: Run Shortlisting Pipeline
is_s1_active = st.session_state["active_nav_screen"] == "Run Shortlisting Pipeline"
s1_label = "🚀 Run Shortlisting Pipeline"
if st.sidebar.button(
    s1_label,
    key="nav_btn_s1",
    use_container_width=True,
    type="primary" if is_s1_active else "secondary"
):
    st.session_state["active_nav_screen"] = "Run Shortlisting Pipeline"
    st.rerun()

# Feature 2: Shortlist Hub & Scheduler
is_s2_active = st.session_state["active_nav_screen"] == "Shortlist Hub & Scheduler"
s2_count = len(shortlisted_cands_all)
s2_label = f"📊 Shortlist Hub & Scheduler ({s2_count})" if s2_count > 0 else "📊 Shortlist Hub & Scheduler"
if st.sidebar.button(
    s2_label,
    key="nav_btn_s2",
    use_container_width=True,
    type="primary" if is_s2_active else "secondary"
):
    st.session_state["active_nav_screen"] = "Shortlist Hub & Scheduler"
    st.rerun()

st.sidebar.markdown("""
<div style="padding: 16px 0 10px 0;">
    <div style="font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.09em; color: #5C5A6E; font-family: 'Inter', sans-serif; margin-bottom: 8px;">
        INTELLIGENCE & MEMORY
    </div>
</div>
""", unsafe_allow_html=True)

# Feature 3: Resume Repository
is_s3_active = st.session_state["active_nav_screen"] == "Resume Repository"
s3_count = len(past_runs)
s3_label = f"📁 Resume Repository ({s3_count})" if s3_count > 0 else "📁 Resume Repository"
if st.sidebar.button(
    s3_label,
    key="nav_btn_s3",
    use_container_width=True,
    type="primary" if is_s3_active else "secondary"
):
    st.session_state["active_nav_screen"] = "Resume Repository"
    st.rerun()

# Feature 4: Recruiter Feedback Loop
is_s4_active = st.session_state["active_nav_screen"] == "Recruiter Feedback Loop"
s4_pending = len(pending_feedback)
s4_label = f"🧠 Recruiter Feedback ({s4_pending} new)" if s4_pending > 0 else "🧠 Recruiter Feedback Loop"
if st.sidebar.button(
    s4_label,
    key="nav_btn_s4",
    use_container_width=True,
    type="primary" if is_s4_active else "secondary"
):
    st.session_state["active_nav_screen"] = "Recruiter Feedback Loop"
    st.rerun()

# Feature 5: System Execution Logs
is_s5_active = st.session_state["active_nav_screen"] == "System Execution Logs"
if st.sidebar.button(
    "📜 System Execution Logs",
    key="nav_btn_s5",
    use_container_width=True,
    type="primary" if is_s5_active else "secondary"
):
    st.session_state["active_nav_screen"] = "System Execution Logs"
    st.rerun()

selected_screen = st.session_state["active_nav_screen"]

# Compact Two-Line Stat Footer at Bottom of Sidebar
st.sidebar.markdown(f"""
<div style="margin-top: 28px; padding-top: 14px; border-top: 1px solid #26262F; font-family: 'Inter', sans-serif;">
  <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
    <span style="font-size: 0.78rem; color: #8E8CA3;">Total Pipeline Runs</span>
    <span style="font-size: 0.82rem; font-weight: 600; color: #F2F1F7; font-family: 'JetBrains Mono', monospace;">{len(past_runs)}</span>
  </div>
  <div style="display: flex; justify-content: space-between; align-items: center;">
    <span style="font-size: 0.78rem; color: #8E8CA3;">Recruiter Corrections</span>
    <span style="font-size: 0.82rem; font-weight: 600; color: #F2F1F7; font-family: 'JetBrains Mono', monospace;">{feedback_count}</span>
  </div>
</div>
""", unsafe_allow_html=True)

# Component 4: Top-Right Model Status Pill + Main Header (Positioned in Normal Document Flow below Streamlit Header)
h_col1, h_col2 = st.columns([3.1, 1.4], vertical_alignment="center")

api_key_env = st.session_state.get("user_gemini_api_key") or os.environ.get("GEMINI_API_KEY", "")
status_dot_color = "#34D399" if api_key_env else "#FBBF24"
status_label = "Connected" if api_key_env else "Pending Key"
model_name = get_current_model_name()

with h_col1:
    st.markdown("""
    <div style="display: flex; align-items: center; gap: 14px; padding: 2px 0;">
        <div style="width: 40px; height: 40px; border-radius: 10px; background: linear-gradient(135deg, #6E62F5 0%, #34D399 100%); display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 14px rgba(110, 98, 245, 0.35); font-size: 20px;">
            🤖
        </div>
        <div>
            <h1 style="margin: 0; color: #F2F1F7; font-family: 'Instrument Sans', sans-serif; font-weight: 700; font-size: 1.6rem; letter-spacing: -0.02em;">VoxTale Talent Intelligence</h1>
            <p style="margin: 2px 0 0 0; font-size: 0.86rem; color: #8E8CA3; font-family: 'Inter', sans-serif;">Autonomous Multi-Stage Candidate Screening & Decision Pipeline</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

with h_col2:
    st.markdown(f"""
    <div style="display: flex; align-items: center; justify-content: flex-end; gap: 10px; margin-bottom: 6px;">
        <div style="display: inline-flex; align-items: center; gap: 8px; background: #14141C; border: 1px solid #26262F; border-radius: 20px; padding: 6px 14px; font-size: 0.78rem; font-family: 'Inter', sans-serif; color: #8E8CA3; white-space: nowrap;">
          <span style="width: 7px; height: 7px; border-radius: 50%; background-color: {status_dot_color}; box-shadow: 0 0 6px {status_dot_color}; display: inline-block;"></span>
          <span style="color: #F2F1F7; font-weight: 500;">{model_name}</span>
          <span style="color: #5C5A6E;">•</span>
          <span style="color: {status_dot_color}; font-weight: 500;">{status_label}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    c_space, c_btn = st.columns([1.4, 1])
    with c_btn:
        if st.button("⚙️ Settings", key="btn_top_settings", use_container_width=True):
            open_settings_modal()

st.divider()

# ==========================================
# SCREEN 1: RUN SHORTLISTING PIPELINE
# ==========================================
if selected_screen == "Run Shortlisting Pipeline":
    st.markdown("## Screening Workflow")
    
    col_left, col_right = st.columns([1, 1])

    with col_left:
        with st.container(border=True):
            st.markdown("### Step 1: Target Role / Job Description (JD)")
            jd_input_method = st.radio("JD Source", ["Paste Text", "Upload File (TXT/PDF/DOCX)"], horizontal=True)
            
            jd_text = ""
            jd_filename = "pasted_jd.txt"
            
            if jd_input_method == "Paste Text":
                jd_text = st.text_area("Job Description Text", height=190, placeholder="Paste Job Description text here...")
            else:
                jd_file = st.file_uploader("Upload Job Description File", type=["txt", "pdf", "docx"], key="jd_upload")
                if jd_file:
                    jd_filename = jd_file.name
                    with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(jd_file.name)[1]) as tmp:
                        tmp.write(jd_file.getvalue())
                        tmp_path = tmp.name
                    doc = load_single_file(tmp_path)
                    jd_text = doc.raw_text
                    st.success(f"Loaded JD '{jd_filename}' ({len(jd_text)} characters)")

    with col_right:
        with st.container(border=True):
            st.markdown("### Step 2: Candidate Resumes Batch")
            uploaded_resumes = st.file_uploader(
                "Upload Resume Files (Select Multiple TXT / PDF / DOCX)",
                type=["txt", "pdf", "docx"],
                accept_multiple_files=True,
                key="resumes_upload"
            )
            
            if uploaded_resumes:
                st.info(f"📁 **{len(uploaded_resumes)}** resume file(s) selected for batch processing.")
            else:
                st.caption("Select candidate resume files (TXT, PDF, or DOCX) to upload for evaluation.")

    st.divider()

    st.markdown("### Step 3: Execute AI Screening")
    c_start, _ = st.columns([1.3, 2.7])
    with c_start:
        start_btn = st.button("🚀 Start Shortlisting Pipeline", type="primary", use_container_width=True)

    if start_btn:
        if not jd_text or len(jd_text.strip()) < 20:
            st.error("Please provide a valid Job Description before running.")
        elif not uploaded_resumes:
            st.error("Please upload candidate resume files before running.")
        elif not os.environ.get("GEMINI_API_KEY"):
            st.error("Please enter a valid GEMINI_API_KEY in top-right Settings before proceeding.")
        else:
            run_id = f"run_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
            
            temp_dir = tempfile.mkdtemp()
            temp_resume_docs: List[ResumeDocument] = []

            for uf in uploaded_resumes:
                fpath = os.path.join(temp_dir, uf.name)
                with open(fpath, "wb") as f:
                    f.write(uf.getvalue())
                doc = load_single_file(fpath)
                temp_resume_docs.append(doc)
                save_resume(run_id=run_id, filename=doc.filename, file_type=doc.extension, file_size=len(uf.getvalue()), raw_text=doc.raw_text)

            save_log(run_id, "INIT", f"Started new pipeline run with {len(temp_resume_docs)} resumes", "INFO")

            st.markdown("### Live Pipeline Stage Visibility")
            progress_bar = st.progress(0, text="Initializing Pipeline...")
            
            with st.status("Executing Multi-Stage Agentic Pipeline...", expanded=True) as status_box:
                try:
                    status_box.write("Stage 1: Ingestion & Text Extraction — Completed for all files.")
                    save_log(run_id, "STAGE_1_INGESTION", f"Loaded {len(temp_resume_docs)} files cleanly", "INFO")
                    progress_bar.progress(15, text="Stage 1/8: Ingestion Complete")

                    status_box.write("Stage 2: Untrusted Input Security Scan — Scanning for prompt injections...")
                    security_scans = []
                    for doc in temp_resume_docs:
                        is_inj, reason = scan_heuristic_prompt_injection(doc.raw_text)
                        security_scans.append((is_inj, reason))
                        if is_inj:
                            status_box.write(f"Security Alert on `{doc.filename}`: {reason}")
                            save_log(run_id, "SECURITY_ALERT", f"{doc.filename}: {reason}", "WARN")
                    progress_bar.progress(30, text="Stage 2/8: Security Scan Complete")

                    status_box.write("Stage 3: Gemini Dynamic JD Requirement Extraction — Analyzing JD structure...")
                    jd_requirements = extract_jd_requirements(jd_text)
                    status_box.write(f"Extracted Role: **{jd_requirements.role_title}** | Seniority: **{jd_requirements.seniority_level}**")
                    save_log(run_id, "STAGE_3_JD", f"Extracted requirements for role '{jd_requirements.role_title}'", "INFO")
                    progress_bar.progress(45, text="Stage 3/8: JD Extraction Complete")

                    status_box.write("Stage 4: Resume Structured Extraction — Extracting candidate profiles & contact info...")
                    resume_profiles = []
                    for doc in temp_resume_docs:
                        status_box.write(f" Parsing `{doc.filename}`...")
                        profile = extract_resume_profile(doc)
                        resume_profiles.append(profile)
                    save_log(run_id, "STAGE_4_RESUME", f"Extracted profiles for {len(resume_profiles)} candidates", "INFO")
                    progress_bar.progress(60, text="Stage 4/8: Candidate Extraction Complete")

                    status_box.write("Stage 5: Cross-Resume Duplicate Detection — Analyzing identity & text similarity...")
                    duplicate_filenames = detect_duplicates(temp_resume_docs, resume_profiles)
                    if duplicate_filenames:
                        status_box.write(f"Found {len(duplicate_filenames)} duplicate submissions: {', '.join(duplicate_filenames)}")
                        save_log(run_id, "DUPLICATES_FOUND", f"Duplicates: {duplicate_filenames}", "WARN")
                    progress_bar.progress(75, text="Stage 5/8: Duplicate Detection Complete")

                    status_box.write("Stage 6 & 7: Gemini Fit Evaluation & Deterministic Decision Engine...")
                    results: List[EvaluationResult] = []
                    for doc, profile, (is_inj, reason) in zip(temp_resume_docs, resume_profiles, security_scans):
                        is_dup = doc.filename in duplicate_filenames
                        fit_assessment = evaluate_fit(jd_requirements, profile, doc)
                        final_record = make_decision(
                            doc=doc,
                            profile=profile,
                            fit=fit_assessment,
                            is_injection=is_inj,
                            injection_reason=reason,
                            is_duplicate=is_dup
                        )
                        results.append(final_record)
                        save_result(run_id, final_record)

                    progress_bar.progress(90, text="Stage 6 & 7 Complete")

                    status_box.write("Stage 8: Exporting CSV & Database Repository Sync...")
                    save_run(run_id, jd_filename, jd_requirements.role_title, len(temp_resume_docs), "COMPLETED")
                    progress_bar.progress(100, text="Pipeline Completed Successfully!")
                    status_box.update(label="Pipeline Completed Successfully!", state="complete", expanded=False)

                    st.session_state["latest_results"] = results
                    st.session_state["latest_run_id"] = run_id

                except JDExtractionError as err:
                    status_box.update(label="Pipeline Execution Failed (JD Extraction Error)", state="error", expanded=True)
                    st.error(f"Could not extract structured requirements from the job description — the run was stopped before evaluating any resumes. {err}")
                    save_log(run_id, "JD_EXTRACTION_FAILED", str(err), "ERROR")
                except Exception as err:
                    status_box.update(label="Pipeline Execution Failed", state="error", expanded=True)
                    st.error(f"Error during execution: {err}")
                    st.info("Please verify your GEMINI_API_KEY in top-right Settings before proceeding.")
                    save_log(run_id, "ERROR", str(err), "ERROR")

    # Display Results if Available
    if "latest_results" in st.session_state:
        results: List[EvaluationResult] = st.session_state["latest_results"]
        st.markdown("### Screening Results & Export Actions")

        data_dicts = [res.model_dump() for res in results]
        active_role_title = st.session_state.get("latest_jd_title", "Target Role")
        for d in data_dicts:
            d["target_role"] = active_role_title
        df = pd.DataFrame(data_dicts)

        kpi1, kpi2, kpi3, kpi4 = st.columns(4)
        c_short = sum(1 for r in results if r.decision == "Shortlist")
        c_maybe = sum(1 for r in results if r.decision == "Maybe")
        c_review = sum(1 for r in results if r.decision == "Needs Manual Review")
        c_reject = sum(1 for r in results if r.decision == "Reject")

        with kpi1:
            st.markdown(render_kpi_card("Shortlisted Matches", c_short, "Top Fit Candidates", "#34D399"), unsafe_allow_html=True)
        with kpi2:
            st.markdown(render_kpi_card("Maybe Matches", c_maybe, "Borderline Qualifications", "#FBBF24"), unsafe_allow_html=True)
        with kpi3:
            st.markdown(render_kpi_card("Manual Review", c_review, "Security / Data Flags", "#A78BFA"), unsafe_allow_html=True)
        with kpi4:
            st.markdown(render_kpi_card("Rejected", c_reject, "Does Not Meet Criteria", "#FB7185"), unsafe_allow_html=True)

        f_col1, f_col2, f_col3 = st.columns([2, 1, 1])
        with f_col1:
            search_query = st.text_input("Real-Time Candidate Search (Search by Name, Skill, or Rationale Keywords...)", "", key="search_s1")
        with f_col2:
            all_decisions = list(df["decision"].unique())
            decision_filter = st.multiselect("Filter by Decision", all_decisions, default=all_decisions, key="dec_filter_s1")
        with f_col3:
            all_flags = list(df["flags"].unique())
            flag_filter = st.multiselect("Filter by Flags", all_flags, default=all_flags, key="flag_filter_s1")

        filtered_df = df[df["decision"].isin(decision_filter) & df["flags"].isin(flag_filter)]

        if search_query.strip():
            sq = search_query.strip().lower()
            filtered_df = filtered_df[
                filtered_df["candidate_name"].str.lower().str.contains(sq) |
                filtered_df["key_strengths"].str.lower().str.contains(sq) |
                filtered_df["rationale"].str.lower().str.contains(sq)
            ]

        # Rich Candidate HTML Table with Confidence Rings & Chips
        st.markdown(build_candidate_html_table(filtered_df.to_dict('records')), unsafe_allow_html=True)

        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
        
        with btn_col1:
            csv_data = filtered_df[CSV_HEADER].to_csv(index=False)
            st.download_button(
                label="Download Results CSV for ATS",
                data=csv_data,
                file_name=f"shortlist_results_{st.session_state.get('latest_run_id', 'run')}.csv",
                mime="text/csv",
                use_container_width=True
            )

        with btn_col2:
            if st.button("Sync to Live Google Sheet", use_container_width=True):
                sa_dict = st.session_state.get("service_account_dict")
                sheet_url = st.session_state.get("target_sheet_url")
                sync_res = export_to_google_sheets(
                    data_dicts,
                    service_account_dict=sa_dict,
                    spreadsheet_id_or_url=sheet_url
                )
                if sync_res["success"]:
                    st.success(f"{sync_res['message']} [Open Google Sheet]({sync_res['url']})")
                else:
                    st.error(f"{sync_res['message']}")

        with btn_col3:
            if st.button("Mail Results Excel (in XLSX format)", use_container_width=True):
                target_email = st.session_state.get("recipient_email", DEFAULT_RECIPIENT_EMAIL)
                excel_bytes = generate_excel_for_sheets(data_dicts)
                
                email_res = send_results_email(
                    recipient_email=target_email,
                    excel_bytes=excel_bytes,
                    filename=f"shortlist_results_{st.session_state.get('latest_run_id', 'run')}.xlsx",
                    run_id=st.session_state.get('latest_run_id', 'run'),
                    results_summary=data_dicts
                )

                if email_res["success"]:
                    st.success(email_res["message"])
                else:
                    st.warning(f"{email_res['message']}")

        st.markdown("### Candidate Dossier Cards & Recruiter Feedback")
        for res in results:
            with st.expander(f"Candidate: {res.candidate_name} ({res.resume_filename})"):
                ring_html = render_confidence_ring(res.score_0_100, res.decision, size=44)
                chip_html = render_chip(res.decision, kind="decision")
                flag_html = render_chip(res.flags, kind="flag")

                st.markdown(f"""
                <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; background: #14141C; padding: 12px 16px; border-radius: 10px; border: 1px solid #26262F;">
                  <div style="display: flex; align-items: center; gap: 14px;">
                    {ring_html}
                    <div>
                      <div style="font-weight: 600; font-size: 1.05rem; color: #F2F1F7;">{res.candidate_name}</div>
                      <div style="font-size: 0.8rem; color: #8E8CA3; font-family: 'JetBrains Mono', monospace;">File: {res.resume_filename}</div>
                    </div>
                  </div>
                  <div style="display: flex; align-items: center; gap: 10px;">
                    {chip_html}
                    {flag_html}
                  </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown(f"**Contact Info**: Email: `{res.email or 'N/A'}` | Phone: `{res.phone or 'N/A'}`")
                st.markdown(f"**Rationale**: {res.rationale}")
                st.markdown(f"**Key Strengths**: {res.key_strengths}")
                st.markdown(f"**Key Gaps**: {res.key_gaps}")

                with st.container(border=True):
                    st.markdown("#### Recruiter Correction & Feedback")
                    
                    fb_col1, fb_col2 = st.columns([1, 2])
                    with fb_col1:
                        new_dec = st.selectbox(
                            "Correct Decision",
                            ["Shortlist", "Maybe", "Reject", "Needs Manual Review"],
                            index=["Shortlist", "Maybe", "Reject", "Needs Manual Review"].index(res.decision),
                            key=f"dec_{res.resume_filename}"
                        )
                    with fb_col2:
                        fb_notes = st.text_input(
                            "Recruiter Rationale for Correction",
                            placeholder="Explain why this decision should be changed...",
                            key=f"notes_{res.resume_filename}"
                        )

                    if st.button(f"Save Recruiter Correction for {res.candidate_name}", key=f"btn_fb_{res.resume_filename}"):
                        if not fb_notes.strip():
                            st.warning("Please provide a short explanation for the correction.")
                        else:
                            save_feedback(
                                run_id=st.session_state.get("latest_run_id", "manual"),
                                resume_filename=res.resume_filename,
                                candidate_name=res.candidate_name,
                                original_decision=res.decision,
                                original_score=res.score_0_100,
                                corrected_decision=new_dec,
                                feedback_notes=fb_notes
                            )
                            st.success(f"Correction saved for '{res.candidate_name}' pending review!")

# ==========================================
# SCREEN 2: SHORTLIST HUB & SCHEDULER (SUB-SCREEN TABS)
# ==========================================
elif selected_screen == "Shortlist Hub & Scheduler":
    st.markdown("## Candidate Shortlist Hub & Interview Scheduler")
    st.markdown("<p style='color: #8E8CA3; font-size: 0.9rem;'>Visualize top-ranked shortlisted candidates, inspect contact details, schedule interviews, and view dossiers.</p>", unsafe_allow_html=True)

    roles_summary = get_all_roles_with_candidates()
    if not roles_summary:
        st.info("No candidate shortlists stored in repository yet. Run a shortlisting pipeline in Screen 1 first!")
    else:
        role_titles = ["All Roles"] + [r["jd_title"] for r in roles_summary if r["jd_title"]]
        role_options = list(dict.fromkeys(role_titles))
        all_shortlisted_cands = get_shortlisted_candidates_by_role("All Roles")

        m1, m2, m3, m4 = st.columns(4)
        top_fit_count = sum(1 for c in all_shortlisted_cands if c["score_0_100"] >= 80)
        avg_score = (sum(c["score_0_100"] for c in all_shortlisted_cands) / len(all_shortlisted_cands)) if all_shortlisted_cands else 0
        with_contact = sum(1 for c in all_shortlisted_cands if c.get("email") and c.get("email") != "N/A")

        with m1:
            st.markdown(render_kpi_card("Shortlisted Candidates", len(all_shortlisted_cands), "Total candidates in hub", "#6E62F5"), unsafe_allow_html=True)
        with m2:
            st.markdown(render_kpi_card("High Fit Match", top_fit_count, "Candidates with Score ≥ 80", "#34D399"), unsafe_allow_html=True)
        with m3:
            st.markdown(render_kpi_card("Average Fit Score", f"{avg_score:.1f} / 100", "Mean candidate score", "#FBBF24"), unsafe_allow_html=True)
        with m4:
            st.markdown(render_kpi_card("Contact Info Extracted", f"{with_contact}/{len(all_shortlisted_cands)}", "Email & phone identified", "#A78BFA"), unsafe_allow_html=True)

        st.divider()

        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs([
            "Master Candidate List",
            "Schedule an Interview",
            "Candidate Dossiers",
            "⚔️ Side-by-Side Comparison"
        ])

        # Sub-Tab 1: Master Candidate List
        with sub_tab1:
            h_f0, h_f1, h_f2, h_f3 = st.columns([1.4, 1.8, 1, 1])
            with h_f0:
                sel_role_sub1 = st.selectbox("Select Target Role / JD", role_options, key="hub_role_sel_tab1")

            shortlisted_cands = get_shortlisted_candidates_by_role(sel_role_sub1)
            for c in shortlisted_cands:
                if "target_role" not in c or not c["target_role"]:
                    c["target_role"] = c.get("jd_title") or sel_role_sub1

            if not shortlisted_cands:
                st.warning(f"No shortlisted candidates found for role '{sel_role_sub1}'.")
            else:
                with h_f1:
                    hub_search = st.text_input("Real-Time Candidate Search...", "", key="hub_search_input")
                with h_f2:
                    unique_hub_decisions = list(dict.fromkeys([c.get("decision", "Shortlist") for c in shortlisted_cands]))
                    hub_decision_filter = st.multiselect("Filter by Decision", unique_hub_decisions, default=unique_hub_decisions, key="hub_dec_filter")
                with h_f3:
                    unique_hub_flags = list(dict.fromkeys([c.get("flags", "none") for c in shortlisted_cands]))
                    hub_flag_filter = st.multiselect("Filter by Flags", unique_hub_flags, default=unique_hub_flags, key="hub_flag_filter")

                filtered_shortlisted = [
                    c for c in shortlisted_cands
                    if c.get("decision", "Shortlist") in hub_decision_filter
                    and c.get("flags", "none") in hub_flag_filter
                ]

                if hub_search.strip():
                    sq = hub_search.strip().lower()
                    filtered_shortlisted = [
                        c for c in filtered_shortlisted
                        if sq in c.get("candidate_name", "").lower()
                        or sq in str(c.get("email", "")).lower()
                        or sq in str(c.get("jd_title", "")).lower()
                        or sq in str(c.get("key_strengths", "")).lower()
                        or sq in str(c.get("key_gaps", "")).lower()
                        or sq in str(c.get("rationale", "")).lower()
                    ]

                # Embedded HTML Candidate Table with Confidence Rings & Chips
                st.markdown(build_candidate_html_table(filtered_shortlisted), unsafe_allow_html=True)

                cand_df = pd.DataFrame(filtered_shortlisted if filtered_shortlisted else shortlisted_cands)
                outreach_csv = cand_df[["candidate_name", "email", "phone", "jd_title", "decision", "score_0_100", "key_strengths", "rationale"]].to_csv(index=False)
                st.download_button(
                    "Download Shortlisted Candidates Contact Outreach CSV",
                    data=outreach_csv,
                    file_name=f"shortlist_outreach_{sel_role_sub1.lower().replace(' ', '_')}.csv",
                    mime="text/csv"
                )

        # Sub-Tab 2: Schedule an Interview
        with sub_tab2:
            st.markdown("### Schedule an Interview")
            sel_role_sub2 = st.selectbox("Select Target Role / JD for Interview", role_options, key="hub_role_sel_tab2")
            shortlisted_cands_tab2 = get_shortlisted_candidates_by_role(sel_role_sub2)

            if not shortlisted_cands_tab2:
                st.warning(f"No shortlisted candidates found for role '{sel_role_sub2}'.")
            else:
                sc_col1, sc_col2 = st.columns([1, 1])
                with sc_col1:
                    cand_names = [f"{c['candidate_name']} ({c['email'] or 'No Email'}) — Role: {c['jd_title']}" for c in shortlisted_cands_tab2]
                    selected_cand_idx = st.selectbox("Select Candidate to Invite", range(len(cand_names)), format_func=lambda i: cand_names[i])
                    target_cand = shortlisted_cands_tab2[selected_cand_idx]

                    interview_round = st.selectbox("Interview Stage / Round", [
                        "Round 1: Technical & Systems Screening",
                        "Round 2: Hiring Manager & Domain Deep-Dive",
                        "Round 3: Executive & Leadership Culture Fit"
                    ])
                    interviewer_name = st.text_input("Interviewer Name", value="Harshit Sharma (Hiring Manager)")

                with sc_col2:
                    interview_date = st.date_input("Scheduled Date", value=datetime.date.today() + datetime.timedelta(days=2))
                    interview_time = st.time_input("Scheduled Time", value=datetime.time(14, 0))
                    meeting_link = st.text_input("Meeting Link (Google Meet / Zoom)", value="https://meet.google.com/abc-defg-hij")
                    additional_note = st.text_area("Custom Message / Note to Candidate", placeholder="Mention key strengths noted during shortlisting...", height=70)

                with st.expander("Live Interview Email Invitation Preview", expanded=True):
                    rec_note = f'<div style="margin-top: 10px; color: #F2F1F7;"><strong>Recruiter Note</strong>: <em>{additional_note.strip()}</em></div>' if additional_note.strip() else ""
                    email_html = f"""
                    <div style="border: 1px dashed rgba(110, 98, 245, 0.4); background: rgba(110, 98, 245, 0.03); padding: 20px; border-radius: 12px; font-family: 'Inter', sans-serif; font-size: 0.9rem; color: #F2F1F7;">
                      <div style="margin-bottom: 6px; font-weight: 500;"><strong>Subject</strong>: Interview Invitation: {target_cand['jd_title']} — {interview_round}</div>
                      <div style="margin-bottom: 12px; color: #8E8CA3;"><strong>To</strong>: <code style="background: rgba(110, 98, 245, 0.12); color: #34D399; padding: 2px 6px; border-radius: 4px;">{target_cand.get('email', 'candidate@example.com')}</code></div>
                      <hr style="border: none; border-top: 1px solid #26262F; margin: 12px 0;" />
                      <p style="margin-bottom: 10px;">Dear <strong>{target_cand['candidate_name']}</strong>,</p>
                      <p style="margin-bottom: 10px;">We are pleased to invite you for <strong>{interview_round}</strong> for the <strong>{target_cand['jd_title']}</strong> position!</p>
                      <ul style="margin: 0 0 12px 20px; padding: 0; color: #8E8CA3;">
                        <li>Date: <span style="color: #F2F1F7;">{interview_date.strftime('%B %d, %Y')}</span></li>
                        <li>Time: <span style="color: #F2F1F7;">{interview_time.strftime('%I:%M %p')}</span></li>
                        <li>Meeting Link: <a href="{meeting_link}" target="_blank" style="color: #6E62F5;">{meeting_link}</a></li>
                      </ul>
                      {rec_note}
                      <div style="margin-top: 16px;">
                        <div>Best regards,</div>
                        <div style="margin-top: 4px;"><strong>{interviewer_name}</strong></div>
                        <div style="font-style: italic; color: #8E8CA3;">VoxTale Hiring Team</div>
                      </div>
                    </div>
                    """
                    st.markdown(email_html, unsafe_allow_html=True)

                c_dispatch, _ = st.columns([1.4, 2.6])
                with c_dispatch:
                    dispatch_btn = st.button("Dispatch Interview Invitation Email", type="primary", use_container_width=True)

                if dispatch_btn:
                    target_email = target_cand.get("email")
                    if not target_email or target_email == "N/A":
                        st.error(f"Candidate '{target_cand['candidate_name']}' does not have a valid extracted email address.")
                    else:
                        invite_summary = [
                            {
                                "decision": f"Invited for {interview_round}",
                                "candidate_name": target_cand["candidate_name"],
                                "email": target_email,
                                "phone": target_cand.get("phone", "N/A"),
                                "score_0_100": target_cand["score_0_100"],
                                "rationale": f"Scheduled for {interview_date} at {interview_time}. Meeting: {meeting_link}. Recruiter Notes: {additional_note}"
                            }
                        ]
                        res = send_results_email(
                            recipient_email=target_email,
                            filename=f"Interview_Invite_{target_cand['candidate_name'].replace(' ', '_')}.xlsx",
                            run_id=target_cand.get("run_id", "interview"),
                            results_summary=invite_summary
                        )
                        if res["success"]:
                            st.success(f"Interview invitation email successfully sent to '{target_cand['candidate_name']}' ({target_email})!")
                        else:
                            st.error(f"Failed to send email: {res['message']}")

        # Sub-Tab 3: Candidate Dossiers
        with sub_tab3:
            st.markdown("### Candidate Dossiers")
            sel_role_sub3 = st.selectbox("Filter Dossiers by Target Role", role_options, key="hub_role_sel_tab3")
            shortlisted_cands_tab3 = get_shortlisted_candidates_by_role(sel_role_sub3)

            if not shortlisted_cands_tab3:
                st.warning(f"No candidate dossiers found for role '{sel_role_sub3}'.")
            else:
                for c in shortlisted_cands_tab3:
                    with st.expander(f"Candidate: {c['candidate_name']} ({c['resume_filename']}) — {c['jd_title']}"):
                        ring_html = render_confidence_ring(c['score_0_100'], c['decision'], size=44)
                        chip_html = render_chip(c['decision'], kind="decision")
                        flag_html = render_chip(c['flags'], kind="flag")

                        st.markdown(f"""
                        <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; background: #14141C; padding: 12px 16px; border-radius: 10px; border: 1px solid #26262F;">
                          <div style="display: flex; align-items: center; gap: 14px;">
                            {ring_html}
                            <div>
                              <div style="font-weight: 600; font-size: 1.05rem; color: #F2F1F7;">{c['candidate_name']}</div>
                              <div style="font-size: 0.8rem; color: #8E8CA3; font-family: 'JetBrains Mono', monospace;">Role: {c['jd_title']} | File: {c['resume_filename']}</div>
                            </div>
                          </div>
                          <div style="display: flex; align-items: center; gap: 10px;">
                            {chip_html}
                            {flag_html}
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                        st.markdown(f"**Contact Info**: Email: `{c.get('email') or 'N/A'}` | Phone: `{c.get('phone') or 'N/A'}`")
                        st.markdown(f"**Rationale**: {c.get('rationale')}")
                        st.markdown(f"**Key Strengths**: {c.get('key_strengths')}")
                        st.markdown(f"**Key Gaps**: {c.get('key_gaps')}")

        # Sub-Tab 4: Side-by-Side Comparison Matrix
        with sub_tab4:
            st.markdown("### ⚔️ Candidate Side-by-Side Comparison Matrix")

            def reset_cmp_candidates():
                st.session_state["cmp_cand_a"] = None
                st.session_state["cmp_cand_b"] = None

            sel_role_sub4 = st.selectbox(
                "Select Target Role for Comparison",
                role_options,
                key="hub_role_sel_tab4",
                on_change=reset_cmp_candidates
            )
            cands_tab4 = get_shortlisted_candidates_by_role(sel_role_sub4)

            if len(cands_tab4) < 2:
                st.info(f"At least 2 candidates needed in role '{sel_role_sub4}' to perform side-by-side comparison.")
            else:
                cmp_col1, cmp_col2 = st.columns(2)
                cand_dict = {f"{c['candidate_name']} ({c['score_0_100']} Fit Score)": c for c in cands_tab4}
                cand_labels = list(cand_dict.keys())

                with cmp_col1:
                    sel_a = st.selectbox(
                        "Select Candidate A",
                        cand_labels,
                        index=None,
                        placeholder="Choose Candidate A...",
                        key="cmp_cand_a"
                    )
                    c1 = cand_dict.get(sel_a) if sel_a else None

                with cmp_col2:
                    sel_b = st.selectbox(
                        "Select Candidate B",
                        cand_labels,
                        index=None,
                        placeholder="Choose Candidate B...",
                        key="cmp_cand_b"
                    )
                    c2 = cand_dict.get(sel_b) if sel_b else None

                st.markdown("---")

                col_a, col_b = st.columns(2)
                with col_a:
                    if not c1:
                        st.info("👈 Please select Candidate A from the dropdown above to view evaluation profile.")
                    else:
                        ring = render_confidence_ring(c1["score_0_100"], c1["decision"], size=52)
                        dec_chip = render_chip(c1["decision"], kind="decision")
                        flag_chip = render_chip(c1.get("flags", "none"), kind="flag")
                        skill_tags = render_skill_tags(c1.get("key_strengths", ""))

                        st.markdown(f"""
                        <div style="background: var(--surface-bg); border: 1px solid var(--border-hairline); border-radius: 14px; padding: 20px; font-family: 'Inter', sans-serif;">
                          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
                            <div>
                              <h3 style="margin: 0; font-size: 1.2rem; color: var(--text-primary);">{c1['candidate_name']}</h3>
                              <div style="font-size: 0.8rem; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; margin-top: 3px;">File: {c1['resume_filename']}</div>
                            </div>
                            {ring}
                          </div>
                          <div style="display: flex; gap: 8px; margin-bottom: 14px;">
                            {dec_chip} {flag_chip}
                          </div>
                          <div style="margin-bottom: 12px;">
                            <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;">Target Role</div>
                            <div style="font-size: 0.9rem; font-weight: 500; color: var(--text-primary);">{c1['jd_title']}</div>
                          </div>
                          <div style="margin-bottom: 12px;">
                            <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;">Contact Info</div>
                            <div style="font-size: 0.84rem; color: var(--text-secondary);">Email: <code style="color: var(--brand-accent);">{c1.get('email') or 'N/A'}</code> | Phone: <code style="color: var(--text-primary);">{c1.get('phone') or 'N/A'}</code></div>
                          </div>
                          <div style="margin-bottom: 12px;">
                            <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;">Key Strengths & Extracted Skills</div>
                            <div style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.4;">{c1.get('key_strengths')}</div>
                            {skill_tags}
                          </div>
                          <div style="margin-bottom: 12px;">
                            <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: #FB7185; margin-bottom: 4px;">Qualification Gaps</div>
                            <div style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.4;">{c1.get('key_gaps')}</div>
                          </div>
                          <div>
                            <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;">AI Rationale</div>
                            <div style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.4; background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px;">{c1.get('rationale')}</div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

                with col_b:
                    if not c2:
                        st.info("👉 Please select Candidate B from the dropdown above to view evaluation profile.")
                    else:
                        ring = render_confidence_ring(c2["score_0_100"], c2["decision"], size=52)
                        dec_chip = render_chip(c2["decision"], kind="decision")
                        flag_chip = render_chip(c2.get("flags", "none"), kind="flag")
                        skill_tags = render_skill_tags(c2.get("key_strengths", ""))

                        st.markdown(f"""
                        <div style="background: var(--surface-bg); border: 1px solid var(--border-hairline); border-radius: 14px; padding: 20px; font-family: 'Inter', sans-serif;">
                          <div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 14px;">
                            <div>
                              <h3 style="margin: 0; font-size: 1.2rem; color: var(--text-primary);">{c2['candidate_name']}</h3>
                              <div style="font-size: 0.8rem; color: var(--text-secondary); font-family: 'JetBrains Mono', monospace; margin-top: 3px;">File: {c2['resume_filename']}</div>
                            </div>
                            {ring}
                          </div>
                          <div style="display: flex; gap: 8px; margin-bottom: 14px;">
                            {dec_chip} {flag_chip}
                          </div>
                          <div style="margin-bottom: 12px;">
                            <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;">Target Role</div>
                            <div style="font-size: 0.9rem; font-weight: 500; color: var(--text-primary);">{c2['jd_title']}</div>
                          </div>
                          <div style="margin-bottom: 12px;">
                            <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;">Contact Info</div>
                            <div style="font-size: 0.84rem; color: var(--text-secondary);">Email: <code style="color: var(--brand-accent);">{c2.get('email') or 'N/A'}</code> | Phone: <code style="color: var(--text-primary);">{c2.get('phone') or 'N/A'}</code></div>
                          </div>
                          <div style="margin-bottom: 12px;">
                            <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;">Key Strengths & Extracted Skills</div>
                            <div style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.4;">{c2.get('key_strengths')}</div>
                            {skill_tags}
                          </div>
                          <div style="margin-bottom: 12px;">
                            <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: #FB7185; margin-bottom: 4px;">Qualification Gaps</div>
                            <div style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.4;">{c2.get('key_gaps')}</div>
                          </div>
                          <div>
                            <div style="font-size: 0.78rem; font-weight: 600; text-transform: uppercase; color: var(--text-muted); margin-bottom: 4px;">AI Rationale</div>
                            <div style="font-size: 0.84rem; color: var(--text-secondary); line-height: 1.4; background: rgba(255,255,255,0.03); padding: 10px; border-radius: 8px;">{c2.get('rationale')}</div>
                          </div>
                        </div>
                        """, unsafe_allow_html=True)

# ==========================================
# SCREEN 3: RESUME REPOSITORY (SUB-SCREEN TABS)
# ==========================================
elif selected_screen == "Resume Repository":
    st.markdown("## Database Resume & Run Repository")
    runs = get_all_runs()
    if not runs:
        st.info("No past runs stored in database yet.")
    else:
        repo_sub1, repo_sub2 = st.tabs([
            "Pipeline Execution History",
            "Stored Candidate Resumes Repository"
        ])

        with repo_sub1:
            run_df = pd.DataFrame(runs)
            st.dataframe(
                run_df,
                column_config={
                    "run_id": st.column_config.TextColumn("Run Identifier", width="medium"),
                    "timestamp": st.column_config.TextColumn("Execution Date & Time", width="medium"),
                    "jd_filename": st.column_config.TextColumn("JD Source File"),
                    "jd_title": st.column_config.TextColumn("Job Title"),
                    "total_resumes": st.column_config.NumberColumn("Candidates Evaluated"),
                    "status": st.column_config.TextColumn("Run Status")
                },
                use_container_width=True,
                hide_index=True
            )

            selected_run_id = st.selectbox("Select Run ID to Inspect Details", run_df["run_id"].unique(), key="repo_run_sel")
            if selected_run_id:
                st.markdown(f"#### Evaluation Results for Run: `{selected_run_id}`")
                run_results = get_results_by_run(selected_run_id)
                if run_results:
                    st.markdown(build_candidate_html_table(run_results), unsafe_allow_html=True)

        with repo_sub2:
            sel_run_resumes = st.selectbox("Select Run ID for Stored Resumes", [r["run_id"] for r in runs], key="repo_resumes_sel")
            if sel_run_resumes:
                stored_resumes = get_resumes_by_run(sel_run_resumes)
                if stored_resumes:
                    st.dataframe(
                        pd.DataFrame(stored_resumes)[["filename", "file_type", "file_size_bytes", "created_at"]],
                        column_config={
                            "filename": st.column_config.TextColumn("Resume File Name"),
                            "file_type": st.column_config.TextColumn("Format"),
                            "file_size_bytes": st.column_config.NumberColumn("File Size (Bytes)"),
                            "created_at": st.column_config.TextColumn("Uploaded At")
                        },
                        use_container_width=True,
                        hide_index=True
                    )

# ==========================================
# SCREEN 4: RECRUITER FEEDBACK LOOP (SUB-SCREEN TABS)
# ==========================================
elif selected_screen == "Recruiter Feedback Loop":
    st.markdown("## Recruiter Feedback & Adaptive Memory System")
    st.markdown("<p style='color: #8E8CA3; font-size: 0.9rem;'>In human-in-the-loop screening, recruiters submit decision corrections. Validated feedback is injected into Gemini context.</p>", unsafe_allow_html=True)

    fb_sub1, fb_sub2 = st.tabs([
        "Pending Corrections (Admin Approval Gate)",
        "Approved & Validated Prompt Context"
    ])

    with fb_sub1:
        pending_items = get_pending_feedback()
        if not pending_items:
            st.info("No pending recruiter corrections awaiting review.")
        else:
            st.markdown(f"Found **{len(pending_items)}** pending correction(s) requiring admin review:")
            for item in pending_items:
                orig_chip = render_chip(item['original_decision'], kind="decision")
                new_chip = render_chip(item['corrected_decision'], kind="decision")
                
                # Individual Rounded Row Container
                with st.container(border=True):
                    r_col1, r_col2 = st.columns([3.5, 1], vertical_alignment="center")
                    with r_col1:
                        st.markdown(f"""
                        <div style="font-weight: 600; font-size: 1.05rem; color: #F2F1F7; margin-bottom: 4px;">
                            {item['candidate_name']} <span style="font-size: 0.8rem; color: #8E8CA3; font-family: 'JetBrains Mono', monospace;">({item['resume_filename']})</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                            <span style="font-size: 0.82rem; color: #8E8CA3;">Correction:</span>
                            {orig_chip}
                            <span style="color: #6E62F5; font-weight: 600;">➔</span>
                            {new_chip}
                        </div>
                        <div style="font-size: 0.85rem; color: #F2F1F7; background: #1C1C28; padding: 6px 12px; border-radius: 6px; border: 1px solid #26262F; margin-top: 4px;">
                            <strong>Recruiter Rationale</strong>: <em>{item['feedback_notes']}</em>
                        </div>
                        <div style="font-size: 0.75rem; color: #5C5A6E; margin-top: 6px;">
                            Submitted: {item['timestamp']} | Run ID: <span style="font-family: 'JetBrains Mono', monospace;">{item['run_id']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                    
                    with r_col2:
                        st.markdown('<div class="btn-approve-green">', unsafe_allow_html=True)
                        if st.button("Approve", key=f"btn_approve_{item['feedback_id']}", use_container_width=True):
                            approve_feedback(item["feedback_id"])
                            st.success(f"Approved correction for '{item['candidate_name']}'!")
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

    with fb_sub2:
        validated_fb = get_validated_feedback(limit=50)
        if not validated_fb:
            st.info("No approved feedback items in the active prompt context yet.")
        else:
            v_df = pd.DataFrame(validated_fb)
            st.dataframe(
                v_df[["timestamp", "resume_filename", "candidate_name", "original_decision", "original_score", "corrected_decision", "feedback_notes"]],
                column_config={
                    "timestamp": st.column_config.TextColumn("Approved Date"),
                    "candidate_name": st.column_config.TextColumn("Candidate Name"),
                    "original_decision": st.column_config.TextColumn("Model Decision"),
                    "original_score": st.column_config.NumberColumn("Model Score"),
                    "corrected_decision": st.column_config.TextColumn("Recruiter Correction"),
                    "feedback_notes": st.column_config.TextColumn("Recruiter Guidance Notes", width="large")
                },
                use_container_width=True,
                hide_index=True
            )

# ==========================================
# SCREEN 5: SYSTEM EXECUTION LOGS
# ==========================================
elif selected_screen == "System Execution Logs":
    st.markdown("## System Execution Logs Viewer")
    runs = get_all_runs()
    if runs:
        sel_run_log = st.selectbox("Select Run ID for Logs", [r["run_id"] for r in runs], key="log_run_sel")
        if sel_run_log:
            logs = get_logs_by_run(sel_run_log)
            if logs:
                log_df = pd.DataFrame(logs)
                st.dataframe(
                    log_df[["timestamp", "stage", "level", "message"]],
                    column_config={
                        "timestamp": st.column_config.TextColumn("Log Timestamp", width="medium"),
                        "stage": st.column_config.TextColumn("Pipeline Stage", width="medium"),
                        "level": st.column_config.TextColumn("Log Level", width="small"),
                        "message": st.column_config.TextColumn("Log Message", width="large")
                    },
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No logs found for this run.")
    else:
        st.info("No run logs available yet.")

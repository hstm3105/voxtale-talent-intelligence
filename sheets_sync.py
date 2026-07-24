import os
import io
import re
import json
import datetime
import traceback
from typing import List, Dict, Any, Optional
import pandas as pd
from utils.logger import logger

def extract_spreadsheet_id(url_or_id: str) -> str:
    """Extracts clean spreadsheet ID from raw URL or key string."""
    clean = url_or_id.strip()
    match = re.search(r'/d/([a-zA-Z0-9-_]+)', clean)
    if match:
        return match.group(1)
    return clean

def generate_excel_for_sheets(results_data: List[Dict[str, Any]]) -> bytes:
    """Generates a downloadable Excel (.xlsx) file bytes formatted for Google Sheets import."""
    header = ["resume_filename", "candidate_name", "decision", "score_0_100", "key_strengths", "key_gaps", "flags", "rationale"]
    df = pd.DataFrame(results_data)
    
    # Ensure all columns exist in contract order
    for col in header:
        if col not in df.columns:
            df[col] = ""
    df = df[header]

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Shortlist Results')
    return output.getvalue()

def export_to_google_sheets(
    results_data: List[Dict[str, Any]], 
    spreadsheet_title: str = "Resume Shortlisting Results",
    service_account_dict: Optional[dict] = None,
    spreadsheet_id_or_url: Optional[str] = None
) -> Dict[str, Any]:
    """Syncs evaluation results to a Google Sheet by creating a NEW timestamped tab per run."""
    import gspread
    
    gc = None
    service_account_email = None
    target_id = extract_spreadsheet_id(spreadsheet_id_or_url) if spreadsheet_id_or_url else None

    # Scopes: If target sheet specified, use Sheets-only scope
    if target_id:
        scopes = ['https://www.googleapis.com/auth/spreadsheets']
    else:
        scopes = ['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']

    # 1. Try dict passed from UI
    if service_account_dict:
        try:
            gc = gspread.service_account_from_dict(service_account_dict, scopes=scopes)
            service_account_email = service_account_dict.get("client_email")
        except Exception as e:
            return {
                "success": False, 
                "message": f"Invalid Service Account JSON provided: {e}",
                "traceback": traceback.format_exc(),
                "url": None
            }

    # 2. Try credentials file or env path
    if not gc:
        credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "google_credentials.json")
        if os.path.exists(credentials_path):
            try:
                with open(credentials_path, "r") as f:
                    sa_data = json.load(f)
                    service_account_email = sa_data.get("client_email")
                gc = gspread.service_account(filename=credentials_path, scopes=scopes)
            except Exception as e:
                return {
                    "success": False, 
                    "message": f"Error loading credentials from '{credentials_path}': {e}",
                    "traceback": traceback.format_exc(),
                    "url": None
                }

    # 3. Try Streamlit secrets
    if not gc:
        try:
            import streamlit as st
            sa_sec = st.secrets.get("GOOGLE_SERVICE_ACCOUNT_JSON", None)
            if sa_sec:
                if isinstance(sa_sec, str):
                    sa_data = json.loads(sa_sec)
                else:
                    sa_data = dict(sa_sec)
                gc = gspread.service_account_from_dict(sa_data, scopes=scopes)
                service_account_email = sa_data.get("client_email")
            if not target_id and st.secrets.get("TARGET_SHEET_URL"):
                target_id = extract_spreadsheet_id(st.secrets.get("TARGET_SHEET_URL"))
        except Exception:
            pass

    if not gc:
        logger.warning("Google credentials not provided. Google Sheets sync requires Service Account JSON.")
        return {
            "success": False,
            "message": "Google Credentials key missing. Please paste/upload your Google Service Account JSON key in the sidebar configuration expander.",
            "traceback": None,
            "url": None
        }

    try:
        sh = None
        if target_id:
            logger.info(f"Opening Google Sheet by key ID: {target_id}")
            sh = gc.open_by_key(target_id)
        else:
            try:
                sh = gc.open(spreadsheet_title)
            except gspread.SpreadsheetNotFound:
                sh = gc.create(spreadsheet_title)

        # Generate unique timestamped tab name for this run
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        tab_name = f"Run {now_str}"

        header = ["resume_filename", "candidate_name", "decision", "score_0_100", "key_strengths", "key_gaps", "flags", "rationale"]
        new_rows = []
        for item in results_data:
            new_rows.append([
                str(item.get("resume_filename", "")),
                str(item.get("candidate_name", "")),
                str(item.get("decision", "")),
                int(item.get("score_0_100", 0)),
                str(item.get("key_strengths", "")),
                str(item.get("key_gaps", "")),
                str(item.get("flags", "")),
                str(item.get("rationale", ""))
            ])

        # Create new timestamped worksheet tab inside the spreadsheet
        try:
            worksheet = sh.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=tab_name, rows=len(new_rows) + 10, cols=len(header) + 2)

        # Populate header + records into the new timestamped tab
        worksheet.update(values=[header] + new_rows, range_name="A1")
        
        logger.info(f"Successfully created timestamped tab '{tab_name}' with {len(new_rows)} records in Google Sheet: {sh.url}")
        return {
            "success": True,
            "message": f"Successfully created tab '{tab_name}' with {len(new_rows)} records in Google Sheet!",
            "traceback": None,
            "url": sh.url
        }

    except Exception as e:
        err_str = str(e)
        tb_str = traceback.format_exc()
        logger.error(f"Google Sheets export error: {err_str}\n{tb_str}")
        
        if "sheets.googleapis.com" in err_str or "Google Sheets API" in err_str:
            return {
                "success": False,
                "message": "⚠️ Google Sheets API is disabled in your GCP Project 249852995966. Please enable [Google Sheets API](https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project=249852995966) in GCP Console.",
                "traceback": tb_str,
                "url": None
            }

        if "drive.googleapis.com" in err_str or "Google Drive API" in err_str:
            return {
                "success": False,
                "message": "⚠️ Google Drive API is disabled in your GCP Project. Enable [Google Drive API](https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=249852995966) in GCP Console.",
                "traceback": tb_str,
                "url": None
            }

        if isinstance(e, gspread.SpreadsheetNotFound):
            email_msg = f" (`{service_account_email}`)" if service_account_email else ""
            return {
                "success": False,
                "message": f"Spreadsheet Not Found / Access Denied. You must share your target Google Sheet with your Service Account email{email_msg} as 'Editor'.",
                "traceback": tb_str,
                "url": None
            }

        if "403" in err_str or "PERMISSION_DENIED" in err_str:
            email_msg = f" (`{service_account_email}`)" if service_account_email else ""
            return {
                "success": False,
                "message": f"Permission Error (403): Please share your target Google Sheet with your Service Account email{email_msg} as 'Editor'.",
                "traceback": tb_str,
                "url": None
            }
        
        return {
            "success": False,
            "message": f"Google Sheets API Error: {err_str}",
            "traceback": tb_str,
            "url": None
        }

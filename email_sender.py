import os
import smtplib
import unicodedata
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.header import Header
from typing import Dict, Any, List, Optional
from utils.logger import logger

DEFAULT_RECIPIENT_EMAIL = "harshit.sharma.3105@gmail.com"
DEFAULT_SENDER_EMAIL = "harshits2023@email.iimcal.ac.in"
DEFAULT_SENDER_PASSWORD = "Anagugu@03081997"

def sanitize_str(s: Optional[str]) -> str:
    """Sanitizes text by replacing non-breaking spaces (\xa0) and stripping whitespace."""
    if not s:
        return ""
    # Normalize unicode to NFKD and replace \xa0 with space
    normalized = unicodedata.normalize("NFKD", str(s))
    return normalized.replace("\xa0", " ").strip()

def send_results_email(
    recipient_email: str = DEFAULT_RECIPIENT_EMAIL,
    excel_bytes: bytes = b"",
    filename: str = "shortlist_results.xlsx",
    run_id: str = "run_latest",
    results_summary: Optional[List[Dict[str, Any]]] = None,
    smtp_server: str = "smtp.gmail.com",
    smtp_port: int = 587,
    sender_email: Optional[str] = None,
    sender_password: Optional[str] = None
) -> Dict[str, Any]:
    """Sends an email with the shortlist results Excel (.xlsx) file attached."""
    sender_email = sanitize_str(sender_email or os.getenv("SENDER_EMAIL") or DEFAULT_SENDER_EMAIL)
    sender_password = sanitize_str(sender_password or os.getenv("SENDER_APP_PASSWORD") or DEFAULT_SENDER_PASSWORD)
    recipient_email = sanitize_str(recipient_email or DEFAULT_RECIPIENT_EMAIL)

    if not sender_email or not sender_password:
        return {
            "success": False,
            "message": "SMTP Sender Credentials missing. Please enter your Sender Email & App Password in the sidebar expander under '✉️ Email Sender Settings'.",
            "details": None
        }

    try:
        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = recipient_email
        msg["Subject"] = str(Header(f"🤖 VoxTale Resume Shortlist Results — Run [{run_id}]", "utf-8"))

        # Calculate statistics
        total = len(results_summary) if results_summary else 0
        shortlisted = sum(1 for r in (results_summary or []) if r.get("decision") == "Shortlist")
        maybe = sum(1 for r in (results_summary or []) if r.get("decision") == "Maybe")
        review = sum(1 for r in (results_summary or []) if r.get("decision") == "Needs Manual Review")
        rejected = sum(1 for r in (results_summary or []) if r.get("decision") == "Reject")

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333333; line-height: 1.6;">
            <div style="background-color: #1E293B; padding: 20px; text-align: center; color: #ffffff; border-radius: 8px 8px 0 0;">
                <h2 style="margin: 0;">🤖 VoxTale Agentic Resume Shortlisting Report</h2>
                <p style="margin: 5px 0 0 0; font-size: 0.9em;">Run ID: {run_id}</p>
            </div>
            <div style="padding: 20px; border: 1px solid #E2E8F0; border-top: none; border-radius: 0 0 8px 8px;">
                <p>Hello Harshit,</p>
                <p>Your agentic resume shortlisting pipeline execution has completed. Attached to this email is the full candidate evaluation report in Excel (<strong>.xlsx</strong>) format.</p>
                
                <h3 style="color: #1E293B;">📊 Batch Summary</h3>
                <ul>
                    <li><strong>Total Resumes Evaluated:</strong> {total}</li>
                    <li><strong>Shortlisted (Score &ge; 80):</strong> <span style="color: #15803D; font-weight: bold;">{shortlisted}</span></li>
                    <li><strong>Maybe (Score 60-79):</strong> <span style="color: #B45309; font-weight: bold;">{maybe}</span></li>
                    <li><strong>Needs Manual Review (Flagged):</strong> <span style="color: #6B21A8; font-weight: bold;">{review}</span></li>
                    <li><strong>Rejected:</strong> <span style="color: #B91C1C; font-weight: bold;">{rejected}</span></li>
                </ul>

                <p>The attached Excel file contains complete candidate names, fit scores (0-100), key strengths, gaps, security flags, and recruiter rationales conforming to your output contract.</p>
                <br>
                <p>Best regards,<br><strong>VoxTale AI Shortlister System</strong></p>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_content, "html", "utf-8"))

        # Attach Excel file
        if excel_bytes:
            part = MIMEApplication(excel_bytes, Name=filename)
            part['Content-Disposition'] = f'attachment; filename="{filename}"'
            msg.attach(part)

        # Connect to SMTP Server
        logger.info(f"Connecting to SMTP server {smtp_server}:{smtp_port} with sender {sender_email}...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()

        logger.info(f"Successfully sent results email to {recipient_email}")
        return {
            "success": True,
            "message": f"Successfully emailed shortlist results (.xlsx) to {recipient_email}!",
            "details": None
        }

    except Exception as e:
        err_str = str(e)
        logger.error(f"Email sending failed: {err_str}")

        if "534" in err_str or "InvalidSecondFactor" in err_str or "Application-specific password required" in err_str:
            return {
                "success": False,
                "message": f"⚠️ Google Account Security (534): 2-Factor Authentication is enabled on '{sender_email}'. Google requires a 16-character **App Password** (not standard login password) to send emails via SMTP.\n\n👉 **To generate an App Password in 10 seconds**:\n1. Go to https://myaccount.google.com/apppasswords\n2. Type 'Resume Shortlister' and click Create.\n3. Paste the 16-character App Password into 'Sender App Password' in the sidebar expander!",
                "details": err_str
            }

        return {
            "success": False,
            "message": f"Email Error: {err_str}",
            "details": err_str
        }

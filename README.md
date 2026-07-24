# VoxTale - Agentic Resume Shortlister

An enterprise-grade, multi-stage agentic resume-shortlisting platform powered by Python, Streamlit, SQLite, and Google's Gemini API (default model: **Gemini 3.5 Flash Lite**). Designed to take any Job Description (JD) and candidate resumes in multi-format batch (TXT, PDF, DOCX), extracting structured requirements and providing an interactive UI with live pipeline stage visibility, database resume repository, Google Sheets live sync, and SMTP email invitation capabilities.

---

## 🌟 Key Features

1. **Interactive Web UI (Streamlit)**: Upload Job Description and candidate resume files via drag-and-drop with real-time candidate search and multi-select filtering by decision & flags.
2. **Multi-Format Ingestion**: Process TXT, PDF (`pdfplumber` + `pypdf`), and DOCX (`python-docx`) files in batch mode with multi-format duplicate detection.
3. **8-Stage Agentic Pipeline**: Autonomous JD requirement extraction, profile extraction, candidate isolation, fit evaluation, and deterministic guardrail rules engine.
4. **Gemini Foundation Models**: Support for **Gemini 3.5 Flash Lite** (Default), **Gemini 3 Flash**, and **Gemini 3.6 Flash**, configurable dynamically in top-right ⚙️ Settings.
5. **Robust Security & Edge Case Defense**:
   - **Sparse Resume Short-Circuit**: Fast-path detection of stub/empty resumes (< 35-40 words) flagging `insufficient_information`.
   - **Disguised Prompt Injection Scanner**: Heuristic pattern detection catching authority spoofing attacks (`NOTE FROM HIRING SYSTEM ADMINISTRATOR...`) and flagging `possible_prompt_injection`.
6. **Database Resume Repository (SQLite)**: Stores every pipeline run, raw resume document, extraction text, and evaluation result in a queryable SQLite database.
7. **Google Sheets & SMTP Email Integration**: Automated live sync to Google Sheets and one-click dispatch of live interview email invitations.
8. **Session Isolation & Cloud Deployment Ready**: Complete session state isolation for multi-user web apps with Streamlit Community Cloud Secrets support.

---

## 🛠️ Requirements & Installation

### Setup Instructions

1. Clone or navigate to the project directory:
   ```bash
   cd ~/Desktop/resume_shortlister
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set your Gemini API Key:
   ```bash
   export GEMINI_API_KEY="your-gemini-api-key-here"
   ```
   *Note: You can also enter the API key directly in the Streamlit web app Settings modal, or configure it in Streamlit Cloud Secrets!*

---

## 💻 Running the Web Application (Interactive UI)

To launch the interactive web app:

```bash
streamlit run app.py
```

Open your browser at **`http://localhost:8501`**.

### App Screens:
- **Screen 1: 🚀 Run Shortlisting Pipeline**: Upload JD text/file and candidate resumes. Click "Start Shortlisting Pipeline" to execute the 8-stage workflow.
- **Screen 2: 📊 Shortlist Hub & Scheduler**: Search and filter shortlisted candidates, export CSV/Excel, sync to Google Sheets, and preview/send live interview email invitations.
- **Screen 3: 📁 Resume Repository**: Inspect historical runs, raw resume documents, and full candidate score records.
- **Screen 4: 🧠 Recruiter Feedback Loop**: Review recruiter corrections and approve validated few-shot examples for in-context learning.
- **Screen 5: 📜 System Execution Logs**: Inspect stage-by-stage execution logs and security events.

---

## 🖥️ Running via Command Line (CLI)

To run the pipeline directly via terminal:

```bash
python main.py --jd sample_data/sample_jd.txt --resumes sample_data/ --output output.csv
```

---

## 🧪 Running the Automated Evaluation Suite

To execute the automated evaluation test suite against 16 edge cases:

1. Generate test data files:
   ```bash
   python generate_test_files.py
   ```

2. Run the evaluation suite:
   ```bash
   python eval_suite.py
   ```

---

## 📊 Output CSV Contract

The system outputs a CSV file conforming to the exact contract below:

| Column | Description | Vocabulary / Constraints |
| :--- | :--- | :--- |
| `resume_filename` | Original filename of candidate resume | e.g. `01_alice_johnson_shortlist.txt` |
| `candidate_name` | Extracted full candidate name | e.g. `Alice Johnson` |
| `decision` | Final shortlisting decision | `Shortlist` \| `Maybe` \| `Reject` \| `Needs Manual Review` |
| `score_0_100` | Integer fit score | `0` to `100` |
| `key_strengths` | 2-3 concrete, JD-specific strengths | Semicolon-delimited string |
| `key_gaps` | 2-3 concrete gaps or missing qualifications | Semicolon-delimited string |
| `flags` | Security or data quality flags | `none` \| `overqualified` \| `duplicate_submission` \| `insufficient_information` \| `possible_prompt_injection` \| `other` |
| `rationale` | Audit-ready summary explaining decision | Free-text string |

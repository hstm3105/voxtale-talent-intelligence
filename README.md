# VoxTale - Agentic Resume Shortlister & Talent Intelligence

An enterprise-grade, multi-stage agentic candidate screening and decision platform powered by Python, Streamlit, SQLite, and Google's Gemini API (default model: **Gemini 3.5 Flash Lite**).

Designed to analyze any Job Description (JD) and candidate resumes in batch across multiple formats (TXT, PDF, DOCX), extracting structured requirements and presenting an interactive Studio UI with live pipeline stage visibility, database resume repository, side-by-side candidate comparison matrix, Google Sheets live sync, and automated SMTP email invitations.

---

## 🌟 Key Features

1. **Studio-Grade Web Application (Streamlit)**: 
   - Executive feature-oriented sidebar navigation menu with real-time candidate and run counters.
   - Studio Dark Mode theme (`#0B0B10`) with glassmorphic metric cards, circular score rings, and high-contrast typography.
2. **5 Integrated Application Workspaces**:
   - **🚀 Run Shortlisting Pipeline**: Multi-file drag-and-drop batch ingestion with real-time execution progress.
   - **📊 Shortlist Hub & Scheduler**: 4 dedicated sub-tabs:
     - `Master Candidate List`: Real-time candidate search, score rings, decision/flag filters, and embedded JD role picker.
     - `Schedule an Interview`: Candidate contact extraction, email draft generator, and automated SMTP dispatch.
     - `Candidate Dossiers`: Complete candidate evaluation dossiers with strengths, gaps, and AI rationales.
     - `⚔️ Side-by-Side Comparison`: Interactive comparison matrix comparing Candidate A and Candidate B side-by-side, featuring automatic selection resets on role change.
   - **📁 Resume Repository**: Queryable SQLite database history of all past pipeline runs, raw candidate text, and full evaluation results.
   - **🧠 Recruiter Feedback Loop**: Labeled few-shot feedback queue with two-stage admin approval (`is_validated`).
   - **📜 System Execution Logs**: Stage-by-stage pipeline logs, execution timestamps, and security events.
3. **Multi-Format Ingestion Cascade**: Process TXT, PDF (`pdfplumber` layout-preserving parser + `pypdf` fallback), and DOCX (`python-docx`) files in batch with cross-format 4-gram Jaccard duplicate detection.
4. **8-Stage Agentic Pipeline**: Autonomous JD requirement extraction, profile extraction, candidate isolation, fit evaluation, and deterministic guardrail rules engine.
5. **Gemini Foundation Models**: Configurable support for **Gemini 3.5 Flash Lite** (Default), **Gemini 3 Flash**, and **Gemini 3.6 Flash**, with automatic 429 rate-limit exponential backoff retries.
6. **Robust Security & Edge Case Defense**:
   - **Sparse Resume Short-Circuit**: Fast-path detection of stub/empty resumes (< 40 words) flagging `insufficient_information`.
   - **Disguised Prompt Injection Scanner**: Multi-pattern heuristic scanner detecting authority spoofing attacks (`NOTE FROM HIRING SYSTEM ADMINISTRATOR...`) and flagging `possible_prompt_injection`.
7. **Clean Skill Token Deduplication**: Intelligent technical keyword extractor (`extract_skill_tokens`) preventing multi-sentence duplication between card body text and skill pill badges.
8. **Exhaustive Error Safeguards & Streamlit Cloud Deployment Ready**:
   - Every database query in `database.py` wrapped in protective `try...except` catch loops.
   - Automated root directory `sys.path` resolution in `app.py` for seamless Streamlit Community Cloud deployment.

---

## 🛠️ Requirements & Local Setup

### Setup Instructions

1. Clone or navigate to the project repository:
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
   *Note: You can also configure your API key directly inside the app's top-right ⚙️ Settings modal or via Streamlit Secrets!*

---

## 💻 Running the Web Application

To launch the interactive web application:

```bash
streamlit run app.py
```

Open your web browser at **`http://localhost:8501`**.

---

## ☁️ Deploying to Streamlit Community Cloud

1. Push the code to your GitHub repository:
   ```bash
   git add .
   git commit -m "deploy: Prepare for Streamlit Cloud"
   git push origin main
   ```
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create a **New App**, select your repository `voxtale-talent-intelligence`, and set Main file path to `app.py`.
3. In **Advanced Settings -> Secrets**, configure your keys:
   ```toml
   GEMINI_API_KEY = "AIzaSy..."
   SENDER_EMAIL = "your-email@gmail.com"
   SENDER_APP_PASSWORD = "abcd efgh ijkl mnop"
   ```

---

## 🖥️ Running via Command Line (CLI)

To run the pipeline directly via terminal:

```bash
python main.py --jd sample_data/sample_jd.txt --resumes sample_data/ --output output.csv
```

---

## 🧪 Running the Automated Evaluation Suite

To execute the automated test suite against 16 edge cases:

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


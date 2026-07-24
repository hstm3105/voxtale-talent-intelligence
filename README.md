# Agentic Resume-Shortlisting System

An enterprise-grade, multi-stage agentic resume-shortlisting platform powered by Python, Streamlit, SQLite, and Google's Gemini API. Designed to take any Job Description (JD) and a directory of candidate resumes in any format (TXT, PDF, DOCX), extracting structured requirements and providing an interactive UI with live pipeline stage visibility, database resume repository, and Google Sheets export capabilities.

---

## 🌟 Key Features

1. **Interactive Web UI (Streamlit)**: Upload Job Description and multiple candidate resume files via drag-and-drop.
2. **Multi-Format Processing**: Process TXT, PDF (`pdfplumber` + `pypdf`), and DOCX (`python-docx`) files in batch mode.
3. **Live Pipeline Stage Visibility**: Real-time stage progress tracker ideal for live interview panel demonstrations.
4. **Database Resume Repository (SQLite)**: Stores every pipeline run, raw resume document, extraction text, and evaluation result in a queryable SQLite database.
5. **System Run Logs**: Detailed stage-by-stage execution logs maintained per run.
6. **Google Sheets & CSV Export**: One-click results download and automated sync to Google Sheets.

---

## 🛠️ Requirements & Installation

### Setup Instructions

1. Navigate to the project directory on Desktop:
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
   *Note: You can also enter the API key directly in the Streamlit web app sidebar!*

---

## 💻 Running the Web Application (Interactive UI)

To launch the interactive web app with live stage visibility:

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501`.

### App Layout & Capabilities:
- **Tab 1: 🚀 Run Shortlister (Live Demo)**: Upload JD text/file and multiple resume files. Click "Start Shortlisting Pipeline" to watch live stage progress and inspect candidate cards.
- **Tab 2: 📁 Resume Database Repository**: View past runs, stored resume binary details, and candidate score records.
- **Tab 3: 📜 Run Execution Logs**: Inspect stage logs, security alerts, and run events.

---

## 🖥️ Running via Command Line (CLI)

To run the pipeline directly via terminal:

```bash
python main.py --jd sample_data/sample_jd.txt --resumes sample_data/ --output output.csv
```

---

## 🧪 Running the Automated Evaluation Suite

To execute the automated evaluation test suite against hand-crafted edge cases:

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
| `resume_filename` | Original filename of candidate resume | e.g. `resume_alice_johnson.txt` |
| `candidate_name` | Extracted full candidate name | e.g. `Alice Johnson` |
| `decision` | Final shortlisting decision | `Shortlist` \| `Maybe` \| `Reject` \| `Needs Manual Review` |
| `score_0_100` | Integer fit score | `0` to `100` |
| `key_strengths` | 2-3 concrete, JD-specific strengths | Semicolon-delimited string |
| `key_gaps` | 2-3 concrete, JD-specific gaps | Semicolon-delimited string |
| `flags` | Categorical security / quality flag | `none` \| `unreadable_file` \| `insufficient_information` \| `possible_prompt_injection` \| `duplicate_submission` \| `overqualified` \| `other` |
| `rationale` | Recruiter-facing explanation | 1 to 3 concise sentences |

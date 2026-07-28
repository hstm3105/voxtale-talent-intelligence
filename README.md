# VoxTale — Talent Intelligence & Candidate Screening Platform

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/streamlit-1.30+-FF4B4B.svg?style=flat&logo=streamlit&logoColor=white)](https://streamlit.io/)
[![Google Gemini API](https://img.shields.io/badge/Gemini_API-3.5_Flash-4285F4.svg?style=flat&logo=google&logoColor=white)](https://ai.google.dev/)
[![SQLite](https://img.shields.io/badge/Database-SQLite-003B57.svg?style=flat&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat)](LICENSE)

**VoxTale** is an enterprise-grade, multi-stage candidate screening and talent intelligence platform. Powered by Python, Streamlit, SQLite, and Google's Gemini API, VoxTale dynamically analyzes Job Descriptions (JDs) and parses multi-format candidate resumes in batch (PDF, DOCX, TXT) to deliver audit-ready, unbiased recruitment evaluations.

---

## 🌐 Live Application & Repositories

| Link Type | URL |
| :--- | :--- |
| **🚀 Live Production Web App** | [**voxtale-talent-intelligence.streamlit.app**](https://voxtale-talent-intelligence.streamlit.app/) |
| **📂 Source Code Repository** | [**github.com/hstm3105/voxtale-talent-intelligence**](https://github.com/hstm3105/voxtale-talent-intelligence) |

---

## ⚡ How to Test & Verify in 60 Seconds

You can evaluate and test VoxTale immediately using the pre-packaged sample files in the [`sample_data/`](sample_data/) folder:

### 1. Test on the Live Web Application (Instant Web Access)
1. Open the [**Live Web App**](https://voxtale-talent-intelligence.streamlit.app/).
2. Enter your **Gemini API Key** in the top-right **⚙️ Settings** modal (or configure it via environment).
3. Navigate to **Workspace 1: 🚀 Run Shortlisting Pipeline**.
4. Copy & paste the contents of [`sample_data/sample_jd.txt`](sample_data/sample_jd.txt) into the Job Description field.
5. Drag and drop the candidate resume files from [`sample_data/`](sample_data/) (e.g. `ec01_strong_fit.txt`, `ec02_clear_reject.txt`, `ec05_prompt_injection_attempt.txt`, etc.).
6. Click **Run Shortlisting Pipeline** to watch live stage execution, inspect fit scores, view candidate dossiers, compare candidates side-by-side, and sync to Google Sheets!

### 2. Test via Terminal CLI
```bash
# Set your API Key and run against pre-packaged sample files
export GEMINI_API_KEY="your_api_key_here"
python main.py --jd sample_data/sample_jd.txt --resumes sample_data/ --output output.csv
```

---

## 🌟 Architectural Overview & Core Capabilities

VoxTale replaces generic keyword matchers with an **8-Stage Autonomous Agentic Pipeline** backed by deterministic guardrails, two-layer prompt injection security, and human-in-the-loop recruiter memory.

```
┌─────────────────┐    ┌─────────────────────────┐    ┌───────────────────────────┐
│ Batch Ingestion │ ──>│ Concurrent Security     │ ──>│ Dynamic JD Requirement    │
│ (PDF, DOCX, TXT)│    │ (Heuristic + LLM Scan)  │    │ Extraction (Gemini)       │
└─────────────────┘    └─────────────────────────┘    └───────────────────────────┘
                                                                    │
┌─────────────────┐    ┌─────────────────────────┐    ┌─────────────▼─────────────┐
│ Duplicate Check │ <──│ Profile & Contact Info  │ <──│ Loud JDExtractionError    │
│ (4-Gram Jaccard)│    │ Structured Parsing      │    │ Safeguard (No Fabrication)│
└─────────────────┘    └─────────────────────────┘    └───────────────────────────┘
        │
┌───────▼─────────┐    ┌─────────────────────────┐    ┌───────────────────────────┐
│ Gemini Fit      │ ──>│ Guardrail Decision Engine│ ─>│ Role-Aware Persistence    │
│ Evaluation      │    │ (Shortlist/Maybe/Reject)│    │ (DB, CSV, Sheets, Email)  │
└─────────────────┘    └─────────────────────────┘    └───────────────────────────┘
```

### Key Highlights

- **8-Stage Autonomous Pipeline**: End-to-end multi-agent orchestration for ingestion, security scanning, requirement extraction, candidate profiling, duplicate detection, fit evaluation, deterministic decision scoring, and persistence.
- **Two-Layer Prompt Injection Security**:
  - *Layer 1 (Heuristic Fast-Pass)*: Substring pattern matching against known injection keywords with **Unicode NFKD Normalization** and zero-width character stripping to catch homoglyph evasion (0 ms latency / 0 API cost).
  - *Layer 2 (Semantic LLM Classifier)*: Dedicated structured Gemini call (`InjectionScanResult`, `temperature=0.0`) detecting paraphrased override instructions, indirect commands, and fake executive clearance claims.
  - *XML Prompt Isolation*: Untrusted resume text is isolated inside `<untrusted_candidate_resume_data>` tags guarded by strict system-level instructions.
- **Loud Exception Safeguards (`JDExtractionError`)**: Eliminates silent fallback fabrications during JD parsing. On network failure, rate limit exhaustion, or schema invalidity, the pipeline fails loudly before evaluating candidates—preventing evaluation against empty requirement sets.
- **Role-Aware Data Persistence**: Every run creates a role-slugified identifier (e.g. `run_20260726_143000_senior_backend_engineer_a1b2`) and exports the target role across SQLite, CSVs, Excel reports, and Google Sheets tabs.
- **Human-in-the-Loop Recruiter Memory**: Recruiter decision corrections are submitted to an admin approval queue (`is_validated`). Validated feedback is dynamically injected into Gemini's evaluation prompt context as few-shot exemplars.

---

## 🎨 Interactive Studio Workspace (Streamlit)

The application provides 5 dedicated workspaces designed for recruiter productivity and operational visibility:

1. **🚀 Run Shortlisting Pipeline**: Batch file drag-and-drop uploader with real-time execution progress, live stage visibility, and status indicators.
2. **📊 Shortlist Hub & Scheduler**:
   - **Master Candidate List**: Multi-attribute search, decision/flag filters, score rings, and skill tag badges.
   - **Schedule an Interview**: Automated email draft generator with one-click SMTP email invitation dispatch.
   - **Candidate Dossiers**: In-depth candidate profiles featuring key strengths, qualification gaps, contact details, and AI rationales.
   - **Candidate Comparison Matrix**: Side-by-side comparison of candidate profiles with automatic reset handlers when changing target roles.
3. **📁 Resume Repository**: Fully queryable database of all past runs with **Target Role Dropdown Filters** and real-time **Run ID Search**.
4. **🧠 Recruiter Feedback Loop**: Labeled feedback memory queue for reviewing, approving, and embedding recruiter decision corrections.
5. **📜 System Execution Logs**: Real-time execution log timeline detailing stage events, warnings, and security alerts.

---

## 🚀 Quickstart & Local Setup

### Prerequisites

- **Python 3.9+**
- **Google Gemini API Key** ([Get your API key here](https://aistudio.google.com/))

### Installation

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/hstm3105/voxtale-talent-intelligence.git
   cd voxtale-talent-intelligence
   ```

2. **Create and Activate a Virtual Environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Set Your Gemini API Key**:
   ```bash
   export GEMINI_API_KEY="your_api_key_here"
   ```
   *(Alternatively, you can enter your API Key in the web app's top-right ⚙️ Settings modal or configure it via `.streamlit/secrets.toml`)*

5. **Launch the Web Application**:
   ```bash
   streamlit run app.py
   ```
   Open your browser at `http://localhost:8501`.

---

## 🧪 Automated Evaluation Suite

The codebase includes an automated test suite verifying 18 edge cases and adversarial attacks (including paraphrased prompt injections, indirect authority claims, unreadable files, overqualification, and duplicate submissions):

```bash
# 1. Generate synthetic test dataset
python generate_test_files.py

# 2. Execute full evaluation test suite
python eval_suite.py
```

---

## 📊 Data Output Contract

Exported CSVs, Excel reports, and Google Sheets tabs conform to the following schema:

| Column | Type | Description | Vocabulary / Constraints |
| :--- | :--- | :--- | :--- |
| `resume_filename` | String | Source filename of candidate resume | e.g. `01_alice_johnson.pdf` |
| `candidate_name` | String | Extracted candidate full name | e.g. `Alice Johnson` |
| `target_role` | String | Extracted Job Description role title | e.g. `Senior Backend Engineer` |
| `decision` | String | Final automated screening decision | `Shortlist` \| `Maybe` \| `Reject` \| `Needs Manual Review` |
| `score_0_100` | Integer | Fit score derived by deterministic engine | `0` to `100` |
| `key_strengths` | String | Key JD-aligned strengths | Semicolon-delimited string |
| `key_gaps` | String | Identified qualification gaps | Semicolon-delimited string |
| `flags` | String | Security or data quality flags | `none` \| `overqualified` \| `duplicate_submission` \| `insufficient_information` \| `possible_prompt_injection` \| `other` |
| `rationale` | String | Audit-ready explanation of evaluation | Free-text string |
| `email` | String | Extracted candidate email address | e.g. `alice@example.com` \| `N/A` |
| `phone` | String | Extracted candidate phone number | e.g. `+1-555-0192` \| `N/A` |

---

## ☁️ Deployment Guide (Streamlit Community Cloud)

1. Push your repository to GitHub.
2. Log into [Streamlit Community Cloud](https://share.streamlit.io/) and create a **New App**.
3. Select your repository `voxtale-talent-intelligence`, set Main file path to `app.py`.
4. Under **Advanced Settings → Secrets**, configure your environment secrets:
   ```toml
   GEMINI_API_KEY = "AIzaSy..."
   SENDER_EMAIL = "recruiter@example.com"
   SENDER_APP_PASSWORD = "abcd efgh ijkl mnop"
   ```

---

## 📄 License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.

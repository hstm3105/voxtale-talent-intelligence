# VoxTale Agentic Resume Shortlister: Complete System Architecture, Concepts & Technical Manual

---

## 1. Executive Summary & Core Architectural Philosophy

The **VoxTale Agentic Resume Shortlister** is an autonomous, multi-stage screening platform designed to evaluate candidate resumes against unstructured Job Descriptions (JDs) with zero hardcoded domain knowledge, zero assumed skills, and zero role-specific heuristics.

Unlike traditional Applicant Tracking Systems (ATS) that rely on superficial keyword matching, or naive LLM applications that pass entire candidate folders into a single prompt context, VoxTale implements an **Explicit 8-Stage Agentic Architecture**. 

### Why This Is a True Agentic System (Proof Points for Evaluation & Demo)

When demonstrating or defending this project in an interview, present these **5 Pillars of Agentic Architecture**:

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                      PILLARS OF AGENTIC ARCHITECTURE                       │
 ├─────────────────────────────────────────────────────────────────────────────┤
 │ 1. Autonomous Reasoning & Schema Extraction (Zero Hardcoded Patterns)       │
 │ 2. Isolated Per-Candidate State Processing (Eliminating Context Contamination)│
 │ 3. Adaptive Memory & Human-in-the-Loop Feedback Integration (Few-Shot Context)│
 │ 4. Deterministic Compliance & Guardrails Engine (LLM Bounded by Hard Rules) │
 │ 5. Multi-Format Ingestion & Robust Error Recovery (Per-File Exception Scope)│
 └─────────────────────────────────────────────────────────────────────────────┘
```

1. **Dynamic Task Deconstruction & Reasoning**:
   - The system does not assume what a "Senior Growth Analyst" or "Backend Developer" requires. Stage 3 autonomously analyzes raw, unstructured JD text to deduce abstract requirements (role title, minimum experience, mandatory vs. nice-to-have skills, key responsibilities) using structured JSON schemas.

2. **Stateless Candidate Isolation (Zero Context Leakage)**:
   - Resumes are evaluated independently in individual sub-context calls. A candidate's score is strictly a function of their alignment with the JD, completely immune to batch order bias, candidate priming, or context length degradation.

3. **Adaptive Few-Shot Feedback Memory**:
   - Recruiters can correct model decisions in the UI. Rather than corrupting the model immediately, corrections enter a **Pending Admin Review (`is_validated = 0`)** queue. Once approved by an admin (`is_validated = 1`), they are dynamically injected as **Labeled Few-Shot Examples** in subsequent LLM prompts, allowing the agent to adapt to team-specific hiring preferences over time.

4. **Deterministic Security Guardrails**:
   - Free-form LLM outputs can hallucinate or be misled by prompt injections. VoxTale pairs LLM reasoning with a **Deterministic Python Rules Engine** that enforces hard security overrides (`unreadable_file`, `possible_prompt_injection`, `duplicate_submission`, `overqualified`, `other`) *after* LLM inference.

5. **Multi-Format Technical Resilience**:
   - Handles corrupted files, empty PDFs, image-based documents, multi-format re-submissions (PDF vs. DOCX), and adversarial attacks without pipeline crashes.

---

## 2. End-to-End 8-Stage Pipeline Data Flow

```
[STAGE 1: Multi-Format File Ingestion (PDF / DOCX / TXT)]
                          │
                          ▼
[STAGE 2: Security Isolation & Prompt Injection Defense]
                          │
                          ▼
[STAGE 3: Dynamic JD Requirements Extraction (Gemini JSON Schema)]
                          │
                          ▼
[STAGE 4: Candidate Profile Extraction (Gemini JSON Schema)]
                          │
                          ▼
[STAGE 5: Cross-Resume Duplicate Detection (Identity + 4-gram Similarity)]
                          │
                          ▼
[STAGE 6: Candidate Fit Evaluation (Stateless Gemini + Few-Shot Memory)]
                          │
                          ▼
[STAGE 7: Deterministic Rules Engine (Score + Flags -> Final Decision)]
                          │
                          ▼
[STAGE 8: SQLite Repository, CSV Export, Email & Google Sheets Sync]
```

---

## 3. Deep Dive into Pipeline Stages & Key Concepts

### Stage 1: Ingestion & Text Extraction (`pipeline/ingestion.py`)
- **Supported Formats**: `.txt`, `.pdf`, `.docx`.
- **PDF Extraction Cascade**: Uses `pdfplumber` for primary layout-preserving text extraction with `pypdf` as a fallback parser.
- **Fault-Tolerant Scope**: Each file extraction is wrapped in per-file `try/except` blocks. A corrupted PDF (e.g. invalid header, zero byte stream) sets `doc.extraction_status = "unreadable_file"` and proceeds gracefully without halting the remaining batch.

### Stage 2: Security Isolation & Untrusted Data Scanning (`pipeline/security.py`)
- **Untrusted XML Enclosure**: Candidate resume text is wrapped inside `<untrusted_candidate_resume_data>` XML tags before being passed to Gemini.
- **Developer System Instructions**: Prompts instruct Gemini that text within XML tags represents candidate data only and must never be interpreted as system commands.
- **Heuristic Injection Scanning**: A multi-pattern regex scanner inspects raw text for override keywords (e.g., *"ignore previous instructions"*, *"system override"*, *"set score to 100"*). If detected, `is_injection = True` is passed down to the decision engine.

### Stage 3: Dynamic JD Requirements Extraction (`pipeline/jd_extractor.py`)
- **Model Choice**: **Gemini 3.5 Flash Lite** (`gemini-3.5-flash-lite`), selectable via Settings dropdown alongside Gemini 3 Flash and Gemini 3.6 Flash.
- **Structured Schema Enforcement**: Uses Pydantic `JDRequirements` schema with `response_mime_type="application/json"`:
  - `role_title`: str
  - `seniority_level`: str
  - `min_years_experience`: float
  - `must_have_skills`: List[str]
  - `nice_to_have_skills`: List[str]
  - `key_responsibilities`: List[str]

### Stage 4: Structured Resume Profile Extraction (`pipeline/resume_extractor.py`)
- Extracts a typed `ResumeProfile` object from candidate text:
  - `candidate_name`, `email`, `phone`, `total_years_experience`, `skills`, `work_history`, `education`, `is_empty_or_garbled`.
- **Fast-Path Short Circuit**: Resumes with `< 25 words` or marked `unreadable_file` bypass LLM extraction and immediately return `is_empty_or_garbled = True` to conserve API tokens and prevent hallucination.

### Stage 5: Cross-Resume Duplicate Detection (`pipeline/duplicate_detector.py`)
- **Identity Matching**: Compares normalized email, phone, and candidate name across the batch.
- **Character 4-Gram Jaccard Text Similarity**:
  $$\text{Jaccard}(A, B) = \frac{|G(A) \cap G(B)|}{|G(A) \cup G(B)|}$$
  If character 4-gram similarity $\ge 0.85$ between two resumes (e.g., candidate submitting `john_doe.pdf` and `john_doe_v2.docx`), the re-submission is flagged as `duplicate_submission`.

### Stage 6: Stateless Candidate Fit Evaluation (`pipeline/fit_evaluator.py`)
- Compares extracted `ResumeProfile` + raw resume text against `JDRequirements`.
- **Few-Shot Context Injection**: Queries SQLite for approved recruiter feedback (`WHERE is_validated = 1`). Injects up to 3 historical corrections:
  ```
  HISTORICAL RECRUITER CORRECTIONS & PREFERENCES:
  - Candidate 'Carol Davis': Model decided Reject (Score 45), but Recruiter corrected to 'Shortlist'. 
    Reason: Startup experience counts towards seniority.
  ```
- Produces typed `FitAssessment`:
  - `score_0_100`: int (0 to 100)
  - `key_strengths`: List[str] (2 to 3 JD-aligned strengths)
  - `key_gaps`: List[str] (2 to 3 missing qualifications)
  - `rationale`: str (1 to 3 concise recruiter sentences)
  - `is_overqualified`: bool
  - `has_data_quality_concern`: bool
  - `data_quality_note`: str

### Stage 7: Deterministic Decision Engine (`pipeline/decision_engine.py`)
Applies a strict, audit-ready priority rules hierarchy to determine the final output record:

```
                          ┌───────────────────────────┐
                          │   INPUT EVALUATION DATA   │
                          └─────────────┬─────────────┘
                                        │
                         Is extraction_status ==      YES ──► Flag: unreadable_file
                           "unreadable_file"?                 Decision: Needs Manual Review
                                        │ NO
                         Is is_empty_or_garbled       YES ──► Flag: insufficient_information
                            or word count < 25?               Decision: Needs Manual Review
                                        │ NO
                         Is prompt injection          YES ──► Flag: possible_prompt_injection
                         detected by scanner?                 Decision: Needs Manual Review
                                        │ NO
                         Is 4-gram text similarity    YES ──► Flag: duplicate_submission
                                 >= 0.85?                     Decision: Needs Manual Review
                                        │ NO
                         Is candidate overqualified   YES ──► Flag: overqualified
                         (is_overqualified == True)?          Decision: Needs Manual Review
                                        │ NO
                         Has data quality concern     YES ──► Flag: other
                         (has_data_quality_concern)?          Decision: Needs Manual Review
                                        │ NO
                                        ▼
                         ┌─────────────────────────────┐
                         │   SCORE-BASED BUCKETING     │
                         ├─────────────────────────────┤
                         │ Score >= 80  ► Shortlist     │
                         │ Score 60-79  ► Maybe         │
                         │ Score < 60   ► Reject        │
                         │ (Flags = "none")            │
                         └─────────────────────────────┘
```

---

## 4. Human-in-the-Loop Safeguards & Pending Review Workflow

To prevent malicious or bad-faith feedback (e.g., a recruiter attempting to shortlist a prompt-injection candidate or distort scoring metrics), the system enforces a **Two-Stage Feedback Approval Pipeline**:

1. **Submission Phase (Tab 1)**:
   - When a recruiter submits a decision correction in Tab 1, `save_feedback()` inserts the record into SQLite with `is_validated = 0` (pending review).
   - The UI notifies the user: *"Correction saved pending admin review!"*

2. **Approval Phase (Tab 3)**:
   - Tab 3 lists all pending corrections in a dedicated section: **"⏳ Pending Corrections Awaiting Approval"**.
   - An admin reviews the candidate name, original decision, corrected decision, and recruiter rationale, then clicks **"✅ Approve Correction"**.
   - Executing `approve_feedback(id)` updates `is_validated = 1`.
   - Only after approval is the entry returned by `get_validated_feedback()` and included in prompt context for future runs.

3. **Post-Evaluation Security Overrides**:
   - Even if an approved feedback item encourages high scores for edge cases, `decision_engine.py` executes *after* the LLM step and enforces hard security overrides (`unreadable_file`, `possible_prompt_injection`), guaranteeing safety.

---

## 5. Technical Stack & File Structure Reference

```
resume_shortlister/
├── app.py                     # Interactive Streamlit Web Application (4 Tabs)
├── main.py                    # CLI Entrypoint & Pipeline Execution Orchestrator
├── config.py                  # Model Mappings, Thresholds & CSV Contract Header
├── models.py                  # Pydantic Schemas (JDRequirements, ResumeProfile, FitAssessment, etc.)
├── database.py                # SQLite Repository (runs, resumes, results, logs, feedback)
├── sheets_sync.py             # Multi-Tab Timestamped Google Sheets Sync & Excel Generator
├── email_sender.py            # SMTP Excel (.xlsx) Report Emailing Service
├── eval_suite.py              # Automated 6/6 Edge-Case Test Suite
├── design_doc.md              # Architectural Overview & Section 4/5 Assessment Document
├── system_architecture_guide.md # Complete Technical Manual & Concepts Blueprint
└── pipeline/
    ├── ingestion.py           # Multi-format document loading (TXT, PDF, DOCX)
    ├── security.py            # Untrusted input XML isolation & prompt injection scanning
    ├── jd_extractor.py        # Gemini structured JD requirement extraction
    ├── resume_extractor.py    # Gemini structured candidate profile extraction
    ├── duplicate_detector.py  # Cross-resume identity & 4-gram text Jaccard similarity
    ├── fit_evaluator.py       # Stateless Gemini fit assessment + Few-shot feedback injection
    ├── decision_engine.py     # Deterministic rules engine (Score + Flags -> Decision)
    └── exporter.py            # Contract CSV exporter
```

---

## 6. How to Run & Validate

### Launching the Interactive Web UI
```bash
cd ~/Desktop/resume_shortlister
source venv/bin/activate
streamlit run app.py
```

### Running the CLI Pipeline Directly
```bash
./venv/bin/python main.py --jd test_data/jd.txt --resumes test_data --output output.csv
```

### Executing the Automated Evaluation Test Suite (16 Test Cases - 100% Pass Rate)
```bash
./venv/bin/python eval_suite.py
```

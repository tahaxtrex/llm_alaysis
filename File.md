# 📘 Course Analysis Engine: Walkthrough & Updates

This document provides a comprehensive overview of the pedagogical analysis engine, detailing the transition from its initial state to the current research-enhanced version.

---

## 🏗 Initial State (Legacy)
The project began as a batch processing engine for educational PDFs with the following core components:
*   **Ingestion**: Extracted text and split it using fixed headings (Regex) or hard character limits (12,000 chars).
*   **Evaluation**: Scored sections 1-10 across 7 rubrics (Goal Focus, Readability, etc.) using LLMs.
*   **Storage**: SQLite database tracking files and scores.
*   **Visuals**: Matplotlib reports (Radar charts and Heatmaps).

### ⚠️ Legacy Issues Found
1.  **Broken API Calls**: Used non-existent model IDs (`claude-opus-4-6`), causing immediate crashes.
2.  **Disconnected Scoring**: Rubric scores were numerical only, with no stored justification for "why" a score was given.
3.  **Inefficient Limits**: The `--limit` flag counted failed API calls toward the quota, wasting runs on errors.
4.  **Fragmented Context**: Simple regex splitting often cut logical lessons in half, confusing the LLM.

---

## 🚀 Key Improvements & New Features

### 1. Research-Grade Data Capture
*   **Rubric Reasoning**: The engine now requires the LLM to provide a specific justification for every score. This is stored in a new `reasoning` column in the database, allowing researchers to audit the "logic" behind the automation.
*   **Human-Readable Analytics**: Heatmaps now use descriptive labels (e.g., "Pedagogic Clarity") instead of internal IDs (`rubric3`).

### 2. Semantic Segmentation (LLM-Assisted)
Instead of arbitrary splits, the engine now uses **Gemini 2.0 Flash** during ingestion to analyze the document structure.
*   **The Logic**: It identifies where one pedagogical module ends and another begins, inserting `[SECTION_BREAK]` markers. 
*   **Benefit**: Evaluation scores are now more accurate because the LLM receives complete, self-contained lessons rather than fragments.

### 3. Automated Synthesis (Meta-Analysis)
A new command, `python main.py synthesize`, has been added.
*   **The Logic**: It fetches all individual section scores and issues for a course and performs a "Global Synthesis."
*   **Output**: Produces a structured Markdown report (`outputs/[Course]_synthesis.md`) summarizing systemic strengths, recurring weaknesses, and a prioritized list of improvements.

---

## 🛠 Working with the New Engine (Walkthrough)

Follow these steps to perform a research-quality analysis of your course materials.

### Step 1: Database Synchronization
Since the schema has changed to include `reasoning` and `synthesis` tables, start fresh:
```bash
python main.py reset
```

### Step 2: Semantic Ingestion
Load your PDFs. By default, this uses the new Semantic Segmentation.
```bash
# High-quality split (LLM-assisted)
python main.py ingest

# Faster split (legacy regex method)
python main.py ingest --no-semantic
```

### Step 3: Targeted Evaluation
Run the scoring pass. The reasoning justifications are captured automatically.
```bash
# Evaluate 5 sections using Claude (Primary)
python main.py evaluate --limit 5

# Force fallback to Gemini for cost-efficiency
python main.py evaluate --model gemini --limit 10
```

### Step 4: High-Level Synthesis
Generate the global pedagogical report for every course that has finished evaluation.
```bash
python main.py synthesize
```

### Step 5: Visual Reporting
Generate your radar charts and weakness heatmaps.
```bash
python main.py report
```

---

## 📊 Output Files
*   `course_analysis.db`: Contains all raw text, scores, and **reasoning strings**.
*   `outputs/*.md`: Section-level notes.
*   `outputs/*_synthesis.md`: **NEW** Global course quality reports.
*   `outputs/graphs/`: Radar charts per course and the cross-course weakness heatmap.

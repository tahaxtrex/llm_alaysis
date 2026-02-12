# Course Analysis Engine: Command Documentation

This document describes the CLI commands available in `main.py` for managing the pedagogical analysis pipeline.

---

## 1. `ingest`
**Purpose:** Scans a directory for PDF files, extracts text, segments it into logical sections, and stores them in the SQLite database.

### Usage
```bash
python main.py ingest [--courses-dir PATH] [--no-semantic]
```

### Arguments
- `--courses-dir` (Default: `./courses`): The directory to scan for PDFs. It searches recursively.
- `--no-semantic`: By default, the engine uses an LLM to find "Semantic Boundaries" (Chapter/Section breaks). Use this flag to fallback to a heuristic-based splitter (regex and line length).

### Workflow
1.  Calculates a SHA-256 hash of each PDF to prevent duplicate ingestion.
2.  Extracts raw text using `pypdf`.
3.  Segments text into sections.
4.  Saves metadata to the `courses` table and text content to the `sections` table.

---

## 2. `evaluate`
**Purpose:** Processes unevaluated sections through an LLM to score them against pedagogical rubrics.

### Usage
```bash
python main.py evaluate [--model MODEL] [--limit N]
```

### Arguments
- `--model` (Default: `claude`): Choose between `claude` (Anthropic) or `gemini` (Google).
- `--limit`: Limits the number of sections to process in one run (useful for cost control or testing).

### Workflow
1.  Queries the database for sections that haven't been evaluated by the selected model.
2.  Sends each section to the LLM with a system prompt defining 7 pedagogical rubrics.
3.  Validates the JSON response against a strict schema.
4.  Stores scores, issues, suggested fixes, and evidence in the `evaluations` table.
5.  Implements a 2-second sleep between requests to respect rate limits.

---

## 3. `report`
**Purpose:** Aggregates evaluation data and generates visual and tabular reports.

### Usage
```bash
python main.py report
```

### Workflow
1.  Loads all evaluation data into a Pandas DataFrame.
2.  **Radar Charts:** Generates a `_radar.png` for every course, showing average rubric scores.
3.  **Heatmap:** Creates `course_heatmap.png` comparing all courses across all rubrics.
4.  **Boxplot:** Generates `source_comparison_boxplot.png` to compare quality across different file sources (folders).
5.  **CSV:** Saves `aggregates.csv` in the `outputs/` folder for external analysis.

---

## 4. `synthesize`
**Purpose:** Generates a high-level qualitative summary of an entire course based on all its individual section evaluations.

### Usage
```bash
python main.py synthesize [--model MODEL]
```

### Arguments
- `--model` (Default: `claude`): The model to perform the synthesis.

### Workflow
1.  Retrieves all section evaluations for each course.
2.  Feeds the aggregated findings (scores, issues, fixes) back to the LLM.
3.  Produces a Markdown report highlighting overall strengths, weaknesses, and a transformation roadmap.
4.  Saves the report to the `synthesis` field in the database and as a `.md` file in `outputs/`.

---

## 5. `reset`
**Purpose:** Wipes the database to allow for a clean restart.

### Usage
```bash
python main.py reset
```

### Workflow
1.  Prompts for user confirmation.
2.  Deletes `course_analysis.db`.
3.  Re-initializes the database with the schema defined in `schema.sql`.

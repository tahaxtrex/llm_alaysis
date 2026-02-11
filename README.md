# Course Analysis Engine 🎓

A modular, linear batch processing engine designed to evaluate educational course materials for pedagogical quality using LLMs (Claude/Gemini).

## 🚀 Overview

This tool automates the analysis of course PDFs by:
1.  **Ingesting** PDFs into a local SQLite database with content deduplication (SHA-256).
2.  **Segmenting** text into logical sections based on headings or fixed chunks.
3.  **Evaluating** each section against 7 pedagogical rubrics using Claude-3.5-Sonnet (with Gemini fallback).
4.  **Analyzing** results via Pandas and generating visual reports (Radar charts, Heatmaps, Boxplots).

## 🛠 Tech Stack

-   **Language**: Python 3.12+
-   **Database**: SQLite (Storage of documents, sections, and evaluations)
-   **LLMs**: Anthropic Claude 3.5 Sonnet (Primary), Google Gemini 2.0 Flash (Fallback)
-   **Analytics**: Pandas, NumPy
-   **Visualization**: Matplotlib
-   **PDF Processing**: pypdf

## 📋 Features

-   **Structured JSON Output**: Strict response validation using `jsonschema`.
-   **Deduplication**: Files are hashed to avoid redundant processing.
-   **Source Comparison**: Analyze pedagogical quality across different platforms/sources.
-   **Visual Reports**: 
    -   Radar charts per course.
    -   Weakness heatmaps across all modules.
    -   Distribution boxplots by source.

## ⚙️ Setup

1.  **Clone the repository and enter the directory**:
    ```bash
    cd course_analysis
    ```

2.  **Create and activate a virtual environment**:
    ```bash
    python3 -m venv env
    source env/bin/activate
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables**:
    Create a `.env` file in the root directory:
    ```ini
    ANTHROPIC_API_KEY=your_anthropic_key
    GEMINI_API_KEY=your_gemini_key
    COURSES_DIR=./courses
    OUTPUT_DIR=./outputs
    ```

## 📖 Usage

The tool uses a CLI interface via `main.py`:

### 1️⃣ Ingest
Scan the `./courses` folder and load new PDFs into the database.
```bash
python main.py ingest
```

### 2️⃣ Evaluate
Run the LLM evaluation. You can limit the number of sections to manage costs/quota.
```bash
# Evaluate 10 sections using Claude
python main.py evaluate --limit 10

# Force Gemini for evaluation
python main.py evaluate --model gemini
```

### 3️⃣ Report
Generate statistical analysis and graphs in the `./outputs` folder.
```bash
python main.py report
```

### 4️⃣ Reset
Wipe the database and start fresh.
```bash
python main.py reset
```

## 📂 Project Structure

-   `main.py`: CLI entry point.
-   `pipeline.py`: Ingestion, hashing, and text segmentation logic.
-   `llm.py`: Interaction with Anthropic and Gemini APIs.
-   `database.py`: SQLite schema and data persistence.
-   `analysis.py`: Aggregation logic and Matplotlib visualizations.
-   `schema.sql`: Database table definitions.

## 📊 Evaluation Rubrics

Each section is scored (1-10) on:
1.  **Goal Focus**: Clarity of concepts vs. "fluff".
2.  **Readability**: Simple language vs. complex jargon.
3.  **Pedagogic Clarity**: Sentence structure and target audience alignment.
4.  **Prerequisite Alignment**: Logical flow of concepts.
5.  **Fluidity & Continuity**: Transition quality between modules.
6.  **Example Concreteness**: Relatability of examples.
7.  **Example Coherence**: Consistency across the entire material.

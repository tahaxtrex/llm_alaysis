import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

DB_PATH = Path("course_analysis.db")
SCHEMA_PATH = Path("schema.sql")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with the schema."""
    conn = get_connection()
    with open(SCHEMA_PATH, "r") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()

def course_exists(course_id: str) -> bool:
    conn = get_connection()
    cursor = conn.execute("SELECT 1 FROM courses WHERE id = ?", (course_id,))
    exists = cursor.fetchone() is not None
    conn.close()
    return exists

def insert_course(course_id: str, filename: str, filepath: str, source: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR IGNORE INTO courses (id, filename, filepath, source) VALUES (?, ?, ?, ?)",
        (course_id, filename, filepath, source)
    )
    conn.commit()
    conn.close()

def insert_sections(course_id: str, sections: List[str]):
    """Insert sections for a course. Deletes existing sections for this course first to avoid duplicates if re-ingested."""
    conn = get_connection()
    # Transactional
    try:
        conn.execute("DELETE FROM sections WHERE course_id = ?", (course_id,))
        for idx, content in enumerate(sections):
            conn.execute(
                "INSERT INTO sections (course_id, section_index, content, char_count) VALUES (?, ?, ?, ?)",
                (course_id, idx, content, len(content))
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_unevaluated_sections(model_name: str) -> List[Dict[str, Any]]:
    """Get sections that have not been evaluated by the specified model."""
    conn = get_connection()
    query = """
        SELECT s.id, s.content, c.filename
        FROM sections s
        JOIN courses c ON s.course_id = c.id
        LEFT JOIN evaluations e ON s.id = e.section_id AND e.model_name = ?
        WHERE e.id IS NULL
    """
    cursor = conn.execute(query, (model_name,))
    rows = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rows

def save_evaluation(section_id: int, model_name: str, result: Dict[str, Any]):
    conn = get_connection()
    scores = result.get("scores", {})
    
    conn.execute("""
        INSERT INTO evaluations (
            section_id, model_name, 
            rubric1, rubric2, rubric3, rubric4, rubric5, rubric6, rubric7,
            issues, fixes, evidence, reasoning, raw_response
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        section_id, model_name,
        scores.get("rubric1"), scores.get("rubric2"), scores.get("rubric3"),
        scores.get("rubric4"), scores.get("rubric5"), scores.get("rubric6"), scores.get("rubric7"),
        json.dumps(result.get("issues", [])),
        json.dumps(result.get("fixes", [])),
        json.dumps(result.get("evidence", [])),
        json.dumps(result.get("reasoning", {})),
        json.dumps(result)
    ))
    conn.commit()
    conn.close()

def get_course_aggregates():
    conn = get_connection()
    query = """
        SELECT 
            c.id, c.filename, c.source,
            AVG(e.rubric1) as r1, AVG(e.rubric2) as r2, AVG(e.rubric3) as r3,
            AVG(e.rubric4) as r4, AVG(e.rubric5) as r5, AVG(e.rubric6) as r6, 
            AVG(e.rubric7) as r7
        FROM courses c
        JOIN sections s ON c.id = s.course_id
        JOIN evaluations e ON s.id = e.section_id
        GROUP BY c.id
    """
    df_data = [dict(row) for row in conn.execute(query).fetchall()]
    conn.close()
    return df_data

def get_course_evaluations(course_id: str) -> List[Dict[str, Any]]:
    """Get all evaluations for a specific course."""
    conn = get_connection()
    query = """
        SELECT e.*, s.section_index 
        FROM evaluations e
        JOIN sections s ON e.section_id = s.id
        WHERE s.course_id = ?
        ORDER BY s.section_index ASC
    """
    rows = [dict(row) for row in conn.execute(query, (course_id,)).fetchall()]
    conn.close()
    return rows

def save_synthesis(course_id: str, model_name: str, report: str):
    """Save the synthesized report for a course."""
    conn = get_connection()
    conn.execute("CREATE TABLE IF NOT EXISTS synthesis (course_id TEXT PRIMARY KEY, model_name TEXT, report TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.execute("INSERT OR REPLACE INTO synthesis (course_id, model_name, report) VALUES (?, ?, ?)", (course_id, model_name, report))
    conn.commit()
    conn.close()

def get_all_courses() -> List[Dict[str, Any]]:
    conn = get_connection()
    rows = [dict(row) for row in conn.execute("SELECT * FROM courses").fetchall()]
    conn.close()
    return rows

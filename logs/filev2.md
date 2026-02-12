# Project Changes v2

## Overview
- **Default Model**: Updated to `claude-opus-4-6`.
- **Workflow Prioritization**: The engine now always attempts to use Claude first, falling back to Gemini only on failure.
- **Strict Segmentation**: Refined heuristics and a 10,000-character minimum section size to ensure only major pedagogical modules are evaluated, preventing over-segmentation.

## Updated llm.py
```python
import os
import json
import jsonschema
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import time
import re

try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-4-6")

ANTHROPIC_DISABLED = False
GEMINI_DISABLED = False

EVALUATION_SCHEMA = {
    "type": "object",
    "properties": {
        "scores": {
            "type": "object",
            "properties": {
                "rubric1": {"type": "integer", "minimum": 1, "maximum": 10},
                "rubric2": {"type": "integer", "minimum": 1, "maximum": 10},
                "rubric3": {"type": "integer", "minimum": 1, "maximum": 10},
                "rubric4": {"type": "integer", "minimum": 1, "maximum": 10},
                "rubric5": {"type": "integer", "minimum": 1, "maximum": 10},
                "rubric6": {"type": "integer", "minimum": 1, "maximum": 10},
                "rubric7": {"type": "integer", "minimum": 1, "maximum": 10}
            },
            "required": ["rubric1", "rubric2", "rubric3", "rubric4", "rubric5", "rubric6", "rubric7"]
        },
        "issues": {"type": "array", "items": {"type": "string"}},
        "fixes": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "reasoning": {
            "type": "object",
            "properties": {
                "rubric1": {"type": "string"},
                "rubric2": {"type": "string"},
                "rubric3": {"type": "string"},
                "rubric4": {"type": "string"},
                "rubric5": {"type": "string"},
                "rubric6": {"type": "string"},
                "rubric7": {"type": "string"}
            },
            "required": ["rubric1", "rubric2", "rubric3", "rubric4", "rubric5", "rubric6", "rubric7"]
        }
    },
    "required": ["scores", "reasoning", "issues", "fixes", "evidence"]
}

def validate_response(data: Dict[str, Any]) -> bool:
    try:
        jsonschema.validate(instance=data, schema=EVALUATION_SCHEMA)
        return True
    except Exception as e:
        print(f"Validation Error: {e}")
        return False

def get_system_prompt() -> str:
    return """You are a pedagogical expert. Evaluate educational material.
Return a valid JSON object with keys: "scores", "reasoning", "issues", "fixes", "evidence".
Inside "scores" and "reasoning", use keys "rubric1" through "rubric7".
Scores are integers 1-10. Return ONLY JSON."""

def get_user_prompt(text: str) -> str:
    return f"Evaluate this section: {text}"

def call_anthropic(system: str, user: str, model: str = None) -> Optional[str]:
    global ANTHROPIC_DISABLED
    if ANTHROPIC_DISABLED or not ANTHROPIC_API_KEY or not Anthropic: return None
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    try:
        message = client.messages.create(
            model=model or ANTHROPIC_MODEL,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        return message.content[0].text
    except Exception as e:
        print(f"Anthropic Error: {e}")
        if "401" in str(e) or "403" in str(e): ANTHROPIC_DISABLED = True
        return None

def call_gemini(system: str, user: str, model: str = "gemini-2.0-flash") -> Optional[str]:
    global GEMINI_DISABLED
    if GEMINI_DISABLED or not GEMINI_API_KEY or not genai: return None
    client = genai.Client(api_key=GEMINI_API_KEY)
    try:
        resp = client.models.generate_content(
            model=model,
            contents=[{"role": "user", "parts": [{"text": user}]}],
            config=types.GenerateContentConfig(system_instruction=system)
        )
        return resp.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        if "429" in str(e) or "quota" in str(e).lower(): GEMINI_DISABLED = True
        return None

def evaluate_section(text: str, preferred_model: str = "claude") -> Optional[Dict[str, Any]]:
    system = get_system_prompt()
    user = get_user_prompt(text)
    res = call_anthropic(system, user)
    if not res: res = call_gemini(system, user)
    if res:
        try:
            match = re.search(r'\{.*\}', res, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                if validate_response(data): return data
        except Exception as e:
            print(f"Error parsing response: {e}")
    return None

def synthesize_course_report(evaluations, model_name="claude"):
    system = "Synthesize a report."
    user = f"Data: {evaluations}"
    res = call_anthropic(system, user)
    if not res: res = call_gemini(system, user)
    return res

def find_semantic_boundaries(text: str, model_name: str = None) -> List[str]:
    system = """Split the provided textbook text into major pedagogical modules (Chapters or Main Sections ONLY). 
DO NOT split on minor sub-headings, figures, or lists. 
Insert the marker [SECTION_BREAK] only at major transitions.
Return the original text with these markers inserted."""
    user = f"Text to segment: {text}"
    res = call_anthropic(system, user)
    if not res:
        res = call_gemini(system, user)
    return [p.strip() for p in res.split("[SECTION_BREAK]") if p.strip()] if res else [text]

```

## Updated pipeline.py
```python
import llm
import os
import re
import hashlib
from pathlib import Path
from typing import List, Tuple
from pypdf import PdfReader
import database

def compute_file_hash(filepath: Path) -> str:
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def extract_text_from_pdf(filepath: Path) -> str:
    try:
        reader = PdfReader(str(filepath))
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "
"
        
        return text.strip().replace("
", "")
    except Exception as e:
        print(f"Error extracting {filepath}: {e}")
        return ""

def is_heading(line: str) -> bool:
    line = line.strip()
    if not line: return False
    if re.match(r"^(Chapter|Module|Section|Unit)\s+\d+", line, re.I):
        return True
    if re.match(r"^\d+(\.\d)?\s+[A-Z]", line):
        return True
    return False

def segment_text(text: str, semantic: bool = True) -> List[str]:
    lines = text.split("
")
    sections = []
    current_section = []
    current_size = 0
    MIN_SIZE = 10000 
    MAX_SIZE = 60000 
    
    for line in lines:
        if is_heading(line) and current_size > MIN_SIZE:
            if current_section:
                sections.append("
".join(current_section))
            current_section = [line]
            current_size = len(line)
            continue
        if current_size > MAX_SIZE:
            if current_section:
                sections.append("
".join(current_section))
            current_section = [line]
            current_size = len(line)
            continue
        current_section.append(line)
        current_size += len(line) + 1
        
    if current_section:
        sections.append("
".join(current_section))
    return sections

def ingest_course(filepath: Path, source: str = "local", semantic: bool = True):
    print(f"Ingesting {filepath.name}...")
    hash_val = compute_file_hash(filepath)
    if database.course_exists(hash_val):
        print(f"Skipping {filepath.name} (already exists).")
        return 
    text = extract_text_from_pdf(filepath)
    if not text:
        print(f"Warning: No text extracted from {filepath.name}")
        return
    database.insert_course(hash_val, filepath.name, str(filepath), source)
    sections = segment_text(text, semantic=semantic)
    print(f"  -> Extracted {len(sections)} sections.")
    database.insert_sections(hash_val, sections)

def scan_and_ingest(courses_dir: Path, semantic: bool = True):
    if not courses_dir.exists(): return
    pdfs = sorted(courses_dir.rglob("*.pdf"))
    for pdf in pdfs:
        ingest_course(pdf, source=pdf.parent.name, semantic=semantic)

```

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
                text += page_text + "\n"
        
        # Basic cleanup
        # Remove null bytes
        text = text.replace("\x00", "") 
        # Normalize whitespace (but keep newlines for structure detection)
        # We might want to be careful not to destroy paragraph structure
        return text.strip()
    except Exception as e:
        print(f"Error extracting {filepath}: {e}")
        return ""

def is_heading(line: str) -> bool:
    line = line.strip()
    if not line:
        return False
    
    # 1. Numbered headings: "1. Introduction", "2.1. Concepts"
    # Matches starting with digit+dot
    if re.match(r"^\d+(\.\d+)*\s", line):
        return True
        
    # 2. ALL CAPS shorter than 60 chars (and at least 4 chars to avoid tiny noise)
    if line.isupper() and 4 < len(line) < 60:
        return True
        
    return False


def segment_text(text: str, semantic: bool = True) -> List[str]:
    """Segment text into modules. If semantic=True, use LLM to refine boundaries."""
    if not semantic:
        # Fallback to existing logic
        lines = text.split("\n")
        sections = []
        current_section = []
        current_size = 0
        for line in lines:
            line_len = len(line)
            if is_heading(line) and current_size > 1000:
                if current_section:
                    sections.append("\n".join(current_section))
                current_section = [line]
                current_size = line_len
                continue
            if current_size > 12000:
                 if current_section:
                    sections.append("\n".join(current_section))
                 current_section = [line]
                 current_size = line_len
                 continue
            current_section.append(line)
            current_size += line_len + 1
        if current_section:
            sections.append("\n".join(current_section))
        return sections

    print("  -> Using Semantic Segmentation (LLM-assisted)...")
    # Split into 30k char blocks for LLM refinement
    rough_chunks = [text[i:i+30000] for i in range(0, len(text), 30000)]
    all_sections = []
    for chunk in rough_chunks:
        refined = llm.find_semantic_boundaries(chunk)
        all_sections.extend(refined)
    return all_sections

def ingest_course(filepath: Path, source: str = "local", semantic: bool = True):
    print(f"Ingesting {filepath.name}...")
    file_hash = compute_file_hash(filepath)
    
    # Check deduplication
    if database.course_exists(file_hash):
        print(f"Skipping {filepath.name} (already exists).")
        return

    text = extract_text_from_pdf(filepath)
    if not text:
        print(f"Warning: No text extracted from {filepath.name}")
        return
        
    # Insert Course
    database.insert_course(file_hash, filepath.name, str(filepath), source)
    
    # Segment
    sections = segment_text(text, semantic=semantic)
    print(f"  -> Extracted {len(sections)} sections.")
    
    # Insert Sections
    database.insert_sections(file_hash, sections)
    print(f"  -> Saved to DB.")

def scan_and_ingest(courses_dir: Path, semantic: bool = True):
    if not courses_dir.exists():
        print(f"Directory {courses_dir} not found.")
        return

    # recurse
    pdf_files = sorted(courses_dir.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDFs in {courses_dir}")
    
    for pdf in pdf_files:
        # source is parent dir name relative to root courses dir, or just direct parent
        source = pdf.parent.name
        ingest_course(pdf, source=source, semantic=semantic)

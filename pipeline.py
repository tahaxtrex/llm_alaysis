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
        
        return text.strip()
    except Exception as e:
        print(f"Error extracting {filepath}: {e}")
        return ""

def is_heading(line: str) -> bool:
    line = line.strip()
    if not line: return False
    # Identify common textbook headings
    if re.match(r"^(Chapter|Module|Section|Unit)\s+\d+", line, re.I):
        return True
    if re.match(r"^\d+(\.\d)?\s+[A-Z]", line):
        return True
    return False

def segment_text(text: str, semantic: bool = True) -> List[str]:
    # Use LLM for semantic segmentation if requested
    if semantic:
        print("  -> Using LLM for semantic segmentation...")
        return llm.find_semantic_boundaries(text)

    # Fallback to heuristic segmentation
    lines = text.split("\n")
    sections = []
    current_section = []
    current_size = 0
    MIN_SIZE = 1000  # Reduced for testing/realism
    MAX_SIZE = 6000 
    
    for line in lines:
        if is_heading(line) and current_size > MIN_SIZE:
            if current_section:
                sections.append("\n".join(current_section))
            current_section = [line]
            current_size = len(line)
            continue
        
        # Force split if section gets too large
        if current_size > MAX_SIZE:
            if current_section:
                sections.append("\n".join(current_section))
            current_section = [line]
            current_size = len(line)
            continue
            
        current_section.append(line)
        current_size += len(line) + 1
        
    if current_section:
        sections.append("\n".join(current_section))
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
    
    # Pass the semantic flag to segment_text
    sections = segment_text(text, semantic=semantic)
    
    print(f"  -> Extracted {len(sections)} sections.")
    database.insert_sections(hash_val, sections)

def scan_and_ingest(courses_dir: Path, semantic: bool = True):
    if not courses_dir.exists(): return
    pdfs = sorted(courses_dir.rglob("*.pdf"))
    for pdf in pdfs:
        ingest_course(pdf, source=pdf.parent.name, semantic=semantic)

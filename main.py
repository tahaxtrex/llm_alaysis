import os, re
from pathlib import Path
from dotenv import load_dotenv
from pypdf import PdfReader
from google import genai
from google.genai import types

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

COURSES_DIR = Path(os.getenv("COURSES_DIR", "./courses"))
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", "./outputs"))
MAX_CHARS = int(os.getenv("MAX_CHARS", "120000"))

if not GEMINI_API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY in .env")

client = genai.Client(api_key=GEMINI_API_KEY)

def extract_pdf_text(pdf_path: Path) -> str:
    reader = PdfReader(str(pdf_path))
    parts = [(page.extract_text() or "") for page in reader.pages]
    raw = "\n".join(parts)
    raw = re.sub(r"[ \t]+", " ", raw)
    raw = re.sub(r"\n\s+\n", "\n\n", raw)
    return raw.strip()

def safe_name(name: str) -> str:
    base = Path(name).stem
    return re.sub(r"[^\w\-]+", "_", base)

def build_system_prompt() -> str:
    return "\n".join([
        "You evaluate educational texts for pedagogical quality.",
        "Assume factual correctness; do not verify truth.",
        "Do not invent missing information; if something isn't present, say it's missing.",
        "Be concise and evidence-based; include short quotes as evidence.",
        "Return Markdown only.",
    ])

def build_user_prompt(filename: str, text: str) -> str:
    return f"""
You are given one course document extracted from a PDF.

File: {filename}

Rubrics (score 1-10, 1=absent, 10=excellent):
- **Rubric 1** : Goal focus, meaning is the text actually explaining or focusing on what should be explained rather than stating fluff and explaining unecessary ideas
- **Rubric 2** : text readability, how easy it is to understand the actual text of a course and how much time is spend understanding fancy words rather than concepts
- **Rubric 3** : pedagogic clarity : does the text avoid unexplained jargon? Is the sentence structure simple enough for the target audience?
    - **4 :** Prerequisite Alignment**:** Does the material introduce Concept B before Concept A has been explained? Or states that that knowlegde is required
- **Rubric 5 (fluidity, continuity)** : Do the transitions between paragraphs and modules feel natural, or does the text jump abruptly between unrelated topics?
- **Rubric 6 :** Are the examples used, if any, concrete and relatable to the target audience?
- **Rubric 7** : examples coherent between modules.

Output format (Markdown):
# <File name>
## Scores
- Rubric 1: X/10 — <1 sentence>
- Rubric 2: X/10 — <1 sentence>
- Rubric 3: X/10 — <1 sentence>
- Rubric 4: X/10 — <1 sentence>
- Rubric 5: X/10 — <1 sentence>
- Rubric 6: X/10 — <1 sentence>
- Rubric 7: X/10 — <1 sentence>

## Key issues found
- ...

## Suggested fixes
- ...

## Evidence (short quotes)
- "..."

Course text:
<<<
{text}
>>>
""".strip()

def call_llm(system: str, user: str) -> str:
    # Gemini 3 supports "thinking" controls; optional.
    # If your SDK/version doesn’t accept this config, remove config=...
    resp = client.models.generate_content(
        model=MODEL,
        contents=[
            {"role": "user", "parts": [{"text": user}]},
        ],
        config=types.GenerateContentConfig(
            temperature=0.2,
            system_instruction=system,
            # Optional thinking control (Gemini 3/2.5):
            # thinking_config=types.ThinkingConfig(thinking_level="low")
        ),
    )
    return (resp.text or "").strip()

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    pdfs = sorted([p for p in COURSES_DIR.iterdir() if p.suffix.lower() == ".pdf"])
    if not pdfs:
        print(f"No PDFs found in {COURSES_DIR.resolve()}")
        return

    system = build_system_prompt()

    for pdf_path in pdfs:
        print(f"Processing: {pdf_path.name}")
        text = extract_pdf_text(pdf_path)
        if not text:
            print(f"  Skipped (no text extracted): {pdf_path.name}")
            continue

        truncated = text[:MAX_CHARS]
        user = build_user_prompt(pdf_path.name, truncated)
        output = call_llm(system, user)

        out_path = OUTPUT_DIR / f"{safe_name(pdf_path.name)}.md"
        header = f"<!-- model={MODEL} originalChars={len(text)} sentChars={len(truncated)} -->\n\n"
        out_path.write_text(header + output, encoding="utf-8")
        print(f"  Wrote: {out_path}")

    print("Done.")

if __name__ == "__main__":
    main()

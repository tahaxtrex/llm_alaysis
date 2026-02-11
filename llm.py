import os
import json
import jsonschema
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Try importing Anthropic
try:
    from anthropic import Anthropic
except ImportError:
    Anthropic = None

# Try importing Gemini
try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Schema for validation
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
        "evidence": {"type": "array", "items": {"type": "string"}}
        , "reasoning": {
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

def get_system_prompt() -> str:
    return (
        "You evaluate educational course material for pedagogical quality.\n"
        "Assume factual correctness. Do not verify truth. Do not invent information.\n"
        "Only evaluate what is explicitly present.\n"
        "Return strict JSON only. No markdown. No commentary."
    )

def get_user_prompt(text: str) -> str:
    return f"""
You are given a section of an educational course document. Evaluate it according to the following rubrics (score 1-10):

1. Goal focus
2. Readability
3. Pedagogic clarity
4. Prerequisite alignment
5. Fluidity and continuity
6. Example concreteness
7. Example coherence across modules

Return JSON in this exact structure:

{{
  "scores": {{
      "rubric1": int,
      "rubric2": int,
      "rubric3": int,
      "rubric4": int,
      "rubric5": int,
      "rubric6": int,
      "rubric7": int
  }},
  "issues": [string],
  "fixes": [string],
  "evidence": [short quotes from the text],
  "reasoning": {
      "rubric1": "description of why this score was given",
      ...
      "rubric7": "description of why this score was given"
  },
}}

Section text:
<<<
{text}
>>>
""".strip()

def validate_response(data: Dict[str, Any]) -> bool:
    try:
        jsonschema.validate(instance=data, schema=EVALUATION_SCHEMA)
        return True
    except jsonschema.ValidationError as e:
        print(f"Validation Error: {e.message}")
        return False

import time
import re

ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022")

def call_anthropic(system: str, user: str, model: str = None) -> Optional[Dict[str, Any]]:
    if not ANTHROPIC_API_KEY:
        print("ANTHROPIC_API_KEY not found.")
        return None
    
    if not Anthropic:
        print("Anthropic library not installed. pip install anthropic")
        return None

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    
    # Use env var if model not explicitly passed or if it's the default
    target_model = model or ANTHROPIC_MODEL
    
    try:
        message = client.messages.create(
            model=target_model,
            max_tokens=2000,
            temperature=0.2,
            system=system,
            messages=[
                {"role": "user", "content": user}
            ]
        )
        response_text = message.content[0].text
        data = json.loads(response_text)
        if validate_response(data):
            return data
        return None
    except Exception as e:
        print(f"Anthropic Error: {e}")
        return None

def call_gemini(system: str, user: str, model: str = "gemini-2.0-flash") -> Optional[Dict[str, Any]]:
    if not GEMINI_API_KEY:
        print("GEMINI_API_KEY not found.")
        return None

    if not genai:
        print("google.genai library not installed.")
        return None

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    try:
        # Use config to pass system instruction properly
        resp = client.models.generate_content(
            model=model,
            contents=[{"role": "user", "parts": [{"text": user}]}],
            config=types.GenerateContentConfig(
                temperature=0.2,
                system_instruction=system,
                response_mime_type="application/json"
            ),
        )
        if not resp.text:
            return None
            
        data = json.loads(resp.text)
        if validate_response(data):
            return data
        return None
    except Exception as e:
        error_str = str(e)
        print(f"Gemini Error: {error_str}")
        
        # Smart retry for Free Tier limits
        if "429" in error_str:
            # Try to extract retry delay
            match = re.search(r"retry in (\d+\.?\d*)s", error_str)
            if match:
                delay = float(match.group(1)) + 1.0 # Add 1s buffer
                print(f"⚠️ Quota exceeded. Sleeping for {delay:.2f}s before skipping/retrying (handled in main loop if implemented)...")
                # We block here to help the *next* call, but effectively this call failed.
                # Ideally we would retry HERE.
                time.sleep(delay)
                # Simple retry logic (recurse once)
                print("Retrying Gemini call...")
                try:
                     resp = client.models.generate_content(
                        model=model,
                        contents=[{"role": "user", "parts": [{"text": user}]}],
                        config=types.GenerateContentConfig(
                            temperature=0.2,
                            system_instruction=system,
                            response_mime_type="application/json"
                        ),
                    )
                     if resp.text:
                         data = json.loads(resp.text)
                         if validate_response(data):
                             return data
                except Exception as retry_e:
                    print(f"Retry failed: {retry_e}")

        return None

def evaluate_section(text: str, preferred_model: str = "claude") -> Dict[str, Any]:
    system = get_system_prompt()
    user = get_user_prompt(text)
    
    result = None
    
    if "claude" in preferred_model.lower() or "anthropic" in preferred_model.lower():
        # Map user friendly names to actual model IDs if needed
        model_id = ANTHROPIC_MODEL
        if "opus" in preferred_model:
             model_id = "claude-3-opus-20240229"
             
        print(f"Calling Anthropic ({model_id})...")
        result = call_anthropic(system, user, model=model_id)
        
        # Fallback to Gemini if Claude fails/no key
        if not result:
            print("Fallback to Gemini...")
            result = call_gemini(system, user)
            
    else:
        # Default to Gemini
        print("Calling Gemini...")
        result = call_gemini(system, user)
        
    return result

def synthesize_course_report(evaluations: List[Dict[str, Any]], model_name: str = "claude") -> Optional[str]:
    """Synthesize a final report based on all section evaluations."""
    summary_data = []
    for e in evaluations:
        summary_data.append({
            "index": e["section_index"],
            "scores": {f"r{i}": e[f"rubric{i}"] for i in range(1, 8)},
            "issues": json.loads(e["issues"])
        })
    
    system = "You are a pedagogical expert. Synthesize a course-level quality report."
    user = f"""
Based on the following per-section evaluation data, provide a comprehensive synthesis of the course quality.
Identify systemic strengths, recurring weaknesses, and a prioritized list of improvements.

Data:
{json.dumps(summary_data, indent=2)}

Format:
# Course Synthesis Report
## Executive Summary
...
## Systemic Strengths
...
## Recurring Weaknesses
...
## Priority Improvements
...
"""
    
    if "claude" in model_name.lower():
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=4000,
            system=system,
            messages=[{"role": "user", "content": user}]
        )
        return resp.content[0].text
    else:
        # Gemini fallback/default
        client = genai.Client(api_key=GEMINI_API_KEY)
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[{"role": "user", "parts": [{"text": user}]}],
            config=types.GenerateContentConfig(system_instruction=system)
        )
        return resp.text

def find_semantic_boundaries(text: str, model_name: str = "gemini-2.0-flash") -> List[str]:
    """Ask LLM to split text into logical pedagogical modules."""
    system = "You are a document structure analyst."
    user = f"""
The following text is from a course. Split it into logical sections where each section is a self-contained pedagogical module (e.g., a specific topic, a lesson, or a set of related concepts).
Return each section separated by a special token [SECTION_BREAK].
Do not change the original text at all, just insert the breaks.

Text:
{text}
"""
    # Using Gemini for this as it has a larger context and is faster/cheaper for high-volume structural tasks
    client = genai.Client(api_key=GEMINI_API_KEY)
    resp = client.models.generate_content(
        model=model_name,
        contents=[{"role": "user", "parts": [{"text": user}]}],
        config=types.GenerateContentConfig(temperature=0.0)
    )
    if not resp.text:
        return [text]
    
    parts = resp.text.split("[SECTION_BREAK]")
    return [p.strip() for p in parts if p.strip()]

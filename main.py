import argparse
import sys
from pathlib import Path
import database
import pipeline
import llm
import analysis

def cmd_ingest(args):
    print("Initializing Database...")
    database.init_db()
    
    courses_dir = Path(args.courses_dir)
    print(f"Scanning {courses_dir}...")
    pipeline.scan_and_ingest(courses_dir, semantic=not args.no_semantic)

def cmd_evaluate(args):
    print("Checking for unevaluated sections...")
    # Default to Claude, fallback to Gemini in llm.py
    model_name = args.model
    
    sections = database.get_unevaluated_sections(model_name)
    print(f"Found {len(sections)} sections to evaluate.")
    
    limit = args.limit
    count = 0
    
    import time
    for section in sections:
        if limit and count >= limit:
            break
            
        print(f"Evaluating section {section['id']} of {section['filename']}...")
        result = llm.evaluate_section(section['content'], preferred_model=model_name)
        
        if result:
            database.save_evaluation(section['id'], model_name, result)
            count += 1
            print("  -> Saved.")
        else:
            print("  -> Failed / Skipped.")
        
        time.sleep(2)

def cmd_report(args):
    print("Generating reports...")
    analysis.run_analysis()

def cmd_reset(args):
    db_path = Path("course_analysis.db")
    if db_path.exists():
        confirm = input(f"Are you sure you want to delete {db_path}? (y/N): ")
        if confirm.lower() == 'y':
            db_path.unlink()
            print("Database deleted.")
            # Verify and recreate empty DB
            database.init_db()
            print("Database re-initialized empty.")
    else:
        print("Database does not exist.")


def cmd_synthesize(args):
    print("Synthesizing reports for all courses...")
    courses = database.get_all_courses()
    for course in courses:
        print(f"Synthesizing {course["filename"]}...")
        evals = database.get_course_evaluations(course["id"])
        if not evals:
            print(f"  -> No evaluations found for {course["filename"]}. Skip.")
            continue
        
        report = llm.synthesize_course_report(evals, model_name=args.model)
        if report:
            database.save_synthesis(course["id"], args.model, report)
            # Also save to disk
            out_path = Path("outputs") / f"{course["filename"].replace(".pdf", "")}_synthesis.md"
            with open(out_path, "w") as f_out:
                f_out.write(report)
            print(f"  -> Saved to DB and {out_path}")
        else:
            print("  -> Synthesis failed.")

def main():
    parser = argparse.ArgumentParser(description="Course Analysis Engine")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Ingest
    parser_ingest = subparsers.add_parser("ingest", help="Scan and ingest PDFs")
    parser_ingest.add_argument("--courses-dir", default="./courses", help="Directory containing PDFs")
    parser_ingest.add_argument("--no-semantic", action="store_true", help="Disable semantic segmentation")
    
    # Evaluate
    parser_evaluate = subparsers.add_parser("evaluate", help="Run LLM evaluation")
    parser_evaluate.add_argument("--model", default="claude", help="Model to use (claude/gemini)")
    parser_evaluate.add_argument("--limit", type=int, default=None, help="Limit number of sections to evaluate")
    
    # Report
    parser_report = subparsers.add_parser("report", help="Generate analysis reports")
    
    # Reset
    parser_reset = subparsers.add_parser("reset", help="Reset database")
    

    # Synthesize
    parser_synth = subparsers.add_parser("synthesize", help="Generate a high-level course synthesis")
    parser_synth.add_argument("--model", default="claude", help="Model to use")
    args = parser.parse_args()
    
    if args.command == "ingest":
        cmd_ingest(args)
    elif args.command == "evaluate":
        cmd_evaluate(args)
    elif args.command == "report":
        cmd_report(args)
    elif args.command == "synthesize":
        cmd_synthesize(args)
    elif args.command == "reset":
        cmd_reset(args)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()

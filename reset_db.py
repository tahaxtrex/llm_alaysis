import os
import sqlite3
from pathlib import Path

# Paths relative to the project root
DB_PATH = "course_analysis.db"
SCHEMA_PATH = "schema.sql"

def reset_database():
    """
    Resets the Course Analysis database by deleting the file 
    and re-applying the schema.sql definitions.
    """
    if os.path.exists(DB_PATH):
        print(f"🗑️  Deleting existing database file: {DB_PATH}")
        try:
            os.remove(DB_PATH)
        except PermissionError:
            print("❌ Error: Permission denied. Make sure no other process is using the database.")
            return
    
    if not os.path.exists(SCHEMA_PATH):
        print(f"❌ Error: {SCHEMA_PATH} not found. Cannot re-initialize schema.")
        return

    print(f"🏗️  Re-initializing database using {SCHEMA_PATH}...")
    try:
        conn = sqlite3.connect(DB_PATH)
        with open(SCHEMA_PATH, "r") as f:
            schema_script = f.read()
            conn.executescript(schema_script)
        conn.commit()
        conn.close()
        print("✅ Database successfully reset. All data cleared, schema is ready.")
    except Exception as e:
        print(f"❌ Error during re-initialization: {e}")

if __name__ == "__main__":
    reset_database()

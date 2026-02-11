CREATE TABLE IF NOT EXISTS courses (
    id TEXT PRIMARY KEY,       -- SHA256 hash of the file content
    filename TEXT NOT NULL,
    filepath TEXT NOT NULL,
    source TEXT,               -- Parent directory name or explicit source
    ingested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id TEXT NOT NULL,
    section_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    char_count INTEGER,
    FOREIGN KEY(course_id) REFERENCES courses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER NOT NULL,
    model_name TEXT NOT NULL,
    rubric1 INTEGER, -- Goal focus
    rubric2 INTEGER, -- Readability
    rubric3 INTEGER, -- Pedagogic clarity
    rubric4 INTEGER, -- Prerequisite alignment
    rubric5 INTEGER, -- Fluidity and continuity
    rubric6 INTEGER, -- Example concreteness
    rubric7 INTEGER, -- Example coherence
    issues TEXT,     -- JSON array of strings
    fixes TEXT,      -- JSON array of strings
    evidence TEXT,   -- JSON array of strings
    raw_response TEXT, -- Full JSON response for debugging
    reasoning TEXT,    -- JSON object containing descriptions for each rubric score
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(section_id) REFERENCES sections(id) ON DELETE CASCADE
);

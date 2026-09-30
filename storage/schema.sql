-- schema.sql
-- Definitions for Wireshark Agent Suite SQLite database

CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    interface TEXT,
    type TEXT, -- 'live' or 'imported'
    started_at TEXT, -- ISO 8601
    ended_at TEXT, -- ISO 8601
    total_flows INTEGER DEFAULT 0,
    alert_low INTEGER DEFAULT 0,
    alert_medium INTEGER DEFAULT 0,
    alert_high INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS flows (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    timestamp TEXT, -- ISO 8601 or float epoch string
    src_ip TEXT,
    dst_ip TEXT,
    src_port INTEGER,
    dst_port INTEGER,
    protocol TEXT,
    length INTEGER,
    classification TEXT,
    confidence REAL,
    tags TEXT,
    raw_json TEXT, -- Deprecated or raw packet dump, we'll store normalized representation here if needed
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flow_id INTEGER, -- Optional, if triggered by specific flow
    session_id INTEGER,
    timestamp TEXT, -- ISO 8601
    severity TEXT,
    category TEXT,
    description TEXT,
    affected_src TEXT,
    affected_dst TEXT,
    reasoning TEXT,
    acknowledged INTEGER DEFAULT 0,
    notes TEXT,
    FOREIGN KEY(session_id) REFERENCES sessions(id)
);

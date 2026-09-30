import sqlite3
import os
import datetime
import json

DB_PATH = "data/wireshark_agent.db"

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    schema_path = os.path.join(os.path.dirname(__file__), 'schema.sql')
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    conn = get_db_connection()
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

def create_session(interface: str, session_type: str = 'live') -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    
    cursor.execute('''
        INSERT INTO sessions (interface, type, started_at, total_flows)
        VALUES (?, ?, ?, 0)
    ''', (interface, session_type, now_iso))
    
    session_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return session_id

def insert_flow(session_id: int, flow: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    tags_str = json.dumps(flow.get("tags", [])) if "tags" in flow else "[]"
    
    cursor.execute('''
        INSERT INTO flows (session_id, timestamp, src_ip, dst_ip, src_port, dst_port, protocol, length, classification, confidence, tags)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        session_id,
        flow.get("timestamp"),
        flow.get("src_ip"),
        flow.get("dst_ip"),
        flow.get("src_port"),
        flow.get("dst_port"),
        flow.get("protocol"),
        flow.get("length"),
        flow.get("classification"),
        flow.get("confidence"),
        tags_str
    ))
    
    conn.commit()
    conn.close()

def close_session(session_id: int, total_flows: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    
    cursor.execute('''
        UPDATE sessions
        SET ended_at = ?, total_flows = ?
        WHERE id = ?
    ''', (now_iso, total_flows, session_id))
    
    conn.commit()
    conn.close()

def insert_alert(session_id: int, alert: dict):
    conn = get_db_connection()
    cursor = conn.cursor()
    now_iso = datetime.datetime.utcnow().isoformat() + "Z"
    
    cursor.execute('''
        INSERT INTO alerts (session_id, timestamp, severity, category, description, affected_src, affected_dst, reasoning, acknowledged)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    ''', (
        session_id,
        now_iso,
        alert.get("severity"),
        alert.get("category"),
        alert.get("description"),
        alert.get("affected_src"),
        alert.get("affected_dst"),
        alert.get("reasoning")
    ))
    
    # Also update session alerts count
    severity = alert.get("severity", "low").lower()
    if severity == "low":
        cursor.execute('UPDATE sessions SET alert_low = alert_low + 1 WHERE id = ?', (session_id,))
    elif severity == "medium":
        cursor.execute('UPDATE sessions SET alert_medium = alert_medium + 1 WHERE id = ?', (session_id,))
    elif severity == "high":
        cursor.execute('UPDATE sessions SET alert_high = alert_high + 1 WHERE id = ?', (session_id,))
        
    conn.commit()
    conn.close()

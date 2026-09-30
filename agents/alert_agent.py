import time
import json
import os
import sys
import yaml
from google import genai
from collections import defaultdict

# Load config
try:
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
except FileNotFoundError:
    config = {"agents": {"alert_thresholds": {"suspicious_count": 3, "unknown_count": 5, "time_window_seconds": 60}}}

THRESHOLDS = config.get("agents", {}).get("alert_thresholds", {})
SUSPICIOUS_COUNT = THRESHOLDS.get("suspicious_count", 3)
UNKNOWN_COUNT = THRESHOLDS.get("unknown_count", 5)
TIME_WINDOW = THRESHOLDS.get("time_window_seconds", 60)

# Memory structures
_flow_history = defaultdict(list)

def get_client():
    # Reuse API_KEY checking logic, we can just load fresh here
    from agents.classifier import API_KEY, get_client as _gc
    return _gc()

ALERT_PROMPT = """You are a Cybersecurity Alert Generator.
Given information about a series of network flows from a source IP address, generate a structured alert.
Output ONLY a raw JSON object with the following schema:
{
    "severity": "low" | "medium" | "high",
    "category": "short description (e.g., Port Scan, Beaconing)",
    "description": "A clear, analyst-facing description of what happened",
    "reasoning": "Why the AI believes this is a threat"
}"""

def evaluate_flow(flow: dict) -> dict | None:
    """
    Evaluates a single flow to see if thresholds have been met for its source IP.
    Returns an alert dictionary if triggered, else None.
    """
    cls = flow.get("classification")
    if cls not in ["suspicious", "unknown"]:
        return None
        
    src_ip = flow.get("src_ip")
    if not src_ip:
         return None
         
    now = time.time()
    
    # Prune old flows
    _flow_history[src_ip] = [
        f for f in _flow_history[src_ip] 
        if now - f.get("timestamp_local", now) <= TIME_WINDOW
    ]
    
    # Add new flow
    flow_copy = flow.copy()
    flow_copy["timestamp_local"] = now
    _flow_history[src_ip].append(flow_copy)
    
    # Check thresholds
    suspicious_flows = [f for f in _flow_history[src_ip] if f["classification"] == "suspicious"]
    unknown_flows = [f for f in _flow_history[src_ip] if f["classification"] == "unknown"]
    
    triggered = False
    trigger_reason = ""
    
    if len(suspicious_flows) >= SUSPICIOUS_COUNT:
        triggered = True
        trigger_reason = f"Suspicious flow count reached {SUSPICIOUS_COUNT}"
    elif len(unknown_flows) >= UNKNOWN_COUNT:
        triggered = True
        trigger_reason = f"Unknown flow count reached {UNKNOWN_COUNT}"
        
    if not triggered:
        return None
        
    # Flush history so we don't alert twice for the same set immediately
    _flow_history[src_ip] = []
    
    # Trigger AI Alert Generation
    try:
        client = get_client()
        context = {
            "trigger_reason": trigger_reason,
            "source_ip": src_ip,
            "flows": [
                {"dst_ip": f["dst_ip"], "dst_port": f["dst_port"], "protocol": f["protocol"]} 
                for f in (suspicious_flows + unknown_flows)
            ]
        }
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[ALERT_PROMPT, json.dumps(context)]
        )
        
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        result = json.loads(text.strip())
        
        # Build full alert struct mapping to Schema
        alert = {
            "severity": result.get("severity", "low"),
            "category": result.get("category", "Unknown Alert"),
            "description": result.get("description", "An anomaly was detected."),
            "affected_src": src_ip,
            "affected_dst": flow.get("dst_ip"),
            "reasoning": result.get("reasoning", "Thresholds exceeded automatically.")
        }
        
        return alert
        
    except Exception as e:
        print(f"Alert generation error: {e}", file=sys.stderr)
        return {
            "severity": "low",
            "category": "Fallback Alert",
            "description": trigger_reason,
            "affected_src": src_ip,
            "affected_dst": flow.get("dst_ip"),
            "reasoning": f"Alert generated due to threshold, AI failed to respond ({e})"
        }

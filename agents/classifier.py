import json
import os
import sys
from google import genai

from dotenv import load_dotenv
load_dotenv() # Load variables from .env if present

API_KEY = os.environ.get("GEMINI_API_KEY")

SYSTEM_PROMPT = """You are an AI network traffic classifier.
You will be provided with a JSON object representing a single network flow.
Your job is to analyze the flow metadata and classify it.
Output ONLY a raw JSON object with the following schema:
{
    "classification": "benign" | "suspicious" | "unknown",
    "confidence": float between 0.0 and 1.0,
    "tags": ["list", "of", "descriptive", "strings"]
}"""

_client = None

def get_client():
    global _client
    if _client is None:
        if not API_KEY:
            print("Error: GEMINI_API_KEY environment variable not found.", file=sys.stderr)
            sys.exit(1)
        _client = genai.Client(api_key=API_KEY)
    return _client

def classify_flow(flow: dict) -> dict:
    """
    Calls Gemini to classify a flow.
    If the API call fails or JSON is invalid, returns classification: unknown with confidence: 0.0.
    """
    fallback_result = {
        "classification": "unknown",
        "confidence": 0.0,
        "tags": ["classification_error"]
    }
    
    try:
        client = get_client()
        # Create a condensed version of flow to send, stripping unneeded fields if any
        flow_json = json.dumps(flow)
        
        response = client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=[SYSTEM_PROMPT, flow_json]
        )
        
        # Parse output as JSON. Strip potential markdown blocks.
        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
            
        result = json.loads(text.strip())
        
        if result.get("classification") not in ["benign", "suspicious", "unknown"]:
            return fallback_result
            
        if not isinstance(result.get("tags"), list):
            result["tags"] = []
            
        return result
        
    except Exception as e:
        print(f"Classification error: {e}", file=sys.stderr)
        return fallback_result


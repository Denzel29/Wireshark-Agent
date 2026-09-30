import sys
import json
import argparse
import threading
import asyncio
import uvicorn

from capture.tshark_stream import start_capture
from capture.filter import apply_filter
from storage.db import init_db, create_session, insert_flow, close_session, insert_alert
from agents.classifier import classify_flow
from agents.alert_agent import evaluate_flow

from server.app import app
from server.websocket import manager

# To cleanly shut down
_stop_event = threading.Event()

def capture_worker(interface: str, loop: asyncio.AbstractEventLoop):
    session_id = create_session(interface)
    total_flows = 0
    print(f"\n[+] Starting capture on interface: {interface} (Session ID: {session_id})")
    
    try:
        for flow in start_capture(interface):
            if _stop_event.is_set():
                break
                
            if apply_filter(flow):
                total_flows += 1
                
                # Classify the flow
                class_info = classify_flow(flow)
                flow.update(class_info)
                
                insert_flow(session_id, flow)
                
                # Push to frontend via threadsafe asyncio call
                asyncio.run_coroutine_threadsafe(manager.broadcast_flow(flow), loop)
                
                # Evaluate for alerts
                alert = evaluate_flow(flow)
                if alert:
                    insert_alert(session_id, alert)
                    print(f"\n[!] ALERT GENERATED: {alert.get('severity').upper()} - {alert.get('category')}")
                    asyncio.run_coroutine_threadsafe(manager.broadcast_alert(alert), loop)
                
                # Output flow to terminal
                print(json.dumps(flow))
    except Exception as e:
        print(f"Capture worker error: {e}")
    finally:
        print(f"\n[+] Closing session {session_id} with {total_flows} flows.")
        close_session(session_id, total_flows)

def main():
    parser = argparse.ArgumentParser(description="Wireshark Agent - Live Traffic Capture")
    parser.add_argument("--interface", required=True, help="Network interface to capture on (e.g. eth0, 'Ethernet', 1)")
    
    args = parser.parse_args()
    interface = args.interface
    
    init_db()

    # The background thread needs a reference to the running event loop of Uvicorn so it can await websocket broadcasts
    # We grab the asyncio loop using an app lifecycle event.
    
    @app.on_event("startup")
    def startup_event():
        loop = asyncio.get_running_loop()
        worker = threading.Thread(target=capture_worker, args=(interface, loop), daemon=True)
        worker.start()

    @app.on_event("shutdown")
    def shutdown_event():
        _stop_event.set()
        print("\nWaiting for capture task to finish (1 sec)...")
    
    # Run uvicorn server in the main thread (blocking until Ctrl+C)
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")
    sys.exit(0)

if __name__ == "__main__":
    main()

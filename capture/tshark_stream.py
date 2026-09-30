import subprocess
import json
import sys
import os

# Default tshark path (Windows) if not in PATH
TSHARK_DEFAULT_PATH = r"C:\Program Files\Wireshark\tshark.exe"

def get_tshark_executable():
    # If tshark is in PATH, this will work. Otherwise fallback.
    return "tshark" if os.system("tshark --version >nul 2>&1") == 0 else TSHARK_DEFAULT_PATH

def parse_ek_flow(line: str) -> dict:
    """
    Parses a single line of tshark -T ek NDJSON output.
    Returns a normalized flow object or None if the JSON doesn't represent a packet we want.
    """
    try:
        data = json.loads(line)
        
        # 'ek' format outputs an index line then a doc line. We only want the doc line containing 'layers'.
        if "layers" not in data:
            return None
            
        layers = data["layers"]
        
        # We only care about IP packets for this suite
        if "ip" not in layers:
            return None
            
        ip_layer = layers["ip"]
        frame_layer = layers.get("frame", {})
        
        # Extract basic fields safely. 
        # EK format values are scalars.
        src_ip = ip_layer.get("ip_ip_src")
        dst_ip = ip_layer.get("ip_ip_dst")
        
        if not src_ip or not dst_ip:
            return None
            
        protocol = "IP"
        src_port = None
        dst_port = None
        
        if "tcp" in layers:
            protocol = "TCP"
            src_port = layers["tcp"].get("tcp_tcp_srcport")
            dst_port = layers["tcp"].get("tcp_tcp_dstport")
        elif "udp" in layers:
            protocol = "UDP"
            src_port = layers["udp"].get("udp_udp_srcport")
            dst_port = layers["udp"].get("udp_udp_dstport")
        elif "icmp" in layers:
            protocol = "ICMP"
            
        # You can see many other protocols, but we default to what tkshark parses or generic IP.
            
        length = frame_layer.get("frame_frame_len", 0)
        timestamp = frame_layer.get("frame_frame_time_epoch", 0.0)
        
        # Convert port strings to ints if possible
        if src_port: src_port = int(src_port)
        if dst_port: dst_port = int(dst_port)
        if length: length = int(length)
        if timestamp: timestamp = float(timestamp)
        
        return {
            "timestamp": timestamp,
            "src_ip": src_ip,
            "dst_ip": dst_ip,
            "src_port": src_port,
            "dst_port": dst_port,
            "protocol": protocol,
            "length": length
        }
        
    except json.JSONDecodeError:
        return None
    except Exception as e:
        # Avoid crashing on unexpected parsing errors
        # print("Error parsing flow:", e, file=sys.stderr)
        return None

def start_capture(interface: str):
    """
    Generator that yields normalized flow dictionaries.
    """
    tshark_exe = get_tshark_executable()
    cmd = [tshark_exe, "-i", interface, "-T", "ek", "-l"]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, # We ignore tshark's generic stderr noise
            text=True
        )
    except FileNotFoundError:
        print(f"Error: tshark not found. Ensure it is installed and in your PATH, or at {TSHARK_DEFAULT_PATH}.", file=sys.stderr)
        sys.exit(1)
        
    try:
        for line in process.stdout:
            flow = parse_ek_flow(line)
            if flow:
                yield flow
    except KeyboardInterrupt:
        pass
    finally:
        process.terminate()
        process.wait()

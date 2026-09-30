import json

def is_broadcast(dst_ip: str) -> bool:
    return dst_ip == "255.255.255.255" or dst_ip.endswith(".255")

def apply_filter(flow: dict) -> bool:
    """
    Returns True if the flow should be kept, False if it should be dropped.
    """
    if "src_ip" not in flow or "dst_ip" not in flow:
        # Not an IP packet (e.g. ARP only has MAC usually, but if it has IP, we check protocol)
        return False

    if is_broadcast(flow["dst_ip"]):
        return False
        
    return True

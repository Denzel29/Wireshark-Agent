import json
from typing import List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast_flow(self, flow: dict):
        message = json.dumps({"type": "flow", "data": flow})
        for connection in self.active_connections:
            # Send async, we could gather them but this works for iter1
            await connection.send_text(message)
            
    async def broadcast_alert(self, alert: dict):
        message = json.dumps({"type": "alert", "data": alert})
        for connection in self.active_connections:
            await connection.send_text(message)

manager = ConnectionManager()

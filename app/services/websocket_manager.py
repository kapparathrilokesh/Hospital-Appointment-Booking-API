
from fastapi import WebSocket
from typing import Dict, Set


class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}

    async def connect(self, doctor_id: int, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.setdefault(doctor_id, set()).add(websocket)

    def disconnect(self, doctor_id: int, websocket: WebSocket):
        connections = self.active_connections.get(doctor_id)
        if connections:
            connections.discard(websocket)
            if not connections:
                self.active_connections.pop(doctor_id, None)

    async def broadcast_to_doctor(self, doctor_id: int, message: dict):
        connections = list(self.active_connections.get(doctor_id, set()))
        disconnected = []

        for websocket in connections:
            try:
                await websocket.send_json(message)
            except Exception:
                disconnected.append(websocket)

        for websocket in disconnected:
            self.disconnect(doctor_id, websocket)


manager = ConnectionManager()

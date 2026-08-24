from collections import defaultdict

from fastapi import WebSocket


class WebSocketManager:
    def __init__(self) -> None:
        self._connections: dict[int, set[WebSocket]] = defaultdict(set)

    async def connect(self, event_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[event_id].add(websocket)

    def disconnect(self, event_id: int, websocket: WebSocket) -> None:
        self._connections[event_id].discard(websocket)
        if not self._connections[event_id]:
            self._connections.pop(event_id, None)

    async def broadcast_event(self, event_id: int, payload: dict) -> None:
        stale_connections: list[WebSocket] = []
        for connection in list(self._connections.get(event_id, set())):
            try:
                await connection.send_json(payload)
            except Exception:  # noqa: BLE001
                stale_connections.append(connection)

        for connection in stale_connections:
            self.disconnect(event_id, connection)


manager = WebSocketManager()


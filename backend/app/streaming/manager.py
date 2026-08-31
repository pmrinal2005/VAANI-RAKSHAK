# ==============================================================================
# VAANI-RAKSHAK — Real-Time WebSocket & SSE Connection Manager
# Manages active call rooms, global SOC broadcast channels, and SSE queues.
# ==============================================================================

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class ConnectionManager:
    """
    Thread-safe connection manager for WebSocket rooms and SSE subscribers.
    Handles per-call real-time streaming, global SOC broadcast, and event distribution.
    """

    def __init__(self) -> None:
        self._call_rooms: dict[str, set[WebSocket]] = {}
        self._global_clients: set[WebSocket] = set()
        self._sse_subscribers: set[asyncio.Queue[dict[str, Any]]] = set()
        self._lock = asyncio.Lock()

    async def connect_call(self, call_id: str, websocket: WebSocket) -> None:
        """Register a WebSocket client to a specific call room."""
        await websocket.accept()
        async with self._lock:
            if call_id not in self._call_rooms:
                self._call_rooms[call_id] = set()
            self._call_rooms[call_id].add(websocket)
        logger.info(
            "streaming.ws_call_connected",
            call_id=call_id,
            total_in_room=len(self._call_rooms.get(call_id, set())),
        )

    async def disconnect_call(self, call_id: str, websocket: WebSocket) -> None:
        """Remove a WebSocket client from a call room."""
        async with self._lock:
            if call_id in self._call_rooms:
                self._call_rooms[call_id].discard(websocket)
                if not self._call_rooms[call_id]:
                    del self._call_rooms[call_id]
        logger.info("streaming.ws_call_disconnected", call_id=call_id)

    async def connect_global(self, websocket: WebSocket) -> None:
        """Register a WebSocket client to the global SOC broadcast channel."""
        await websocket.accept()
        async with self._lock:
            self._global_clients.add(websocket)
        logger.info(
            "streaming.ws_global_connected",
            total_global=len(self._global_clients),
        )

    async def disconnect_global(self, websocket: WebSocket) -> None:
        """Remove a WebSocket client from the global SOC broadcast channel."""
        async with self._lock:
            self._global_clients.discard(websocket)
        logger.info(
            "streaming.ws_global_disconnected",
            total_global=len(self._global_clients),
        )

    def subscribe_sse(self) -> asyncio.Queue[dict[str, Any]]:
        """Create and register a new SSE event queue subscriber."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=100)
        self._sse_subscribers.add(queue)
        logger.info(
            "streaming.sse_subscribed",
            total_subscribers=len(self._sse_subscribers),
        )
        return queue

    def unsubscribe_sse(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Unregister an SSE event queue subscriber."""
        self._sse_subscribers.discard(queue)
        logger.info(
            "streaming.sse_unsubscribed",
            total_subscribers=len(self._sse_subscribers),
        )

    async def send_personal_message(
        self, data: dict[str, Any], websocket: WebSocket
    ) -> bool:
        """Send a message directly to an individual WebSocket."""
        try:
            await websocket.send_json(data)
            return True
        except Exception as exc:
            logger.warning("streaming.send_personal_failed", error=str(exc))
            return False

    async def broadcast_to_call(self, call_id: str, data: dict[str, Any]) -> int:
        """
        Broadcast a message to all active WebSocket clients in a specific call room.
        Returns the number of clients successfully messaged.
        """
        clients = list(self._call_rooms.get(call_id, set()))
        if not clients:
            return 0

        sent_count = 0
        dead_clients: list[WebSocket] = []

        for ws in clients:
            try:
                await ws.send_json(data)
                sent_count += 1
            except Exception:
                dead_clients.append(ws)

        if dead_clients:
            async with self._lock:
                for dead in dead_clients:
                    if call_id in self._call_rooms:
                        self._call_rooms[call_id].discard(dead)
                        if not self._call_rooms[call_id]:
                            del self._call_rooms[call_id]

        return sent_count

    async def broadcast_global(self, data: dict[str, Any]) -> int:
        """
        Broadcast a message to all active global SOC WebSocket clients.
        Returns the number of clients successfully messaged.
        """
        clients = list(self._global_clients)
        if not clients:
            return 0

        sent_count = 0
        dead_clients: list[WebSocket] = []

        for ws in clients:
            try:
                await ws.send_json(data)
                sent_count += 1
            except Exception:
                dead_clients.append(ws)

        if dead_clients:
            async with self._lock:
                for dead in dead_clients:
                    self._global_clients.discard(dead)

        return sent_count

    def broadcast_sse(self, event_type: str, data: dict[str, Any]) -> int:
        """
        Push an event to all active SSE subscriber queues.
        Returns the number of subscribers queued.
        """
        if not self._sse_subscribers:
            return 0

        packet = {"event": event_type, "data": data}
        queued_count = 0

        for queue in list(self._sse_subscribers):
            try:
                queue.put_nowait(packet)
                queued_count += 1
            except asyncio.QueueFull:
                # Discard oldest to prevent slow consumers from leaking memory
                with contextlib.suppress(Exception):
                    queue.get_nowait()
                    queue.put_nowait(packet)
                    queued_count += 1

        return queued_count

    def get_active_call_count(self) -> int:
        """Return total active call rooms."""
        return len(self._call_rooms)

    def get_global_client_count(self) -> int:
        """Return total active global SOC WebSocket connections."""
        return len(self._global_clients)

    def get_sse_subscriber_count(self) -> int:
        """Return total active SSE subscribers."""
        return len(self._sse_subscribers)

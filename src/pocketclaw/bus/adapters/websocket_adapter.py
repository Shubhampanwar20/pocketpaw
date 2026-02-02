"""
WebSocket channel adapter.
Created: 2026-02-02
"""

from fastapi import WebSocket
from typing import Any
import json
import logging

from pocketclaw.bus.adapters import BaseChannelAdapter
from pocketclaw.bus.events import Channel, InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


class WebSocketAdapter(BaseChannelAdapter):
    """
    WebSocket channel adapter.

    Manages multiple WebSocket connections and routes messages appropriately.
    """

    def __init__(self):
        super().__init__()
        self._connections: dict[str, WebSocket] = {}  # chat_id -> WebSocket

    @property
    def channel(self) -> Channel:
        return Channel.WEBSOCKET

    async def register_connection(self, websocket: WebSocket, chat_id: str) -> None:
        """Register a new WebSocket connection."""
        await websocket.accept()
        self._connections[chat_id] = websocket
        logger.info(f"🔌 WebSocket connected: {chat_id}")

    async def unregister_connection(self, chat_id: str) -> None:
        """Unregister a WebSocket connection."""
        self._connections.pop(chat_id, None)
        logger.info(f"🔌 WebSocket disconnected: {chat_id}")

    async def handle_message(self, chat_id: str, data: dict[str, Any]) -> None:
        """Handle incoming WebSocket message."""
        action = data.get("action", "chat")

        if action == "chat":
            message = InboundMessage(
                channel=Channel.WEBSOCKET,
                sender_id=chat_id,
                chat_id=chat_id,
                content=data.get("message", ""),
                metadata=data,
            )
            await self._publish_inbound(message)
        # Other actions (settings, tools) handled separately

    async def send(self, message: OutboundMessage) -> None:
        """Send message to WebSocket client."""
        ws = self._connections.get(message.chat_id)
        if not ws:
            # Broadcast to all if no specific chat_id
            for ws in self._connections.values():
                await self._send_to_socket(ws, message)
        else:
            await self._send_to_socket(ws, message)

    async def _send_to_socket(self, ws: WebSocket, message: OutboundMessage) -> None:
        """Send to a specific WebSocket."""
        try:
            msg_type = "stream" if message.is_stream_chunk else "message"
            await ws.send_json({
                "type": msg_type,
                "content": message.content,
                "metadata": message.metadata,
                "is_stream_end": message.is_stream_end,
            })
        except Exception:
            pass  # Connection closed

    async def broadcast(self, content: str, msg_type: str = "notification") -> None:
        """Broadcast to all connected clients."""
        for ws in self._connections.values():
            try:
                await ws.send_json({"type": msg_type, "content": content})
            except Exception:
                pass

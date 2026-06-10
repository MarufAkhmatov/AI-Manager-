"""/ws/activity — broadcasts agent events to subscribed UIs."""

from __future__ import annotations

import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.events import bus

router = APIRouter(tags=["ws"])


@router.websocket("/ws/activity")
async def activity(ws: WebSocket) -> None:
    await ws.accept()
    async with bus.subscribe() as q:
        try:
            while True:
                event = await q.get()
                await ws.send_text(json.dumps(event.to_json()))
        except WebSocketDisconnect:
            return

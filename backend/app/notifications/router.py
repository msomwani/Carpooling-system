import logging
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from app.auth.dependencies import get_current_user_id
from app.notifications.websocket import manager

router = APIRouter(prefix="/notifications", tags=["Notifications"])

logger = logging.getLogger(__name__)


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, user_id: str = Depends(get_current_user_id)
):
    """WebSocket connection for real‑time notifications.
    The user is identified via the same cookie‑based Google auth used elsewhere.
    """
    await manager.connect(user_id, websocket)
    try:
        while True:
            # Keep the connection alive – we don't expect inbound messages for now.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(user_id, websocket)
        logger.info("WebSocket disconnected for user %s", user_id)

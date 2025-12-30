from typing import Dict, List, Set
import logging
from fastapi import WebSocket
import json

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections for team chat rooms.
    Each team has its own room with multiple connected users.
    """

    def __init__(self):
        # room_id -> set of (websocket, user_id) tuples
        self.active_connections: Dict[int, Set[tuple[WebSocket, str]]] = {}

    async def connect(self, websocket: WebSocket, room_id: int, user_id: str):
        """
        Connect a user to a team chat room.
        """
        await websocket.accept()

        if room_id not in self.active_connections:
            self.active_connections[room_id] = set()

        # Remove any existing connection for this user in this room
        self.active_connections[room_id] = {
            (ws, uid) for ws, uid in self.active_connections[room_id]
            if uid != user_id
        }

        # Add new connection
        self.active_connections[room_id].add((websocket, user_id))

        logger.info(f"User {user_id} connected to team chat room {room_id}")

        # Notify others that user joined
        await self.broadcast_to_room(
            room_id,
            {
                "type": "user_joined",
                "user_id": user_id,
                "timestamp": "now"
            },
            exclude_user=user_id
        )

    def disconnect(self, room_id: int, user_id: str):
        """
        Disconnect a user from a team chat room.
        """
        if room_id in self.active_connections:
            # Remove the connection for this user
            self.active_connections[room_id] = {
                (ws, uid) for ws, uid in self.active_connections[room_id]
                if uid != user_id
            }

            # If room is empty, clean it up
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

            logger.info(f"User {user_id} disconnected from team chat room {room_id}")

    async def broadcast_to_room(self, room_id: int, message: dict, exclude_user: str = None):
        """
        Broadcast a message to all users in a team chat room.
        """
        if room_id not in self.active_connections:
            return

        disconnected = set()

        for websocket, user_id in self.active_connections[room_id]:
            if exclude_user and user_id == exclude_user:
                continue

            try:
                await websocket.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message to user {user_id}: {e}")
                disconnected.add((websocket, user_id))

        # Clean up disconnected users
        for websocket, user_id in disconnected:
            await self._cleanup_connection(room_id, websocket, user_id)

    def get_room_online_count(self, room_id: int) -> int:
        """
        Get the number of online users in a room.
        """
        if room_id not in self.active_connections:
            return 0
        return len(self.active_connections[room_id])

    def get_room_users(self, room_id: int) -> List[str]:
        """
        Get list of user IDs currently in a room.
        """
        if room_id not in self.active_connections:
            return []
        return [user_id for _, user_id in self.active_connections[room_id]]

    async def _cleanup_connection(self, room_id: int, websocket: WebSocket, user_id: str):
        """
        Clean up a disconnected connection.
        """
        try:
            await websocket.close()
        except Exception:
            pass  # Connection might already be closed

        if room_id in self.active_connections:
            self.active_connections[room_id].discard((websocket, user_id))
            if not self.active_connections[room_id]:
                del self.active_connections[room_id]

    async def send_to_user(self, room_id: int, user_id: str, message: dict):
        """
        Send a message to a specific user in a room.
        """
        if room_id not in self.active_connections:
            return

        for websocket, uid in self.active_connections[room_id]:
            if uid == user_id:
                try:
                    await websocket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Failed to send message to user {user_id}: {e}")
                    await self._cleanup_connection(room_id, websocket, user_id)
                break

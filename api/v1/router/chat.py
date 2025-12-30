from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from typing import Dict, List
import json
import logging
from datetime import datetime
from uuid import UUID

from service.auth import verify_access_token_ws, verify_access_token
from controller.teams import TeamsOp
from schema.chat import ChatMessage, FileMessage
from service.chat.connection_manager import ConnectionManager
from model.teams import Team

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

# Global connection manager instance
manager = ConnectionManager()


@router.websocket("/ws/chat/{team_id}")
async def chat_websocket(
    websocket: WebSocket,
    team_id: int,
    token: str = None
):
    """
    WebSocket endpoint for team chat.
    Query parameter: token (JWT token for authentication)
    """
    try:
        # Authenticate user
        if not token:
            await websocket.close(code=1008, reason="Authentication token required")
            return

        try:
            auth_data = verify_access_token_ws(token)
            user_id = auth_data.get("user_id")
            if not user_id:
                await websocket.close(code=1008, reason="Invalid authentication")
                return
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            await websocket.close(code=1008, reason="Authentication failed")
            return

        # Verify team membership
        try:
            from model.teams import Team
            team = Team.get_team_by_id(team_id)
            if not team:
                await websocket.close(code=1008, reason="Team not found")
                return

            # Check if user is a member of the team
            is_member = any(str(member.id) == user_id for member in team.students)
            is_creator = str(team.creator_id) == user_id

            if not (is_member or is_creator):
                await websocket.close(code=1008, reason="Not a team member")
                return

        except Exception as e:
            logger.error(f"Team verification failed: {e}")
            await websocket.close(code=1008, reason="Team access denied")
            return

        # Accept connection and join room
        await manager.connect(websocket, team_id, user_id)

        try:
            while True:
                # Receive message from client
                data = await websocket.receive_text()
                message_data = json.loads(data)

                # Validate message structure
                if not isinstance(message_data, dict):
                    continue

                message_type = message_data.get("type")

                if message_type == "chat_message":
                    # Handle text message
                    content = message_data.get("content", "").strip()
                    if not content:
                        continue

                    # Create message object
                    message = ChatMessage(
                        type="chat_message",
                        user_id=user_id,
                        content=content,
                        timestamp=datetime.utcnow().isoformat()
                    )

                    # Broadcast to team room
                    await manager.broadcast_to_room(team_id, message.model_dump())

                elif message_type == "file_shared":
                    # Handle file sharing notification
                    file_data = message_data.get("file")
                    if not file_data:
                        continue

                    # Create file message object
                    file_message = FileMessage(
                        type="file_shared",
                        user_id=user_id,
                        file=file_data,
                        timestamp=datetime.utcnow().isoformat()
                    )

                    # Broadcast to team room
                    await manager.broadcast_to_room(team_id, file_message.model_dump())

                elif message_type == "typing":
                    # Handle typing indicators
                    is_typing = message_data.get("is_typing", False)
                    typing_message = {
                        "type": "typing",
                        "user_id": user_id,
                        "is_typing": is_typing,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    await manager.broadcast_to_room(team_id, typing_message, exclude_user=user_id)

        except WebSocketDisconnect:
            logger.info(f"User {user_id} disconnected from team {team_id}")
        except Exception as e:
            logger.error(f"Error in chat websocket: {e}")
        finally:
            # Clean up connection
            manager.disconnect(team_id, user_id)


@router.get("/teams/{team_id}/chat/status")
async def get_chat_status(
    team_id: int,
    auth_data: dict = Depends(verify_access_token)
):
    """
    Get chat room status (online members count)
    """
    user_id = auth_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify team membership
    try:
        team = Team.get_team_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        is_member = any(str(member.id) == user_id for member in team.students)
        is_creator = str(team.creator_id) == user_id

        if not (is_member or is_creator):
            raise HTTPException(status_code=403, detail="Not a team member")

    except Exception as e:
        raise HTTPException(status_code=403, detail="Team access denied")

    # Get online users count
    online_count = manager.get_room_online_count(team_id)

    return {
        "team_id": team_id,
        "online_members": online_count,
        "total_members": len(team.students) + 1  # +1 for creator
    }

from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """
    Schema for chat text messages
    """
    type: str = "chat_message"
    user_id: str
    content: str
    timestamp: str


class FileMessage(BaseModel):
    """
    Schema for file sharing messages
    """
    type: str = "file_shared"
    user_id: str
    file: Dict[str, Any]  # File metadata
    timestamp: str


class TypingIndicator(BaseModel):
    """
    Schema for typing indicators
    """
    type: str = "typing"
    user_id: str
    is_typing: bool
    timestamp: str


class UserJoinedMessage(BaseModel):
    """
    Schema for user join notifications
    """
    type: str = "user_joined"
    user_id: str
    timestamp: str


class UserLeftMessage(BaseModel):
    """
    Schema for user leave notifications
    """
    type: str = "user_left"
    user_id: str
    timestamp: str


class FileUploadResponse(BaseModel):
    """
    Response schema for file uploads
    """
    file_id: str
    filename: str
    original_name: str
    file_size: int
    file_type: str
    download_url: str
    expires_at: str


class ChatStatusResponse(BaseModel):
    """
    Response schema for chat room status
    """
    team_id: int
    online_members: int
    total_members: int

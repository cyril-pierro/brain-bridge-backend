from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from fastapi.responses import FileResponse
from typing import List
import os
import uuid
from datetime import datetime, timedelta
import shutil
import logging

from service.auth import verify_access_token
from controller.teams import TeamsOp
from schema.chat import FileUploadResponse
from service.files.storage import FileStorage

router = APIRouter(tags=["files"])
logger = logging.getLogger(__name__)

# Initialize file storage service
file_storage = FileStorage()


@router.post("/teams/{team_id}/files", response_model=FileUploadResponse)
async def upload_file(
    team_id: int,
    file: UploadFile = File(...),
    auth_data: dict = Depends(verify_access_token)
):
    """
    Upload a file to team storage (temporary, auto-deleted after 24 hours)
    """
    user_id = auth_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify team membership
    try:
        from model.teams import Team
        team = Team.get_team_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        is_member = any(str(member.id) == user_id for member in team.students)
        is_creator = str(team.creator_id) == user_id

        if not (is_member or is_creator):
            raise HTTPException(status_code=403, detail="Not a team member")

    except Exception as e:
        raise HTTPException(status_code=403, detail="Team access denied")

    # Validate file
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided")

    # Check file size (10MB limit)
    file_size = 0
    content = await file.read()
    file_size = len(content)

    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(status_code=413, detail="File too large (max 10MB)")

    # Validate file type
    allowed_extensions = {
        # Documents
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        # Images
        '.jpg', '.jpeg', '.png', '.gif',
        # Archives
        '.zip'
    }

    file_ext = os.path.splitext(file.filename.lower())[1]
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(allowed_extensions)}"
        )

    try:
        # Save file
        file_info = await file_storage.save_file(
            content=content,
            filename=file.filename,
            team_id=team_id,
            user_id=user_id
        )

        return FileUploadResponse(
            file_id=file_info["file_id"],
            filename=file_info["filename"],
            original_name=file.filename,
            file_size=file_size,
            file_type=file.content_type or "application/octet-stream",
            download_url=file_info["download_url"],
            expires_at=file_info["expires_at"]
        )

    except Exception as e:
        logger.error(f"File upload failed: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")


@router.get("/files/{file_id}")
async def download_file(
    file_id: str,
    auth_data: dict = Depends(verify_access_token)
):
    """
    Download a file from team storage
    """
    user_id = auth_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    try:
        # Get file info
        file_info = file_storage.get_file_info(file_id)
        if not file_info:
            raise HTTPException(status_code=404, detail="File not found")

        # Verify team membership
        team_id = file_info["team_id"]
        from model.teams import Team
        team = Team.get_team_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        is_member = any(str(member.id) == user_id for member in team.students)
        is_creator = str(team.creator_id) == user_id

        if not (is_member or is_creator):
            raise HTTPException(status_code=403, detail="Not a team member")

        # Check if file has expired
        expires_at = datetime.fromisoformat(file_info["expires_at"])
        if datetime.utcnow() > expires_at:
            # Clean up expired file
            await file_storage.delete_file(file_id)
            raise HTTPException(status_code=404, detail="File has expired")

        # Return file
        file_path = file_info["file_path"]
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found on disk")

        return FileResponse(
            path=file_path,
            filename=file_info["original_name"],
            media_type=file_info.get("content_type", "application/octet-stream")
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download failed: {e}")
        raise HTTPException(status_code=500, detail="File download failed")


@router.get("/teams/{team_id}/files")
async def list_team_files(
    team_id: int,
    auth_data: dict = Depends(verify_access_token)
):
    """
    List active files for a team
    """
    user_id = auth_data.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Verify team membership
    try:
        from model.teams import Team
        team = Team.get_team_by_id(team_id)
        if not team:
            raise HTTPException(status_code=404, detail="Team not found")

        is_member = any(str(member.id) == user_id for member in team.students)
        is_creator = str(team.creator_id) == user_id

        if not (is_member or is_creator):
            raise HTTPException(status_code=403, detail="Not a team member")

    except Exception as e:
        raise HTTPException(status_code=403, detail="Team access denied")

    try:
        files = file_storage.list_team_files(team_id)
        return {"files": files}
    except Exception as e:
        logger.error(f"File listing failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to list files")

import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FileStorage:
    """
    Temporary file storage for team chat files.
    Files are automatically deleted after 24 hours.
    """

    def __init__(self):
        self.storage_dir = os.getenv("CHAT_FILE_STORAGE_DIR", "/tmp/chat_files")
        self.retention_hours = int(os.getenv("CHAT_FILE_RETENTION_HOURS", "24"))

        # Create storage directory if it doesn't exist
        Path(self.storage_dir).mkdir(parents=True, exist_ok=True)

        # Clean up expired files on startup
        self._cleanup_expired_files()

    async def save_file(
        self,
        content: bytes,
        filename: str,
        team_id: int,
        user_id: str
    ) -> Dict[str, Any]:
        """
        Save a file to temporary storage
        """
        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Create file extension
        file_ext = os.path.splitext(filename)[1]
        stored_filename = f"{file_id}{file_ext}"

        # Create team subdirectory
        team_dir = os.path.join(self.storage_dir, str(team_id))
        Path(team_dir).mkdir(parents=True, exist_ok=True)

        # File path
        file_path = os.path.join(team_dir, stored_filename)

        # Write file
        with open(file_path, "wb") as f:
            f.write(content)

        # Calculate expiration
        expires_at = datetime.utcnow() + timedelta(hours=self.retention_hours)

        # Create file metadata
        metadata = {
            "file_id": file_id,
            "filename": stored_filename,
            "original_name": filename,
            "file_path": file_path,
            "team_id": team_id,
            "user_id": user_id,
            "uploaded_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at.isoformat(),
            "file_size": len(content)
        }

        # Save metadata
        metadata_path = os.path.join(team_dir, f"{file_id}.meta.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Create download URL
        download_url = f"/api/v1/files/{file_id}"

        return {
            "file_id": file_id,
            "filename": stored_filename,
            "file_path": file_path,
            "download_url": download_url,
            "expires_at": expires_at.isoformat()
        }

    def get_file_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get file metadata
        """
        # Find metadata file
        for team_dir in os.listdir(self.storage_dir):
            team_path = os.path.join(self.storage_dir, team_dir)
            if not os.path.isdir(team_path):
                continue

            metadata_path = os.path.join(team_path, f"{file_id}.meta.json")
            if os.path.exists(metadata_path):
                with open(metadata_path, "r") as f:
                    return json.load(f)

        return None

    async def delete_file(self, file_id: str) -> bool:
        """
        Delete a file and its metadata
        """
        try:
            file_info = self.get_file_info(file_id)
            if not file_info:
                return False

            # Delete files
            file_path = file_info["file_path"]
            metadata_path = file_path.replace(os.path.splitext(file_path)[1], ".meta.json")

            if os.path.exists(file_path):
                os.remove(file_path)

            if os.path.exists(metadata_path):
                os.remove(metadata_path)

            return True

        except Exception as e:
            logger.error(f"Failed to delete file {file_id}: {e}")
            return False

    def list_team_files(self, team_id: int) -> List[Dict[str, Any]]:
        """
        List all active files for a team
        """
        team_dir = os.path.join(self.storage_dir, str(team_id))
        if not os.path.exists(team_dir):
            return []

        files = []
        now = datetime.utcnow()

        try:
            for filename in os.listdir(team_dir):
                if filename.endswith(".meta.json"):
                    metadata_path = os.path.join(team_dir, filename)
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)

                    # Check if expired
                    expires_at = datetime.fromisoformat(metadata["expires_at"])
                    if now > expires_at:
                        # Clean up expired file
                        self._cleanup_expired_file(metadata)
                        continue

                    files.append({
                        "file_id": metadata["file_id"],
                        "filename": metadata["original_name"],
                        "uploaded_by": metadata["user_id"],
                        "uploaded_at": metadata["uploaded_at"],
                        "expires_at": metadata["expires_at"],
                        "file_size": metadata["file_size"],
                        "download_url": f"/api/v1/files/{metadata['file_id']}"
                    })

        except Exception as e:
            logger.error(f"Failed to list team files: {e}")

        return files

    def _cleanup_expired_files(self):
        """
        Clean up all expired files (called on startup)
        """
        now = datetime.utcnow()

        try:
            for team_dir in os.listdir(self.storage_dir):
                team_path = os.path.join(self.storage_dir, team_dir)
                if not os.path.isdir(team_path):
                    continue

                for filename in os.listdir(team_path):
                    if filename.endswith(".meta.json"):
                        metadata_path = os.path.join(team_path, filename)
                        try:
                            with open(metadata_path, "r") as f:
                                metadata = json.load(f)

                            expires_at = datetime.fromisoformat(metadata["expires_at"])
                            if now > expires_at:
                                self._cleanup_expired_file(metadata)
                        except Exception as e:
                            logger.error(f"Failed to process metadata {metadata_path}: {e}")

        except Exception as e:
            logger.error(f"Failed to cleanup expired files: {e}")

    def _cleanup_expired_file(self, metadata: Dict[str, Any]):
        """
        Clean up a single expired file
        """
        try:
            file_path = metadata["file_path"]
            metadata_path = file_path.replace(os.path.splitext(file_path)[1], ".meta.json")

            if os.path.exists(file_path):
                os.remove(file_path)

            if os.path.exists(metadata_path):
                os.remove(metadata_path)

            logger.info(f"Cleaned up expired file: {metadata['file_id']}")

        except Exception as e:
            logger.error(f"Failed to cleanup file {metadata.get('file_id', 'unknown')}: {e}")

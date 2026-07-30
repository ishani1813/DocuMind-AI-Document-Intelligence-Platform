"""Storage service — AWS S3 with automatic local filesystem fallback."""

import uuid
import os
from typing import Optional
import structlog

from app.core.config import settings

logger = structlog.get_logger()

LOCAL_STORAGE_DIR = "/app/uploads"


class StorageService:
    def __init__(self):
        self._s3_client = None

    @property
    def s3_client(self):
        if not settings.USE_S3 or not settings.AWS_ACCESS_KEY_ID:
            return None
        if self._s3_client is None:
            try:
                import boto3
                self._s3_client = boto3.client(
                    "s3",
                    region_name=settings.AWS_REGION,
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                )
            except Exception as e:
                logger.warning("S3 client init failed", error=str(e))
                return None
        return self._s3_client

    async def upload_pdf(self, file_bytes: bytes, original_filename: str, owner_id: str):
        """Upload PDF — to S3 if configured, otherwise local disk."""
        if self.s3_client:
            return await self._upload_s3(file_bytes, original_filename, owner_id)
        return await self._upload_local(file_bytes, original_filename, owner_id)

    async def _upload_s3(self, file_bytes: bytes, original_filename: str, owner_id: str):
        s3_key = f"documents/{owner_id}/{uuid.uuid4()}/{original_filename}"
        try:
            self.s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME, Key=s3_key, Body=file_bytes,
                ContentType="application/pdf",
            )
            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": settings.S3_BUCKET_NAME, "Key": s3_key},
                ExpiresIn=3600,
            )
            return {"s3_key": s3_key, "s3_url": url, "local_path": None}
        except Exception as e:
            logger.error("S3 upload failed, falling back to local", error=str(e))
            return await self._upload_local(file_bytes, original_filename, owner_id)

    async def _upload_local(self, file_bytes: bytes, original_filename: str, owner_id: str):
        owner_dir = os.path.join(LOCAL_STORAGE_DIR, owner_id)
        os.makedirs(owner_dir, exist_ok=True)
        unique_name = f"{uuid.uuid4()}_{original_filename}"
        path = os.path.join(owner_dir, unique_name)
        with open(path, "wb") as f:
            f.write(file_bytes)
        return {"s3_key": None, "s3_url": None, "local_path": path}

    async def delete_file(self, s3_key: Optional[str] = None, local_path: Optional[str] = None):
        if s3_key and self.s3_client:
            try:
                self.s3_client.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
            except Exception as e:
                logger.warning("S3 delete failed", error=str(e))
        if local_path and os.path.exists(local_path):
            try:
                os.remove(local_path)
            except Exception as e:
                logger.warning("Local delete failed", error=str(e))


storage_service = StorageService()

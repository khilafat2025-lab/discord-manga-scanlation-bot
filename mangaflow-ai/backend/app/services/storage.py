"""
MangaFlow AI - Storage Service (Cloudflare R2 / Local fallback)
"""
import os
import logging
from typing import Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageService:
    def __init__(self):
        self._client = None
        self._use_local = not all([settings.R2_ACCOUNT_ID, settings.R2_ACCESS_KEY_ID, settings.R2_SECRET_ACCESS_KEY])
        if not self._use_local:
            self._client = boto3.client(
                "s3",
                endpoint_url=f"https://{settings.R2_ACCOUNT_ID}.r2.cloudflarestorage.com",
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4"),
                region_name="auto",
            )
            logger.info("Cloudflare R2 storage initialized")
        else:
            logger.info("Using local filesystem storage (R2 not configured)")

    def upload_file(self, file_path: str, key: str, content_type: Optional[str] = None, public: bool = False) -> str:
        if self._use_local:
            return self._local_upload(file_path, key)
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        if public:
            extra_args["ACL"] = "public-read"
        try:
            self._client.upload_file(file_path, settings.R2_BUCKET_NAME, key, ExtraArgs=extra_args if extra_args else None)
            if settings.R2_PUBLIC_URL and public:
                return f"{settings.R2_PUBLIC_URL}/{key}"
            return key
        except ClientError as e:
            logger.error(f"R2 upload failed: {e}")
            return self._local_upload(file_path, key)

    def upload_bytes(self, data: bytes, key: str, content_type: Optional[str] = None) -> str:
        if self._use_local:
            local_path = os.path.join(settings.UPLOAD_DIR, key)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, "wb") as f:
                f.write(data)
            return key
        self._client.put_object(Bucket=settings.R2_BUCKET_NAME, Key=key, Body=data, ContentType=content_type or "application/octet-stream")
        return key

    def download_file(self, key: str, local_path: str) -> str:
        if self._use_local:
            src = os.path.join(settings.UPLOAD_DIR, key)
            if os.path.exists(src):
                import shutil
                shutil.copy2(src, local_path)
            return local_path
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        self._client.download_file(settings.R2_BUCKET_NAME, key, local_path)
        return local_path

    def get_presigned_url(self, key: str, expires_in: int = 3600) -> str:
        if self._use_local:
            return f"/api/v1/files/{key}"
        try:
            return self._client.generate_presigned_url("get_object", Params={"Bucket": settings.R2_BUCKET_NAME, "Key": key}, ExpiresIn=expires_in)
        except ClientError as e:
            logger.error(f"Presigned URL failed: {e}")
            return ""

    def delete_file(self, key: str) -> bool:
        if self._use_local:
            local_path = os.path.join(settings.UPLOAD_DIR, key)
            if os.path.exists(local_path):
                os.remove(local_path)
            return True
        try:
            self._client.delete_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
            return True
        except ClientError as e:
            logger.error(f"Delete failed: {e}")
            return False

    def file_exists(self, key: str) -> bool:
        if self._use_local:
            return os.path.exists(os.path.join(settings.UPLOAD_DIR, key))
        try:
            self._client.head_object(Bucket=settings.R2_BUCKET_NAME, Key=key)
            return True
        except ClientError:
            return False

    def _local_upload(self, file_path: str, key: str) -> str:
        dest = os.path.join(settings.UPLOAD_DIR, key)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        import shutil
        shutil.copy2(file_path, dest)
        return key


storage = StorageService()

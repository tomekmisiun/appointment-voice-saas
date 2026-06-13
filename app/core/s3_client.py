import boto3
from botocore.client import BaseClient

from app.core.config import settings


_s3_client: BaseClient | None = None


def get_s3_client() -> BaseClient:
    global _s3_client

    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            region_name=settings.s3_region_name,
        )

    return _s3_client


def reset_s3_client_cache() -> None:
    global _s3_client
    _s3_client = None

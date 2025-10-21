"""File upload recorder Lambda.

This module intentionally mirrors a legacy-style implementation that couples
business logic with boto3 clients. The workshop exercise asks participants to
backfill pytest-based unit tests around the existing behaviour.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# グローバルクライアント（テストしづらいポイント）
_dynamodb = boto3.resource("dynamodb")
_s3 = boto3.client("s3")


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """AWS Lambda entry point for S3 Put events."""
    try:
        # 環境変数チェック
        table_name = os.environ.get("FILES_TABLE")
        if not table_name:
            raise RuntimeError("FILES_TABLE environment variable is required")

        table = _dynamodb.Table(table_name)

        # S3イベントからファイル情報を抽出
        record = event["Records"][0]
        bucket = record["s3"]["bucket"]["name"]
        key = record["s3"]["object"]["key"]
        size = record["s3"]["object"]["size"]

        # file_id を生成（重複チェック用）
        file_id = f"{bucket}#{key}"

        # 既存レコードをチェック（重複防止）
        existing = _fetch_file_record(table, file_id)
        if existing:
            logger.info("File already recorded, skipping", extra={"file_id": file_id})
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {"message": "File already recorded", "file_id": file_id}
                ),
            }

        # S3からファイルメタデータを取得
        metadata = _get_file_metadata(bucket, key)

        # DynamoDBに保存
        item = {
            "file_id": file_id,
            "bucket": bucket,
            "key": key,
            "size": size,
            "content_type": metadata.get("ContentType", "application/octet-stream"),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }
        table.put_item(Item=item)

        logger.info(
            "File recorded successfully", extra={"file_id": file_id, "size": size}
        )

        return {
            "statusCode": 200,
            "body": json.dumps(
                {"message": "File recorded successfully", "file_id": file_id}
            ),
        }

    except KeyError as exc:
        logger.error("Invalid S3 event structure", exc_info=True)
        raise ValueError(f"Invalid S3 event structure: {exc}") from exc
    except ClientError as exc:
        logger.error("AWS API call failed", exc_info=True)
        raise RuntimeError(f"AWS API call failed: {exc}") from exc


def _fetch_file_record(table, file_id: str) -> Optional[Dict[str, Any]]:
    """DynamoDBから既存レコードを取得（重複チェック用）"""
    try:
        response = table.get_item(Key={"file_id": file_id})
        return response.get("Item")
    except ClientError as exc:
        logger.exception("Failed to fetch file record", extra={"file_id": file_id})
        raise RuntimeError("Failed to fetch file record from DynamoDB") from exc


def _get_file_metadata(bucket: str, key: str) -> Dict[str, Any]:
    """S3からファイルメタデータを取得"""
    try:
        response = _s3.head_object(Bucket=bucket, Key=key)
        return response
    except ClientError as exc:
        logger.warning(
            "Failed to get file metadata from S3, using defaults",
            extra={"bucket": bucket, "key": key},
        )
        # メタデータ取得に失敗してもエラーにしない（デフォルト値を使用）
        return {}

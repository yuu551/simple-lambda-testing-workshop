"""Solution for file_recorder tests.

このファイルは演習の解答例です。参加者は演習後に参照できます。
"""

import json
from pathlib import Path

import pytest
import boto3
from moto import mock_aws

import file_recorder

SAMPLES_DIR = Path(__file__).resolve().parent.parent / "samples"


@pytest.fixture
def mock_aws_services(monkeypatch):
    """AWSサービスのモックをセットアップ"""
    with mock_aws():
        # DynamoDBテーブルを作成
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = dynamodb.create_table(
            TableName="files_table",
            KeySchema=[{"AttributeName": "file_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "file_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        # S3バケットを作成
        s3 = boto3.client("s3", region_name="ap-northeast-1")
        s3.create_bucket(
            Bucket="my-upload-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"},
        )

        # S3にオブジェクトを配置（head_object用）
        s3.put_object(
            Bucket="my-upload-bucket",
            Key="uploads/report.pdf",
            Body=b"test content",
            ContentType="application/pdf",
        )

        # 大きいファイルも配置
        s3.put_object(
            Bucket="my-upload-bucket",
            Key="uploads/large-video.mp4",
            Body=b"large video content",
            ContentType="video/mp4",
        )

        # 環境変数を設定
        monkeypatch.setenv("FILES_TABLE", "files_table")

        # boto3クライアントを差し替え
        monkeypatch.setattr(file_recorder, "_dynamodb", dynamodb)
        monkeypatch.setattr(file_recorder, "_s3", s3)

        # テストに渡すデータ
        yield {"table": table, "dynamodb": dynamodb, "s3": s3}


def test_records_new_file(mock_aws_services):
    """新規ファイルのアップロードイベントでレコードが作成される"""
    # イベントを読み込む
    event = load_event("s3_put_event.json")

    # Lambda関数を実行
    response = file_recorder.lambda_handler(event, context=None)

    # レスポンスを検証
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["message"] == "File recorded successfully"
    assert body["file_id"] == "my-upload-bucket#uploads/report.pdf"

    # DynamoDBを検証
    table = mock_aws_services["table"]
    stored = table.get_item(Key={"file_id": "my-upload-bucket#uploads/report.pdf"})

    assert "Item" in stored
    item = stored["Item"]
    assert item["file_id"] == "my-upload-bucket#uploads/report.pdf"
    assert item["bucket"] == "my-upload-bucket"
    assert item["key"] == "uploads/report.pdf"
    assert item["size"] == 102400
    assert item["content_type"] == "application/pdf"
    assert "uploaded_at" in item


def test_skips_duplicate_file(mock_aws_services):
    """重複ファイルのイベントで処理がスキップされる"""
    table = mock_aws_services["table"]

    # 既存レコードを投入
    table.put_item(
        Item={
            "file_id": "my-upload-bucket#uploads/report.pdf",
            "bucket": "my-upload-bucket",
            "key": "uploads/report.pdf",
            "size": 102400,
            "content_type": "application/pdf",
            "uploaded_at": "2025-03-01T09:00:00.000Z",
        }
    )

    # イベントを読み込む
    event = load_event("s3_put_event.json")

    # Lambda関数を実行
    response = file_recorder.lambda_handler(event, context=None)

    # レスポンスを検証
    assert response["statusCode"] == 200

    body = json.loads(response["body"])
    assert body["message"] == "File already recorded"
    assert body["file_id"] == "my-upload-bucket#uploads/report.pdf"

    # DynamoDBを検証（変更されていないことを確認）
    stored = table.get_item(Key={"file_id": "my-upload-bucket#uploads/report.pdf"})[
        "Item"
    ]
    assert stored["uploaded_at"] == "2025-03-01T09:00:00.000Z"  # 元の値のまま


def load_event(name: str) -> dict:
    """samples/ ディレクトリからイベントJSONファイルを読み込む"""
    return json.loads((SAMPLES_DIR / name).read_text(encoding="utf-8"))

"""Backfill tests for `file_recorder.lambda_handler`.

このファイルはワークショップ参加者が編集します。最低限の骨組みと
観点メモだけを残しているため、必要なフィクスチャや補助関数は自由に
追加してください。
"""

import json
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

import file_recorder

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"


# 演習1: 新規ファイルのアップロードイベントでレコードが作成されることを検証してください
# EXERCISE.md の「課題1」を参照して、以下の関数を実装してください
def test_records_new_file(monkeypatch):
    """新規ファイルのアップロードイベントでレコードがDynamoDBに保存されることを検証する

    実装手順:
    1. @pytest.fixture で mock_aws_services を定義
    2. load_event("s3_put_event.json") でイベントを読み込む
    3. file_recorder.lambda_handler() を実行
    4. レスポンスとDynamoDBの内容を検証

    詳細は EXERCISE.md と HINTS.md を参照してください
    """
    pass


# 演習2: 重複ファイルのイベントで処理がスキップされることを検証してください
# EXERCISE.md の「課題2」を参照して、以下の関数を実装してください
def test_skips_duplicate_file(monkeypatch):
    """既存レコードと同じfile_idのイベントを受信した際、DynamoDBが書き換わらないことを確認

    実装手順:
    1. 既存レコードをDynamoDBに投入
    2. 同じfile_idのイベントを送信
    3. 処理がスキップされることを確認
    4. DynamoDBが更新されていないことを確認

    詳細は EXERCISE.md と HINTS.md を参照してください
    """
    pass


def load_event(name: str) -> dict:
    """samples/ ディレクトリからイベントJSONファイルを読み込む

    使い方:
        event = load_event("s3_put_event.json")
        # samples/s3_put_event.json が読み込まれる

    Args:
        name: ファイル名（例: "s3_put_event.json"）

    Returns:
        イベントデータの辞書
    """
    return json.loads((SAMPLES_DIR / name).read_text(encoding="utf-8"))

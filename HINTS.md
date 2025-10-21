# ヒント集

このドキュメントでは、演習課題で詰まった時のヒントを段階的に提供します。

**ヒントの使い方:**
1. まず自分で考えてみる
2. レベル1のヒントを読む
3. それでも分からなければレベル2へ
4. 最後の手段としてレベル3の実装例を参照

---

## レベル1: 基礎知識

### 1-1. motoとは？

`moto` は、AWSサービスをモック化（偽物化）するPythonライブラリです。

**なぜmotoが必要？**
- 実際のAWSアカウントやリソースがなくてもテストできる
- テストが高速（ネットワーク通信が不要）
- 無料（AWS課金が発生しない）

**基本的な使い方:**

```python
from moto import mock_aws
import boto3

# motoのモックを有効化
with mock_aws():
    # この中では boto3 が偽物のAWSに接続される
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    
    # テーブルを作成（メモリ上に作られる）
    table = dynamodb.create_table(
        TableName="test_table",
        KeySchema=[{"AttributeName": "id", "KeyType": "HASH"}],
        AttributeDefinitions=[{"AttributeName": "id", "AttributeType": "S"}],
        BillingMode="PAY_PER_REQUEST"
    )
    
    # データを保存（メモリ上に保存される）
    table.put_item(Item={"id": "123", "name": "test"})
    
    # データを取得
    response = table.get_item(Key={"id": "123"})
    print(response["Item"])  # => {"id": "123", "name": "test"}
```

**重要:**
- `with mock_aws():` のブロックを抜けると、すべてのデータは消える
- テストごとに独立した環境が作られる

---

### 1-2. pytestのfixtureとは？

`fixture` は、テストの前準備（セットアップ）を行う仕組みです。

**なぜfixtureが必要？**
- 複数のテストで共通のセットアップを再利用できる
- テストコードがシンプルになる

**基本的な使い方:**

```python
import pytest

@pytest.fixture
def sample_data():
    """テスト用のデータを準備"""
    return {"name": "Alice", "age": 30}

def test_example(sample_data):
    """fixtureを使ったテスト"""
    # sample_data が自動的に渡される
    assert sample_data["name"] == "Alice"
    assert sample_data["age"] == 30
```

**yieldを使った後片付け:**

```python
@pytest.fixture
def database():
    """データベース接続を準備"""
    db = connect_database()  # セットアップ
    yield db                  # テストに渡す
    db.close()               # 後片付け
```

---

### 1-3. monkeypatchとは？

`monkeypatch` は、テスト中だけ特定の値や関数を差し替える仕組みです。

**なぜmonkeypatchが必要？**
- 環境変数を設定したい
- グローバル変数を差し替えたい
- 外部APIを偽物に差し替えたい

**基本的な使い方:**

**環境変数の設定:**
```python
def test_with_env(monkeypatch):
    monkeypatch.setenv("MY_VAR", "test_value")
    
    import os
    assert os.environ["MY_VAR"] == "test_value"
```

**グローバル変数の差し替え:**
```python
import my_module

def test_with_mock_client(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr(my_module, "_client", fake_client)
    
    # これ以降、my_module._client は fake_client になる
```

---

## レベル2: 実装ヒント

### 2-1. DynamoDBテーブルの作成方法

**最小構成のテーブル作成:**

```python
import boto3
from moto import mock_aws

with mock_aws():
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    
    table = dynamodb.create_table(
        TableName="files_table",
        KeySchema=[
            {"AttributeName": "file_id", "KeyType": "HASH"}  # プライマリキー
        ],
        AttributeDefinitions=[
            {"AttributeName": "file_id", "AttributeType": "S"}  # S = String型
        ],
        BillingMode="PAY_PER_REQUEST"  # オンデマンド課金
    )
    
    # テーブルを返す
    return table
```

**ポイント:**
- `KeySchema`: プライマリキーの定義
  - `HASH`: パーティションキー（必須）
  - `RANGE`: ソートキー（オプション）
- `AttributeDefinitions`: キーで使う属性の型定義
  - `S`: String（文字列）
  - `N`: Number（数値）
  - `B`: Binary（バイナリ）
- `BillingMode`: 課金モード
  - `PAY_PER_REQUEST`: オンデマンド（テストではこれを推奨）
  - `PROVISIONED`: プロビジョンド（キャパシティ指定が必要）

---

### 2-2. S3バケットとオブジェクトの作成方法

**S3バケットの作成:**

```python
import boto3
from moto import mock_aws

with mock_aws():
    s3 = boto3.client("s3", region_name="ap-northeast-1")
    
    # バケット作成（ap-northeast-1 リージョン）
    s3.create_bucket(
        Bucket="my-upload-bucket",
        CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
    )
    
    # オブジェクト配置
    s3.put_object(
        Bucket="my-upload-bucket",
        Key="uploads/report.pdf",
        Body=b"test content",  # ファイルの中身（バイト列）
        ContentType="application/pdf"  # MIMEタイプ
    )
```

**ポイント:**
- `CreateBucketConfiguration` は `us-east-1` 以外のリージョンで必須
- `Body` はバイト列（`b"..."`）で指定
- `ContentType` を設定すると、`head_object` で取得できる

---

### 2-3. 環境変数の設定方法

**monkeypatchを使った環境変数の設定:**

```python
def test_example(monkeypatch):
    monkeypatch.setenv("FILES_TABLE", "files_table")
    
    # 以降、os.environ["FILES_TABLE"] は "files_table" になる
    import os
    assert os.environ["FILES_TABLE"] == "files_table"
```

**複数の環境変数を設定:**

```python
def test_example(monkeypatch):
    monkeypatch.setenv("FILES_TABLE", "files_table")
    monkeypatch.setenv("AWS_REGION", "ap-northeast-1")
```

---

### 2-4. boto3クライアントの差し替え方法

`file_recorder.py` はモジュールレベルでboto3クライアントを初期化しています：

```python
_dynamodb = boto3.resource("dynamodb")
_s3 = boto3.client("s3")
```

これらをmotoのモッククライアントに差し替える必要があります。

**差し替え方法:**

```python
import file_recorder
import boto3
from moto import mock_aws

with mock_aws():
    # モッククライアントを作成
    mock_dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    mock_s3 = boto3.client("s3", region_name="ap-northeast-1")
    
    # file_recorder モジュールのグローバル変数を差し替え
    monkeypatch.setattr(file_recorder, "_dynamodb", mock_dynamodb)
    monkeypatch.setattr(file_recorder, "_s3", mock_s3)
    
    # これ以降、file_recorder._dynamodb と file_recorder._s3 はモックになる
```

---

### 2-5. 課題1の実装ステップ（test_records_new_file）

**ステップ1: fixtureを作成**

```python
import pytest
import boto3
from moto import mock_aws
import file_recorder

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
            BillingMode="PAY_PER_REQUEST"
        )
        
        # S3バケットを作成
        s3 = boto3.client("s3", region_name="ap-northeast-1")
        s3.create_bucket(
            Bucket="my-upload-bucket",
            CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
        )
        
        # S3にオブジェクトを配置
        s3.put_object(
            Bucket="my-upload-bucket",
            Key="uploads/report.pdf",
            Body=b"test content",
            ContentType="application/pdf"
        )
        
        # 環境変数を設定
        monkeypatch.setenv("FILES_TABLE", "files_table")
        
        # boto3クライアントを差し替え
        monkeypatch.setattr(file_recorder, "_dynamodb", dynamodb)
        monkeypatch.setattr(file_recorder, "_s3", s3)
        
        # テストに渡すデータ
        yield {
            "table": table,
            "dynamodb": dynamodb,
            "s3": s3
        }
```

**ステップ2: テスト関数を実装**

```python
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
    
    # DynamoDBを検証
    table = mock_aws_services["table"]
    stored = table.get_item(Key={"file_id": "my-upload-bucket#uploads/report.pdf"})
    
    assert "Item" in stored
    item = stored["Item"]
    assert item["file_id"] == "my-upload-bucket#uploads/report.pdf"
    assert item["bucket"] == "my-upload-bucket"
    assert item["key"] == "uploads/report.pdf"
    assert item["size"] == 102400
```

---

### 2-6. 課題2の実装ステップ（test_skips_duplicate_file）

**ステップ1: 既存レコードを投入**

```python
def test_skips_duplicate_file(mock_aws_services):
    """重複ファイルのイベントで処理がスキップされる"""
    table = mock_aws_services["table"]
    
    # 既存レコードを投入
    table.put_item(Item={
        "file_id": "my-upload-bucket#uploads/report.pdf",
        "bucket": "my-upload-bucket",
        "key": "uploads/report.pdf",
        "size": 102400,
        "content_type": "application/pdf",
        "uploaded_at": "2025-03-01T09:00:00.000Z"
    })
    
    # イベントを読み込む
    event = load_event("s3_put_event.json")
    
    # Lambda関数を実行
    response = file_recorder.lambda_handler(event, context=None)
    
    # レスポンスを検証
    assert response["statusCode"] == 200
    
    body = json.loads(response["body"])
    assert body["message"] == "File already recorded"
    
    # DynamoDBを検証（変更されていないことを確認）
    stored = table.get_item(Key={"file_id": "my-upload-bucket#uploads/report.pdf"})["Item"]
    assert stored["uploaded_at"] == "2025-03-01T09:00:00.000Z"  # 元の値のまま
```

---

## レベル3: デバッグヒント

### 3-1. よくあるエラーと解決方法

#### エラー1: KeyError: 'Records'

```
KeyError: 'Records'
```

**原因:**
- イベントの構造が正しくない
- `load_event()` で読み込んだJSONが期待と違う

**解決方法:**
```python
# イベントの中身を確認
event = load_event("s3_put_event.json")
print(json.dumps(event, indent=2))
```

#### エラー2: RuntimeError: FILES_TABLE environment variable is required

```
RuntimeError: FILES_TABLE environment variable is required
```

**原因:**
- 環境変数 `FILES_TABLE` が設定されていない

**解決方法:**
```python
# fixtureで環境変数を設定
monkeypatch.setenv("FILES_TABLE", "files_table")
```

#### エラー3: ClientError: The specified bucket does not exist

```
botocore.exceptions.ClientError: The specified bucket does not exist
```

**原因:**
- S3バケットが作成されていない
- または、Lambda関数がモックのS3クライアントを使っていない

**解決方法:**
```python
# S3バケットを作成
s3 = boto3.client("s3", region_name="ap-northeast-1")
s3.create_bucket(
    Bucket="my-upload-bucket",
    CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
)

# boto3クライアントを差し替え
monkeypatch.setattr(file_recorder, "_s3", s3)
```

#### エラー4: ResourceNotFoundException: Requested resource not found

```
botocore.exceptions.ClientError: Requested resource not found
```

**原因:**
- DynamoDBテーブルが作成されていない
- または、テーブル名が間違っている

**解決方法:**
```python
# テーブル名を確認
print(os.environ["FILES_TABLE"])  # => "files_table"

# テーブルが作成されているか確認
tables = list(dynamodb.tables.all())
print([t.name for t in tables])  # => ["files_table"]
```

---

### 3-2. デバッグに便利なコード

**DynamoDBの全レコードを表示:**

```python
def test_example(mock_aws_services):
    table = mock_aws_services["table"]
    
    # 全レコードをスキャン
    response = table.scan()
    items = response["Items"]
    
    print(f"Total items: {len(items)}")
    for item in items:
        print(json.dumps(item, indent=2, default=str))
```

**S3のオブジェクト一覧を表示:**

```python
def test_example(mock_aws_services):
    s3 = mock_aws_services["s3"]
    
    # オブジェクト一覧を取得
    response = s3.list_objects_v2(Bucket="my-upload-bucket")
    
    if "Contents" in response:
        for obj in response["Contents"]:
            print(f"Key: {obj['Key']}, Size: {obj['Size']}")
    else:
        print("No objects found")
```

**S3オブジェクトのメタデータを確認:**

```python
def test_example(mock_aws_services):
    s3 = mock_aws_services["s3"]
    
    # メタデータを取得
    response = s3.head_object(
        Bucket="my-upload-bucket",
        Key="uploads/report.pdf"
    )
    
    print(f"ContentType: {response.get('ContentType')}")
    print(f"ContentLength: {response.get('ContentLength')}")
```

---

### 3-3. pytest の便利なオプション

**詳細な出力を表示:**
```bash
pytest tests/ -v
```

**print文を表示:**
```bash
pytest tests/ -s
```

**特定のテストだけ実行:**
```bash
pytest tests/test_file_recorder.py::test_records_new_file -v
```

**失敗したテストで止まる:**
```bash
pytest tests/ -x
```

**詳細なトレースバックを表示:**
```bash
pytest tests/ --tb=long
```

---

## まとめ

**ヒントの活用方法:**
1. まず自分で考える（10分）
2. レベル1を読む（基礎知識の確認）
3. レベル2を読む（実装ステップの確認）
4. レベル3を読む（デバッグ方法の確認）
5. それでも分からなければ質問する

**重要なポイント:**
- `mock_aws()` のコンテキスト内でAWSリソースを作成する
- boto3クライアントを `monkeypatch.setattr()` で差し替える
- S3オブジェクトを事前に配置する（`put_object`）
- 環境変数を設定する（`monkeypatch.setenv`）

頑張ってください！🎉

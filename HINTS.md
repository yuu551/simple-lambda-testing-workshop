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

#### DynamoDBとは？

DynamoDBは、AWSが提供するNoSQLデータベースです。

**従来のリレーショナルDB（MySQL、PostgreSQLなど）との違い:**
- テーブル間の結合（JOIN）がない
- スキーマが柔軟（自由に属性を追加できる）
- 高速で自動スケールする

**基本概念:**
- **テーブル**: データの保存場所（MySQLのテーブルと似ている）
- **Item**: 1件のレコード（MySQLの行と似ている）
- **Attribute**: 項目（MySQLの列と似ている）
- **Primary Key**: データを一意に識別するキー（必須）

#### 今回のワークショップで作るテーブル

このワークショップでは、**S3にアップロードされたファイルのメタデータを記録するテーブル**を作成します。

**テーブル名:** `files_table`

**保存するデータの例:**
```python
{
    "file_id": "my-upload-bucket#uploads/report.pdf",  # プライマリキー
    "bucket": "my-upload-bucket",                      # S3バケット名
    "key": "uploads/report.pdf",                       # S3オブジェクトキー
    "size": 102400,                                     # ファイルサイズ（バイト）
    "content_type": "application/pdf",                 # MIMEタイプ
    "uploaded_at": "2025-03-01T10:30:00.000Z"          # アップロード日時
}
```

**file_id の設計:**
- 形式: `{bucket}#{key}`（例: `my-upload-bucket#uploads/report.pdf`）
- なぜこの形式？
  - 同じファイル名でも、バケットが違えば別のファイル
  - バケット名とキーを組み合わせて一意なIDを作る
  - `#` で区切ることで、後から分解できる

**重複チェックの仕組み:**
1. Lambda関数がS3イベントを受信
2. `file_id` を生成（例: `my-upload-bucket#uploads/report.pdf`）
3. DynamoDBで `get_item` を実行
4. 既にレコードが存在する → 処理をスキップ
5. レコードが存在しない → 新規作成

#### テーブル作成のコード

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

#### パラメータの詳細

**KeySchema: プライマリキーの定義**
- `HASH`: パーティションキー（必須）
  - データを一意に識別するキー
  - 今回は `file_id` を使用
- `RANGE`: ソートキー（オプション）
  - 同じパーティションキー内でデータを並べるキー
  - 今回は使用しない

**AttributeDefinitions: キーで使う属性の型定義**
- `S`: String（文字列）
- `N`: Number（数値）
- `B`: Binary（バイナリ）
- **重要:** プライマリキーで使う属性のみ定義する
  - `bucket`, `key`, `size` などは定義不要（自由に追加できる）

**BillingMode: 課金モード**
- `PAY_PER_REQUEST`: オンデマンド課金
  - 使った分だけ課金
  - テストではこれを推奨（シンプル）
- `PROVISIONED`: プロビジョンド課金
  - 事前にキャパシティを指定
  - 本番環境で使うことが多い

#### テストでの注意点

**moto では実際のAWSに接続しない:**
- テーブルはメモリ上に作られる
- `with mock_aws():` のブロックを抜けると消える
- 課金は一切発生しない

**テーブル名は環境変数と一致させる:**
```python
# テーブル作成
table = dynamodb.create_table(TableName="files_table", ...)

# 環境変数設定
monkeypatch.setenv("FILES_TABLE", "files_table")
```

**実装例（fixtureで使う場合）:**
```python
@pytest.fixture
def mock_aws_services(monkeypatch):
    with mock_aws():
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        
        # テーブル作成
        table = dynamodb.create_table(
            TableName="files_table",
            KeySchema=[{"AttributeName": "file_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "file_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST"
        )
        
        # 環境変数設定
        monkeypatch.setenv("FILES_TABLE", "files_table")
        
        # boto3クライアントを差し替え
        monkeypatch.setattr(file_recorder, "_dynamodb", dynamodb)
        
        yield {"table": table, "dynamodb": dynamodb}
```

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

#### なぜ差し替えが必要？

`file_recorder.py` はモジュールレベルでboto3クライアントを初期化しています。

```python
_dynamodb = boto3.resource("dynamodb")
_s3 = boto3.client("s3")
```

このままだとテスト実行時に**実際のAWS**に接続しようとします。motoのモックを使うには、これらを差し替える必要があります。

#### 差し替え方法

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

#### 差し替え後の動作

差し替えたクライアントは、Lambda関数内部で自動的に使われます。

**Lambda関数内部（file_recorder.py）:**
```python
def lambda_handler(event, context):
    # 環境変数からテーブル名を取得
    table_name = os.environ.get("FILES_TABLE")
    
    # ここで差し替えた _dynamodb が使われる
    table = _dynamodb.Table(table_name)  # ← motoのモックテーブル
    
    # get_itemもモックで動作
    existing = table.get_item(Key={"file_id": file_id})  # ← メモリ上のデータにアクセス
    
    # S3もモックで動作
    metadata = _s3.head_object(Bucket=bucket, Key=key)  # ← motoのモックS3
```

#### テスト内での検証方法

fixtureで差し替えたクライアントとテスト内で使うクライアントは**同じインスタンス**です。

```python
@pytest.fixture
def mock_aws_services(monkeypatch):
    with mock_aws():
        # モッククライアントを作成
        dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
        table = dynamodb.create_table(...)
        
        # 差し替え
        monkeypatch.setattr(file_recorder, "_dynamodb", dynamodb)
        
        # テストに渡す
        yield {"table": table, "dynamodb": dynamodb}

def test_example(mock_aws_services):
    # Lambda関数を実行
    response = file_recorder.lambda_handler(event, context=None)
    
    # 同じテーブルインスタンスで検証できる
    table = mock_aws_services["table"]
    stored = table.get_item(Key={"file_id": "my-upload-bucket#uploads/report.pdf"})
    
    # Lambda関数が書き込んだデータを取得できる
    assert "Item" in stored
```

**ポイント:**
- fixtureで差し替えたクライアント = Lambda関数内で使われるクライアント
- 同じメモリ上のデータにアクセスしている
- だからテスト内でLambda関数の実行結果を検証できる

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

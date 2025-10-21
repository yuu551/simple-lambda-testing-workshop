# 演習課題

このドキュメントでは、`tests/test_file_recorder.py` に実装する2つのテスト関数の詳細を説明します。

## 演習の目的

この演習では、以下のスキルを習得します。

1. **AWS Lambda のユニットテスト** - motoを使った実践的なテスト手法
2. **S3イベント駆動システムのテスト** - S3 Putイベントの検証
3. **外部サービスのモック** - DynamoDBとS3のモック化
4. **重複処理の防止** - file_idによるべき等性の実装

## 演習の進め方

### 推奨学習フロー

```
1. この EXERCISE.md を読む（いま！）
   ↓
2. DESIGN.md でシステム全体を理解する
   ↓
3. samples/ ディレクトリのイベントファイルを確認
   ↓
4. 課題1から順番に実装
   ↓
5. 詰まったら HINTS.md を参照
   ↓
6. pytest で動作確認
   ↓
7. 次の課題へ
```

### 実装順序

必ず以下の順番で進めてください。

1. 課題1: test_records_new_file（基礎）
2. 課題2: test_skips_duplicate_file（応用）

---

## samples/ ディレクトリについて

### S3イベント形式とは

S3は、ファイルがアップロードされた時に以下のようなJSON形式でLambda関数にイベントを渡します。

```json
{
  "Records": [
    {
      "eventName": "ObjectCreated:Put",
      "s3": {
        "bucket": {
          "name": "バケット名"
        },
        "object": {
          "key": "ファイルパス",
          "size": ファイルサイズ
        }
      }
    }
  ]
}
```

**重要なポイント:**
- `Records` は配列形式（複数のイベントをまとめて送信できる）
- `s3.bucket.name` にS3バケット名が入る
- `s3.object.key` にファイルパスが入る
- `s3.object.size` にファイルサイズ（バイト）が入る

### 利用可能なイベントファイル

`samples/` ディレクトリには、2つのサンプルイベントが用意されています。

#### 1. s3_put_event.json - 通常のファイルアップロード

**用途:** 小さいファイル（PDFなど）がアップロードされた時のイベント

```json
{
  "Records": [
    {
      "eventName": "ObjectCreated:Put",
      "s3": {
        "bucket": {
          "name": "my-upload-bucket"
        },
        "object": {
          "key": "uploads/report.pdf",
          "size": 102400
        }
      }
    }
  ]
}
```

**フィールドの説明:**
- `bucket.name`: `"my-upload-bucket"`（S3バケット名）
- `object.key`: `"uploads/report.pdf"`（ファイルパス）
- `object.size`: `102400`（100KB）

**このイベントで何が起こる？**
1. Lambda関数がイベントを受信
2. file_id = `"my-upload-bucket#uploads/report.pdf"` を生成
3. DynamoDBに新しいレコードを作成
4. S3から `head_object` でメタデータ取得（Content-Type など）
5. DynamoDBに保存

#### 2. s3_large_file_event.json - 大きいファイルのアップロード

**用途:** 動画ファイルなど、マルチパートアップロードで送信された時のイベント

```json
{
  "Records": [
    {
      "eventName": "ObjectCreated:CompleteMultipartUpload",
      "s3": {
        "bucket": {
          "name": "my-upload-bucket"
        },
        "object": {
          "key": "uploads/large-video.mp4",
          "size": 524288000
        }
      }
    }
  ]
}
```

**フィールドの説明:**
- `bucket.name`: `"my-upload-bucket"`
- `object.key`: `"uploads/large-video.mp4"`
- `object.size`: `524288000`（500MB）

**このイベントで何が起こる？**
- 基本的には `s3_put_event.json` と同じ処理
- eventName が `CompleteMultipartUpload` になっているだけ
- Lambda関数は eventName に関係なく同じ処理を実行

### load_event() 関数の使い方

`tests/test_file_recorder.py` には、サンプルイベントを読み込むための便利な関数が用意されています：

```python
def load_event(name: str) -> dict:
    """samples/ ディレクトリからイベントJSONファイルを読み込む"""
    return json.loads((SAMPLES_DIR / name).read_text(encoding="utf-8"))
```

**基本的な使い方:**

```python
# s3_put_event.json を読み込む
event = load_event("s3_put_event.json")

# これで event には上記のJSONデータが辞書として入る
print(event["Records"][0]["s3"]["bucket"]["name"])  # => "my-upload-bucket"
print(event["Records"][0]["s3"]["object"]["key"])    # => "uploads/report.pdf"
```

### イベントの編集方法

テストによっては、イベントの内容を編集する必要があります。

**例1: バケット名を変更する**

```python
event = load_event("s3_put_event.json")

# バケット名を変更
event["Records"][0]["s3"]["bucket"]["name"] = "test-bucket"

# この状態で lambda_handler に渡すと、bucket="test-bucket" として処理される
```

**例2: ファイルサイズを変更する**

```python
event = load_event("s3_put_event.json")

# サイズを変更
event["Records"][0]["s3"]["object"]["size"] = 999999

# この状態で lambda_handler に渡すと、size=999999 として処理される
```

**重要:** イベントを編集しても、元のJSONファイルには影響しません。メモリ上のデータだけが変更されます。

---

## 課題1: test_records_new_file（基礎）

### 難易度と所要時間
- **難易度**: ★☆☆（基礎）
- **所要時間**: 約15分

### 目的

新規ファイルのアップロードイベント（S3 Put）を処理したときに、DynamoDBに正しくレコードが保存されることを検証します。

これはLambda関数の**最も基本的な動作**をテストする課題です。

### 使用するサンプルイベント

`samples/s3_put_event.json` を使用します。

このイベントは：
- bucket: `"my-upload-bucket"`
- key: `"uploads/report.pdf"`
- size: `102400`（100KB）

### 実装すべきテストケース

以下の4つを検証してください：

#### 1. Lambda関数が正常に実行される

```python
assert response["statusCode"] == 200
```

#### 2. レスポンスボディに成功メッセージが含まれる

```python
body = json.loads(response["body"])
assert body["message"] == "File recorded successfully"
assert "file_id" in body
```

#### 3. DynamoDBにレコードが作成される

```python
table = mock_aws_services["table"]
stored = table.get_item(Key={"file_id": "my-upload-bucket#uploads/report.pdf"})
assert "Item" in stored  # レコードが存在する
```

#### 4. 保存されたデータの各フィールドが正しい

```python
item = stored["Item"]
assert item["file_id"] == "my-upload-bucket#uploads/report.pdf"
assert item["bucket"] == "my-upload-bucket"
assert item["key"] == "uploads/report.pdf"
assert item["size"] == 102400
assert "content_type" in item
assert "uploaded_at" in item
```

### 期待される動作フロー

```
1. load_event("s3_put_event.json") でイベントを読み込む
   ↓
2. file_recorder.lambda_handler(event, context=None) を実行
   ↓
3. Lambda内部の処理:
   - イベントを検証
   - file_id = "my-upload-bucket#uploads/report.pdf" を生成
   - DynamoDBで重複チェック（レコードなし）
   - S3から head_object でメタデータ取得
   - DynamoDBに新規レコードを作成
   ↓
4. レスポンスを返す（statusCode: 200）
   ↓
5. テストコードでDynamoDBを確認
   - レコードが作成されている
   - 各フィールドが正しい値
```

### 実装チェックリスト

実装を進める際に、以下を確認してください。

- [ ] `@pytest.fixture` で `mock_aws_services` を定義した
- [ ] `with mock_aws():` のコンテキスト内でAWSリソースを作成した
- [ ] DynamoDBテーブルを作成した（テーブル名: `files_table`）
- [ ] S3バケットを作成した
- [ ] S3にテスト用オブジェクトを配置した（`put_object`）
- [ ] 環境変数を設定した（`FILES_TABLE`）
- [ ] `monkeypatch.setattr()` で boto3クライアントを差し替えた
- [ ] `load_event("s3_put_event.json")` でイベントを読み込んだ
- [ ] `lambda_handler(event, context=None)` を実行した
- [ ] レスポンスのstatusCodeとbodyを検証した
- [ ] DynamoDBから `get_item()` でデータを取得して検証した

### HINTS.md 参照先

詰まったら、以下のヒントを参照してください：

- **レベル1**: motoの基本、fixtureの使い方、monkeypatchの使い方
- **レベル2 ヒント2-1**: DynamoDBテーブルの作成方法
- **レベル2 ヒント2-2**: S3バケットとオブジェクトの作成方法
- **レベル2 ヒント2-3**: 環境変数の設定方法
- **レベル2 ヒント2-4**: boto3クライアントの差し替え方法
- **レベル2 ヒント2-5**: このテストの実装ステップ詳細

### つまずきやすいポイント

#### ポイント1: boto3クライアントの差し替え

`file_recorder.py` はモジュールレベルで boto3 クライアントを初期化しています。

```python
_dynamodb = boto3.resource("dynamodb")
_s3 = boto3.client("s3")
```

これらを moto のモッククライアントに差し替える必要があります。

#### ポイント2: S3オブジェクトの事前配置

Lambda関数内で `_s3.head_object(Bucket=bucket, Key=key)` を呼び出しています。

このため、テスト前にS3バケットとオブジェクトを作成しておく必要があります。

```python
s3 = boto3.client("s3", region_name="ap-northeast-1")
s3.create_bucket(
    Bucket="my-upload-bucket",
    CreateBucketConfiguration={"LocationConstraint": "ap-northeast-1"}
)
s3.put_object(
    Bucket="my-upload-bucket",
    Key="uploads/report.pdf",
    Body=b"test content",
    ContentType="application/pdf"
)
```

#### ポイント3: 環境変数の設定

`FILES_TABLE` 環境変数が必須です。設定しないとエラーになります。

---

## 課題2: test_skips_duplicate_file（応用）

### 難易度と所要時間
- **難易度**: ★★☆（応用）
- **所要時間**: 約15分

### 目的

同じファイルのアップロードイベントを2回受信した場合、2回目は処理をスキップし、DynamoDBが更新されないことを検証します。

これは**重複イベント処理の防止**（べき等性）を実装する重要な課題です。

### 使用するサンプルイベント

`samples/s3_put_event.json` をそのまま使用します。

### シナリオ設定

#### 前提条件
- DynamoDBには既に同じfile_idのレコードが存在する
- file_id: `"my-upload-bucket#uploads/report.pdf"`

#### 受信イベント
- 同じファイルのアップロードイベント（2回目）

#### 期待される結果
- 重複なので処理をスキップ
- DynamoDBのレコードは変更されない
- "File already recorded" というメッセージが返る

### 実装すべきテストケース

以下の3つを検証してください：

#### 1. 既存レコードをDynamoDBに投入

```python
table = mock_aws_services["table"]

table.put_item(Item={
    "file_id": "my-upload-bucket#uploads/report.pdf",
    "bucket": "my-upload-bucket",
    "key": "uploads/report.pdf",
    "size": 102400,
    "content_type": "application/pdf",
    "uploaded_at": "2025-03-01T09:00:00.000Z"
})
```

#### 2. レスポンスで「already recorded」が返される

```python
response = file_recorder.lambda_handler(event, context=None)
body = json.loads(response["body"])

assert response["statusCode"] == 200
assert body["message"] == "File already recorded"
```

#### 3. DynamoDBのレコードが変更されていない

```python
stored = table.get_item(Key={"file_id": "my-upload-bucket#uploads/report.pdf"})["Item"]

# 元のデータが保持されていることを確認
assert stored["uploaded_at"] == "2025-03-01T09:00:00.000Z"  # 更新されていない
```

### 期待される動作フロー

```
1. テスト開始前に既存レコードをDynamoDBに投入
   ↓
2. load_event("s3_put_event.json") でイベントを読み込む
   ↓
3. file_recorder.lambda_handler(event, context=None) を実行
   ↓
4. Lambda内部の処理:
   - file_id = "my-upload-bucket#uploads/report.pdf" を生成
   - DynamoDBで重複チェック → レコードあり
   - 処理をスキップ（No-Op）
   - "File already recorded" レスポンスを返す
   ↓
5. DynamoDBを確認
   - レコードが変更されていない
```

### 実装チェックリスト

- [ ] fixture でDynamoDBテーブルと環境変数を設定した
- [ ] テスト開始前に既存レコードを `put_item()` で投入した
- [ ] `load_event("s3_put_event.json")` でイベントを読み込んだ
- [ ] `lambda_handler()` を実行した
- [ ] レスポンスで `message == "File already recorded"` を確認した
- [ ] DynamoDBから `get_item()` でレコードを再取得した
- [ ] `uploaded_at` が変更されていないことを確認した

### HINTS.md 参照先

- **レベル2 ヒント2-6**: このテストの実装ステップ詳細
- **DESIGN.md**: 重複チェックの仕組み（「重複チェックの仕組み」セクション）

### つまずきやすいポイント

#### ポイント1: 既存レコードの投入

テストの前提条件として、DynamoDBに既存レコードを投入する必要があります。`put_item()` を使います。

#### ポイント2: uploaded_atフィールド

同じfile_idのレコードが既に存在する場合、Lambda関数は処理をスキップします。

`uploaded_at` フィールドが元の値のまま保持されていることを確認することで、レコードが更新されていないことを検証できます。

---

## 発展課題（時間がある場合）

全ての課題を完了した方は、以下の発展課題に挑戦してみてください。

### 発展1: s3_large_file_event.json を使ったテストを追加

**課題:**
`samples/s3_large_file_event.json` を使って、大きいファイルのアップロードイベントのテストを追加してください。

**検証項目:**
- file_id が正しく生成される（`my-upload-bucket#uploads/large-video.mp4`）
- size が正しく保存される（`524288000`）
- content_type が正しく取得される

### 発展2: 環境変数未設定時のエラーハンドリングをテスト

**課題:**
`FILES_TABLE` 環境変数が未設定の場合、適切なエラーが発生することをテストしてください。

**ヒント:**
- fixtureで環境変数を設定しない
- `pytest.raises(RuntimeError)` を使う

```python
def test_missing_files_table_env():
    # FILES_TABLE を設定しない
    with pytest.raises(RuntimeError, match="FILES_TABLE"):
        file_recorder.lambda_handler(event, context=None)
```

### 発展3: 不正なイベント構造のテスト

**課題:**
S3イベントの構造が不正な場合、適切なエラーが発生することをテストしてください。

**ヒント:**
- イベントから `Records` フィールドを削除
- `pytest.raises(ValueError)` を使う

```python
def test_invalid_event_structure():
    event = {"invalid": "structure"}
    with pytest.raises(ValueError, match="Invalid S3 event structure"):
        file_recorder.lambda_handler(event, context=None)
```

---

## デバッグのコツ

**print文を活用:**

```python
def test_records_new_file(mock_aws_services):
    event = load_event("s3_put_event.json")
    print(f"Event: {json.dumps(event, indent=2)}")  # イベント内容を確認
    
    response = file_recorder.lambda_handler(event, context=None)
    print(f"Response: {json.dumps(response, indent=2)}")  # レスポンスを確認
```

**DynamoDBの内容を確認:**

```python
table = mock_aws_services["table"]
stored = table.get_item(Key={"file_id": "my-upload-bucket#uploads/report.pdf"})
print(f"Stored: {json.dumps(stored, indent=2, default=str)}")
```

**pytest の -s オプションを使う:**

```bash
pytest tests/test_file_recorder.py::test_records_new_file -v -s
```

これでprint文の出力が表示されます。

---

## 次のステップ

この演習を完了したら：

1. **legacy-lambda-testing-workshop に挑戦**
   - より複雑なEventBridge + DynamoDB + SNS構成
   - バージョン管理、履歴管理
   - SNS通知のテスト

2. **カバレッジを測定**
   ```bash
   pytest tests/ --cov=src --cov-report=html
   open htmlcov/index.html
   ```

3. **CI/CDに統合**
   - GitHub Actions でテストを自動実行
   - プルリクエスト時にテストを実行

おつかれさまでした！🎉

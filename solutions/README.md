# 解答例（Solutions）

このディレクトリには、演習課題の解答例が含まれています。

## 注意事項

⚠️ **このディレクトリは演習中は見ないでください！**

- まず自分で考えて実装してみましょう
- 詰まったら `HINTS.md` を参照しましょう
- それでも分からない場合に、この解答例を参照してください

## ファイル

### test_file_recorder_solution.py

`tests/test_file_recorder.py` の完成版です。

**含まれるテスト:**
1. `test_records_new_file` - 新規ファイルの記録
2. `test_skips_duplicate_file` - 重複ファイルのスキップ

## 実行方法

```bash
# 解答例のテストを実行
pytest solutions/test_file_recorder_solution.py -v

# カバレッジ付きで実行
pytest solutions/test_file_recorder_solution.py --cov=src --cov-report=term-missing
```

## 学習のポイント

### ポイント1: fixtureの使い方

```python
@pytest.fixture
def mock_aws_services(monkeypatch):
    with mock_aws():
        # セットアップ処理
        yield {...}  # テストに渡すデータ
```

- `yield` を使うことで、セットアップと後片付けを明確に分離
- 複数のAWSサービスをまとめてセットアップ
- `monkeypatch` で環境変数やグローバル変数を差し替え

### ポイント2: motoの使い方

```python
with mock_aws():
    dynamodb = boto3.resource("dynamodb", region_name="ap-northeast-1")
    # この中では boto3 が偽物のAWSに接続される
```

- `mock_aws()` のコンテキスト内でAWSリソースを作成
- `region_name` の指定は必須
- `with` ブロックを抜けると、すべてのデータは消える

### ポイント3: boto3クライアントの差し替え

```python
monkeypatch.setattr(file_recorder, "_dynamodb", dynamodb)
monkeypatch.setattr(file_recorder, "_s3", s3)
```

- グローバル変数を `monkeypatch.setattr()` で差し替え
- モジュール名とグローバル変数名を指定
- この差し替えにより、`file_recorder.lambda_handler()` がモックのAWSを使うようになる

### ポイント4: S3オブジェクトの事前配置

```python
s3.put_object(
    Bucket="my-upload-bucket",
    Key="uploads/report.pdf",
    Body=b"test content",
    ContentType="application/pdf"
)
```

- `file_recorder.py` 内で `head_object()` を呼び出しているため、事前にオブジェクトを配置する必要がある
- `Body` はバイト列（`b"..."`）で指定
- `ContentType` を設定することで、`head_object()` で取得できる

## よくある質問

### Q1: fixtureを各テストで定義できないの？

A: できますが、重複コードが増えます。共通のセットアップはfixtureにまとめることで、テストコードがシンプルになります。

### Q2: mock_aws() はどこまでモック化するの？

A: `with mock_aws():` ブロック内で作成された boto3 クライアントのみがモック化されます。ブロック外のクライアントは実際のAWSに接続しようとします。

### Q3: 環境変数はテスト後にリセットされる？

A: pytest の `monkeypatch` は自動的にリセットしてくれます。テストごとに独立した環境が作られるので安心してください。

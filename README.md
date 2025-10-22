# Lambda関数へのテスト追加ワークショップ（入門編）

## 目的
Lambda関数が初めての方向けに、シンプルなS3→Lambda→DynamoDB構成でユニットテストの書き方を学ぶワークショップです。pytestとmotoを使った実践的なテスト手法を身につけます。

## 学習目標
- S3イベントをトリガーとするLambda関数の理解
- boto3を使ったAWSサービス連携のテスト方法
- motoを使ったAWSサービスのモック化
- イベント駆動システムにおける重複処理の防止
- テストしづらいコードの特徴とその対処法

## フォルダ構成
```
simple-lambda-testing-workshop/
├── README.md                 # このファイル
├── DESIGN.md                 # 設計ドキュメント（アーキテクチャ、データモデル）
├── EXERCISE.md              # 演習課題の詳細
├── HINTS.md                 # 段階的なヒント集
├── requirements-dev.txt     # Python依存パッケージ
├── src/
│   └── file_recorder.py     # テスト対象のLambda関数
├── tests/
│   ├── conftest.py          # pytest設定
│   └── test_file_recorder.py # テストコード（演習で実装）
└── samples/
    ├── s3_put_event.json             # S3 Putイベント（小さいファイル）
    └── s3_large_file_event.json      # S3 Putイベント（大きいファイル）
```

## 前提条件
- **Git** がインストールされていること
  - インストールが未実施の場合は下記からインストールすること
    - https://git-scm.com/
- **Python 3.11 以降**がインストールされていること
- **pytest基礎、フィクスチャ、モック**の基礎知識があること

## セットアップ

### 1. リポジトリの取得

```bash
# すでにクローン済みの場合
cd simple-lambda-testing-workshop

# 未クローンの場合
git clone https://github.com/yuu551/simple-lambda-testing-workshop.git
cd simple-lambda-testing-workshop
```

### 2. 仮想環境のセットアップ

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements-dev.txt
```

### 3. セットアップの確認

```bash
# pytestが正しくインストールされているか確認
pytest --version

# テストが実行できるか確認（最初はすべてスキップされます）
pytest tests/ -v
```

以下のような出力が表示されればOKです。

```
tests/test_file_recorder.py::test_records_new_file SKIPPED
tests/test_file_recorder.py::test_skips_duplicate_file SKIPPED
```

## ワークショップの流れ

### Phase 1: Lambda関数のデモ
- S3にファイルがアップロードされた時の動作を見る
- Lambda関数のコードを読んで理解する
- テストしづらいポイントを確認する

### Phase 2: 設計資料の理解
1. `DESIGN.md` を開いてアーキテクチャを確認
2. S3 → Lambda → DynamoDB の処理フローを理解
3. テスト観点を確認する（重複チェック、データ保存など）

### Phase 3: テスト実装
1. `EXERCISE.md` を開いて課題を確認
2. `tests/test_file_recorder.py` にテストを実装
   - **課題1**: 新規ファイルの記録（基礎）
   - **課題2**: 重複ファイルのスキップ（応用）
3. 詰まったら `HINTS.md` を参照

### Phase 4: 動作確認と振り返り
1. `pytest tests/ -v` でテストを実行
2. カバレッジを測定（オプション）
   ```bash
   # HTMLレポート生成（推奨）
   pytest --cov=src --cov-report=html
   # ブラウザで htmlcov/index.html を開いて確認
   
   # ターミナルで確認（簡易）
   pytest --cov=src --cov-report=term-missing
   ```
3. 学んだことを共有

## 次のステップ

このワークショップを完了したら、以下に挑戦してください。

### 1. 追加課題に挑戦
より複雑な EventBridge + SNS 構成のワークショップに挑戦します。

**レポジトリURL:** https://github.com/yuu551/lambda-pytest-workshop

```bash
# 別ディレクトリにクローン
cd ..
git clone https://github.com/yuu551/lambda-pytest-workshop.git
cd lambda-pytest-workshop
```

## トラブルシューティング

### motoのインストールエラー

```bash
# アップグレードしてから再インストール
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements-dev.txt
```

### 仮想環境がアクティベートされていない

プロンプトに `(.venv)` が表示されていることを確認してください。

**Windows:**
```bash
.venv\Scripts\activate
```

## 質問・フィードバック

ワークショップ中に疑問点があれば、遠慮なく質問してください！

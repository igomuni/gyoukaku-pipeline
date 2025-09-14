# 行政事業レビューシート データ処理パイプライン API

## 概要

本プロジェクトは、日本の「行政事業レビューシート」の元データ（Excel/ZIP形式）を処理・正規化するための、堅牢なPythonバックエンドサービスです。

FastAPIフレームワークを使用し、フロントエンドアプリケーションが非同期でデータ処理を実行・監視できるRESTful APIを公開します。

## 主な機能

- **非同期パイプライン処理**: 重いデータ処理をバックグラウンドで実行し、APIサーバーの応答性を維持します。
- **多段階のデータ処理**: `Excel/ZIP -> 生CSV -> 正規化済みCSV -> マスターテーブル` の4段階でデータを変換・構築します。
- **柔軟な実行制御**:
    - 特定のステージからの処理再開
    - 処理対象とする入力ファイルの指定
- **堅牢なジョブ管理**:
    - パイプラインの同時実行を抑制
    - 実行中のジョブのステータス追跡
    - 全ジョブ履歴のリスト表示
    - 実行中ジョブの安全なキャンセル機能
- **RESTful API**: 使いやすいAPIエンドポイントと、自動生成される対話的なAPIドキュメント（Swagger UI）を提供します。

## 技術スタック

- **言語**: Python 3.9+
- **フレームワーク**: FastAPI
- **主要ライブラリ**: Uvicorn, Pandas, OpenPyXL, Python-Multipart

## プロジェクト構造

```
/
|-- .gitignore
|-- README.md
|-- main.py            # FastAPIアプリケーションのエントリーポイント
|-- requirements.txt   # 依存ライブラリ
|-- config.py          # 設定ファイル
|-- /data/             # データディレクトリ (Git管理外)
|   |-- download/      # <- 元データ(xlsx/zip)をここに配置
|   |-- raw/
|   |-- normalized/
|   `-- processed/
|-- /models
|   `-- api_models.py    # APIのPydanticモデル
|-- /pipeline
|   |-- manager.py     # ジョブ管理とパイプライン実行
|   `-- stages.py      # 各ステージの処理ロジック
`-- /utils
    `-- normalization.py # 日本語正規化ユーティリティ
```

## セットアップと実行手順

### 1. リポジトリのクローン
```bash
git clone <リポジトリURL>
cd gyoukaku-pipeline
```

### 2. (推奨) 仮想環境の作成と有効化
```bash
# 仮想環境を作成
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. 依存ライブラリのインストール
```bash
pip install -r requirements.txt
```

### 4. ディレクトリの準備
プロジェクトルートに `data` ディレクトリと、その下に `download` ディレクトリを作成してください。
（`raw`, `normalized`, `processed` は初回実行時に自動生成されます）
```bash
mkdir -p data/download
```

### 5. 元データの配置
処理対象となる `.xlsx` または `.zip` ファイルを `data/download` ディレクトリに配置します。

### 6. サーバーの起動
```bash
uvicorn main:app --reload
```

### 7. APIドキュメントへのアクセス
Webブラウザで `http://127.0.0.1:8000/docs` にアクセスすると、対話的なAPIドキュメント（Swagger UI）が表示され、そこから直接APIをテストできます。

## API仕様

### `POST /api/pipeline/run`
パイプラインの実行を開始します。

- **リクエストボディ例 (全ステージ実行):**
  ```json
  {}
  ```
- **リクエストボディ例 (ステージ3から再開):**
  ```json
  {
    "start_stage": 3
  }
  ```
- **リクエストボディ例 (ZIP作成のみ実行):**
  ```json
  {
    "start_stage": 4
  }
  ```
- **レスポンス:**
  ```json
  {
    "job_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "message": "パイプラインの実行を受け付けました。"
  }
  ```

### `GET /api/pipeline/jobs`
全ジョブの一覧を取得します。

### `GET /api/pipeline/status/{job_id}`
指定したジョブの現在のステータスを確認します。処理の完了は、このエンドポイントを定期的にポーリングして検知します。

- **完了時のレスポンス例:**
  ```json
  {
    "job_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "status": "completed",
    "current_stage": "完了",
    "message": "パイプラインは正常に完了しました。",
    "results_url": "/api/results/processed_data_xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx.zip",
    "error_message": null,
    "cancel_requested": false
  }
  ```

### `POST /api/pipeline/cancel/{job_id}`
実行中のジョブのキャンセルを要求します。

### `GET /api/results/{filename}`
完了したジョブの成果物（ZIPファイル）をダウンロードします。
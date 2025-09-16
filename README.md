# 行政事業レビューシート データ処理パイプライン API v1.2.0

## 概要

本プロジェクトは、日本の「行政事業レビューシート」の元データ（Excel/ZIP形式）を処理・正規化するための、堅牢なPythonバックエンドサービスです。

FastAPIフレームワークを使用し、フロントエンドアプリケーションが非同期でデータ処理を実行・監視できるRESTful APIを公開します。

## 主な機能

- **非同期パイプライン処理**: 重いデータ処理をバックグラウンドで実行し、APIサーバーの応答性を維持します。
- **多段階のデータ処理**: `Excel/ZIP -> 生CSV -> 正規化済みCSV -> マスターテーブル -> 予算実績テーブル -> ZIPアーカイブ` の多段階でデータを変換・構築します。
- **堅牢なデータ抽出**:
    - 年度ごとに異なるCSVの列名やフォーマットの揺れを吸収し、統一されたスキーマを持つマスターテーブルを生成します。
    - 複数年度にまたがる複雑な書式の予算・執行関連データを抽出し、事業ごとの時系列（ワイド形式）テーブルを生成します。
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
- **主要ライブラリ**: Uvicorn, Pandas, OpenPyXL

## プロジェクト構造

```
/
|-- .gitignore
|-- LICENSE
|-- README.md
|-- main.py                     # FastAPIアプリケーションのエントリーポイント
|-- requirements.txt            # 依存ライブラリ
|-- config.py                   # 設定ファイル
|-- /analysis/                  # データ分析用のユーティリティスクリプト
|   `-- header_matrix_generator.py
|-- /scripts/                   # 個別のバッチ処理を実行するためのスクリプト
|   |-- extract_budgets.py
|   `-- rerun_normalization.py
|-- /data/
|   |-- download/               # <- 元データ(xlsx/zip)をここに配置
|   |-- raw/                    # (自動生成, Git管理外)
|   |-- normalized/             # (自動生成, Git管理外)
|   `-- processed/              # (自動生成, Git管理外)
|-- /models/
|   `-- api_models.py           # APIのPydanticモデル
|-- /pipeline/
|   |-- budget_processing.py    # << 予算データ抽出の共通ロジック
|   |-- manager.py              # ジョブ管理とパイプライン実行
|   `-- stages.py               # 各ステージの処理ロジック
`-- /utils/
    `-- normalization.py        # 日本語正規化ユーティリティ
```

## セットアップと実行手順

### 1. リポジトリのクローンと仮想環境の作成
```bash
git clone https://github.com/igomuni/gyoukaku-pipeline.git
cd gyoukaku-pipeline
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate  # Windows
```

### 2. 依存ライブラリのインストール
```bash
pip install -r requirements.txt
```

### 3. 元データの配置
処理対象となる `.xlsx` または `.zip` ファイルを `data/download` ディレクトリに配置します。

### 4. サーバーの起動
```bash
uvicorn main:app --reload
```

### 5. APIドキュメントへのアクセス
Webブラウザで `http://127.0.0.1:8000/docs` にアクセスすると、対話的なAPIドキュメントが表示され、APIをテストできます。

## API仕様

### `POST /api/pipeline/run`
パイプラインの実行を開始します。

- **リクエストボディ例 (全ステージ実行):**
  ```json
  {}
  ```
- **リクエストボディ例 (ステージ3: マスター構築から再開):**
  ```json
  {
    "start_stage": 3
  }
  ```
- **リクエストボディ例 (ステージ4: 予算実績構築のみ実行):**
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
指定したジョブの現在のステータスを確認します。

### `POST /api/pipeline/cancel/{job_id}`
実行中のジョブのキャンセルを要求します。

### `GET /api/results/{filename}`
完了したジョブの成果物（ZIPファイル）をダウンロードします。

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
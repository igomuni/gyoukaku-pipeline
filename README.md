# 行政事業レビューシート データ処理パイプライン API v1.3.0

## 概要

本プロジェクトは、日本の「行政事業レビューシート」の元データ（Excel/ZIP形式）を処理・正規化するための、堅牢なPythonバックエンドサービスです。

FastAPIフレームワークを使用し、フロントエンドアプリケーションが非同期でデータ処理を実行・監視できるRESTful APIを公開します。年度ごとに異なる複雑なExcelフォーマットを吸収し、分析に適したクリーンで一貫性のあるテーブルデータセットを生成します。

## 主な機能

- **非同期パイプライン処理**: 重いデータ処理をバックグラウンドで実行し、APIサーバーの応答性を維持します。
- **多段階のデータ処理**: `Excel/ZIP -> 生CSV -> 正規化済みCSV -> 4つのマスターテーブル -> ZIPアーカイブ` の多段階でデータを変換・構築します。
- **堅牢なデータ抽出**:
    - **事業テーブル (`business.csv`)**: 年度ごとに異なる列名やフォーマットの揺れを吸収し、統一されたスキーマを持つマスターテーブルを生成します。
    - **予算テーブル (`budgets.csv`)**: 複数年度にまたがる複雑な書式の予算・執行関連データを抽出し、事業ごとの時系列（ワイド形式）テーブルを生成します。
    - **資金の流れテーブル (`fund_flow.csv`)**: 「費目・使途」ブロックから、資金の流れに関する詳細データを縦持ち形式で抽出します。
    - **支出テーブル (`expenditure.csv`)**: 「支出先上位10者リスト」から、支出先の詳細データを縦持ち形式で抽出します。
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
|-- config.py                   # 設定ファイル (パス定義、マッピング等)
|-- /analysis/                  # データ分析・スキーマ調査用のユーティリティスクリプト
|   |-- expenditure_item_finder.py
|   |-- expenditure_list_item_finder.py
|   `-- header_matrix_generator.py
|-- /scripts/                   # 個別のバッチ処理を実行するためのスクリプト
|   |-- extract_budgets.py
|   |-- extract_expenditures.py
|   `-- rerun_normalization.py
|-- /data/
|   |-- download/               # <- 元データ(xlsx/zip)をここに配置
|   |-- raw/                    # (自動生成, Git管理外)
|   |-- normalized/             # (自動生成, Git管理外)
|   `-- processed/              # (自動生成, Git管理外) 成果物CSVが出力される
|-- /models/
|   `-- api_models.py           # APIのPydanticモデル
|-- /pipeline/
|   |-- budget_processing.py    # 予算テーブル(`budgets.csv`)の構築ロジック
|   |-- business_processing.py  # 事業テーブル(`business.csv`)の構築ロジック
|   |-- expenditure_processing.py # 支出テーブル(`expenditure.csv`)の構築ロジック
|   |-- fund_flow_processing.py # 資金の流れテーブル(`fund_flow.csv`)の構築ロジック
|   |-- manager.py              # ジョブ管理とパイプライン実行制御
|   `-- stages.py               # 各ステージの処理を呼び出す指揮役
`-- /utils/
    `-- normalization.py        # 日本語正規化ユーティリティ
```

## セットアップと実行手順

### 1. リポジトリのクローンと仮想環境の作成
```bash
git clone https://github.com/your_username/gyoukaku-pipeline.git
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
データ処理パイプラインの実行を開始します。

- **リクエストボディ例 (全ステージ実行):**
  ```json
  {}
  ```
- **リクエストボディ例 (ステージ3: 事業テーブル構築から再開):**
  ```json
  {
    "start_stage": 3
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
実行中のジョबのキャンセルを要求します。

### `GET /api/results/{filename}`
完了したジョブの成果物（ZIPファイル）をダウンロードします。

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
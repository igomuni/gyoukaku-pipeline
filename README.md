# 行政事業レビューシート データ処理パイプライン API v1.3.0

## 概要

本プロジェクトは、日本の「行政事業レビューシート」の元データ（Excel/ZIP形式）を処理・正規化するための、堅牢なPythonバックエンドサービスです。

FastAPIフレームワークを使用し、フロントエンドアプリケーションが非同期でデータ処理を実行・監視できるRESTful APIを公開します。
年度ごとに異なる複雑なExcelフォーマットを吸収し、分析に適したクリーンで一貫性のあるテーブルデータセットを生成します。
その生成物を活用して自然言語からSQLを生成するText-to-SQLの実験・評価を行うためのWeb UIツールを提供します。

## 主要機能

### データ処理パイプライン (`main.py`)

- **非同期パイプライン処理**: 重いデータ処理をバックグラウンドで実行し、APIサーバーの応答性を維持します。
- **多段階のデータ処理**: `Excel/ZIP -> 生CSV -> 正規化済みCSV -> 5つのマスターテーブル -> ZIPアーカイブ` の多段階でデータを変換・構築します。
- **堅牢なデータ抽出**:
    - **事業・予算・資金の流れ・支出先**: 年度ごとにフォーマットが異なる複雑なExcelシートから、統一されたスキーマを持つ5つの主要なテーブル (`business.csv`, `budgets.csv`等) を安定して生成します。
- **柔軟な実行制御**: 特定のステージからの処理再開や、処理対象ファイルの指定が可能です。
- **堅牢なジョブ管理**: パイプラインの同時実行抑制、ステータス追跡、安全なキャンセル機能を提供します。
- **RESTful API**: 使いやすいAPIエンドポイントと、自動生成される対話的なAPIドキュメント（Swagger UI）を提供します。

### Text-to-SQL 実験ツール (`text_to_sql_ui/`)

- **高機能なWeb UI**: プロンプトエンジニアリングの試行錯誤を効率化するための、独立したWebアプリケーションです。
- **動的プロンプト生成**: データベースのスキーマを自動で読み込み、外部テンプレートファイル (`prompt_template.txt`) と組み合わせて、LLMに投入するプロンプトを動的に生成します。
- **SQL実行と高度な結果表示**:
    - LLMが生成したSQLを直接実行し、結果を画面に表示します。
    - 結果テーブルは**ソート（並び替え）**、**横スクロール**、**検索**が可能な高機能テーブル（DataTables.net）です。
    - 実行結果はCSV形式でクリップボードにコピー、またはファイルとしてダウンロードが可能です。
- **豊富な履歴管理**:
    - 実行した「質問」「SQL」「結果概要（件数/エラー）」を自動で保存・表示します。
    - 履歴の**全件クリア**、**個別削除**、JSON形式での**インポート/エクスポート**に対応し、実験結果の共有や再現を容易にします。
- **柔軟なレイアウト**: ユーザーがドラッグで自由に調整可能な3カラムリサイザブルレイアウト (`Split.js`) を採用。

## 技術スタック

- **言語**: Python 3.9+
- **フレームワーク**: FastAPI
- **主要ライブラリ**: Uvicorn, Pandas, OpenPyXL, DuckDB, aiosqlite, Jinja2
- **フロントエンド**: Vanilla JavaScript, HTML5, CSS3
- **フロントエンドライブラリ**: DataTables.net, Split.js

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
|-- /utils/
|    `-- normalization.py        # 日本語正規化ユーティリティ
|-- /text_to_sql_app/           # <- SQL分析のコアロジック
|   |-- db_connector.py         # DuckDBへの接続とテーブル構築
|   |-- generate_schema.py      # スキーマ情報をMarkdownで生成
|   `-- run_queries.py          # CUIでのクエリ実行スクリプト
`-- /text_to_sql_ui/            # <- Text-to-SQL 実験ツール (Web UI)
    |-- app.py                  # Web UI用のFastAPIエントリーポイント
    |-- prompt_template.txt     # LLM向けプロンプトのテンプレート
    |-- /static/
    |   |-- main.js             # フロントエンドの全ロジック
    |   `-- style.css           # スタイルシート
    `-- /templates/
        `-- index.html          # UIのHTML構造

```

## データ処理パイプライン (`main.py`)　セットアップと実行手順

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

---

## Text-to-SQL 実験ツール (`text_to_sql_ui/`) 実験ツールの起動

次に、SQL生成の実験を行うためのWeb UIサーバーを起動します。**データパイプラインのサーバーとは別のプロセスです。**

```bash
uvicorn text_to_sql_ui.app:app --reload
```

サーバーが起動したら、ブラウザで `http://127.0.0.1:8000` を開きます。

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
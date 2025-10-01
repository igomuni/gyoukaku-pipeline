# Text-to-SQL 実験ツール (Next.js版)

既存のText-to-SQL実験ツールをNext.jsで再実装したWebアプリケーションです。

## 概要

このプロジェクトは、行政事業レビューシートのデータを活用して自然言語からSQLを生成・評価するためのNext.js版Web UIです。元のPython FastAPI + Vanilla JSアプリケーションと同じ機能を、モダンなReact/Next.jsスタックで提供します。

## 主要機能

- **動的プロンプト生成**: データベースのスキーマを自動で読み込み、外部テンプレートファイルと組み合わせてLLM向けプロンプトを生成
- **SQL実行と高度な結果表示**: LLMが生成したSQLを直接実行し、結果をソート・検索可能な高機能テーブル(DataTables.net)で表示
- **豊富な履歴管理**: 実行した質問・SQL・結果を自動保存。再実行機能、全件クリア、個別削除、JSON形式でのインポート/エクスポートに対応
- **柔軟なレイアウト**: ドラッグで自由に調整可能な3カラムリサイザブルレイアウト(Split.js)

## 技術スタック

- **フレームワーク**: Next.js 15 (App Router)
- **言語**: TypeScript
- **スタイリング**: Tailwind CSS + カスタムCSS
- **UI**: React Hooks
- **データテーブル**: DataTables.net
- **レイアウト**: Split.js

## セットアップと実行

### 1. バックエンドサーバーの起動

このNext.jsアプリケーションは、既存のFastAPIサーバー(`text_to_sql_ui/app.py`)をバックエンドとして使用します。

```bash
# プロジェクトルートで
uvicorn text_to_sql_ui.app:app --reload --port 8001
```

**注意**: バックエンドは`http://localhost:8001`で起動してください。Next.jsの設定でこのポートにプロキシします。

### 2. Next.jsアプリケーションの起動

```bash
cd text-to-sql-nextjs
npm install
npm run dev
```

ブラウザで `http://localhost:3000` を開きます。

## プロジェクト構造

```
text-to-sql-nextjs/
├── app/
│   ├── page.tsx           # メインページコンポーネント
│   ├── globals.css        # グローバルスタイル
│   └── layout.tsx         # ルートレイアウト
├── next.config.ts         # Next.js設定(APIプロキシ含む)
├── package.json
└── README.md
```

## 開発上の注意点

- APIリクエストは`/api/*`パスで行い、Next.jsの`rewrites`設定により`http://localhost:8001/api/*`にプロキシされます
- バックエンドサーバー(FastAPI)が起動していない場合、APIエラーが発生します
- DataTables.netは動的にDOMを操作するため、React管理外のHTML操作を行っています

## 元の実装との違い

- Vanilla JavaScript → React/TypeScript
- Jinja2テンプレート → Next.js App Router (RSC)
- 静的ファイル配信 → Next.jsの最適化された配信
- 状態管理がより明示的に(React Hooks)

## License

MIT License

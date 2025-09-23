データベースのスキーマ情報を生成します...

==================================================
# データベーススキーマ
**テーブル一覧:** `budgets`, `business`, `expenditure`, `fund_flow`, `ministries`

## テーブル: `budgets`

| カラム名 | データ型 |
|---|---|
| `business_id` | `VARCHAR` |
| `予算の状況予備費等_py3` | `VARCHAR` |
| `予算の状況前年度から繰越し_py3` | `VARCHAR` |
| `予算の状況当初予算_py3` | `VARCHAR` |
| `予算の状況翌年度へ繰越し_py3` | `VARCHAR` |
| `予算の状況補正予算_py3` | `VARCHAR` |
| `予算の状況計_py3` | `VARCHAR` |
| `執行率(%)_py3` | `VARCHAR` |
| `執行額_py3` | `VARCHAR` |
| `予算の状況予備費等_py2` | `VARCHAR` |
| `予算の状況前年度から繰越し_py2` | `VARCHAR` |
| `予算の状況当初予算_py2` | `VARCHAR` |
| `予算の状況翌年度へ繰越し_py2` | `VARCHAR` |
| `予算の状況補正予算_py2` | `VARCHAR` |
| `予算の状況計_py2` | `VARCHAR` |
| `執行率(%)_py2` | `VARCHAR` |
| `執行額_py2` | `VARCHAR` |
| `予算の状況予備費等_py1` | `VARCHAR` |
| `予算の状況前年度から繰越し_py1` | `VARCHAR` |
| `予算の状況当初予算_py1` | `VARCHAR` |
| `予算の状況翌年度へ繰越し_py1` | `VARCHAR` |
| `予算の状況補正予算_py1` | `VARCHAR` |
| `予算の状況計_py1` | `VARCHAR` |
| `執行率(%)_py1` | `VARCHAR` |
| `執行額_py1` | `VARCHAR` |
| `予算の状況予備費等` | `VARCHAR` |
| `予算の状況前年度から繰越し` | `VARCHAR` |
| `予算の状況当初予算` | `VARCHAR` |
| `予算の状況翌年度へ繰越し` | `VARCHAR` |
| `予算の状況補正予算` | `VARCHAR` |
| `予算の状況計` | `VARCHAR` |
| `要求予算の状況当初予算_req` | `VARCHAR` |
| `要求予算の状況計_req` | `VARCHAR` |

## テーブル: `business`

| カラム名 | データ型 |
|---|---|
| `business_id` | `VARCHAR` |
| `source_year` | `BIGINT` |
| `ministry_id` | `BIGINT` |
| `府省庁` | `VARCHAR` |
| `事業番号-1` | `VARCHAR` |
| `事業番号-2` | `BIGINT` |
| `事業番号-3` | `BIGINT` |
| `事業番号-4` | `VARCHAR` |
| `事業番号-5` | `VARCHAR` |
| `事業名` | `VARCHAR` |
| `担当部局庁` | `VARCHAR` |
| `作成責任者` | `VARCHAR` |
| `事業開始終了年度` | `VARCHAR` |
| `担当課室` | `VARCHAR` |
| `会計区分` | `VARCHAR` |
| `根拠法令（具体的な条項も記載）` | `VARCHAR` |
| `関係する計画、通知等` | `VARCHAR` |
| `政策` | `VARCHAR` |
| `施策` | `VARCHAR` |
| `政策体系・評価書URL` | `VARCHAR` |
| `主要経費` | `VARCHAR` |
| `事業の目的` | `VARCHAR` |
| `現状・課題` | `VARCHAR` |
| `事業概要` | `VARCHAR` |
| `事業概要URL` | `VARCHAR` |
| `実施方法` | `VARCHAR` |

## テーブル: `expenditure`

| カラム名 | データ型 |
|---|---|
| `business_id` | `VARCHAR` |
| `block_id` | `VARCHAR` |
| `sequence` | `BIGINT` |
| `番号` | `BIGINT` |
| `支出先` | `VARCHAR` |
| `業務概要` | `VARCHAR` |
| `支出額` | `VARCHAR` |
| `入札者数` | `VARCHAR` |
| `落札率` | `VARCHAR` |
| `契約方式` | `VARCHAR` |
| `契約方式等` | `VARCHAR` |
| `法人番号` | `VARCHAR` |
| `一者応札・一者応募又は競争性のない随意契約となった理由及び改善策` | `VARCHAR` |

## テーブル: `fund_flow`

| カラム名 | データ型 |
|---|---|
| `business_id` | `VARCHAR` |
| `block_id` | `VARCHAR` |
| `sequence` | `VARCHAR` |
| `支払先費目` | `VARCHAR` |
| `支払先使途` | `VARCHAR` |
| `支払先金額(百万円)` | `VARCHAR` |
| `支払先計` | `DOUBLE` |

## テーブル: `ministries`

| カラム名 | データ型 |
|---|---|
| `ministry_id` | `BIGINT` |
| `ministry_name` | `VARCHAR` |
==================================================

上記の内容を `schema.md` などのファイルに保存して、LLMのプロンプトに活用することをお勧めします。
例: python text_to_sql_app/generate_schema.py > schema.md

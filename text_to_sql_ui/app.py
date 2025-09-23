import sys
import json
import time
import sqlite3
from pathlib import Path
import pandas as pd
from fastapi import FastAPI, Request, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from typing import List

# --- 親ディレクトリをPythonのパスに追加 ---
sys.path.append(str(Path(__file__).resolve().parent.parent))

# --- 既存の自作モジュールをインポート ---
from text_to_sql_app.db_connector import get_db_connection
from text_to_sql_app.generate_schema import generate_schema_markdown

# --- FastAPIアプリケーションのセットアップ ---
app = FastAPI(
    title="Text-to-SQL 実験ツール",
    description="LLM向けのプロンプト生成、SQL実行、履歴管理を行うためのWeb UIです。",
    version="1.1.0"
)

# パス設定
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
HISTORY_DB_PATH = BASE_DIR.parent / "history.db"
PROMPT_TEMPLATE_PATH = BASE_DIR / "prompt_template.txt"

# 静的ファイルとテンプレートの設定
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# --- データベース履歴管理 ---
def init_history_db():
    with sqlite3.connect(HISTORY_DB_PATH) as con:
        cur = con.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS execution_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                question TEXT,
                sql_query TEXT NOT NULL,
                status TEXT NOT NULL,
                result_json TEXT,
                duration_ms INTEGER NOT NULL
            )
        """)
        con.commit()

# --- APIモデルの定義 ---
class SqlExecutionRequest(BaseModel):
    sql: str
    question: str | None = None

# --- Web UI用エンドポイント ---
@app.get("/", response_class=HTMLResponse, tags=["UI"])
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# --- APIエンドポイント ---
@app.get("/api/get-prompt-template", response_class=JSONResponse, tags=["API"])
async def get_prompt_template():
    schema_md = generate_schema_markdown()
    if not schema_md:
        raise HTTPException(status_code=404, detail="スキーマ情報が見つかりません。")
    try:
        with open(PROMPT_TEMPLATE_PATH, "r", encoding="utf-8") as f:
            base_prompt = f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail=f"プロンプトテンプレートファイルが見つかりません: {PROMPT_TEMPLATE_PATH}")
    prompt_template = base_prompt.replace("{{schema}}", schema_md)
    return {"template": prompt_template}

@app.post("/api/execute-sql", response_class=JSONResponse, tags=["API"])
async def execute_sql(request: SqlExecutionRequest):
    start_time = time.perf_counter()
    status = "success"
    result_data = None
    try:
        duckdb_con = get_db_connection()
        if not duckdb_con:
            raise RuntimeError("DuckDBへの接続に失敗しました。")
        result_df = duckdb_con.execute(request.sql).df()
        duckdb_con.close()
        result_df = result_df.astype(object).where(pd.notna(result_df), None)
        result_data = result_df.to_dict(orient='split')
    except Exception as e:
        status = "error"
        result_data = {"error": str(e)}
    finally:
        duration_ms = int((time.perf_counter() - start_time) * 1000)
        init_history_db()
        with sqlite3.connect(HISTORY_DB_PATH) as history_con:
            history_con.execute(
                "INSERT INTO execution_history (question, sql_query, status, result_json, duration_ms) VALUES (?, ?, ?, ?, ?)",
                (request.question, request.sql, status, json.dumps(result_data), duration_ms)
            )
            history_con.commit()
    if status == "error":
        return JSONResponse(status_code=400, content={"status": "error", "result": result_data, "duration_ms": duration_ms})
    return {"status": "success", "result": result_data, "duration_ms": duration_ms}

# ▼▼▼【ここからが新規・修正点】▼▼▼
@app.get("/api/history", response_class=JSONResponse, tags=["History API"])
async def get_history():
    """実行履歴を新しい順に取得します。"""
    init_history_db()
    with sqlite3.connect(HISTORY_DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM execution_history ORDER BY id DESC").fetchall()
        return JSONResponse(content=[dict(row) for row in rows])

@app.get("/api/history/export", response_class=JSONResponse, tags=["History API"])
async def export_history():
    """全実行履歴をJSONファイルとしてエクスポートします。"""
    init_history_db()
    with sqlite3.connect(HISTORY_DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute("SELECT * FROM execution_history ORDER BY id ASC").fetchall()
        history_data = [dict(row) for row in rows]
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    headers = {
        "Content-Disposition": f"attachment; filename=history_export_{timestamp}.json"
    }
    return JSONResponse(content=history_data, headers=headers)

@app.post("/api/history/import", response_class=JSONResponse, tags=["History API"])
async def import_history(file: UploadFile = File(...)):
    """アップロードされたJSONファイルから履歴をインポートします。"""
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="無効なファイル形式です。JSONファイルをアップロードしてください。")

    content = await file.read()
    try:
        data = json.loads(content)
        if not isinstance(data, list):
            raise ValueError()
    except (json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=400, detail="JSONの解析に失敗しました。ファイルが正しい形式か確認してください。")

    records_to_insert = []
    for item in data:
        records_to_insert.append((
            item.get("question"),
            item.get("sql_query"),
            item.get("status"),
            item.get("result_json"),
            item.get("duration_ms"),
            item.get("timestamp") # タイムスタンプもインポート
        ))
    
    init_history_db()
    with sqlite3.connect(HISTORY_DB_PATH) as con:
        # タイムスタンプの有無でSQLを分岐
        if all(rec[5] is not None for rec in records_to_insert):
             con.executemany(
                "INSERT INTO execution_history (question, sql_query, status, result_json, duration_ms, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                records_to_insert
            )
        else:
             con.executemany(
                "INSERT INTO execution_history (question, sql_query, status, result_json, duration_ms) VALUES (?, ?, ?, ?, ?)",
                [rec[:-1] for rec in records_to_insert] # タイムスタンプを除外
            )
        con.commit()

    return {"message": f"{len(records_to_insert)}件の履歴をインポートしました。"}

@app.delete("/api/history/all", response_class=JSONResponse, tags=["History API"])
async def clear_all_history():
    """全実行履歴を削除します。"""
    init_history_db()
    with sqlite3.connect(HISTORY_DB_PATH) as con:
        con.execute("DELETE FROM execution_history")
        con.commit()
    return {"message": "すべての履歴を削除しました。"}

@app.delete("/api/history/{history_id}", response_class=JSONResponse, tags=["History API"])
async def delete_history_item(history_id: int):
    """指定されたIDの実行履歴を削除します。"""
    init_history_db()
    with sqlite3.connect(HISTORY_DB_PATH) as con:
        cur = con.execute("DELETE FROM execution_history WHERE id = ?", (history_id,))
        con.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="指定されたIDの履歴が見つかりません。")
    return {"message": f"ID:{history_id}の履歴を削除しました。"}

# ▲▲▲【ここまでが新規・修正点】▲▲▲

@app.on_event("startup")
async def startup_event():
    init_history_db()
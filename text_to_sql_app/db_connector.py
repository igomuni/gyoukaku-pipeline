import duckdb
from pathlib import Path
from typing import List

# このスクリプトの場所を基準にプロジェクトルートディレクトリを特定
PROJECT_ROOT = Path(__file__).parent.parent
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

def get_db_connection() -> duckdb.DuckDBPyConnection | None:
    """
    インメモリのDuckDBデータベースに接続し、
    /data/processed 内の全CSVファイルからビューを作成して、
    接続オブジェクトを返す。
    
    Returns:
        duckdb.DuckDBPyConnection | None: 成功した場合は接続オブジェクト、
                                           データディレクトリが存在しない場合はNone。
    """
    if not PROCESSED_DATA_DIR.exists():
        print(f"エラー: データディレクトリが見つかりません: {PROCESSED_DATA_DIR}")
        print("先にデータ処理パイプラインを実行して、成果物CSVを生成してください。")
        return None

    # インメモリのDuckDBデータベースに接続
    con = duckdb.connect(database=':memory:', read_only=False)
    
    csv_files = list(PROCESSED_DATA_DIR.glob("*.csv"))
    if not csv_files:
        print(f"警告: {PROCESSED_DATA_DIR} 内にCSVファイルが見つかりません。")
        con.close()
        return None
        
    # /data/processed/ 内のCSVファイルをDuckDBのビューとして登録
    for file_path in csv_files:
        table_name = file_path.stem  # ファイル名から拡張子を除いた部分をテーブル名とする
        
        # ▼▼▼【ここが修正点】▼▼▼
        # Windowsのパス区切り文字'\'に対応するため、.as_posix() を使用して
        # パスを常に'/'区切りに変換する。
        posix_path = file_path.as_posix()
        con.sql(f"CREATE OR REPLACE VIEW {table_name} AS SELECT * FROM read_csv_auto('{posix_path}')")
        # ▲▲▲【ここまでが修正点】▲▲▲

    return con

def get_table_names(con: duckdb.DuckDBPyConnection) -> List[str]:
    """
    データベース接続からテーブル/ビューの一覧を取得する。
    """
    result = con.sql("SHOW TABLES").df()
    return result['name'].tolist()
import duckdb
from text_to_sql_app.db_connector import get_db_connection, get_table_names

def generate_schema_markdown() -> str | None:
    """
    データベースに接続し、そのスキーマ情報をMarkdown形式で生成する。
    """
    con = get_db_connection()
    if not con:
        return None
    
    markdown_output = ["# データベーススキーマ\n"]
    
    try:
        table_names = sorted(get_table_names(con))
        markdown_output.append(f"**テーブル一覧:** `{'`, `'.join(table_names)}`\n\n")

        # 各テーブルのスキーマ情報を取得してMarkdownに追加
        for table_name in table_names:
            markdown_output.append(f"## テーブル: `{table_name}`\n\n")
            markdown_output.append("| カラム名 | データ型 |\n")
            markdown_output.append("|---|---|\n")
            
            try:
                schema_df = con.sql(f"DESCRIBE {table_name}").df()
                for _, row in schema_df.iterrows():
                    markdown_output.append(f"| `{row['column_name']}` | `{row['column_type']}` |\n")
            except duckdb.Error as e:
                markdown_output.append(f"| (エラー) | {e} |\n")
            
            markdown_output.append("\n")

    except Exception as e:
        print(f"スキーマ生成中に予期せぬエラーが発生しました: {e}")
        return None
    finally:
        con.close()
        
    return "".join(markdown_output)

if __name__ == "__main__":
    print("データベースのスキーマ情報を生成します...")
    schema_markdown = generate_schema_markdown()
    if schema_markdown:
        print("\n" + "="*50)
        print(schema_markdown.strip())
        print("="*50)
        print("\n上記の内容を `schema.md` などのファイルに保存して、LLMのプロンプトに活用することをお勧めします。")
        print("例: python text_to_sql_app/generate_schema.py > schema.md")
import duckdb
import pandas
from text_to_sql_app.db_connector import get_db_connection

def run_sample_queries():
    """
    データベースに接続し、分析用のサンプルクエリを実行する。
    クエリは generate_schema.py で生成されたスキーマ情報に基づいて記述されている。
    """
    print("データベースに接続しています...")
    con = get_db_connection()
    if not con:
        return
    
    print("接続に成功しました。サンプルクエリを実行します。\n")

    try:
        print("---[サンプルクエリ1: 省庁別の事業数トップ10]---")
        # スキーマに基づきJOINキーを 'ministry_id' に、
        # COUNT対象を 'business_id' に、省庁名を 'ministry_name' に修正
        query1 = """
        SELECT
            m.ministry_name,
            COUNT(b.business_id) AS business_count
        FROM
            business b
        JOIN
            ministries m ON b.ministry_id = m.ministry_id
        GROUP BY
            m.ministry_name
        ORDER BY
            business_count DESC
        LIMIT 10;
        """
        try:
            result1 = con.sql(query1).df()
            print(result1)
        except duckdb.Error as e:
            print(f"クエリ1の実行中にエラーが発生しました: {e}")


        # 当該年度の当初予算カラムを直接指定
        target_budget_col = '予算の状況当初予算'
        
        try:
            budget_columns = [col[0] for col in con.execute("DESCRIBE budgets").fetchall()]
        except duckdb.Error:
            budget_columns = []

        if target_budget_col in budget_columns:
            print(f"\n---[サンプルクエリ2: デジタル庁の'{target_budget_col}'が高い事業トップ10]---")
            # エラー解決のため、CAST を TRY_CAST に変更。
            # TRY_CASTは '-' のような変換できない文字列をエラーにせずNULLに変換する。
            # WHERE句でそのNULLを除外することで、数値データのみを対象とする。
            query2 = f"""
            SELECT
                b.事業名,
                TRY_CAST(bu."{target_budget_col}" AS DOUBLE) AS 当初予算額_百万円
            FROM
                business b
            JOIN
                ministries m ON b.ministry_id = m.ministry_id
            LEFT JOIN
                budgets bu ON b.business_id = bu.business_id
            WHERE
                m.ministry_name = 'デジタル庁'
                AND 当初予算額_百万円 IS NOT NULL
            ORDER BY
                当初予算額_百万円 DESC
            LIMIT 10;
            """
            try:
                result2 = con.sql(query2).df()
                print(result2)
            except duckdb.Error as e:
                print(f"クエリ2の実行中にエラーが発生しました: {e}")
        else:
            print(f"\n---[サンプルクエリ2はスキップされました]---")
            print(f"理由: budgetsテーブルに '{target_budget_col}' カラムが見つかりませんでした。")

    finally:
        con.close()
        print("\nDuckDBとの接続を閉じました。")

if __name__ == "__main__":
    pandas.set_option('display.max_rows', 50)
    pandas.set_option('display.max_columns', 20)
    pandas.set_option('display.width', 120)
    pandas.set_option('display.float_format', '{:,.1f}'.format) # 金額を見やすくフォーマット
    run_sample_queries()
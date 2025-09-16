import csv
import logging
from pathlib import Path

# --- 設定 ---
# このスクリプトの親ディレクトリ（/analysis）の、さらに親がプロジェクトルート
PROJECT_ROOT = Path(__file__).parent.parent 
TARGET_DIR = PROJECT_ROOT / "data" / "normalized"
OUTPUT_DIR = PROJECT_ROOT / "data" / "analysis"
OUTPUT_FILENAME = "header_keyword_matrix.csv"
KEYWORDS = ['予算', '執行', '支出', '費目']

# ロガー設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_header_matrix():
    """
    /data/normalized 内のCSVファイルのヘッダーを分析し、キーワードを含む
    列名の有無をマトリクス形式で /data/analysis にCSVとして出力する。
    縦軸：キーワードを含む列名
    横軸：ファイル名
    値　：存在すれば1, 存在しなければ0
    """
    logging.info("ヘッダー分析マトリクスの生成を開始します...")

    # 1. 分析対象のCSVファイルを取得
    if not TARGET_DIR.is_dir():
        logging.error(f"分析対象ディレクトリが見つかりません: {TARGET_DIR}")
        return
    
    csv_files = sorted(list(TARGET_DIR.glob('*.csv')))
    if not csv_files:
        logging.warning(f"分析対象のCSVファイルが {TARGET_DIR} に見つかりません。")
        return

    filenames = [f.name for f in csv_files]
    logging.info(f"{len(filenames)}個のCSVファイルを分析対象とします。")
    
    # 2. 全ファイルのヘッダー情報を読み込み、キーワードに合致する列名をすべて収集
    all_headers_by_file = {}  # key: ファイル名, value: ヘッダー列名のセット
    relevant_columns = set()  # キーワードに合致した全てのユニークな列名を格納

    for file_path in csv_files:
        try:
            with file_path.open('r', encoding='utf-8-sig', errors='ignore') as f:
                reader = csv.reader(f)
                header = next(reader, [])
                
                header_set = set(header)
                all_headers_by_file[file_path.name] = header_set
                
                for col_name in header:
                    if any(keyword in col_name for keyword in KEYWORDS):
                        relevant_columns.add(col_name)
        except StopIteration:
            logging.warning(f"空のファイルまたはヘッダーのないファイルをスキップしました: {file_path.name}")
        except Exception as e:
            logging.error(f"ファイル処理中にエラーが発生しました: {file_path.name} - {e}")
            all_headers_by_file[file_path.name] = set() # エラー発生時もキーは作成

    if not relevant_columns:
        logging.warning("キーワードに合致する列がどのファイルにも見つかりませんでした。")
        return

    sorted_columns = sorted(list(relevant_columns))
    logging.info(f"キーワードに合致した {len(sorted_columns)} 個のユニークな列名を抽出しました。")

    # 3. マトリクスデータを作成
    matrix_rows = []
    # ヘッダー行（[列名, ファイル名1, ファイル名2, ...]）
    header_row = ['column_name'] + filenames
    matrix_rows.append(header_row)

    # データ行
    for col in sorted_columns:
        row = [col]
        for fname in filenames:
            # ファイルのヘッダーセットに列名が存在するかチェック
            is_present = 1 if col in all_headers_by_file.get(fname, set()) else 0
            row.append(is_present)
        matrix_rows.append(row)

    # 4. 結果をCSVファイルに出力
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / OUTPUT_FILENAME
        
        with output_path.open('w', newline='', encoding='utf-8-sig') as f:
            writer = csv.writer(f)
            writer.writerows(matrix_rows)
            
        logging.info(f"分析結果マトリクスを正常に出力しました: {output_path}")

    except Exception as e:
        logging.error(f"CSVファイルへの書き込み中にエラーが発生しました: {e}")

if __name__ == '__main__':
    create_header_matrix()
import sys
import re
import csv
import logging
from pathlib import Path

# --- プロジェクトルートをPythonパスに追加 ---
# このスクリプトをプロジェクトのルートからでも、
# /analysis ディレクトリからでも実行できるようにするため。
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from config import NORMALIZED_DIR

# --- 定数定義 ---
ANALYSIS_OUTPUT_DIR = PROJECT_ROOT / "data" / "analysis"
OUTPUT_FILENAME = "expenditure_items.txt"

# --- ロガー設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_expenditure_headers():
    """
    正規化済みCSVファイルのヘッダーを解析し、支出関連の項目名を抽出する。
    """
    logging.info("支出関連の列名解析を開始します...")

    # パターン定義: `費目・使途(...)-[A-Z].(項目名)-[数字]`
    # (項目名) の部分をキャプチャする
    pattern = re.compile(r"費目・使途.*?-[A-Z]\.(.+?)-\d+$")

    unique_items = set()

    # 出力ディレクトリの作成
    ANALYSIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    logging.info(f"解析結果は '{ANALYSIS_OUTPUT_DIR}' に出力されます。")

    normalized_files = sorted(list(NORMALIZED_DIR.glob('*.csv')))
    if not normalized_files:
        logging.warning(f"解析対象のファイルが見つかりません。'{NORMALIZED_DIR}' を確認してください。")
        return

    logging.info(f"{len(normalized_files)}個の正規化済みファイルを解析します。")

    for filepath in normalized_files:
        try:
            with open(filepath, 'r', encoding='utf-8-sig') as f:
                reader = csv.reader(f)
                header = next(reader, None)

                if not header:
                    logging.warning(f"  -> スキップ (空のファイル): {filepath.name}")
                    continue

                for column_name in header:
                    match = pattern.match(column_name)
                    if match:
                        # キャプチャした項目名（グループ1）を取得し、前後の空白を除去
                        item_name = match.group(1).strip()
                        unique_items.add(item_name)
        except Exception as e:
            logging.error(f"ファイル処理中にエラーが発生しました: {filepath.name} - {e}", exc_info=True)

    if not unique_items:
        logging.warning("支出関連の項目は見つかりませんでした。")
        return

    # 結果をソートしてファイルに出力
    sorted_items = sorted(list(unique_items))
    output_path = ANALYSIS_OUTPUT_DIR / OUTPUT_FILENAME

    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            for item in sorted_items:
                f.write(f"{item}\n")
        logging.info(f"解析が完了しました。{len(sorted_items)}個のユニークな項目を '{output_path}' に保存しました。")
    except Exception as e:
        logging.error(f"結果のファイル書き込み中にエラーが発生しました: {e}", exc_info=True)


if __name__ == "__main__":
    analyze_expenditure_headers()
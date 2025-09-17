import sys
import re
import csv
import logging
from pathlib import Path

# --- プロジェクトルートをPythonパスに追加 ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from config import NORMALIZED_DIR

# --- 定数定義 ---
ANALYSIS_OUTPUT_DIR = PROJECT_ROOT / "data" / "analysis"
OUTPUT_FILENAME = "expenditure_list_items.txt"
PREFIX = "支出先上位10者リスト"

# --- ロガー設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_expenditure_list_headers():
    """
    正規化済みCSVファイルのヘッダーを解析し、「支出先上位10者リスト」関連の項目名を抽出する。
    """
    logging.info(f"「{PREFIX}」関連の列名解析を開始します...")

    # パターン定義
    # 1. 2014年形式: `...-グループ-(項目名)-番号`
    pattern_group = re.compile(rf"{PREFIX}-グループ-(.+?)-\d+$")
    # 2. 2015年以降形式: `...-[A-Z].支払先-番号-(項目名)` (末尾の連番は任意)
    pattern_payment = re.compile(rf"{PREFIX}-[A-Z]\.支払先-\d+-(.+?)(?:-\d+)?$")

    unique_items = set()

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
                    continue

                for column_name in header:
                    if not column_name.startswith(PREFIX):
                        continue
                    
                    item_name = None
                    
                    # より一般的な2015年以降の形式から先に試す
                    match_payment = pattern_payment.match(column_name)
                    if match_payment:
                        item_name = match_payment.group(1)
                    else:
                        match_group = pattern_group.match(column_name)
                        if match_group:
                            item_name = match_group.group(1)

                    if item_name:
                        # 括弧とその中身を削除して表記揺れを吸収 (例: "入札者数(応募者数)" -> "入札者数")
                        cleaned_item = re.sub(r'\(.*\)', '', item_name).strip()
                        unique_items.add(cleaned_item)
        except Exception as e:
            logging.error(f"ファイル処理中にエラーが発生しました: {filepath.name} - {e}", exc_info=True)

    if not unique_items:
        logging.warning(f"「{PREFIX}」関連の項目は見つかりませんでした。")
        return

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
    analyze_expenditure_list_headers()
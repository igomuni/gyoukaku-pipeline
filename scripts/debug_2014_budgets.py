import logging
import re
from pathlib import Path
import sys
import pandas as pd

# --- プロジェクトルートをPythonのパスに追加 ---
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
# -----------------------------------------

from config import FILENAME_YEAR_MAP, NORMALIZED_DIR

# ログ設定をデバッグレベルに
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# --- デバッグ対象の主要関数 ---

PAST_BUDGET_ITEMS = [
    '予算の状況予備費等', '予算の状況前年度から繰越し', '予算の状況当初予算',
    '予算の状況翌年度へ繰越し', '予算の状況補正予算', '予算の状況計',
    '執行率(%)', '執行額', '当初予算+補正予算に対する執行額の割合(%)'
]
REQUEST_BUDGET_ITEMS = ['要求予算の状況当初予算', '要求予算の状況計']

def standardize_item_name(raw_item_name, is_request):
    """抽出した生の項目名を、定義済みの統一項目名にマッピングする"""
    target_items = REQUEST_BUDGET_ITEMS if is_request else PAST_BUDGET_ITEMS
    for standard_item in target_items:
        if standard_item in raw_item_name:
            logging.debug(f"  [標準化OK] '{raw_item_name}' -> '{standard_item}'")
            return standard_item
    logging.debug(f"  [標準化NG] '{raw_item_name}' はどの標準項目にもマッチしませんでした。")
    return None

def debug_2014_file():
    """
    2014年のファイルに特化して、列名の解析プロセスを詳細に出力するデバッグスクリプト。
    """
    logging.info("--- 2014年予算データ抽出のデバッグを開始 ---")

    target_filename_key = 'database2015_Sheet1'
    target_filepath = None
    
    all_csv_files = sorted(list(NORMALIZED_DIR.glob('*.csv')))
    for filepath in all_csv_files:
        if target_filename_key in filepath.name:
            target_filepath = filepath
            break
    
    if not target_filepath:
        logging.error(f"'{target_filename_key}' を含むファイルが見つかりませんでした。")
        return

    logging.info(f"デバッグ対象ファイル: {target_filepath.name}")
    review_year = 2014

    # --- パターン定義 ---
    p_2015 = re.compile(r'.*?-(\d{4})年度(.*)')
    p_2014 = re.compile(r'.*?-(.*?)-(\d{4})年度(.*)')
    
    try:
        df = pd.read_csv(target_filepath, low_memory=False, dtype=str, keep_default_na=False, na_values=[''])
        logging.info(f"ファイル読み込み完了。{len(df.columns)}個の列を検出。")
        
        # 最初の5行のみを対象にデバッグ
        for index, row in df.head(5).iterrows():
            business_id = f"{review_year}-{str(index+1).zfill(5)}"
            logging.info(f"\n--- 事業ID: {business_id} (元CSVの{index+1}行目) の処理を開始 ---")

            for col_name in df.columns:
                if not isinstance(col_name, str) or pd.isna(row[col_name]) or str(row[col_name]).strip() == '':
                    continue
                
                logging.debug(f"\n[列名スキャン] '{col_name}' (値: '{row[col_name]}')")

                match_2015 = p_2015.fullmatch(col_name)
                match_2014 = p_2014.fullmatch(col_name)

                raw_item, target_year_str, is_request_str = None, None, ''
                
                if match_2014:
                    raw_item, target_year_str, is_request_str = match_2014.groups()
                    logging.debug(f"  [パターン一致] 2014年のパターンにマッチ。")
                    logging.debug(f"    -> 抽出された項目部分: '{raw_item}', 年度: '{target_year_str}', 要求部分: '{is_request_str}'")
                elif match_2015:
                    target_year_str, raw_item = match_2015.groups()
                    logging.debug(f"  [パターン一致] 2015年以降のパターンにマッチ。")
                    logging.debug(f"    -> 抽出された年度: '{target_year_str}', 項目部分: '{raw_item}'")
                else:
                    logging.debug("  [パターン不一致] どのパターンにもマッチしませんでした。スキップします。")
                    continue
                    
                is_request = '要求' in raw_item or '要求' in is_request_str
                item_name = standardize_item_name(raw_item, is_request)
                
                if not item_name:
                    logging.debug("  [最終結果] 標準項目名に変換できなかったため、この列は処理されません。")
                    continue

                target_year = int(target_year_str)
                relative_pos = target_year - review_year if not is_request else 1
                
                suffix_map = {-3: '_py3', -2: '_py2', -1: '_py1', 0: '', 1: '_req'}
                suffix = suffix_map.get(relative_pos, '_INVALID_YEAR') # 範囲外の年はINVALIDとする

                new_col_name = f"{item_name}{suffix}"
                logging.info(f"  [最終結果] 生成レコード: business_id='{business_id}', 列名='{new_col_name}', 値='{row[col_name]}'")

    except Exception as e:
        logging.error(f"デバッグ中にエラーが発生しました: {e}", exc_info=True)

if __name__ == '__main__':
    debug_2014_file()
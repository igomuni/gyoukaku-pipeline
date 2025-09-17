import sys
import re
import logging
from pathlib import Path
from collections import defaultdict

import pandas as pd

# --- プロジェクトルートをPythonパスに追加 ---
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))

from config import NORMALIZED_DIR, PROCESSED_DIR, FILENAME_YEAR_MAP

# --- 定数定義 ---
OUTPUT_FILENAME = "expenditure.csv"
PREFIX = "支出先上位10者リスト"

# 抽出対象の項目リスト
EXPENDITURE_LIST_ITEMS = [
    '番号',
    '支出先',
    '業務概要',
    '支出額',
    '入札者数',
    '落札率',
    '契約方式',
    '契約方式等',
    '法人番号',
    '一者応札・一者応募又は競争性のない随意契約となった理由及び改善策'
]

# --- ロガー設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_year_from_filename(filename: str) -> int | None:
    """ファイル名から事業年度を特定するヘルパー関数"""
    for key, year in FILENAME_YEAR_MAP.items():
        if key in filename:
            return year
    return None


def process_expenditures(file_paths: list[Path]) -> pd.DataFrame:
    """
    指定されたCSVファイルのリストを処理し、支出明細のDataFrameを返す。
    """
    logging.info("支出先リストデータの抽出処理を開始...")
    all_expenditure_records = []

    pattern_2014 = re.compile(rf"{PREFIX}-グループ-(.+?)-(\d+)$")
    pattern_2015_on = re.compile(rf"{PREFIX}-([A-Za-z])\.支払先-(\d+)-(.+)")

    REQUIRED_COLS_FOR_REVIEW_SHEET = {'府省', '府省庁', '事業名', '事業番号', '事業番号-1'}
    EXCLUSION_COL = 'セグメント名'

    for filepath in file_paths:
        logging.info(f"  -> 処理中: {filepath.name}")

        review_year = get_year_from_filename(filepath.stem)
        if not review_year:
            logging.warning(f"    レビュー年度を特定できずスキップ: {filepath.name}")
            continue

        try:
            df = pd.read_csv(filepath, low_memory=False, dtype=str, keep_default_na=False)
            
            # df = df.head(10)
            # logging.info(f"    -> テストモード: 先頭{len(df)}行のみ処理します。")
            
            cleaned_header = {str(col).replace('\n', '').replace('\r', '').replace(' ', '') for col in df.columns}

            if EXCLUSION_COL in cleaned_header or len(REQUIRED_COLS_FOR_REVIEW_SHEET.intersection(cleaned_header)) < 3:
                logging.info(f"    レビューシートではないためスキップ: {filepath.name}")
                continue

            df['business_id'] = [f"{review_year}-{str(idx+1).zfill(5)}" for idx in range(len(df))]

            for index, row in df.iterrows():
                business_expenditures = defaultdict(dict)
                business_id = row['business_id']

                for col_name in df.columns:
                    if not col_name.startswith(PREFIX) or pd.isna(row[col_name]) or str(row[col_name]).strip() == '':
                        continue

                    block_id, sequence, item_name = None, None, None

                    match_2015 = pattern_2015_on.match(col_name)
                    if match_2015:
                        block_id, sequence, raw_item = match_2015.groups()
                        item_name = re.sub(r'\(.*\)|-\d+$', '', raw_item).strip()
                    else:
                        match_2014 = pattern_2014.match(col_name)
                        if match_2014:
                            block_id = 'グループ'
                            item_name, sequence = match_2014.groups()
                    
                    if item_name in EXPENDITURE_LIST_ITEMS:
                        record_key = f"{block_id}-{sequence}"
                        business_expenditures[record_key][item_name] = row[col_name]

                for key, data_dict in business_expenditures.items():
                    block_id, sequence = key.split('-', 1)
                    
                    if not data_dict.get('支出先') and not data_dict.get('支出額'):
                        continue

                    record = {
                        'business_id': business_id,
                        'block_id': block_id,
                        'sequence': int(sequence),
                    }
                    for item in EXPENDITURE_LIST_ITEMS:
                        record[item] = data_dict.get(item, '').strip()
                    
                    all_expenditure_records.append(record)

        except Exception as e:
            logging.error(f"    ファイル処理中にエラー: {filepath.name} - {e}", exc_info=True)
    
    if not all_expenditure_records:
        logging.warning("抽出対象となる支出データが見つかりませんでした。")
        return pd.DataFrame()

    return pd.DataFrame(all_expenditure_records)


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    all_csv_files = sorted(list(NORMALIZED_DIR.glob('*.csv')))
    if not all_csv_files:
        logging.error(f"処理対象のCSVファイルが'{NORMALIZED_DIR}'に見つかりません。")
        sys.exit(1)
        
    final_df = process_expenditures(all_csv_files)
    
    if not final_df.empty:
        base_cols = ['business_id', 'block_id', 'sequence']
        
        output_columns = base_cols + EXPENDITURE_LIST_ITEMS
        
        final_df = final_df.reindex(columns=output_columns)
        
        output_path = PROCESSED_DIR / OUTPUT_FILENAME
        final_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logging.info(f"処理が完了しました。{len(final_df)}件の支出明細を '{output_path}' に保存しました。")
    else:
        logging.info("支出データが見つからなかったため、ファイルは出力されませんでした。")


if __name__ == "__main__":
    main()
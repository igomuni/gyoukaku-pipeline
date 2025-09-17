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
OUTPUT_FILENAME = "fund_flow.csv"

# 抽出対象とする項目名
FUND_FLOW_ITEMS = [
    '支払先使途',
    '支払先計',
    '支払先費目',
    '支払先金額(百万円)'
]

# --- ロガー設定 ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def get_year_from_filename(filename: str) -> int | None:
    """ファイル名から事業年度を特定するヘルパー関数"""
    for key, year in FILENAME_YEAR_MAP.items():
        if key in filename:
            return year
    return None


def process_fund_flow(file_paths: list[Path]) -> pd.DataFrame:
    """
    指定されたCSVファイルのリストを処理し、「資金の流れ」明細のDataFrameを返す。
    """
    logging.info("「資金の流れ」データの抽出処理を開始...")
    all_fund_flow_records = []

    pattern_with_seq = re.compile(r"費目・使途.*?([A-Za-z])\.(.+?)-(\d+)$")
    pattern_without_seq = re.compile(r"費目・使途.*?([A-Za-z])\.(.+)$")

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
            
            # df = df.head(10) # テスト用の行数制限（本番時はコメントアウト）
            # logging.info(f"    -> テストモード: 先頭{len(df)}行のみ処理します。")
            
            cleaned_header = {str(col).replace('\n', '').replace('\r', '').replace(' ', '') for col in df.columns}

            if EXCLUSION_COL in cleaned_header or len(REQUIRED_COLS_FOR_REVIEW_SHEET.intersection(cleaned_header)) < 3:
                logging.info(f"    レビューシートではないためスキップ: {filepath.name}")
                continue

            df['business_id'] = [f"{review_year}-{str(idx+1).zfill(5)}" for idx in range(len(df))]

            for index, row in df.iterrows():
                business_fund_flows = defaultdict(dict)
                business_id = row['business_id']

                for col_name in df.columns:
                    if not isinstance(col_name, str) or pd.isna(row[col_name]) or str(row[col_name]).strip() == '':
                        continue

                    match = pattern_with_seq.match(col_name)
                    if match:
                        block_id, item_name, sequence_str = match.groups()
                    else:
                        match = pattern_without_seq.match(col_name)
                        if match:
                            block_id, item_name = match.groups()
                            sequence_str = ""
                        else:
                            continue
                    
                    item_name = item_name.strip()

                    if item_name not in FUND_FLOW_ITEMS:
                        continue
                    
                    record_key = f"{block_id}-{sequence_str}"
                    business_fund_flows[record_key][item_name] = row[col_name]
                
                for key, data_dict in business_fund_flows.items():
                    block_id, sequence_part = key.split('-', 1)
                    
                    record = {
                        'business_id': business_id,
                        'block_id': block_id,
                        'sequence': int(sequence_part) if sequence_part.isdigit() else '',
                        '支払先使途': data_dict.get('支払先使途', '').strip(),
                        '支払先計': data_dict.get('支払先計', '').strip(),
                        '支払先費目': data_dict.get('支払先費目', '').strip(),
                        '支払先金額(百万円)': data_dict.get('支払先金額(百万円)', '').strip(),
                    }

                    has_primary_data = any([
                        record['支払先費目'],
                        record['支払先使途'],
                        record['支払先金額(百万円)']
                    ])
                    total_amount_str = record['支払先計']
                    has_meaningful_total = total_amount_str and total_amount_str != '0'

                    if has_primary_data or has_meaningful_total:
                        all_fund_flow_records.append(record)

        except Exception as e:
            logging.error(f"    ファイル処理中にエラー: {filepath.name} - {e}", exc_info=True)
    
    if not all_fund_flow_records:
        logging.warning("抽出対象となる「資金の流れ」データが見つかりませんでした。")
        return pd.DataFrame()

    return pd.DataFrame(all_fund_flow_records)


def main():
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    
    all_csv_files = sorted(list(NORMALIZED_DIR.glob('*.csv')))
    if not all_csv_files:
        logging.error(f"処理対象のCSVファイルが'{NORMALIZED_DIR}'に見つかりません。")
        sys.exit(1)
        
    final_df = process_fund_flow(all_csv_files)
    
    if not final_df.empty:
        output_columns = [
            'business_id', 'block_id', 'sequence', 
            '支払先費目', '支払先使途', '支払先金額(百万円)', '支払先計'
        ]
        final_df = final_df.reindex(columns=output_columns)
        
        output_path = PROCESSED_DIR / OUTPUT_FILENAME
        final_df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logging.info(f"処理が完了しました。{len(final_df)}件の「資金の流れ」明細を '{output_path}' に保存しました。")
    else:
        logging.info("「資金の流れ」データが見つからなかったため、ファイルは出力されませんでした。")


if __name__ == "__main__":
    main()
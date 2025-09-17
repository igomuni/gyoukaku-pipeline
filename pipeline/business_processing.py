import csv
import logging
from typing import Callable

import pandas as pd

from config import (
    NORMALIZED_DIR, PROCESSED_DIR, MINISTRY_MASTER_DATA,
    FILENAME_YEAR_MAP, MINISTRY_NAME_VARIATIONS
)

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_year_from_filename(filename):
    """ファイル名から事業年度を特定するヘルパー関数"""
    for key, year in FILENAME_YEAR_MAP.items():
        if key in filename:
            return year
    return None

def build_business_tables(update_status: Callable, job_id: str):
    """
    ステージ3: 事業テーブルの構築
    正規化済みCSVを結合し、ministries.csv と business.csv を生成する。
    """
    update_status(current_stage="ステージ3: 事業テーブルの構築", message="処理を開始します...")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Build Ministry Master
    update_status(message="府省庁マスターを生成中...")
    ministry_df = pd.DataFrame(MINISTRY_MASTER_DATA)
    ministry_output_path = PROCESSED_DIR / 'ministries.csv'
    ministry_df.to_csv(ministry_output_path, index=False, encoding='utf-8-sig', quoting=csv.QUOTE_MINIMAL)
    logging.info(f"  - Saved 'ministries.csv' with {len(ministry_df)} records.")

    # 2. Build Business Tables
    update_status(message="事業テーブルを生成中...")
    all_business_records = []
    
    REQUIRED_COLS_FOR_REVIEW_SHEET = {'府省', '府省庁', '事業名', '事業番号', '事業番号-1'}
    EXCLUSION_COL = 'セグメント名'
    
    FINAL_OUTPUT_COLS = [
        'business_id', 'source_year', 'ministry_id', '府省庁',
        '事業番号-1', '事業番号-2', '事業番号-3', '事業番号-4', '事業番号-5',
        '事業名', '担当部局庁', '作成責任者', '事業開始終了年度', '担当課室',
        '会計区分', '根拠法令（具体的な条項も記載）', '関係する計画、通知等',
        '政策', '施策', '政策体系・評価書URL', '主要経費', '事業の目的',
        '現状・課題', '事業概要', '事業概要URL', '実施方法'
    ]
    
    all_csv_files = sorted(list(NORMALIZED_DIR.glob('*.csv')))
    
    if not all_csv_files:
        logging.warning("[Stage 3] No .csv files found. Skipping.")
        update_status(message="正規化済みCSVが見つかりません。")
        return

    total_files = len(all_csv_files)
    for i, filepath in enumerate(all_csv_files):
        update_status(message=f"ファイル {i+1}/{total_files} を分析中: {filepath.name}")
        file_year = get_year_from_filename(filepath.name)
        if not file_year:
            logging.warning(f"Could not determine year for '{filepath.name}'. Skipping.")
            continue
        
        try:
            df = pd.read_csv(filepath, low_memory=False, dtype=str, encoding='utf-8-sig')

            cleaned_header = [str(col).replace('\n', '').replace('\r', '').replace(' ', '') for col in df.columns]

            if EXCLUSION_COL in cleaned_header:
                logging.info(f"Skipping '{filepath.name}' due to exclusion column.")
                continue
            if len(REQUIRED_COLS_FOR_REVIEW_SHEET.intersection(cleaned_header)) < 3:
                logging.info(f"Skipping '{filepath.name}' as not a review sheet.")
                continue

            rename_map = {}
            for original_col in df.columns:
                clean_col = str(original_col).replace('\n', '').replace('\r', '').replace(' ', '')
                
                if clean_col == '府省': rename_map[original_col] = '府省庁'
                elif clean_col == '事業番号': rename_map[original_col] = '事業番号-1'
                elif clean_col.startswith('事業の目的'): rename_map[original_col] = '事業の目的'
                elif clean_col == '事業概要URL':
                    rename_map[original_col] = '事業概要URL'
                elif clean_col.startswith('事業概要'):
                    rename_map[original_col] = '事業概要'
                elif clean_col.startswith('根拠法令'): rename_map[original_col] = '根拠法令（具体的な条項も記載）'
                elif clean_col.startswith('現状・課題'): rename_map[original_col] = '現状・課題'
                elif clean_col in ('政策・施策名', '主要政策・施策'): rename_map[original_col] = '政策'
                elif clean_col == '主要施策': rename_map[original_col] = '施策'
            df.rename(columns=rename_map, inplace=True)
            
            df = df.loc[:, ~df.columns.duplicated(keep='first')]
            
            df['事業開始終了年度'] = ''
            if '事業開始・終了(予定)年度' in df.columns:
                df['事業開始終了年度'] = df['事業開始・終了(予定)年度'].fillna('')
            
            if '事業開始年度' in df.columns and '事業終了(予定)年度' in df.columns:
                start_year = df['事業開始年度'].fillna('')
                end_year = df['事業終了(予定)年度'].fillna('')
                combined_year = start_year.str.cat(end_year, sep='-').where(start_year.ne('') & end_year.ne(''), '')
                df['事業開始終了年度'] = df['事業開始終了年度'].where(df['事業開始終了年度'].ne(''), combined_year)

            df['business_id'] = [f"{file_year}-{str(idx+1).zfill(5)}" for idx in range(len(df))]
            df['source_year'] = file_year
            
            all_business_records.append(df)
        except Exception as e:
            logging.error(f"    [ERROR] Failed to process {filepath.name}: {e}", exc_info=True)
            raise
    
    if all_business_records:
        update_status(message="全レビューシートを結合中...")
        master_df = pd.concat(all_business_records, ignore_index=True)
        
        ministry_name_to_id = pd.Series(ministry_df.ministry_id.values, index=ministry_df.ministry_name).to_dict()
        if '府省庁' in master_df.columns:
             master_df['normalized_ministry_name'] = master_df['府省庁'].replace(MINISTRY_NAME_VARIATIONS)
             master_df['ministry_id'] = master_df['normalized_ministry_name'].map(ministry_name_to_id).astype('Int64')
        
        final_df = master_df.reindex(columns=FINAL_OUTPUT_COLS)
        
        business_output_path = PROCESSED_DIR / 'business.csv'
        
        UNQUOTED_COLS = {'business_id', 'source_year', 'ministry_id'}

        with open(business_output_path, 'w', newline='', encoding='utf-8-sig') as f:
            f.write(','.join(final_df.columns) + '\n')

            for row in final_df.itertuples(index=False, name=None):
                row_values = []
                for i, value in enumerate(row):
                    col_name = final_df.columns[i]
                    str_value = str(value) if pd.notna(value) else ''
                    
                    if col_name in UNQUOTED_COLS:
                        row_values.append(str_value)
                    else:
                        escaped_str = str_value.replace('"', '""')
                        quoted_value = f'"{escaped_str}"'
                        row_values.append(quoted_value)
                
                f.write(','.join(row_values) + '\n')
        
        logging.info(f"  - Saved 'business.csv' with {len(final_df)} records.")
    
    update_status(message="ステージ3が完了しました。")
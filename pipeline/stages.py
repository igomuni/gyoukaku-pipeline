import os
import csv
import zipfile
import logging
from typing import Callable, Optional, List
from pathlib import Path

import pandas as pd
import openpyxl

from config import (
    DOWNLOAD_DIR, RAW_DIR, NORMALIZED_DIR, PROCESSED_DIR,
    MINISTRY_MASTER_DATA, FILENAME_YEAR_MAP, MINISTRY_NAME_VARIATIONS
)
from utils.normalization import normalize_text
# from pipeline.manager import check_for_cancellation  <- この行を削除しました

# ロガーの設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# --- Stage 1: Convert Excel/ZIP to CSV ---
def run_stage_01_convert(update_status: Callable, job_id: str, target_files: Optional[List[str]]):
    update_status(current_stage="ステージ1: CSVへの変換", message="処理を開始します...")
    
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    
    source_paths = list(DOWNLOAD_DIR.glob('*.zip')) + list(DOWNLOAD_DIR.glob('*.xlsx'))

    if target_files:
        source_paths = [p for p in source_paths if p.name in target_files]

    if not source_paths:
        logging.warning("[Stage 1] No target files found. Skipping.")
        update_status(message="対象ファイルが見つかりません。スキップします。")
        return

    def _convert_excel_to_csv(excel_source, file_stem, output_dir):
        try:
            workbook = openpyxl.load_workbook(excel_source, read_only=True, data_only=True)
            for sheet_name in workbook.sheetnames:
                worksheet = workbook[sheet_name]
                output_path = output_dir / f"{file_stem}_{sheet_name}.csv"
                logging.info(f"  - Saving sheet: '{sheet_name}' -> '{output_path.name}'")
                with open(output_path, 'w', newline='', encoding='utf-8-sig') as csv_file:
                    csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
                    for row in worksheet.iter_rows(values_only=True):
                        escaped_row = [str(cell).replace('\n', '\\n').replace('\r', '') if cell is not None else "" for cell in row]
                        csv_writer.writerow(escaped_row)
        except Exception as e:
            logging.error(f"  [ERROR] Failed to process Excel data from {file_stem}: {e}", exc_info=True)
            raise

    total_files = len(source_paths)
    for i, path in enumerate(source_paths):
        # update_statusを呼び出すと、内部でキャンセルチェックが実行されます
        update_status(message=f"ファイル {i+1}/{total_files} を処理中: {path.name}")
        logging.info(f"Processing '{path.name}'...")
        if path.suffix == '.zip':
            try:
                with zipfile.ZipFile(path, 'r') as zf:
                    for file_in_zip in zf.namelist():
                        if file_in_zip.endswith('.xlsx') and not file_in_zip.startswith('__MACOSX'):
                            file_stem = Path(file_in_zip).stem
                            logging.info(f"  - Extracting '{file_in_zip}'")
                            with zf.open(file_in_zip) as excel_stream:
                                _convert_excel_to_csv(excel_stream, file_stem, RAW_DIR)
            except Exception as e:
                logging.error(f"  [ERROR] Failed to process zip file {path.name}: {e}", exc_info=True)
                raise
        elif path.suffix == '.xlsx':
            _convert_excel_to_csv(path, path.stem, RAW_DIR)
    
    update_status(message="ステージ1が完了しました。")

# --- Stage 2: Normalize CSV Files ---
def run_stage_02_normalize(update_status: Callable, job_id: str):
    update_status(current_stage="ステージ2: データの正規化", message="処理を開始します...")

    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

    csv_files = sorted(list(RAW_DIR.glob('*.csv')))
    if not csv_files:
        logging.warning("[Stage 2] No .csv files found in 'data/raw/'. Skipping.")
        update_status(message="対象ファイルが見つかりません。スキップします。")
        return

    total_files = len(csv_files)
    for i, input_path in enumerate(csv_files):
        # update_statusを呼び出すと、内部でキャンセルチェックが実行されます
        update_status(message=f"ファイル {i+1}/{total_files} を正規化中: {input_path.name}")
        output_path = NORMALIZED_DIR / input_path.name
        try:
            with open(input_path, 'r', encoding='utf-8-sig') as infile, \
                 open(output_path, 'w', encoding='utf-8-sig', newline='') as outfile:
                reader = csv.reader(infile)
                writer = csv.writer(outfile, quoting=csv.QUOTE_ALL)
                
                header = next(reader, None)
                if header:
                    writer.writerow([normalize_text(cell) for cell in header])
                
                for row in reader:
                    writer.writerow([normalize_text(cell) for cell in row])

        except Exception as e:
            logging.error(f"  [ERROR] Failed to process {input_path.name}: {e}", exc_info=True)
            raise

    update_status(message="ステージ2が完了しました。")


# --- Stage 3: Build Master Tables ---
def run_stage_03_build_masters(update_status: Callable, job_id: str):
    update_status(current_stage="ステージ3: マスターテーブルの構築", message="処理を開始します...")
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Build Ministry Master
    update_status(message="府省庁マスターを生成中...")
    ministry_df = pd.DataFrame(MINISTRY_MASTER_DATA)
    ministry_output_path = PROCESSED_DIR / 'ministry_master.csv'
    ministry_df.to_csv(ministry_output_path, index=False, encoding='utf-8-sig')
    logging.info(f"  - Saved 'ministry_master.csv' with {len(ministry_df)} records.")

    # 2. Build Business Master
    update_status(message="事業マスターを生成中...")
    all_business_records = []
    review_sheets = sorted(list(NORMALIZED_DIR.glob('*レビューシート*.csv')))
    if not review_sheets:
        logging.warning("[Stage 3] No '*レビューシート*.csv' files found. Cannot build business master.")
        update_status(message="事業レビューシートCSVが見つかりません。事業マスターの構築をスキップします。")
        return

    def get_year_from_filename(filename):
        for key, year in FILENAME_YEAR_MAP.items():
            if key in filename: return year
        return None
    
    total_files = len(review_sheets)
    for i, filepath in enumerate(review_sheets):
        # update_statusを呼び出すと、内部でキャンセルチェックが実行されます
        update_status(message=f"レビューシート {i+1}/{total_files} を処理中: {filepath.name}")

        file_year = get_year_from_filename(filepath.name)
        if not file_year:
            logging.warning(f"Could not determine year for '{filepath.name}'. Skipping.")
            continue
        
        try:
            df = pd.read_csv(filepath, low_memory=False, dtype=str)
            df.rename(columns={'府省': '府省庁'}, inplace=True)
            
            df['business_id'] = [f"{file_year}-{str(idx+1).zfill(5)}" for idx in range(len(df))]
            df['source_file'] = filepath.name
            df['source_year'] = file_year
            all_business_records.append(df)
        except Exception as e:
            logging.error(f"    [ERROR] Failed to process {filepath.name}: {e}", exc_info=True)
            raise
    
    if all_business_records:
        # 最終的な結合処理の前にも念のためチェック
        update_status(message="全レビューシートを結合中...")
        master_df = pd.concat(all_business_records, ignore_index=True)
        
        ministry_name_to_id = pd.Series(ministry_df.ministry_id.values, index=ministry_df.ministry_name).to_dict()
        if '府省庁' in master_df.columns:
             master_df['normalized_ministry_name'] = master_df['府省庁'].replace(MINISTRY_NAME_VARIATIONS)
             master_df['ministry_id'] = master_df['normalized_ministry_name'].map(ministry_name_to_id).astype('Int64')
        
        output_cols = [
            'business_id', 'source_year', 'ministry_id', '府省庁', '事業名', '事業番号', 
            '事業番号-1', '事業番号-2', '事業番号-3', '事業番号-4', '事業番号-5',
            'source_file'
        ]
        final_cols = [col for col in output_cols if col in master_df.columns]
        final_df = master_df[final_cols]
        
        business_output_path = PROCESSED_DIR / 'business_master.csv'
        final_df.to_csv(business_output_path, index=False, encoding='utf-8-sig')
        logging.info(f"  - Saved 'business_master.csv' with {len(final_df)} records.")
    
    update_status(message="ステージ3が完了しました。")
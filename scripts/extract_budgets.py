import logging
from pathlib import Path
import sys
import pandas as pd

# --- プロジェクトルートをPythonのパスに追加 ---
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
# -----------------------------------------

from config import FILENAME_YEAR_MAP, NORMALIZED_DIR, PROCESSED_DIR
# --- ▼▼▼ 修正箇所: 共通ロジックをインポート ▼▼▼ ---
from pipeline.budget_processing import process_budget_files, PAST_BUDGET_ITEMS, REQUEST_BUDGET_ITEMS
# --- ▲▲▲ 修正箇所ここまで ▲▲▲ ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_year_from_filename(filename):
    """ファイル名からレビューシートの基準年度を取得する"""
    for key, year in FILENAME_YEAR_MAP.items():
        if key in filename:
            return year
    return None

if __name__ == '__main__':
    logging.info("予算・執行データ（超ワイド形式）の個別抽出を開始します...")
    
    all_csv_files = sorted(list(NORMALIZED_DIR.glob('*.csv')))
    if not all_csv_files:
        logging.warning(f"分析対象のCSVファイルが見つかりません: {NORMALIZED_DIR}")
    else:
        # ファイル名から年度を取得するためのマップを作成
        review_year_map = {f.stem: get_year_from_filename(f.name) for f in all_csv_files}
        
        # 共通ロジックを呼び出してDataFrameを取得
        final_df = process_budget_files(all_csv_files, review_year_map)

        if not final_df.empty:
            # 列の順序を定義・整理
            final_columns = ['business_id']
            for i in range(-3, 1):
                suffix = {-3: '_py3', -2: '_py2', -1: '_py1', 0: ''}[i]
                for item in PAST_BUDGET_ITEMS:
                    final_columns.append(f"{item}{suffix}")
            for item in REQUEST_BUDGET_ITEMS:
                final_columns.append(f"{item}_req")
                
            ordered_cols = [col for col in final_columns if col in final_df.columns]
            other_cols = [col for col in final_df.columns if col not in ordered_cols]
            final_df = final_df[ordered_cols + other_cols]

            output_path = PROCESSED_DIR / "budgets_timeseries_wide.csv"
            final_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            logging.info(f"予算時系列データを {output_path} に正常に出力しました。({len(final_df)}件)")
        else:
            logging.warning("抽出対象となる予算データが見つかりませんでした。")
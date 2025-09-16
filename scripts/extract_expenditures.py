import logging
import re
from pathlib import Path
import sys

import pandas as pd

# --- プロジェクトルートをPythonのパスに追加 ---
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
# -----------------------------------------

from config import FILENAME_YEAR_MAP, NORMALIZED_DIR, PROCESSED_DIR

# ロガー設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_year_from_filename(filename):
    """ファイル名からレビューシートの基準年度を取得する"""
    for key, year in FILENAME_YEAR_MAP.items():
        if key in filename:
            return year
    return None

def extract_expenditure_data():
    """
    normalized/*.csv ファイルから支出明細データを抽出し、
    縦持ちのCSVとして processed/expenditures.csv に出力する。
    """
    logging.info("支出明細データの抽出を開始します...")

    all_csv_files = sorted(list(NORMALIZED_DIR.glob('*.csv')))
    if not all_csv_files:
        logging.warning(f"分析対象のCSVファイルが {NORMALIZED_DIR} に見つかりません。")
        return

    all_expenditures = []

    # --- ▼▼▼ 修正箇所: ここから ▼▼▼ ---
    # 支出明細の列名を特定するための正規表現を修正
    # 「費目・使途」から始まり、間に任意の文字(改行含む)を挟んで、
    # グループ(A,B,...)、種別(費目,使途,金額)、ID(01,02,..)を抽出する
    # 例: 「費目・使途(...)-A.支払先費目-01」 -> group1: A, group2: 費目, group3: 01
    exp_col_pattern = re.compile(r'費目・使途.*?-([A-Za-z])\..*?(費目|使途|金額).*?-?(\d{2})?')
    # --- ▲▲▲ 修正箇所: ここまで ▲▲▲ ---

    for filepath in all_csv_files:
        logging.info(f"処理中: {filepath.name}")
        
        source_year = get_year_from_filename(filepath.name)
        if not source_year:
            logging.warning(f"基準年度を特定できませんでした。スキップ: {filepath.name}")
            continue

        try:
            df = pd.read_csv(filepath, low_memory=False, dtype=str)
            df.reset_index(inplace=True)
            df['business_id'] = df['index'].apply(lambda idx: f"{source_year}-{str(idx+1).zfill(5)}")
            
            exp_cols = [col for col in df.columns if col.startswith('費目・使途')]
            if not exp_cols:
                continue

            # 支出明細データを縦持ちに変換
            melted_df = df.melt(
                id_vars=['business_id'],
                value_vars=exp_cols,
                var_name='original_column',
                value_name='value'
            ).dropna(subset=['value'])

            if melted_df.empty:
                continue
            
            # 元の列名からグループ(A,B,..), 種別(費目,使途,金額), ID(01,02,..)を抽出
            extracted_data = melted_df['original_column'].str.extract(exp_col_pattern)
            melted_df['group'] = extracted_data[0]
            melted_df['type'] = extracted_data[1]
            melted_df['item_id'] = extracted_data[2].fillna('00') # 番号なしは '00' とする
            
            melted_df.dropna(subset=['group', 'type'], inplace=True)
            
            # 1明細=1行の形式にピボットする
            pivoted_df = melted_df.pivot_table(
                index=['business_id', 'group', 'item_id'],
                columns='type',
                values='value',
                aggfunc='first'
            ).reset_index()

            # 列名を分かりやすいものに変更
            pivoted_df.rename(columns={'費目': 'expense_item', '使途': 'purpose', '金額': 'amount'}, inplace=True)
            
            # 金額が空、または数値に変換できないデータは除外
            pivoted_df = pivoted_df[pd.to_numeric(pivoted_df['amount'], errors='coerce').notna()]
            
            all_expenditures.append(pivoted_df)

        except Exception as e:
            logging.error(f"ファイル処理中にエラーが発生しました: {filepath.name} - {e}")

    if not all_expenditures:
        logging.warning("抽出対象となる支出データが見つかりませんでした。")
        return

    final_df = pd.concat(all_expenditures, ignore_index=True)

    output_path = PROCESSED_DIR / "expenditures.csv"
    final_df.to_csv(output_path, index=False, encoding='utf-8-sig')
    logging.info(f"支出明細データを {output_path} に正常に出力しました。({len(final_df)}件)")

if __name__ == '__main__':
    extract_expenditure_data()
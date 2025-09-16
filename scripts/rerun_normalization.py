import csv
import logging
import sys
from pathlib import Path

# --- プロジェクトルートをPythonのパスに追加 ---
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))
# -----------------------------------------

from utils.normalization import normalize_text

# --- 設定 ---
RAW_DIR = project_root / "data" / "raw"
NORMALIZED_DIR = project_root / "data" / "normalized"

# ロガー設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    /data/raw 内の全CSVファイルに対して正規化処理を再実行し、
    結果を /data/normalized に出力する。
    """
    logging.info("--- 正規化処理の再実行を開始します ---")

    if not RAW_DIR.is_dir():
        logging.error(f"入力ディレクトリが見つかりません: {RAW_DIR}")
        return

    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
    logging.info(f"入力元: {RAW_DIR}")
    logging.info(f"出力先: {NORMALIZED_DIR}")

    csv_files = sorted(list(RAW_DIR.glob('*.csv')))
    if not csv_files:
        logging.warning(f"処理対象のCSVファイルが {RAW_DIR} に見つかりません。")
        return
        
    logging.info(f"{len(csv_files)}個のファイルを処理します。")

    total_files = len(csv_files)
    for i, input_path in enumerate(csv_files, 1):
        output_path = NORMALIZED_DIR / input_path.name
        logging.info(f"[{i}/{total_files}] 処理中: {input_path.name} -> {output_path.name}")
        
        try:
            with open(input_path, 'r', encoding='utf-8-sig', errors='ignore') as infile, \
                 open(output_path, 'w', encoding='utf-8-sig', newline='') as outfile:
                
                reader = csv.reader(infile)
                writer = csv.writer(outfile, quoting=csv.QUOTE_ALL)
                
                # ヘッダー行を正規化
                header = next(reader, None)
                if header:
                    # <<< 修正: \\n は文字列として扱いため、replace処理は行わない >>>
                    writer.writerow([normalize_text(cell) for cell in header])
                
                # データ行を正規化
                for row in reader:
                    # <<< 修正: \\n は文字列として扱いため、replace処理は行わない >>>
                    writer.writerow([normalize_text(cell) for cell in row])

        except Exception as e:
            logging.error(f"  [エラー] ファイル処理中にエラーが発生しました: {input_path.name} - {e}")
    
    logging.info("--- すべてのファイルの正規化処理が完了しました ---")

if __name__ == '__main__':
    main()
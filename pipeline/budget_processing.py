import logging
import re
import pandas as pd

# 統一ヘッダーの項目名を定義
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
            return standard_item
    return None

def process_budget_files(file_paths, review_year_map):
    """
    指定されたCSVファイルのリストを処理し、予算時系列ワイドDataFrameを返す。
    この関数が、パイプラインと個別実行スクリプトから共有される。
    """
    logging.info("予算・執行データの抽出（共通ロジック）を開始...")
    all_business_records = {}
    
    # パターン定義
    p_2015 = re.compile(r'.*?-(\d{4})年度(.*)')
    p_2014 = re.compile(r'.*?-(.*?)-(\d{4})年度(.*)')

    for filepath in file_paths:
        logging.info(f"  -> 処理中: {filepath.name}")
        
        review_year = review_year_map.get(filepath.stem)
        if not review_year:
            logging.warning(f"    レビュー年度を特定できずスキップ: {filepath.name}")
            continue

        try:
            df = pd.read_csv(filepath, low_memory=False, dtype=str, keep_default_na=False, na_values=[''])
            
            cleaned_header = {str(col).replace('\n', '').replace('\r', '').replace(' ', '') for col in df.columns}
            REQUIRED_COLS = {'府省', '府省庁', '事業名', '事業番号', '事業番号-1'}
            EXCLUSION_COL = 'セグメント名'
            if EXCLUSION_COL in cleaned_header or len(REQUIRED_COLS.intersection(cleaned_header)) < 3:
                logging.info(f"    レビューシートではないためスキップ: {filepath.name}")
                continue

            df.reset_index(inplace=True)
            df['business_id'] = df['index'].apply(lambda idx: f"{review_year}-{str(idx+1).zfill(5)}")
            
            for index, row in df.iterrows():
                business_id = row['business_id']
                if business_id not in all_business_records:
                    all_business_records[business_id] = {'business_id': business_id}

                for col_name in df.columns:
                    if not isinstance(col_name, str) or pd.isna(row[col_name]) or str(row[col_name]).strip() == '':
                        continue

                    match_2014 = p_2014.fullmatch(col_name)
                    match_2015 = p_2015.fullmatch(col_name)

                    raw_item, target_year_str, is_request_str = None, None, ''
                    
                    if match_2014:
                        raw_item, target_year_str, is_request_str = match_2014.groups()
                    elif match_2015:
                        target_year_str, raw_item = match_2015.groups()
                    else:
                        continue
                        
                    is_request = '要求' in raw_item or ('要求' in is_request_str if is_request_str else False)
                    item_name = standardize_item_name(raw_item, is_request)
                    
                    if not item_name: continue

                    target_year = int(target_year_str)
                    relative_pos = target_year - review_year if not is_request else 1
                    
                    if not (-3 <= relative_pos <= 1): continue
                    
                    suffix_map = {-3: '_py3', -2: '_py2', -1: '_py1', 0: '', 1: '_req'}
                    suffix = suffix_map.get(relative_pos)

                    new_col_name = f"{item_name}{suffix}"
                    all_business_records[business_id][new_col_name] = row[col_name]
        except Exception as e:
            logging.error(f"    ファイル処理中にエラー: {filepath.name} - {e}", exc_info=True)

    if not all_business_records:
        logging.warning("抽出対象となる予算データが見つかりませんでした。")
        return pd.DataFrame()

    return pd.DataFrame.from_dict(all_business_records, orient='index')
from pathlib import Path

# --- Path Definitions ---
# プロジェクトのルートディレクトリを基準とする
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
DOWNLOAD_DIR = DATA_DIR / "download"
RAW_DIR = DATA_DIR / "raw"
NORMALIZED_DIR = DATA_DIR / "normalized"
PROCESSED_DIR = DATA_DIR / "processed"

# --- Master Data Definitions ---
# 省庁名の表記揺れを統一するためのマッピング
MINISTRY_NAME_VARIATIONS = {
    '原子力規制員会': '原子力規制委員会',
    '特定個人情報保護委員会': '個人情報保護委員会',
}

# 府省庁マスターテーブルの元データ
MINISTRY_MASTER_DATA = {
    'ministry_id': [
        1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
        11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
        21, 22, 23, 99
    ],
    'ministry_name': [
        '内閣官房', '内閣府', '宮内庁', '公正取引委員会', '警察庁',
        '個人情報保護委員会', 'カジノ管理委員会', '金融庁', '消費者庁', 'こども家庭庁',
        'デジタル庁', '復興庁', '総務省', '法務省', '外務省',
        '財務省', '文部科学省', '厚生労働省', '農林水産省', '経済産業省',
        '国土交通省', '環境省', '原子力規制委員会', '防衛省'
    ]
}

# ファイル名から事業年度を特定するためのマッピング
FILENAME_YEAR_MAP = {
    'database240918': 2023, 'database240502': 2022, 'database220524': 2021,
    'database_220427': 2020, 'database2019_220427': 2019, 'database2018_220427': 2018,
    'database2017': 2017, 'database2016': 2016, 'database2015': 2015,
    'database2014': 2014,
}
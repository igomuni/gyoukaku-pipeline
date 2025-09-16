import re
import unicodedata
from typing import Optional

# --- Regex Definitions ---
RE_LIST_MARKER = re.compile(r'([①-⑳])')
RE_TILDE_VARIANTS = re.compile(r'\s*[~～]\s*')
RE_WAREKI_RANGE = re.compile(r'(明治|M|大正|T|昭和|S|平成|H|令和|R)(\d{1,2}|元)\s*～\s*(\d{1,2})')
RE_WAREKI_SINGLE = re.compile(r'(明治|M|大正|T|昭和|S|平成|H|令和|R)(\d{1,2}|元)')
# 西暦（例: 2016年度）と誤マッチングしないよう、数字の前に他の数字がないことを条件とする
RE_WAREKI_ABBREVIATED = re.compile(r'(?<!\d)(\d{1,2})年度')
HYPHEN_LIKE_CHARS = r'[\u002D\u2010\u2011\u2012\u2013\u2014\u2015\u2212\uFF0D]'
RE_HYPHEN_LIKE = re.compile(HYPHEN_LIKE_CHARS)
RE_KATAKANA_HYPHEN = re.compile(r'([ァ-ヴ])' + HYPHEN_LIKE_CHARS + r'(?=[ァ-ヴ])')
# <<< 修正箇所: 削除してしまった重要な定義を復元 >>>
KATAKANA_HYPHEN_PRE_NORMALIZATION = {"リスト-グル-プ": "リスト-グループ"}
KATAKANA_HYPHEN_EXCLUSIONS = ["リスト-グループ"]


def _get_seireki(era: str, year_str: str) -> Optional[int]:
    """Helper function to convert Japanese era year to Western calendar year."""
    year = 1 if year_str == '元' else int(year_str)
    if era in ('明治', 'M'): return 1867 + year
    if era in ('大正', 'T'): return 1911 + year
    if era in ('昭和', 'S'): return 1925 + year
    if era in ('平成', 'H'): return 1988 + year
    if era in ('令和', 'R'): return 2018 + year
    return None

def normalize_text(text: str) -> str:
    """Applies all defined Japanese normalization rules to a single cell string."""
    if not isinstance(text, str) or not text:
        return text

    # Step 1: Pre-processing (before NFKC)
    def replace_list_marker(match):
        marker_map = { '①':'1','②':'2','③':'3','④':'4','⑤':'5','⑥':'6','⑦':'7','⑧':'8','⑨':'9','⑩':'10',
                       '⑪':'11','⑫':'12','⑬':'13','⑭':'14','⑮':'15','⑯':'16','⑰':'17','⑱':'18','⑲':'19','⑳':'20'}
        return marker_map.get(match.group(1), match.group(1)) + '. '
    text = RE_LIST_MARKER.sub(replace_list_marker, text)

    # Step 2: Basic Normalization
    text = unicodedata.normalize('NFKC', text)
    text = RE_TILDE_VARIANTS.sub('～', text)

    # Step 3: Wareki to Seireki Conversion
    def convert_wareki_range(match):
        era, year1_str, year2_str = match.groups()
        seireki1 = _get_seireki(era, year1_str)
        seireki2 = _get_seireki(era, year2_str)
        if seireki1 is not None and seireki2 is not None:
            return f"{seireki1}～{seireki2}"
        return match.group(0)
    text = RE_WAREKI_RANGE.sub(convert_wareki_range, text)

    def convert_wareki_single(match):
        era, year_str = match.groups()
        seireki = _get_seireki(era, year_str)
        return str(seireki) if seireki is not None else match.group(0)
    text = RE_WAREKI_SINGLE.sub(convert_wareki_single, text)
    
    # Step 3.5: Abbreviated Wareki to Seireki Conversion (Heisei/Reiwa)
    def convert_wareki_abbreviated(match):
        year_str = match.group(1)
        if not year_str.isdigit(): return match.group(0)
        
        year = int(year_str)
        REIWA_HEURISTIC_THRESHOLD = 5  # 令和5年(2023年)まで

        if year <= REIWA_HEURISTIC_THRESHOLD:
            seireki = 2018 + year # Reiwa
        else:
            seireki = 1988 + year # Heisei
        
        return match.group(0).replace(year_str, str(seireki))
    
    text = RE_WAREKI_ABBREVIATED.sub(convert_wareki_abbreviated, text)
    
    # Step 4: Hyphen Processing
    import uuid
    placeholders = {}
    for wrong, correct in KATAKANA_HYPHEN_PRE_NORMALIZATION.items():
        pattern_str = HYPHEN_LIKE_CHARS.join(map(re.escape, wrong.split('-')))
        text = re.sub(pattern_str, correct, text)
    for exclusion in KATAKANA_HYPHEN_EXCLUSIONS:
        pattern_str = HYPHEN_LIKE_CHARS.join(map(re.escape, exclusion.split('-')))
        def replacer(match):
            placeholder = f"__PLACEHOLDER_{uuid.uuid4().hex}__"
            placeholders[placeholder] = match.group(0)
            return placeholder
        text = re.compile(pattern_str).sub(replacer, text)
    
    text = RE_KATAKANA_HYPHEN.sub(r'\1ー', text)
    text = RE_HYPHEN_LIKE.sub('-', text)
    text = re.sub(r'([ぁ-んァ-ヴ一-龠])-(?=[ぁ-んァ-ヴ一-龠])', r'\1', text)
    
    for placeholder, original_value in placeholders.items():
        text = text.replace(placeholder, original_value)

    return text.strip()
import subprocess
import os
from pathlib import Path

# --- 設定 ---
OUTPUT_FILENAME = "prompt_source.md"

# プロンプトに含めないファイル、ディレクトリ、拡張子のパターン
EXCLUDE_PATTERNS = [
    ".git/",
    ".gitignore",
    ".venv/",
    "__pycache__/",
    "data/",
    ".vscode/",
    "LICENSE",
    "__init__.py",
    ".db",
    ".sqlite",
    ".DS_Store",
    "create_prompt.py",
    OUTPUT_FILENAME,
]

# --- メインロジック ---

def get_git_tracked_files():
    """Gitで追跡されているファイルのリストを取得する"""
    try:
        result = subprocess.run(
            ['git', 'ls-files'], 
            capture_output=True, 
            text=True, 
            check=True,
            encoding='utf-8'
        )
        return result.stdout.strip().split('\n')
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("[警告] 'git ls-files' コマンドの実行に失敗しました。")
        print("       Gitがインストールされているか、リポジトリ内で実行しているか確認してください。")
        return []

def filter_files(file_list):
    """除外パターンに基づいてファイルのリストをフィルタリングする"""
    filtered_list = []
    for filepath_str in file_list:
        path = Path(filepath_str)
        path_posix = path.as_posix() 
        
        is_excluded = False
        for pattern in EXCLUDE_PATTERNS:
            if pattern.endswith('/'):
                if path_posix.startswith(pattern):
                    is_excluded = True
                    break
            elif path.name == pattern:
                is_excluded = True
                break
            elif path_posix.endswith(pattern):
                is_excluded = True
                break
        
        if not is_excluded:
            filtered_list.append(filepath_str)
            
    return sorted(filtered_list)

def get_markdown_fence(filepath):
    """
    ファイルタイプに応じてMarkdownのコードフェンス(区切り文字)を返す。
    .mdファイルの場合は4つのバッククォート、それ以外は3つ。
    """
    return "````" if Path(filepath).suffix.lower() == '.md' else "```"

def get_language_hint(filepath):
    """ファイル拡張子からMarkdownの言語ヒントを取得する"""
    ext = Path(filepath).suffix.lower()
    lang_map = {
        '.py': 'python',
        '.md': 'markdown',
        '.txt': 'text',
        '.json': 'json',
        '.yml': 'yaml',
        '.yaml': 'yaml',
    }
    return lang_map.get(ext, '')

def create_prompt_file():
    """プロジェクトのソースコードを単一のMarkdownファイルにまとめる"""
    
    all_git_files = get_git_tracked_files()
    if not all_git_files:
        return
        
    files_to_include = filter_files(all_git_files)
    
    if os.path.exists(OUTPUT_FILENAME):
        os.remove(OUTPUT_FILENAME)
        
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as outfile:
        outfile.write(f"# Project Source Code for Prompt\n\n")
        
        for filepath in files_to_include:
            print(f"Processing: {filepath}")
            
            # === ▼▼▼ 修正箇所 ▼▼▼ ===
            lang = get_language_hint(filepath)
            fence = get_markdown_fence(filepath) # ファイルタイプに応じた区切り文字を取得
            
            # --- ファイルヘッダーの書き込み ---
            outfile.write("---\n")
            outfile.write(f"- {Path(filepath).as_posix()}\n")
            outfile.write(f"{fence}{lang}\n") # 取得した区切り文字を使用
            # ========================
            
            # --- ファイル内容の書き込み ---
            try:
                with open(filepath, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    outfile.write(content.strip() + "\n")
            except Exception as e:
                print(f"  [エラー] ファイル読み込み中に問題が発生しました {filepath}: {e}")
                outfile.write(f"# ERROR READING FILE: {e}\n")

            # --- ファイルフッターの書き込み ---
            outfile.write(f"{fence}\n") # ヘッダーと同じ区切り文字を使用

    print(f"\nプロンプトファイル '{OUTPUT_FILENAME}' を正常に作成しました。")
    print("このファイルの内容をコピーして、次の会話のプロンプトとして使用できます。")

if __name__ == "__main__":
    create_prompt_file()
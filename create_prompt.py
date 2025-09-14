import os

# プロンプトに含めるファイルのリスト (git ls-treeの結果に基づく)
FILES_TO_INCLUDE = [
    '.gitignore',
    'LICENSE', # LICENSEファイルを追加
    'README.md',
    'config.py',
    # 'data/download/.gitkeep', # .gitkeepは中身が空なので不要
    'main.py',
    'models/__init__.py',
    'models/api_models.py',
    'pipeline/__init__.py',
    'pipeline/manager.py',
    'pipeline/stages.py',
    'requirements.txt',
    'utils/__init__.py',
    'utils/normalization.py',
]

OUTPUT_FILENAME = "prompt_source.txt"

def create_prompt_file():
    """プロジェクトのソースコードを単一のテキストファイルにまとめる"""
    
    # 既存の出力ファイルを削除
    if os.path.exists(OUTPUT_FILENAME):
        os.remove(OUTPUT_FILENAME)
        
    with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as outfile:
        outfile.write(f"# Project Source Code for Prompt\n\n")
        
        for filepath in FILES_TO_INCLUDE:
            print(f"Processing: {filepath}")
            
            # --- ファイルヘッダーの書き込み ---
            outfile.write("--- " + "="*20 + "\n")
            outfile.write(f"--- START OF FILE: {filepath.replace(os.sep, '/')}\n")
            outfile.write("--- " + "="*20 + "\n\n")
            
            # --- ファイル内容の書き込み ---
            try:
                with open(filepath, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    outfile.write(content)
            except FileNotFoundError:
                print(f"  [Warning] File not found, skipping: {filepath}")
                outfile.write("# FILE NOT FOUND\n")
            except Exception as e:
                print(f"  [Error] Could not read file {filepath}: {e}")
                outfile.write(f"# ERROR READING FILE: {e}\n")

            # --- ファイルフッターの書き込み ---
            outfile.write("\n\n--- " + "="*20 + "\n")
            outfile.write(f"--- END OF FILE: {filepath.replace(os.sep, '/')}\n")
            outfile.write("--- " + "="*20 + "\n\n\n")

    print(f"\nSuccessfully created '{OUTPUT_FILENAME}'.")
    print("You can now copy the content of this file into the prompt.")

if __name__ == "__main__":
    create_prompt_file()
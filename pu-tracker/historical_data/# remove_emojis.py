# remove_emojis.py
import os
import re

def remove_emojis_from_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    changed = False
    new_lines = []
    for line in lines:
        # Remove all non-ASCII characters (including emojis)
        new_line = re.sub(r'[^\x00-\x7F]+', '', line)
        if new_line != line:
            changed = True
        new_lines.append(new_line)
    if changed:
        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        print(f"Cleaned: {filepath}")

def scan_and_clean(root_dir):
    for dirpath, _, filenames in os.walk(root_dir):
        for filename in filenames:
            if filename.endswith(".py"):
                filepath = os.path.join(dirpath, filename)
                remove_emojis_from_file(filepath)

if __name__ == "__main__":
    # Set this to your project root
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
    scan_and_clean(PROJECT_ROOT)
    print("Done cleaning all .py files.")
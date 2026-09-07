#!/usr/bin/env python3
"""
md_to_word.py - Convert a Markdown file to Word (.docx).
Output is saved in the same folder as the input .md file.
If a .docx already exists, a timestamp is appended to avoid overwriting.

Usage:
    python md_to_word.py <file.md>
"""

import sys
import os
import pypandoc
from datetime import datetime

PAGEBREAK_OPENXML = """```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```"""


def normalize_page_breaks(markdown_text: str) -> str:
    normalized_lines = []
    first_newpage_skipped = False
    for line in markdown_text.splitlines():
        if line.strip() == "\\newpage":
            if not first_newpage_skipped:
                first_newpage_skipped = True  # skip it — no page break inserted
            else:
                normalized_lines.append(PAGEBREAK_OPENXML)
        else:
            normalized_lines.append(line)
    return "\n".join(normalized_lines)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python md_to_word.py <file.md>")
        sys.exit(1)

    input_path = sys.argv[1]

    if not os.path.isfile(input_path) or not input_path.lower().endswith(".md"):
        print(f"[ERROR] Not a valid .md file: {input_path}")
        sys.exit(1)

    folder = os.path.dirname(os.path.abspath(input_path))
    base_name = os.path.splitext(os.path.basename(input_path))[0]
    output_path = os.path.join(folder, base_name + ".docx")

    if os.path.exists(output_path):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(folder, f"{base_name}_{timestamp}.docx")

    try:
        with open(input_path, "r", encoding="utf-8") as md_file:
            markdown_text = md_file.read()

        markdown_text = normalize_page_breaks(markdown_text)

        pypandoc.convert_text(
            markdown_text,
            "docx",
            format="markdown+raw_attribute+raw_tex",
            outputfile=output_path,
        )
        print(f"[OK] {os.path.basename(input_path)} -> {os.path.basename(output_path)}")
    except Exception as e:
        print(f"[FAIL] {e}")
        sys.exit(1)

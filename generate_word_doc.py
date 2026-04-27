import markdown
import os

md_path = "Project_Documentation.md"
doc_path = "Project_Documentation.doc"

with open(md_path, "r", encoding="utf-8") as f:
    text = f.read()

html = markdown.markdown(text, extensions=['tables', 'fenced_code'])

doc_content = f"""
<html>
<head>
<meta charset="utf-8">
<style>
    body {{ font-family: Arial, sans-serif; line-height: 1.6; margin: 40px; }}
    h1, h2, h3 {{ color: #333; }}
    pre {{ background: #f4f4f4; padding: 10px; border: 1px solid #ddd; }}
    code {{ font-family: Consolas, monospace; background: #f4f4f4; padding: 2px 5px; }}
    table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #f2f2f2; }}
</style>
</head>
<body>
{html}
</body>
</html>
"""

with open(doc_path, "w", encoding="utf-8") as f:
    f.write(doc_content)

print(f"Generated {doc_path} successfully!")

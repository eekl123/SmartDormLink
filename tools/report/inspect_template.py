"""Inspect the report template structure so the generator can target exact anchors."""
import sys
from docx import Document

path = sys.argv[1]
doc = Document(path)
print("paragraphs:", len(doc.paragraphs), "tables:", len(doc.tables), "sections:", len(doc.sections))
for i, p in enumerate(doc.paragraphs):
    text = p.text.strip()
    if text:
        print(f"{i:4d} | {p.style.name:22s} | {text[:78]}")
print("--- tables ---")
for ti, tb in enumerate(doc.tables):
    print(ti, "rows", len(tb.rows), "cols", len(tb.columns), "| first cell:", tb.rows[0].cells[0].text[:24])

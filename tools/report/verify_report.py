"""Structural verification of the generated report (text-level, no rendering)."""
import os

from docx import Document
from docx.oxml.ns import qn

PATH = r'D:\大作业\鸿蒙高级应用开发工程师认证-20230313230-赵硕-期末大作业报告.docx'

doc = Document(PATH)
print('file size KB:', round(os.path.getsize(PATH) / 1024, 1))
print('paragraphs:', len(doc.paragraphs), 'tables:', len(doc.tables))

print('\n--- cover ---')
for p in doc.paragraphs[:20]:
    if p.text.strip():
        print('  ', p.text.strip()[:60])

print('\n--- headings ---')
for p in doc.paragraphs:
    if p.style.name in ('Heading 1', 'Heading 2'):
        print(f'  {p.style.name:10s} {p.text.strip()}')

print('\n--- tables ---')
for i, t in enumerate(doc.tables):
    first = t.rows[0].cells[0].text.strip().replace('\n', ' ')
    print(f'  [{i}] rows={len(t.rows)} cols={len(t.columns)} head="{first[:26]}"')

print('\n--- images ---')
blips = doc.element.body.findall('.//' + qn('a:blip'))
print('  embedded images:', len(blips))

print('\n--- placeholders ---')
for p in doc.paragraphs:
    if '【此处插入' in p.text:
        print('  ', p.text.strip()[:70])

print('\n--- key facts present? ---')
text = '\n'.join(p.text for p in doc.paragraphs)
for t in doc.tables:
    for row in t.rows:
        for cell in row.cells:
            text += '\n' + cell.text
for needle in ('赵硕', '20230313230', '23 物联网工程 2 班', 'DormLink',
               'runEngine', 'Preferences', 'RDB', 'tests 36', '通过'):
    print(f'  {needle:18s}', 'OK' if needle in text else 'MISSING')
print('\n--- git table sample ---')
print('  ', doc.tables[-2].rows[1].cells[0].text, '|', doc.tables[-2].rows[1].cells[1].text[:40])

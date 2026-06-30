#!/usr/bin/env python3
"""Reconstruct the OIAH lab Schedule-of-Activities matrix from protocol JSON
coordinates. Visit columns come from each page's 'Visit Number' row; each X/O
mark is assigned to the nearest lab-row (by y) and nearest visit (by x)."""
from pathlib import Path
import json

import os
PROTO = os.environ.get('RFP_PROTOCOL', '/mnt/workspace/input/OIAH protocol markdown.txt')
VISIT_ORDER = ['1','2','3','4','5','6','7','8','9','ED','V801']
LAB_ROWS = [
    'Hematology','Clinical chemistry','Lipids','HbA1c','Vitamin B12','Vitamin B6',
    'Serum folate','Homocysteine','Methylmalonic acid','Serum pregnancy',
    'Urine pregnancy test','Follicle-stimulating hormone','Urinalysis','Urine drug screen',
    'Thyroid stimulating hormone','HIV testing','HCV screening tests','HBV screening tests',
    'eGFR','C-reactive protein','Anti-nuclear antibody','PK samples - predose',
    'PK samples - random','PK samples - postdose','Genetics Sample','Exploratory Biomarker',
]
LAB_PAGES = [26, 27, 28, 29]

def _load_pages(p):
    lines = Path(p).read_text(errors='replace').splitlines()
    for i, l in enumerate(lines):
        if l.strip() == '{' and i > 5:
            return json.loads('\n'.join(lines[i:]))['pages']

def _visit_columns(items):
    vn = [it for it in items if it['text'].strip() == 'Visit Number']
    if not vn: return None
    vy = vn[0]['y']
    return {it['text'].strip(): it['x'] for it in items
            if abs(it['y']-vy) < 4 and it['text'].strip() in VISIT_ORDER}

def _nearest(val, mapping, tol):
    best, bd = None, tol
    for k, x in mapping.items():
        if abs(val-x) <= bd: best, bd = k, abs(val-x)
    return best

def build_matrix():
    pages = {p['page']: p for p in _load_pages(PROTO)}
    matrix = {r: {v: '' for v in VISIT_ORDER} for r in LAB_ROWS}
    for pno in LAB_PAGES:
        items = pages[pno]['textItems']
        cols = _visit_columns(items)
        if not cols: continue
        labels = {}
        for it in items:
            t = it['text'].strip()
            for key in LAB_ROWS:
                if t == key or t.startswith(key):
                    labels.setdefault(key, it['y'])
        label_ys = sorted(labels.items(), key=lambda kv: kv[1])
        for it in items:
            t = it['text'].strip()
            if t in ('X','O','x','o') and label_ys:
                row = min(label_ys, key=lambda kv: abs(kv[1]-it['y']))
                if abs(row[1]-it['y']) <= 9:
                    col = _nearest(it['x'], cols, 11)
                    if col: matrix[row[0]][col] = t.upper()
    rows = [[r] + [matrix[r][v] for v in VISIT_ORDER] for r in LAB_ROWS]
    return VISIT_ORDER, rows

if __name__ == '__main__':
    visits, rows = build_matrix()
    hdr = 'LAB ROW'.ljust(30) + ' '.join(v.rjust(4) for v in visits)
    print(hdr); print('-'*len(hdr))
    for r in rows:
        print(r[0].ljust(30) + ' '.join((m or '·').rjust(4) for m in r[1:]))
    print('\n', len(rows), 'rows x', len(visits), 'visits')

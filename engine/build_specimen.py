#!/usr/bin/env python3
"""Reconstruct the two Specimen-Management sections (Referral Lab Samples and
Storage Samples / LTS) from the completed OIAH RFP's positional JSON.
Returns {row_label: {column: value}} for each section. N/A is a real value."""
from pathlib import Path
import json

import os
RFP = os.environ.get('RFP_PREV', '/mnt/workspace/input/rfp markdown.txt')

def _pages():
    lines = Path(RFP).read_text(errors='replace').splitlines()
    for i, l in enumerate(lines):
        if l.strip() == '{' and i > 5:
            return {p['page']: p for p in json.loads('\n'.join(lines[i:]))['pages']}

PROP = ['Analyte name','Analyte','Validated assay','Lilly proprietary assay',
        'Ref Lab contract owner','Assay lab city, state, country','Assay lab',
        'Special collection tube required?','Special collection tube',
        'Special processing requirements','Sample type','Sample vol / collection',
        '# aliquots/expected sample','Total # of expected samples for the trial',
        '# of results per expected sample','Post-LPV storage','# post-LPV storage aliquots']
PROP_SORTED = sorted(PROP, key=len, reverse=True)

def clean(v):
    v = ''.join(ch for ch in v if not (0xE000 <= ord(ch) <= 0xF8FF))  # drop private-use glyphs
    out = []
    for t in v.split():                       # collapse repeated tokens (NA NA -> NA)
        if not out or out[-1] != t: out.append(t)
    return ' '.join(out).strip()

def _reconstruct(items, col_centers, tol=46):
    labels = {}
    for it in items:
        if it['x'] < 210:
            t = it['text'].strip()
            for lab in PROP_SORTED:
                if t.startswith(lab):
                    labels.setdefault(lab, it['y']); break
    order = sorted(labels.items(), key=lambda kv: kv[1])
    out = {}
    for i, (lab, y) in enumerate(order):
        ynext = order[i+1][1] if i+1 < len(order) else y+13
        band = [it for it in items if (y-6) <= it['y'] < (ynext-3) and it['x'] >= 210]
        cells = {}
        for cname, cx in col_centers.items():
            vals = sorted([it for it in band if abs(it['x']-cx) <= tol],
                          key=lambda it: (it['y'], it['x']))
            cells[cname] = clean(' '.join(v['text'].strip() for v in vals))
        out[lab] = cells
    return out

def build():
    P = _pages()
    ref_items = P[14]['textItems'] + [it for it in P[15]['textItems'] if it['y'] < 160]
    referral = _reconstruct(ref_items, {'LTS PK': 265}, tol=70)
    p16 = [{**it, 'y': it['y'] + 1000} for it in P[16]['textItems'] if it['y'] < 250]
    sto_items = [it for it in P[15]['textItems'] if it['y'] >= 190] + p16
    storage = _reconstruct(sto_items,
        {'LTS DNA': 267, 'LTS Serum': 365, 'LTS Plasma': 466, 'LTS RNA': 565}, tol=46)
    return referral, storage

if __name__ == '__main__':
    ref, sto = build()
    print('=== REFERRAL (LTS PK) ===')
    for lab, c in ref.items():
        print(f'  {lab:42} -> {c["LTS PK"]!r}')
    print('\n=== STORAGE (DNA | Serum | Plasma | RNA) ===')
    for lab, c in sto.items():
        print(f'  {lab:42} | {c["LTS DNA"]:20} | {c["LTS Serum"]:14} | {c["LTS Plasma"]:12} | {c["LTS RNA"]}')

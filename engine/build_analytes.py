#!/usr/bin/env python3
"""Reconstruct the protocol's Appendix 2 'Clinical Laboratory Tests' table as
proper (Test, Comment) rows from JSON coordinates. Test column ~x57, Comment
column ~x234; editorial 'Commented [..]' annotations (x>=410) are excluded."""
from pathlib import Path
import json, re

import os
PROTO = os.environ.get('RFP_PROTOCOL', '/mnt/workspace/input/OIAH protocol markdown.txt')

def _pages():
    lines = Path(PROTO).read_text(errors='replace').splitlines()
    for i, l in enumerate(lines):
        if l.strip() == '{' and i > 5:
            return {p['page']: p for p in json.loads('\n'.join(lines[i:]))['pages']}

SKIP = re.compile(r'^(CONFIDENTIAL|Author and Content|Approved on|J6V-MC-OIAH'
                  r'|Commented \[|Comments$|\d{1,3}$)')

def build():
    P = _pages()
    appendix = sorted(n for n, p in P.items()
                      if 'Assayed by Lilly' in p.get('text', '')
                      and 'Clinical Laboratory Tests' in p.get('text', ''))
    rows = []
    for pno in appendix:
        items = P[pno]['textItems']
        hdr = [it for it in items if it['text'].strip().startswith('Clinical Laboratory Tests')]
        start_y = (hdr[0]['y'] + 6) if hdr else 130
        body = [it for it in items if it['y'] > start_y]
        # cluster into rows by y
        body.sort(key=lambda it: (round(it['y']), it['x']))
        clusters, cur, cy = [], [], None
        for it in body:
            y = round(it['y'])
            if cy is None or abs(y - cy) > 3:
                if cur: clusters.append(cur)
                cur, cy = [], y
            cur.append(it)
        if cur: clusters.append(cur)
        for cl in clusters:
            left = sorted([it for it in cl if it['x'] < 210], key=lambda it: it['x'])
            right = sorted([it for it in cl if 210 <= it['x'] < 410
                            and not re.fullmatch(r'\d{1,3}', it['text'].strip())],
                           key=lambda it: it['x'])
            test = ' '.join(it['text'].strip() for it in left).strip()
            comment = ' '.join(it['text'].strip() for it in right).strip()
            if SKIP.match(test):       # page furniture / annotation line
                continue
            if test:
                rows.append([test, comment])
            elif comment and rows:     # wrapped comment continuation
                rows[-1][1] = (rows[-1][1] + ' ' + comment).strip()
    return rows

if __name__ == '__main__':
    rows = build()
    print(f'{len(rows)} analyte rows\n' + '-'*70)
    for t, c in rows:
        print(f'  {t[:42]:42} | {c[:40]}')

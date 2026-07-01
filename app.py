#!/usr/bin/env python3
"""Central Lab RFP Generator — pywebview desktop app.
Threaded API: heavy operations run in background, JS polls for results.
"""
import os, sys, json, base64, tempfile, subprocess, threading, uuid, logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'engine'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
logger = logging.getLogger('rfp')

class API:
    def __init__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix='rfp_'))
        self.parsed = {}
        self.template = None
        self.template_name = ''
        self.gen_docx = None
        self.gen_name = ''
        self.gen_report = ''
        self.review_fields = []
        self._agent = None
        self._tasks = {}
        self._lock = threading.Lock()
        self._parse_count = 0  # track how many PDFs parsed

    # ── Task system (threaded) ──
    def _new_task(self, target, args=(), kwargs=None):
        tid = str(uuid.uuid4())[:8]
        with self._lock:
            self._tasks[tid] = {'status': 'pending', 'result': None, 'progress': 0, 'message': ''}
        threading.Thread(target=self._run_task, args=(tid, target, args, kwargs or {}), daemon=True).start()
        return tid

    def _run_task(self, tid, target, args, kwargs):
        try:
            with self._lock:
                self._tasks[tid]['status'] = 'running'
                self._tasks[tid]['message'] = 'Starting...'
            result = target(tid, *args, **kwargs)
            with self._lock:
                self._tasks[tid]['status'] = 'done'
                self._tasks[tid]['result'] = result
                self._tasks[tid]['progress'] = 100
                self._tasks[tid]['message'] = 'Complete'
        except Exception as e:
            logger.exception('Task %s failed', tid)
            with self._lock:
                self._tasks[tid]['status'] = 'error'
                self._tasks[tid]['result'] = str(e)
                self._tasks[tid]['message'] = str(e)

    def _update_task(self, tid, **kw):
        with self._lock:
            self._tasks[tid].update(kw)

    def task_status(self, tid):
        with self._lock:
            t = self._tasks.get(tid)
            if t is None:
                return {'status': 'unknown'}
            return dict(t)

    def task_result(self, tid):
        with self._lock:
            t = self._tasks.pop(tid, None)
            if t is None:
                return {'status': 'unknown'}
            return dict(t)

    # ── Ping ──
    def ping(self):
        return 'pong'

    # ── Parse PDF ──
    def start_parse(self, field, b64):
        return self._new_task(self._do_parse, args=(field, b64))

    def _do_parse(self, tid, field, b64):
        raw = base64.b64decode(b64)
        # Try liteparse first
        try:
            from liteparse import LiteParse
            parser = LiteParse()
            result = parser.parse(raw)
            md = result.text
            pages = []
            for p in result.pages:
                pages.append({
                    'page': p.page_num, 'width': p.width, 'height': p.height,
                    'text': p.text,
                    'textItems': [
                        {'text': i.text, 'x': i.x, 'y': i.y, 'width': i.width, 'height': i.height}
                        for i in p.text_items
                    ],
                })
            full = md + '\n' + json.dumps({'pages': pages}, indent=2)
            self.parsed[field] = full
            self._parse_count += 1
            return {'ok': True, 'field': field, 'chars': len(full), 'engine': 'liteparse', 'pages': len(pages)}
        except Exception as e:
            logger.warning('liteparse failed, falling back to PyMuPDF: %s', e)
        # Fallback to PyMuPDF
        try:
            import fitz
            doc = fitz.open(stream=base64.b64decode(b64), filetype='pdf')
            text = ''
            pages = []
            for i, page in enumerate(doc):
                txt = page.get_text()
                text += txt + '\n\n'
                pages.append({'page': i+1, 'width': page.rect.width, 'height': page.rect.height, 'text': txt, 'textItems': []})
            doc.close()
            full = text + '\n' + json.dumps({'pages': pages}, indent=2)
            self.parsed[field] = full
            self._parse_count += 1
            return {'ok': True, 'field': field, 'chars': len(full), 'engine': 'pymupdf', 'pages': len(pages)}
        except Exception as e2:
            return {'ok': False, 'error': f'PyMuPDF: {e2}'}

    # ── Upload template ──
    def upload_template(self, b64, name):
        self.template = base64.b64decode(b64)
        self.template_name = name
        return {'ok': True, 'name': name, 'size': len(self.template)}

    # ── Generate ──
    def start_generate(self, answers_json):
        return self._new_task(self._do_generate, args=(answers_json,))

    def _do_generate(self, tid, answers_json):
        io_in = self.tmp / 'in'
        io_out = self.tmp / 'out'
        io_in.mkdir(parents=True, exist_ok=True)
        io_out.mkdir(parents=True, exist_ok=True)

        for f, name in [('f-protocol','protocol'), ('f-design','design'), ('f-prev','previous_rfp')]:
            p = io_in / f'{name}.md'
            p.write_text(self.parsed.get(f, ''))
            self._update_task(tid, message=f'Writing {name}.md...')
        if self.template:
            (io_in / 'template.docx').write_bytes(self.template)

        env = os.environ.copy()
        env.update({
            'RFP_INPUT_DIR': str(io_in),
            'RFP_OUTPUT_DIR': str(io_out),
            'RFP_PROTOCOL': str(io_in / 'protocol.md'),
            'RFP_DESIGN': str(io_in / 'design.md'),
            'RFP_PREV': str(io_in / 'previous_rfp.md'),
            'RFP_TEMPLATE': str(io_in / 'template.docx'),
            'RFP_OUTDOC': str(io_out / 'RFP.docx'),
            'RFP_REPORT': str(io_out / 'report.md'),
            'RFP_ANSWERS': answers_json,
        })

        engine = str(Path(__file__).parent / 'engine' / 'populate_rfp.py')
        self._update_task(tid, message='Running RFP engine...', progress=30)
        result = subprocess.run([sys.executable, engine], env=env,
                                capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            err = result.stderr or result.stdout or 'Unknown error'
            return {'ok': False, 'error': err[:2000]}

        self._update_task(tid, message='Reading output...', progress=80)
        docx_bytes = (io_out / 'RFP.docx').read_bytes()
        report = (io_out / 'report.md').read_text()

        self.gen_docx = base64.b64encode(docx_bytes).decode()
        self.gen_name = f'Central_Laboratory_RFP_{__import__("datetime").date.today().isoformat()}.docx'
        self.gen_report = report

        # Extract review fields
        rv = []
        for line in report.split('\n'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 5 and parts[4] == 'review':
                rv.append({'field': parts[1], 'value': parts[2], 'source': parts[3]})
        self.review_fields = rv

        filled = report.count('| filled')
        computed = report.count('| computed')
        review = report.count('| review')

        return {
            'ok': True,
            'filled': filled, 'computed': computed, 'review': review,
            'total': filled + computed + review,
            'name': self.gen_name,
            'reviewFields': rv,
        }

    # ── AI Agent ──
    def agent_status(self):
        return {'ready': self._agent is not None and self._agent.is_ready}

    def start_agent_load(self):
        return self._new_task(self._do_agent_load)

    def _do_agent_load(self, tid):
        from agent import RFPAgent
        self._agent = RFPAgent()
        self._agent.load_model()
        return {'ok': True}

    def start_agent_answer(self, field_name):
        return self._new_task(self._do_agent_answer, args=(field_name,))

    def _do_agent_answer(self, tid, field_name):
        if not self._agent or not self._agent.is_ready:
            return {'ok': False, 'error': 'Model not loaded'}
        ctx = '\n\n'.join(self.parsed.get(f, '')[:15000] for f in ['f-protocol','f-design','f-prev'])[:30000]
        try:
            r = self._agent.answer(ctx, field_name)
            if r:
                return {'ok': True, 'value': r['value'], 'confidence': round(r['confidence'], 3)}
            return {'ok': True, 'value': None, 'confidence': 0}
        except Exception as e:
            return {'ok': False, 'error': str(e)}

    def agent_patch(self, overrides_json):
        from engine.patch_docx import patch_review_tokens
        overrides = json.loads(overrides_json)
        src = str(self.tmp / 'out' / 'RFP.docx')
        dst = str(self.tmp / 'out' / 'RFP_patched.docx')
        n = patch_review_tokens(src, overrides, dst)
        self.gen_docx = base64.b64encode(Path(dst).read_bytes()).decode()
        return {'ok': True, 'patched': n}

    # ── Download ──
    def get_docx(self):
        if self.gen_docx:
            return {'ok': True, 'data': self.gen_docx, 'name': self.gen_name}
        return {'ok': False, 'error': 'No document'}

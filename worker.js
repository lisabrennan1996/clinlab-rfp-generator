/* ─────────────────────────────────────────────────────────────────────────
   worker.js — Web Worker (module) for heavy operations
   Runs liteparse (PDF parsing) and Pyodide (Python engine) off the
   main thread so the browser tab never freezes.
   ───────────────────────────────────────────────────────────────────────── */
import { LiteParse, default as initLiteparse } from './liteparse/liteparse_wasm.js';

let liteparseReady = false;
let py = null;

// Top-level error reporting
self.addEventListener('error', (e) => {
  self.postMessage({ id: -1, type: 'error', error: e.message || 'Uncaught worker error' });
});

self.addEventListener('message', async (e) => {
  const { id, cmd, args } = e.data;
  function progress(msg, pct) {
    self.postMessage({ id, type: 'progress', msg, pct });
  }
  try {
    let result;
    switch (cmd) {

      case 'parsePDF': {
        progress('Loading PDF parser…', 10);
        if (!liteparseReady) {
          await initLiteparse('./liteparse/liteparse_wasm_bg.wasm');
          liteparseReady = true;
        }
        progress('Parsing document…', 20);
        const parser = new LiteParse({ outputFormat: 'markdown', ocrEnabled: false });
        const bytes = new Uint8Array(args.data);
        const parsed = await parser.parse(bytes);
        progress('Building result…', 30);
        const pages = parsed.pages.map(p => ({
          page: p.pageNumber, width: p.width, height: p.height,
          text: p.items.map(i => i.text).join(' '),
          textItems: p.items.map(i => ({
            text: i.text, x: i.bbox[0], y: i.bbox[1],
            width: i.bbox[2] - i.bbox[0], height: i.bbox[3] - i.bbox[1],
          })),
        }));
        result = parsed.text + '\n' + JSON.stringify({ pages }, null, 2);
        break;
      }

      case 'bootPyodide': {
        progress('Loading Python runtime…', 30);
        importScripts('./pyodide/pyodide.js');
        py = await loadPyodide({ indexURL: './pyodide/' });
        progress('Installing packages…', 50);
        await py.loadPackage(['micropip', 'lxml']);
        await py.runPythonAsync(`import micropip; await micropip.install('python-docx')`);
        progress('Loading engine…', 70);
        py.FS.mkdir('/engine');
        for (const m of ['build_soa','build_specimen','build_analytes','populate_rfp','patch_docx']) {
          const resp = await fetch(`./engine/${m}.py`);
          const src = await resp.text();
          py.FS.writeFile(`/engine/${m}.py`, src);
        }
        py.runPython(`import sys; sys.path.insert(0, '/engine')`);
        result = 'ok';
        break;
      }

      case 'bootPyodideStatus':
        result = py !== null;
        break;

      case 'writeFile': {
        if (!py) throw new Error('Pyodide not booted');
        py.FS.writeFile(args.path, args.data);
        result = 'ok';
        break;
      }

      case 'readFile': {
        if (!py) throw new Error('Pyodide not booted');
        const data = py.FS.readFile(args.path);
        result = data;
        break;
      }

      case 'mkdir': {
        if (!py) throw new Error('Pyodide not booted');
        py.FS.mkdirTree(args.path);
        result = 'ok';
        break;
      }

      case 'runPython': {
        if (!py) throw new Error('Pyodide not booted');
        py.runPython(args.code);
        result = 'ok';
        break;
      }

      default:
        throw new Error('Unknown command: ' + cmd);
    }
    self.postMessage({ id, result });
  } catch (err) {
    self.postMessage({ id, error: err.message });
  }
});

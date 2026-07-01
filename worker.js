/* ─────────────────────────────────────────────────────────────────────────
   worker.js — Web Worker (module) for Pyodide only
   Liteparse PDF parsing is done on the main thread.
   ───────────────────────────────────────────────────────────────────────── */
let py = null;

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

      case 'bootPyodide': {
        progress('Loading Python runtime\u2026', 10);
        importScripts('./pyodide/pyodide.js');
        py = await loadPyodide({ indexURL: './pyodide/' });
        progress('Installing packages\u2026', 40);
        await py.loadPackage(['micropip', 'lxml']);
        await py.runPythonAsync(`import micropip; await micropip.install('python-docx')`);
        progress('Loading engine\u2026', 70);
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

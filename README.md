# Central Lab RFP Generator — Desktop App

A native desktop application that generates Central Lab RFPs from clinical study documents.

**No servers, no API keys, no WASM** — everything runs locally in Python.

## Quick Start

```bash
pip install -r requirements.txt
python run.py
```

The app will open a window. Drag-and-drop your PDFs and template, click Generate.

## How It Works

1. **Upload PDFs** — Drop protocol, design elements, and previous RFP PDFs into the zones
2. **Upload Template** — Drop the blank RFP .docx template
3. **Generate** — The engine extracts fields via regex from the parsed text and fills the template
4. **AI Agent (optional)** — Click "Send to Agent" to have a local Hugging Face QA model search the documents for fields the regex couldn't find
5. **Download** — Save the completed .docx

## Features

- **Drag & drop file upload** — No browsing needed
- **All fields optional** — Works with whatever documents you have
- **Threaded parsing** — UI stays responsive during PDF processing
- **AI gap-filling** — Local QA model (distilbert, ~250 MB, downloaded on first agent use)
- **liteparse + PyMuPDF fallback** — Best-effort PDF text extraction

## For Developers

### Project Structure

```
├── app.py          # Python API (threaded)
├── agent.py        # Local Hugging Face QA model
├── gui.py          # pywebview window launcher
├── run.py          # Dev launcher
├── build.spec      # PyInstaller config
├── ui/
│   ├── index.html    # Upload & Parse page
│   └── generate.html # Generate & AI Agent page
└── engine/
    ├── populate_rfp.py  # Core RFP generation
    ├── patch_docx.py    # AI patching
    ├── build_analytes.py
    ├── build_soa.py
    └── build_specimen.py
```

### Building a Distributable

**Windows (on a Windows machine):**

```bash
pip install -r requirements.txt
pyinstaller build.spec
```

The `.exe` will be in `dist/RFPGenerator.exe`.

**Note:** The PyInstaller build bundles a Python interpreter with all dependencies (~500 MB+ with torch). The AI agent (transformers/torch) can be excluded from the build if not needed — just comment out those lines in `requirements.txt`.

## Requirements

- Python 3.10+
- Windows 10+ (or macOS/Linux with pywebview support)
- 2 GB RAM (4 GB recommended for AI agent)
- ~500 MB disk for dependencies (or ~2 GB with torch/transformers)

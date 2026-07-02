# Central Lab RFP Generator — Desktop App

Generates populated Central Lab RFP documents from clinical study PDFs. No servers, no API keys — everything runs locally.

## Quick Install

### Windows

1. **Download** `clinlab-rfp-desktop.zip` from [Releases](https://github.com/lisabrennan1996/clinlab-rfp-generator/releases)
2. **Extract** the zip to a folder
3. **Double-click** `run_windows.bat`
   - *First run only:* It installs Python dependencies automatically (~1 minute)
4. The app window opens — drag-and-drop your PDFs and click Generate

### macOS / Linux

```bash
# Extract then run:
chmod +x run_macos.sh
./run_macos.sh
```

### Requirements

- **Python 3.10+** ([Download](https://www.python.org/downloads/))
- **2 GB RAM** (4 GB recommended if using AI agent)
- **Operating System:** Windows 10+, macOS 13+, or Linux with GTK

## How to Use

### Step 1: Upload Documents

![Upload screen](screenshot-upload.png)

| Zone | Required? | What to upload |
|------|-----------|----------------|
| Protocol / Protocol Amendment | Yes | Clinical study protocol PDF |
| Design Elements | Recommended | Study design elements PDF |
| Previous RFP | Optional | Prior completed RFP for reference |
| RFP Template | Pre-loaded | The blank RFP template (.docx) is built-in |

Drag PDF files onto the drop zones. They parse automatically with liteparse.

### Step 2: Generate RFP

1. Click **"Next: Generate RFP"**
2. Select study options (Decentralized, Penalties, Anatomic Pathology)
3. Click **"Generate RFP"**
4. Review fields the regex engine couldn't fill
5. Click **"Send to Agent"** to have the AI search the documents

### Step 3: Download

- **Download** the completed .docx
- Or **Download AI Enhanced** if you used the agent to fill gaps

## For Developers

### Project Structure

```
├── app.py          # Python API (threaded parsing, generation, AI)
├── agent.py        # BioBERT QA model (~440 MB, downloaded on first AI use)
├── gui.py          # pywebview window setup
├── run.py          # Dev launcher
├── run_windows.bat # Windows launcher (auto-setup)
├── run_macos.sh    # macOS/Linux launcher (auto-setup)
├── requirements.txt
├── template.docx   # Bundled RFP template
├── build.spec      # PyInstaller config (for creating .exe)
├── engine/
│   ├── extractors.py     # Regex-based field extraction (Lilly-optimized)
│   ├── populate_rfp.py   # Core RFP document generation
│   ├── patch_docx.py     # AI-based field patching
│   └── build_*.py        # Table reconstruction (analytes, SoA, specimen)
└── ui/
    ├── index.html    # Upload & Parse page
    └── generate.html # Generate & AI review page
```

### Building a Standalone .exe (Windows only)

For distributing to colleagues without Python:

```bash
# On a Windows machine with Python installed:
pip install -r requirements.txt
pip install pyinstaller
pyinstaller build.spec
```

The `.exe` will be in `dist/RFPGenerator.exe` (~500 MB with AI dependencies).

### Extraction Logic (Lilly-Optimized)

The extractors in `engine/extractors.py` use a cascade of patterns:

| Field | Priority Pattern |
|-------|-----------------|
| **Protocol Number** | `XXXX-XX-XXXXX` format (e.g., `H8H-MC-LAHD`) |
| **Compound** | `LY######` code → "Compound:" label → title drug name |
| **Phase** | Title context → "Phase:" label → Arabic/Roman numerals |
| **Enrollment** | `N = X` → "Approximately X patients" → "sample size: X" |
| **Min Age** | `≥ X years` → "Age X to Y" → "Inclusion Criteria: Age ≥ X" |

The extractors also normalize PDF text artifacts (spaced-out characters in codes).

## AI Agent

The app includes a local BioBERT QA model (`ktrapeznikov/biobert_v1.1_pubmed_squad_v2`):
- **~440 MB** downloaded on first use (cached locally)
- **No API key required** — runs entirely on your machine
- **No internet needed** after initial download
- Used via the "Send to Agent" button after generation

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `liteparse` install fails | The app falls back to PyMuPDF automatically |
| Agent model download fails | Check disk space (~1 GB needed). Retry. |
| Document won't parse | Try a different PDF (print-to-PDF from source) |
| App won't open | Run from terminal to see error messages |

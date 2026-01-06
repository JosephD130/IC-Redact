# IC Redact

Automatically detect and redact sensitive information from PDFs.

![IC Redact Screenshot](screenshot.png)

## What It Does

Project documents often contain PII that shouldn't be shared externally. IC Redact scans PDFs and automatically redacts:

- Social Security Numbers
- Phone Numbers
- Email Addresses
- Physical Addresses
- Dates of Birth
- Bank Account Numbers
- Credit Card Numbers
- Names (common first names)
- Custom words/phrases you specify

## Privacy

**IC Redact runs 100% offline.** Your files never leave your computer. All processing happens locally.

## Download

Pre-built applications available at [infrastructure-catalyst.com/resources](https://www.infrastructure-catalyst.com/resources/)

- **Windows** - Standalone .exe for Windows 10/11
- **Mac** - Native .app for macOS

## Run From Source

### Requirements
- Python 3.8+
- PyQt6
- PyMuPDF

### Install Dependencies
```bash
pip install PyQt6 pymupdf
```

### Run
```bash
python ic_redact.py
```

## Build Executable

### Windows
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "IC Redact" --add-data "logo.jpg;." ic_redact.py
```

### Mac
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "IC Redact" --add-data "logo.jpg:." ic_redact.py
```

The executable will be in the `dist/` folder.

## License

MIT License - See [LICENSE](LICENSE) file.

## About

Built by [Infrastructure Catalyst](https://www.infrastructure-catalyst.com) - Tools and systems for infrastructure project managers.

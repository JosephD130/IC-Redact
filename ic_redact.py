"""
IC Redact v4 - Infrastructure Catalyst
Cross-platform version using PyQt6
https://infrastructurecatalyst.com
"""

import sys
import os
import re
import json
import threading
from pathlib import Path
from datetime import datetime

# Install dependencies if needed
def install(package):
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])

try:
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
        QHBoxLayout, QLabel, QPushButton, QTextEdit, QCheckBox, QRadioButton,
        QFileDialog, QMessageBox, QTabWidget, QFrame, QButtonGroup, QScrollArea,
        QDialog, QSplitter)
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap
except ImportError:
    install("PyQt6")
    from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
        QHBoxLayout, QLabel, QPushButton, QTextEdit, QCheckBox, QRadioButton,
        QFileDialog, QMessageBox, QTabWidget, QFrame, QButtonGroup, QScrollArea,
        QDialog, QSplitter)
    from PyQt6.QtCore import Qt, QThread, pyqtSignal
    from PyQt6.QtGui import QFont, QColor, QPalette, QPixmap

try:
    import fitz
except ImportError:
    install("pymupdf")
    import fitz

# Get base path for bundled resources
def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".ic_redact_config.json")

# PII Patterns
PII_PATTERNS = {
    "SSN": [r"\b\d{3}-\d{2}-\d{4}\b", r"\b\d{3}\s\d{2}\s\d{4}\b"],
    "PHONE": [r"\b\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"],
    "EMAIL": [r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"],
    "CREDIT_CARD": [r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"],
    "BANK_ACCOUNT": [r"\b\d{8,17}\b"],
    "DATE_OF_BIRTH": [
        r"\b(0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])[-/](19|20)\d{2}\b",
        r"\b(19|20)\d{2}[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b",
        r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+(19|20)\d{2}\b",
    ],
    "ADDRESS": [
        r"\b\d{1,5}\s+[\w\s]{1,30}\s+(Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd|Drive|Dr|Lane|Ln|Way|Court|Ct)\.?\b",
        r"\b[A-Z][a-z]+,?\s+[A-Z]{2}\s+\d{5}(-\d{4})?\b",
    ],
}

COMMON_NAMES = [
    "James", "John", "Robert", "Michael", "William", "David", "Richard", "Joseph", "Thomas", "Charles",
    "Mary", "Patricia", "Jennifer", "Linda", "Barbara", "Elizabeth", "Susan", "Jessica", "Sarah", "Karen",
    "Christopher", "Daniel", "Matthew", "Anthony", "Mark", "Donald", "Steven", "Paul", "Andrew", "Joshua",
]

# Stylesheet - IC Brand Colors
STYLESHEET = """
QMainWindow, QWidget {
    background-color: #F1F5F9;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    font-size: 13px;
}
QLabel {
    color: #334155;
}
QPushButton {
    background-color: #0A3D62;
    color: white;
    border: none;
    padding: 12px 20px;
    border-radius: 6px;
    font-size: 13px;
    font-weight: 500;
    min-width: 80px;
}
QPushButton:hover {
    background-color: #2E86DE;
}
QPushButton:pressed {
    background-color: #084B8A;
}
QPushButton:disabled {
    background-color: #94A3B8;
}
QPushButton#secondary {
    background-color: #64748B;
}
QPushButton#secondary:hover {
    background-color: #475569;
}
QPushButton#preview {
    background-color: #F59E0B;
    font-size: 14px;
    font-weight: 600;
    padding: 16px;
    min-height: 50px;
}
QPushButton#preview:hover {
    background-color: #D97706;
}
QPushButton#redact {
    background-color: #10B981;
    font-size: 14px;
    font-weight: 600;
    padding: 16px;
    min-height: 50px;
}
QPushButton#redact:hover {
    background-color: #059669;
}
QPushButton#header {
    background-color: transparent;
    border: 1px solid #2E86DE;
    padding: 8px 16px;
    min-width: 60px;
}
QPushButton#header:hover {
    background-color: #2E86DE;
}
QTextEdit {
    background-color: white;
    border: 1px solid #CBD5E1;
    border-radius: 6px;
    padding: 10px;
    font-size: 13px;
    color: #334155;
}
QTextEdit:focus {
    border: 2px solid #2E86DE;
}
QCheckBox, QRadioButton {
    font-size: 13px;
    color: #334155;
    spacing: 8px;
    padding: 4px;
}
QCheckBox::indicator, QRadioButton::indicator {
    width: 18px;
    height: 18px;
}
QCheckBox::indicator:checked {
    background-color: #0A3D62;
    border: 2px solid #0A3D62;
    border-radius: 3px;
}
QCheckBox::indicator:unchecked {
    background-color: white;
    border: 2px solid #CBD5E1;
    border-radius: 3px;
}
QRadioButton::indicator:checked {
    background-color: #0A3D62;
    border: 2px solid #0A3D62;
    border-radius: 9px;
}
QRadioButton::indicator:unchecked {
    background-color: white;
    border: 2px solid #CBD5E1;
    border-radius: 9px;
}
QTabWidget::pane {
    border: none;
    background: white;
    border-radius: 8px;
}
QTabBar::tab {
    background: #E2E8F0;
    color: #64748B;
    padding: 12px 24px;
    border: none;
    font-weight: 500;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background: #0A3D62;
    color: white;
}
QTabBar::tab:hover:!selected {
    background: #CBD5E1;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollBar:vertical {
    background: #F1F5F9;
    width: 12px;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #CBD5E1;
    border-radius: 6px;
    min-height: 20px;
}
QScrollBar::handle:vertical:hover {
    background: #94A3B8;
}
"""


class WorkerThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(dict)
    
    def __init__(self, files, detection, custom_words, output_dir=None, preview_data=None, output_mode="black"):
        super().__init__()
        self.files = files
        self.detection = detection
        self.custom_words = custom_words
        self.output_dir = output_dir
        self.preview_data = preview_data or {}
        self.output_mode = output_mode
        self.is_preview = output_dir is None
    
    def find_pii(self, text):
        detections = []
        
        if self.detection.get("ssn"):
            for p in PII_PATTERNS["SSN"]:
                for m in re.finditer(p, text):
                    detections.append({"text": m.group(), "type": "SSN", "start": m.start()})
        
        if self.detection.get("phone"):
            for p in PII_PATTERNS["PHONE"]:
                for m in re.finditer(p, text):
                    detections.append({"text": m.group(), "type": "PHONE", "start": m.start()})
        
        if self.detection.get("email"):
            for p in PII_PATTERNS["EMAIL"]:
                for m in re.finditer(p, text, re.IGNORECASE):
                    detections.append({"text": m.group(), "type": "EMAIL", "start": m.start()})
        
        if self.detection.get("credit_card"):
            for p in PII_PATTERNS["CREDIT_CARD"]:
                for m in re.finditer(p, text):
                    detections.append({"text": m.group(), "type": "CREDIT_CARD", "start": m.start()})
        
        if self.detection.get("bank"):
            for p in PII_PATTERNS["BANK_ACCOUNT"]:
                for m in re.finditer(p, text):
                    detections.append({"text": m.group(), "type": "BANK_ACCOUNT", "start": m.start()})
        
        if self.detection.get("dob"):
            for p in PII_PATTERNS["DATE_OF_BIRTH"]:
                for m in re.finditer(p, text, re.IGNORECASE):
                    detections.append({"text": m.group(), "type": "DOB", "start": m.start()})
        
        if self.detection.get("address"):
            for p in PII_PATTERNS["ADDRESS"]:
                for m in re.finditer(p, text, re.IGNORECASE):
                    detections.append({"text": m.group(), "type": "ADDRESS", "start": m.start()})
        
        if self.detection.get("names"):
            for name in COMMON_NAMES:
                for m in re.finditer(r'\b' + re.escape(name) + r'\b', text, re.IGNORECASE):
                    detections.append({"text": m.group(), "type": "NAME", "start": m.start()})
        
        for word in self.custom_words:
            for m in re.finditer(re.escape(word), text, re.IGNORECASE):
                detections.append({"text": m.group(), "type": "CUSTOM", "start": m.start()})
        
        seen = set()
        unique = []
        for d in sorted(detections, key=lambda x: x["start"]):
            key = (d["start"], d["text"])
            if key not in seen:
                seen.add(key)
                unique.append(d)
        return unique
    
    def run(self):
        results = {"detected": "", "output": "", "stats": {}, "preview_data": {}}
        
        for filepath in self.files:
            filename = os.path.basename(filepath)
            self.progress.emit(f"Processing: {filename}")
            results["detected"] += f"{'='*45}\n{filename}\n{'='*45}\n\n"
            
            try:
                doc = fitz.open(filepath)
                file_detections = []
                
                for page_num, page in enumerate(doc):
                    text = page.get_text()
                    for d in self.find_pii(text):
                        d["page"] = page_num + 1
                        file_detections.append(d)
                        results["stats"][d["type"]] = results["stats"].get(d["type"], 0) + 1
                
                results["preview_data"][filepath] = file_detections
                
                if file_detections:
                    for d in file_detections:
                        results["detected"] += f"  Page {d['page']}: [{d['type']}] \"{d['text']}\"\n"
                else:
                    results["detected"] += "  No PII detected.\n"
                
                if not self.is_preview:
                    # Redact
                    use_labels = self.output_mode == "labels"
                    dets = self.preview_data.get(filepath, file_detections)
                    
                    for page_num, page in enumerate(doc):
                        page_dets = [d for d in dets if d.get("page") == page_num + 1]
                        for d in page_dets:
                            for inst in page.search_for(d["text"]):
                                if use_labels:
                                    page.add_redact_annot(inst, text=f"[{d['type']}]",
                                        fontsize=8, fill=(1,1,1), text_color=(0.5,0.5,0.5))
                                else:
                                    annot = page.add_redact_annot(inst)
                                    annot.set_colors(stroke=(0,0,0), fill=(0,0,0))
                        page.apply_redactions()
                    
                    out_path = os.path.join(self.output_dir, Path(filepath).stem + "_REDACTED.pdf")
                    doc.save(out_path, garbage=4, deflate=True)
                    
                    report_path = os.path.join(self.output_dir, Path(filepath).stem + "_report.txt")
                    with open(report_path, 'w') as f:
                        f.write(f"IC Redact Report\nSource: {filename}\n")
                        f.write(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"{'='*50}\n\nItems redacted: {len(dets)}\n\n")
                        for d in dets:
                            f.write(f"Page {d['page']}: [{d['type']}] \"{d['text']}\"\n")
                    
                    results["output"] += f"✓ {filename}\n  → {out_path}\n  → {report_path}\n\n"
                
                doc.close()
                
            except Exception as e:
                results["detected"] += f"  ERROR: {str(e)}\n"
                if not self.is_preview:
                    results["output"] += f"✗ {filename}: {str(e)}\n\n"
            
            results["detected"] += "\n"
        
        self.finished.emit(results)


class ICRedactApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("IC Redact - Infrastructure Catalyst")
        self.setMinimumSize(1100, 750)
        self.resize(1200, 800)
        
        self.selected_files = []
        self.preview_data = {}
        self.config = self.load_config()
        
        self.setup_ui()
        self.apply_saved_settings()
    
    def load_config(self):
        default = {
            "custom_words": "JOHN SMITH\nJANE DOE",
            "detection": {"ssn": True, "names": True, "phone": True, "email": True,
                         "address": True, "dob": True, "bank": True, "credit_card": True},
            "output_mode": "black"
        }
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    saved = json.load(f)
                    default.update(saved)
        except:
            pass
        return default
    
    def save_config(self):
        try:
            self.config["custom_words"] = self.custom_words.toPlainText()
            self.config["detection"] = {
                "ssn": self.chk_ssn.isChecked(),
                "names": self.chk_names.isChecked(),
                "phone": self.chk_phone.isChecked(),
                "email": self.chk_email.isChecked(),
                "address": self.chk_address.isChecked(),
                "dob": self.chk_dob.isChecked(),
                "bank": self.chk_bank.isChecked(),
                "credit_card": self.chk_cc.isChecked()
            }
            self.config["output_mode"] = "black" if self.radio_black.isChecked() else "labels"
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except:
            pass
    
    def apply_saved_settings(self):
        self.custom_words.setPlainText(self.config.get("custom_words", ""))
        det = self.config.get("detection", {})
        self.chk_ssn.setChecked(det.get("ssn", True))
        self.chk_names.setChecked(det.get("names", True))
        self.chk_phone.setChecked(det.get("phone", True))
        self.chk_email.setChecked(det.get("email", True))
        self.chk_address.setChecked(det.get("address", True))
        self.chk_dob.setChecked(det.get("dob", True))
        self.chk_bank.setChecked(det.get("bank", True))
        self.chk_cc.setChecked(det.get("credit_card", True))
        if self.config.get("output_mode") == "labels":
            self.radio_labels.setChecked(True)
        else:
            self.radio_black.setChecked(True)
    
    def setup_ui(self):
        self.setStyleSheet(STYLESHEET)
        
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header = QFrame()
        header.setStyleSheet("background-color: #0A3D62;")
        header.setFixedHeight(70)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(24, 0, 24, 0)
        
        # Brand
        brand = QWidget()
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(0, 0, 0, 0)
        brand_layout.setSpacing(12)
        
        # Try to load logo image
        logo = QLabel()
        logo_path = os.path.join(get_base_path(), 'logo.jpg')
        if os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            pixmap = pixmap.scaled(50, 50, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            logo.setPixmap(pixmap)
        else:
            logo.setText("IC")
            logo.setStyleSheet("""
                background-color: #2E86DE;
                color: white;
                font-size: 20px;
                font-weight: bold;
                border-radius: 8px;
                padding: 10px;
            """)
            logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(50, 50)
        brand_layout.addWidget(logo)
        
        brand_text = QWidget()
        brand_text_layout = QVBoxLayout(brand_text)
        brand_text_layout.setContentsMargins(0, 0, 0, 0)
        brand_text_layout.setSpacing(0)
        
        lbl1 = QLabel("INFRASTRUCTURE")
        lbl1.setStyleSheet("color: white; font-size: 11px; font-weight: bold;")
        lbl2 = QLabel("CATALYST")
        lbl2.setStyleSheet("color: #2E86DE; font-size: 11px; font-weight: bold;")
        brand_text_layout.addWidget(lbl1)
        brand_text_layout.addWidget(lbl2)
        brand_layout.addWidget(brand_text)
        
        header_layout.addWidget(brand)
        
        # Divider
        divider = QFrame()
        divider.setStyleSheet("background-color: #2E86DE;")
        divider.setFixedWidth(2)
        divider.setFixedHeight(40)
        header_layout.addWidget(divider)
        header_layout.addSpacing(20)
        
        # Title
        title_widget = QWidget()
        title_layout = QVBoxLayout(title_widget)
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(0)
        
        title = QLabel("IC Redact")
        title.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
        subtitle = QLabel("Remove sensitive information from PDFs")
        subtitle.setStyleSheet("color: #2E86DE; font-size: 11px;")
        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addWidget(title_widget)
        
        header_layout.addStretch()
        
        # Header buttons
        btn_help = QPushButton("Help")
        btn_help.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: 1px solid #2E86DE;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #2E86DE; }
        """)
        btn_help.clicked.connect(self.show_help)
        btn_about = QPushButton("About")
        btn_about.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: white;
                border: 1px solid #2E86DE;
                padding: 8px 16px;
                border-radius: 6px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #2E86DE; }
        """)
        btn_about.clicked.connect(self.show_about)
        header_layout.addWidget(btn_help)
        header_layout.addWidget(btn_about)
        
        main_layout.addWidget(header)
        
        # Content
        content = QWidget()
        content.setStyleSheet("background-color: #F1F5F9;")
        content_layout = QHBoxLayout(content)
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(20)
        
        # Left panel
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setFixedWidth(450)
        left_scroll.setStyleSheet("background: white; border-radius: 12px;")
        
        left = QWidget()
        left.setStyleSheet("background: white;")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(20, 20, 20, 20)
        left_layout.setSpacing(16)
        
        # Status
        self.status_label = QLabel("✓ Ready")
        self.status_label.setStyleSheet("""
            background-color: #ECFDF5;
            color: #059669;
            padding: 14px 16px;
            border-radius: 8px;
            font-size: 14px;
            font-weight: 500;
        """)
        left_layout.addWidget(self.status_label)
        
        # Files section
        files_section = QWidget()
        files_layout = QVBoxLayout(files_section)
        files_layout.setContentsMargins(0, 0, 0, 0)
        files_layout.setSpacing(12)
        
        files_title = QLabel("FILES")
        files_title.setStyleSheet("color: #0A3D62; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        files_layout.addWidget(files_title)
        
        # Drop zone style area
        drop_label = QLabel("Drag & drop PDFs here or use buttons below")
        drop_label.setStyleSheet("""
            background-color: #F8FAFC;
            border: 2px dashed #CBD5E1;
            border-radius: 8px;
            padding: 20px;
            color: #64748B;
            font-size: 12px;
        """)
        drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        files_layout.addWidget(drop_label)
        
        btn_row = QWidget()
        btn_row_layout = QHBoxLayout(btn_row)
        btn_row_layout.setContentsMargins(0, 0, 0, 0)
        btn_row_layout.setSpacing(10)
        
        self.btn_select = QPushButton("Select PDFs")
        self.btn_select.setStyleSheet("""
            QPushButton {
                background-color: #0A3D62;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #2E86DE; }
        """)
        self.btn_select.clicked.connect(self.select_files)
        
        self.btn_folder = QPushButton("Folder")
        self.btn_folder.setStyleSheet("""
            QPushButton {
                background-color: #0A3D62;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #2E86DE; }
        """)
        self.btn_folder.clicked.connect(self.select_folder)
        
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #64748B;
                color: white;
                border: none;
                padding: 12px 20px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover { background-color: #475569; }
        """)
        self.btn_clear.clicked.connect(self.clear_files)
        
        btn_row_layout.addWidget(self.btn_select)
        btn_row_layout.addWidget(self.btn_folder)
        btn_row_layout.addWidget(self.btn_clear)
        files_layout.addWidget(btn_row)
        
        self.file_list = QLabel("No files selected")
        self.file_list.setStyleSheet("""
            background-color: #F8FAFC;
            padding: 14px;
            border-radius: 8px;
            font-size: 12px;
            color: #64748B;
            border: 1px solid #E2E8F0;
        """)
        self.file_list.setWordWrap(True)
        self.file_list.setMinimumHeight(60)
        files_layout.addWidget(self.file_list)
        
        left_layout.addWidget(files_section)
        
        # Custom words
        cw_section = QWidget()
        cw_layout = QVBoxLayout(cw_section)
        cw_layout.setContentsMargins(0, 0, 0, 0)
        cw_layout.setSpacing(8)
        
        cw_title = QLabel("CUSTOM WORDS")
        cw_title.setStyleSheet("color: #0A3D62; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        cw_layout.addWidget(cw_title)
        
        cw_hint = QLabel("Add names or text to redact (one per line)")
        cw_hint.setStyleSheet("color: #64748B; font-size: 11px;")
        cw_layout.addWidget(cw_hint)
        
        self.custom_words = QTextEdit()
        self.custom_words.setPlaceholderText("JOHN SMITH\nJANE DOE\nPROJECT-123")
        self.custom_words.setMinimumHeight(100)
        self.custom_words.setMaximumHeight(120)
        cw_layout.addWidget(self.custom_words)
        
        left_layout.addWidget(cw_section)
        
        # Detection options
        det_section = QWidget()
        det_layout = QVBoxLayout(det_section)
        det_layout.setContentsMargins(0, 0, 0, 0)
        det_layout.setSpacing(10)
        
        det_title = QLabel("DETECT")
        det_title.setStyleSheet("color: #0A3D62; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        det_layout.addWidget(det_title)
        
        check_grid = QWidget()
        check_grid.setStyleSheet("background-color: #F8FAFC; border-radius: 8px; padding: 8px;")
        check_layout = QHBoxLayout(check_grid)
        check_layout.setContentsMargins(12, 12, 12, 12)
        
        col1 = QWidget()
        col1_layout = QVBoxLayout(col1)
        col1_layout.setContentsMargins(0, 0, 0, 0)
        col1_layout.setSpacing(4)
        
        col2 = QWidget()
        col2_layout = QVBoxLayout(col2)
        col2_layout.setContentsMargins(0, 0, 0, 0)
        col2_layout.setSpacing(4)
        
        self.chk_ssn = QCheckBox("SSN / Tax ID")
        self.chk_names = QCheckBox("Names")
        self.chk_phone = QCheckBox("Phone Numbers")
        self.chk_email = QCheckBox("Email Addresses")
        self.chk_address = QCheckBox("Addresses")
        self.chk_dob = QCheckBox("Dates of Birth")
        self.chk_bank = QCheckBox("Bank Accounts")
        self.chk_cc = QCheckBox("Credit Cards")
        
        for chk in [self.chk_ssn, self.chk_names, self.chk_phone, self.chk_email]:
            col1_layout.addWidget(chk)
        for chk in [self.chk_address, self.chk_dob, self.chk_bank, self.chk_cc]:
            col2_layout.addWidget(chk)
        
        check_layout.addWidget(col1)
        check_layout.addWidget(col2)
        det_layout.addWidget(check_grid)
        
        left_layout.addWidget(det_section)
        
        # Output style
        out_section = QWidget()
        out_layout = QVBoxLayout(out_section)
        out_layout.setContentsMargins(0, 0, 0, 0)
        out_layout.setSpacing(10)
        
        out_title = QLabel("OUTPUT STYLE")
        out_title.setStyleSheet("color: #0A3D62; font-size: 12px; font-weight: bold; letter-spacing: 1px;")
        out_layout.addWidget(out_title)
        
        radio_container = QWidget()
        radio_container.setStyleSheet("background-color: #F8FAFC; border-radius: 8px; padding: 8px;")
        radio_layout = QVBoxLayout(radio_container)
        radio_layout.setContentsMargins(12, 12, 12, 12)
        radio_layout.setSpacing(8)
        
        self.radio_black = QRadioButton("Black boxes (permanent)")
        self.radio_labels = QRadioButton("Labels ([SSN], [NAME])")
        self.radio_black.setChecked(True)
        
        radio_layout.addWidget(self.radio_black)
        radio_layout.addWidget(self.radio_labels)
        out_layout.addWidget(radio_container)
        
        left_layout.addWidget(out_section)
        
        # Spacer before buttons
        left_layout.addSpacing(10)
        
        # Action buttons - make them prominent
        buttons_section = QWidget()
        buttons_layout = QVBoxLayout(buttons_section)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(12)
        
        self.btn_preview = QPushButton("Preview")
        self.btn_preview.setStyleSheet("""
            QPushButton {
                background-color: #F59E0B;
                color: white;
                border: none;
                padding: 16px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #D97706; }
            QPushButton:disabled { background-color: #94A3B8; }
        """)
        self.btn_preview.clicked.connect(self.preview)
        self.btn_preview.setMinimumHeight(50)
        buttons_layout.addWidget(self.btn_preview)
        
        self.btn_redact = QPushButton("Redact PDFs")
        self.btn_redact.setStyleSheet("""
            QPushButton {
                background-color: #10B981;
                color: white;
                border: none;
                padding: 16px;
                border-radius: 6px;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #059669; }
            QPushButton:disabled { background-color: #94A3B8; }
        """)
        self.btn_redact.clicked.connect(self.redact)
        self.btn_redact.setMinimumHeight(50)
        buttons_layout.addWidget(self.btn_redact)
        
        left_layout.addWidget(buttons_section)
        left_layout.addStretch()
        
        left_scroll.setWidget(left)
        content_layout.addWidget(left_scroll)
        
        # Right panel - tabs
        right = QWidget()
        right.setStyleSheet("background: white; border-radius: 12px;")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        
        self.detected_text = QTextEdit()
        self.detected_text.setReadOnly(True)
        self.detected_text.setStyleSheet("background: #FEF9E7; color: #92400E; font-family: monospace;")
        
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setStyleSheet("background: #E8F8F5; color: #065F46; font-family: monospace;")
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setStyleSheet("background: white; color: #334155; font-family: monospace;")
        
        self.tabs.addTab(self.detected_text, "Detected PII")
        self.tabs.addTab(self.output_text, "Output Log")
        self.tabs.addTab(self.summary_text, "Summary")
        
        right_layout.addWidget(self.tabs)
        content_layout.addWidget(right)
        
        main_layout.addWidget(content)
    
    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Select PDFs", "", "PDF Files (*.pdf)")
        if files:
            self.selected_files.extend(files)
            self.update_file_list()
    
    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            pdfs = list(Path(folder).glob("*.pdf"))
            if pdfs:
                self.selected_files.extend([str(f) for f in pdfs])
                self.update_file_list()
            else:
                QMessageBox.information(self, "No PDFs", "No PDF files found in folder.")
    
    def update_file_list(self):
        if not self.selected_files:
            self.file_list.setText("No files selected")
        else:
            text = "\n".join([f"• {os.path.basename(f)}" for f in self.selected_files[-6:]])
            text += f"\n\n{len(self.selected_files)} file(s) selected"
            self.file_list.setText(text)
        self.preview_data = {}
    
    def clear_files(self):
        self.selected_files = []
        self.preview_data = {}
        self.file_list.setText("No files selected")
        self.detected_text.clear()
        self.output_text.clear()
        self.summary_text.clear()
    
    def get_detection_settings(self):
        return {
            "ssn": self.chk_ssn.isChecked(),
            "names": self.chk_names.isChecked(),
            "phone": self.chk_phone.isChecked(),
            "email": self.chk_email.isChecked(),
            "address": self.chk_address.isChecked(),
            "dob": self.chk_dob.isChecked(),
            "bank": self.chk_bank.isChecked(),
            "credit_card": self.chk_cc.isChecked()
        }
    
    def get_custom_words(self):
        text = self.custom_words.toPlainText()
        return [l.strip() for l in text.split('\n') if l.strip() and not l.strip().startswith('#')]
    
    def preview(self):
        if not self.selected_files:
            QMessageBox.warning(self, "No Files", "Please select PDF files first.")
            return
        
        self.save_config()
        self.set_buttons_enabled(False)
        self.status_label.setText("Scanning...")
        self.status_label.setStyleSheet("background-color: #FEF3C7; color: #D97706; padding: 14px 16px; border-radius: 8px; font-size: 14px; font-weight: 500;")
        
        self.worker = WorkerThread(
            self.selected_files,
            self.get_detection_settings(),
            self.get_custom_words()
        )
        self.worker.progress.connect(lambda msg: self.status_label.setText(msg))
        self.worker.finished.connect(self.preview_finished)
        self.worker.start()
    
    def preview_finished(self, results):
        self.preview_data = results.get("preview_data", {})
        self.detected_text.setPlainText(results["detected"])
        
        stats = results.get("stats", {})
        total = sum(stats.values())
        
        summary = f"PREVIEW SUMMARY\n{'='*45}\n\n"
        summary += f"Files scanned: {len(self.selected_files)}\n"
        summary += f"Total items found: {total}\n\n"
        if stats:
            summary += f"By Type:\n{'-'*30}\n"
            for t, c in sorted(stats.items(), key=lambda x: -x[1]):
                summary += f"  {t}: {c}\n"
        
        self.summary_text.setPlainText(summary)
        self.tabs.setCurrentIndex(0)
        
        self.status_label.setText(f"✓ Preview: {total} items found")
        self.status_label.setStyleSheet("background-color: #ECFDF5; color: #059669; padding: 14px 16px; border-radius: 8px; font-size: 14px; font-weight: 500;")
        self.set_buttons_enabled(True)
    
    def redact(self):
        if not self.selected_files:
            QMessageBox.warning(self, "No Files", "Please select PDF files first.")
            return
        
        output_dir = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if not output_dir:
            return
        
        self.save_config()
        self.set_buttons_enabled(False)
        self.status_label.setText("Redacting...")
        self.status_label.setStyleSheet("background-color: #FEF3C7; color: #D97706; padding: 14px 16px; border-radius: 8px; font-size: 14px; font-weight: 500;")
        
        self.worker = WorkerThread(
            self.selected_files,
            self.get_detection_settings(),
            self.get_custom_words(),
            output_dir,
            self.preview_data,
            "black" if self.radio_black.isChecked() else "labels"
        )
        self.worker.progress.connect(lambda msg: self.status_label.setText(msg))
        self.worker.finished.connect(self.redact_finished)
        self.worker.start()
    
    def redact_finished(self, results):
        self.detected_text.setPlainText(results["detected"])
        self.output_text.setPlainText(results["output"])
        
        stats = results.get("stats", {})
        total = sum(stats.values())
        
        summary = f"REDACTION COMPLETE\n{'='*45}\n\n"
        summary += f"Files processed: {len(self.selected_files)}\n"
        summary += f"Total redacted: {total}\n\n"
        if stats:
            summary += f"By Type:\n{'-'*30}\n"
            for t, c in sorted(stats.items(), key=lambda x: -x[1]):
                summary += f"  {t}: {c}\n"
        
        self.summary_text.setPlainText(summary)
        self.tabs.setCurrentIndex(2)
        
        self.status_label.setText(f"✓ Complete: {total} items redacted")
        self.status_label.setStyleSheet("background-color: #ECFDF5; color: #059669; padding: 14px 16px; border-radius: 8px; font-size: 14px; font-weight: 500;")
        self.set_buttons_enabled(True)
        
        QMessageBox.information(self, "Done", f"Processed {len(self.selected_files)} PDF(s)\nRedacted {total} items")
    
    def set_buttons_enabled(self, enabled):
        self.btn_select.setEnabled(enabled)
        self.btn_folder.setEnabled(enabled)
        self.btn_preview.setEnabled(enabled)
        self.btn_redact.setEnabled(enabled)
    
    def show_about(self):
        QMessageBox.about(self, "About IC Redact", """
<h2>IC Redact</h2>
<p><b>Infrastructure Catalyst • v4.0</b></p>

<h3>What It Does</h3>
<p>Removes sensitive information from PDFs before sharing with AI tools or external parties.</p>

<h3>Security & Privacy</h3>
<p>All processing happens locally on your computer.</p>
<ul>
<li>No internet connection required</li>
<li>No data sent to external servers</li>
<li>Original files never modified</li>
</ul>

<h3>IT Compliance</h3>
<p>Supports NIST, GDPR, CCPA, and HIPAA-conscious workflows.</p>
        """)
    
    def show_help(self):
        QMessageBox.information(self, "How to Use IC Redact", """
<h3>1. Select Files</h3>
<p>Click 'Select PDFs' or 'Folder' to choose files.</p>

<h3>2. Add Custom Words</h3>
<p>Enter names or text to redact, one per line.</p>

<h3>3. Choose Detection Types</h3>
<p>Check what types of PII to detect.</p>

<h3>4. Select Output Style</h3>
<p>Black boxes or labels like [SSN].</p>

<h3>5. Preview</h3>
<p>See what will be redacted first.</p>

<h3>6. Redact</h3>
<p>Process and save redacted PDFs.</p>
        """)
    
    def closeEvent(self, event):
        self.save_config()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ICRedactApp()
    window.show()
    sys.exit(app.exec())

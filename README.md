# 🌍 ESG PDF Text Analysis

A Streamlit application for analyzing Environmental, Social, and Governance (ESG) content in PDF documents using text selection and classification.

## 📋 Features

- **📄 PDF Viewer**: Interactive PDF viewer with text selection capabilities
- **✂️ Text Selection**: Highlight and extract text from PDFs with yellow highlighting
- **🤖 ESG Classification**: Rule-based classification into Environmental, Social, Governance categories
- **📊 Visualization**: Interactive charts and progress bars for analysis results
- **🔄 Real-time Processing**: File-based workflow for seamless text transfer

## 🏗️ Project Structure

```
ESG_FE/
├── app_main.py                 # Main Streamlit application
├── text_server.py             # Background text server
├── requirements.txt           # Python dependencies
├── README.md                  # This file
│
├── models/
│   └── esg_classifier.py      # ESG classification logic
│
├── utils/
│   └── components.py          # Component rendering utilities
│
├── static/
│   ├── css/
│   │   ├── style.css          # Main application styles
│   │   └── pdf_viewer.css     # PDF viewer specific styles
│   └── js/
│       └── pdf_viewer.js      # PDF viewer JavaScript
│
├── templates/
│   └── components/
│       └── pdf_viewer.html    # PDF viewer HTML template
│
└── temp_text/                 # Temporary text files
    ├── selected.txt           # Selected text from PDF
    ├── full_pdf.txt          # Full PDF extracted text
    └── metadata.json         # File metadata
```
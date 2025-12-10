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

## 🎯 Usage

### Download model
Download the model from the link https://huggingface.co/Trungdjoon and save it into two folders:
- ESG_classify/models for the classification model
- ESG_score/models for the sentiment model
**Note:**  
- Rename folder from `esg_score-{model_name}-{category}` to `{model_name}/{category}`  
- Rename folder from `esg-{model_name}_run_3` to `{model_name}`

### Running the Application

1. **Activate environment**
   ```bash
   conda activate virtual environment
   ```

2. **Start the application**
   ```bash
   streamlit run app_main.py
   ```

3. **Open browser**
   - Navigate to `http://localhost:8501`
   - The application will start automatically

### Workflow

1. **📁 Upload PDF**: Upload a PDF file using the file uploader
2. **✂️ Select Text**: Highlight text in the PDF viewer (yellow highlighting)
3. **📥 Read File**: Click "Đọc file" to load selected text
4. **🚀 Analyze**: Click "Phân tích ESG" to classify the text
5. **📊 View Results**: See charts and detailed analysis

### Keyboard Shortcuts

- **Ctrl+S**: Save current text selection
- **Ctrl+W**: Expand selection to word boundaries
- **Ctrl++/Ctrl+-**: Zoom in/out
- **Ctrl+0**: Reset zoom

## 🔧 Architecture

### Modular Design

The application follows a clean, modular architecture:

- **`app_main.py`**: Main Streamlit interface and workflow
- **`ESG_classify`**: ESG classification logic
- **`ESG_score`**: ESG score calculation logic
- **`utils/components.py`**: Component rendering utilities
- **`static/`**: CSS and JavaScript assets
- **`templates/`**: HTML templates

### Key Components

#### ESG Classifier and Scoring
- Classify Environmental, Social, Governance, and Irrelevant Sentences 
- Evaluate the ESG report based on ESG scoring criteria

#### PDF Viewer
- Interactive PDF rendering with PDF.js
- Text selection with custom highlighting
- Zoom controls and keyboard shortcuts
- Real-time text extraction

## 🎨 Customization

### Styling
- Modify `static/css/style.css` for main application styles
- Modify `static/css/pdf_viewer.css` for PDF viewer styles

### Templates
- Modify HTML templates in `templates/components/`
- Update JavaScript in `static/js/`

## 🐛 Troubleshooting

### Common Issues

2. **Text Server Not Starting**
   ```bash
   # Check if port 8888 is available
   lsof -i :8888
   # Kill existing process if needed
   pkill -f text_server
   ```

3. **PDF Not Loading**
   - Ensure PDF file is not corrupted

### Debug Mode

Run with debug information:
```bash
streamlit run app_main.py --logger.level debug
```

import streamlit as st
import streamlit.components.v1 as components
import time
import pandas as pd
import plotly.express as px
from pathlib import Path
import json
import pdfplumber, fitz
import io
import re

# Import custom modules
from text_server import run_server_background
from utils.components import render_pdf_viewer, get_custom_css, normalize_full_text
from ESG_classify.esg_classifier import ESGClassifier
from ESG_score.ESG_score import ESGScoreCalculator
import warnings

warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# Page configuration
st.set_page_config(page_title="ESG PDF Text Analysis", layout="wide")

# Load custom CSS
st.markdown(get_custom_css(), unsafe_allow_html=True)

model_classifer = "ESG_classify\models\ViBert-ESG-base"
model_score = "ESG_score\models\phobert-base"

# Initialize ESG classifier
@st.cache_resource
def get_esg_classifier():
    """Get ESG classifier instance"""
    return ESGClassifier(model_classifer)

@st.cache_resource
def get_esg_sentiment():
    """Get ESG Score"""
    return ESGScoreCalculator()

# Start text server in background
if 'server_started' not in st.session_state:
    try:
        run_server_background()
        st.session_state.server_started = True
        print("Text server started in background")
    except Exception as e:
        print(f"⚠️ Could not start text server: {e}")
        st.session_state.server_started = False

# Create temp directory for text transfer
TEMP_DIR = Path("temp_text")
TEMP_DIR.mkdir(exist_ok=True)
TEXT_FILE = TEMP_DIR / "selected.txt"
FULL_PDF_FILE = TEMP_DIR / "full_pdf.txt"
METADATA_FILE = TEMP_DIR / "metadata.json"

# Session state initialization
if 'selected_text' not in st.session_state:
    st.session_state.selected_text = ""
if 'last_check' not in st.session_state:
    st.session_state.last_check = 0
if 'uploaded_file' not in st.session_state:
    st.session_state.uploaded_file = None
    
def extract_pdf_text(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        full_text = []
        for i, page in enumerate(doc, start=1):
            text = page.get_text()
            if text.strip():
                full_text.append(f'--- Page {i} ---\n{text.strip()}')
        return '\n'.join(full_text), None
    except Exception as e:
        return None, f"Lỗi khi extract PDF: {str(e)}"


def save_full_pdf_to_file(text):
    """Save full PDF text to file"""
    try:
        with open(FULL_PDF_FILE, 'w', encoding='utf-8') as f:
            f.write(text)
        
        # Save metadata
        metadata = {
            'timestamp': time.time(),
            'length': len(text),
            'type': 'Full PDF text (extracted in app)',
            'preview': text[:100] + "..." if len(text) > 100 else text
        }
        
        metadata_file = TEMP_DIR / "full_pdf_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        
        return True
    except Exception as e:
        st.error(f"Lỗi lưu file: {e}")
        return False

def check_for_new_text():
    """Check if there's new text in file"""
    try:
        if TEXT_FILE.exists():
            stat = TEXT_FILE.stat()
            if stat.st_mtime > st.session_state.last_check:
                with open(TEXT_FILE, 'r', encoding='utf-8') as f:
                    text = f.read().strip()
                if text and text != st.session_state.selected_text:
                    st.session_state.selected_text = text
                    st.session_state.last_check = stat.st_mtime
                    return True
    except:
        pass
    return False

def get_file_info(file_path=TEXT_FILE):
    """Get file information - improved to handle both files"""
    if file_path.exists():
        stat = file_path.stat()
        age = time.time() - stat.st_mtime
        size = stat.st_size
        preview = ""
        
        # Load metadata if exists
        metadata_file = TEMP_DIR / f"{file_path.stem}_metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    preview = metadata.get('preview', '')
            except:
                pass
        
        return {
            'exists': True,
            'age': age,
            'size': size,
            'preview': preview
        }
    return {'exists': False}

# Main UI
st.title("🌍 ESG PDF Text Classification")
st.markdown("**Workflow: Bôi đen text → Lưu file → Hiển thị area → Phân tích**")

# Load model status
with st.expander("Model Status", expanded=False):
    classifier = get_esg_classifier()
    if classifier.is_ready():
        st.success("✅ ESG Classifier đã sẵn sàng!")
    else:
        st.error("❌ Không thể tải model")

col1, col2 = st.columns([1.2, 0.8])

with col1:
    st.markdown("### 📄 PDF Viewer")
    uploaded_file = st.file_uploader("📁 Upload PDF file", type="pdf", key="pdf_uploader")
    
    # Store uploaded file in session state
    if uploaded_file:
        st.session_state.uploaded_file = uploaded_file
        uploaded_file.seek(0)
        st.session_state.pdf_bytes = uploaded_file.read()
    
    display_file = st.session_state.uploaded_file or uploaded_file
    
    if display_file:
        if 'pdf_bytes' in st.session_state:
            pdf_bytes = st.session_state.pdf_bytes
        else:
            display_file.seek(0)
            pdf_bytes = display_file.read()
            st.session_state.pdf_bytes = pdf_bytes
        
        # Use external template for PDF viewer
        pdf_viewer_html = render_pdf_viewer(pdf_bytes)
        pdf_viewer = components.html(pdf_viewer_html, height=850)

with col2:
    st.markdown("### 🔍 Phân tích ESG")
    
    # Server status
    server_status = "🟢 Hoạt động" if st.session_state.get('server_started', False) else "🔴 Không hoạt động"
    st.caption(f"Text Server: {server_status}")
    
    #hiển thị cả 2 loại file
    file_info = get_file_info(TEXT_FILE)
    full_pdf_info = get_file_info(FULL_PDF_FILE)
    
    col_status1, col_status2 = st.columns(2)
    
    with col_status1:
        if file_info['exists']:
            age_text = f"{file_info['age']:.1f}s" if file_info['age'] < 60 else f"{file_info['age']/60:.1f}m"
            st.success(f"📄 Selected: {file_info['size']} bytes, {age_text}")
        else:
            st.info("📄 Chưa có selected text")
    
    with col_status2:
        if full_pdf_info['exists']:
            age_text = f"{full_pdf_info['age']:.1f}s" if full_pdf_info['age'] < 60 else f"{full_pdf_info['age']/60:.1f}m"
            st.success(f"📚 Full PDF: {full_pdf_info['size']} bytes")
        else:
            st.info("📚 Chưa có full PDF text")

    # Control buttons
    col_a, col_b, col_c = st.columns(3)
    
    with col_a:
        if st.button("📥 Đọc file", key="read_selected_btn"):
            
            if TEXT_FILE.exists():
                try:
                    with open(TEXT_FILE, 'r', encoding='utf-8') as f:
                        text = f.read().strip()
                    if text:
                        st.session_state.selected_text = text
                        st.success(f"✅ Đã đọc {len(text)} ký tự từ Selected text!")
                    else:
                        st.warning("File selected text trống")
                except Exception as e:
                    st.error(f"Lỗi đọc file: {e}")
            else:
                st.warning(f"Chưa có selected text. Hãy bôi đen text trong PDF")
    
    with col_b:
        if st.button("📄 Lấy text cả PDF", key="extract_full_btn"):
            if 'pdf_bytes' in st.session_state:
                with st.spinner("🔄 Đang trích xuất text từ PDF..."):
                    full_text, error = extract_pdf_text(st.session_state.pdf_bytes)
                    
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        cleaned_text = normalize_full_text(full_text)
                        if save_full_pdf_to_file(cleaned_text):
                            st.session_state.selected_text = cleaned_text
                            st.success(f"✅ Đã lấy và hiển thị {len(cleaned_text)} ký tự từ toàn bộ PDF!")
                        else:
                            st.error("❌ Lỗi lưu file")
            else:
                st.warning("Vui lòng upload PDF trước")
    
    with col_c:
        if st.button("🗑️ Xóa", key="clear_btn"):
            st.session_state.selected_text = ""
            try:
                if TEXT_FILE.exists():
                    TEXT_FILE.unlink()
                if METADATA_FILE.exists():
                    METADATA_FILE.unlink()
                if FULL_PDF_FILE.exists():
                    FULL_PDF_FILE.unlink()
                # Xóa cả metadata files
                selected_metadata = TEMP_DIR / "selected_metadata.json"
                full_pdf_metadata = TEMP_DIR / "full_pdf_metadata.json"
                if selected_metadata.exists():
                    selected_metadata.unlink()
                if full_pdf_metadata.exists():
                    full_pdf_metadata.unlink()
                st.success("🗑️ Đã xóa sạch")
            except Exception as e:
                st.error(f"Lỗi xóa: {e}")
    
    # Selection industry
    data_industry = pd.read_csv("ESG_company.csv")
    company_industry_map = data_industry.set_index("Company")["Industry"].to_dict()

    # option list với tự nhập ở cuối
    company_options = sorted(list(company_industry_map.keys())) + ["Nhập công ty khác..."]

    selected_option = st.selectbox(
        "Chọn hoặc nhập tên công ty:",
        options=company_options,
        index=0
    )

    #
    if selected_option == "Nhập công ty khác...":
        company_name = st.text_input("Nhập tên công ty mới:")
        if company_name:
            industry = st.text_input("Nhập industry:", value="Telecommunication Services (Technology & Communications)")
        else:
            company_name = None
            industry = None
    else:
        company_name = selected_option
        industry = company_industry_map[company_name]
    if company_name and industry:
        st.write(f"**Công ty:** {company_name}")
        st.write(f"**Industry:** {industry}")
    
    # Text area
    text_to_analyze = st.text_area(
        "✂️ Text để phân tích ESG:",
        value=st.session_state.selected_text,
        height=200,
        placeholder="Bôi đen text trong PDF → Text sẽ được lưu vào file → Click 'Đọc file' để hiển thị ở đây\nHoặc click 'Lấy text cả PDF' để trích xuất toàn bộ",
        key="text_analysis"
    )
    
    # Update session state when user manually edits
    if text_to_analyze != st.session_state.selected_text:
        st.session_state.selected_text = text_to_analyze
    
    # Show text info
    if text_to_analyze.strip():
        sentences = [s.strip() for s in text_to_analyze.split('.') if s.strip()]
        words = len(text_to_analyze.split())
        lines = len(text_to_analyze.split('\n'))
        num_sentences = len(sentences)
        st.caption(f"📊 {words} từ, {lines} dòng, {num_sentences} câu")
    
    # Status
    if not text_to_analyze.strip():
        st.info("📋 **Workflow**: Bôi đen text trong PDF → Lưu file → Click 'Đọc file' → Phân tích")
    else:
        st.success(f"✅ Sẵn sàng phân tích ({num_sentences} câu)")

classifier = get_esg_classifier()
esg_score = get_esg_sentiment()
# ANALYSIS SECTION
if text_to_analyze.strip() and len(text_to_analyze) >= 10:
    if st.button("🚀 Phân tích ESG", type="primary", key="classify_btn"):
        with st.spinner("🔍 Đang phân tích ESG..."):
            counts, data = classifier.classify_text(sentences)
            
            st.markdown("#### 📊 Kết quả phân tích:")
            st.info("🤖 **Phân tích bằng Rule-based Classifier**")
            
            df = pd.DataFrame({
                'Category': list(counts.keys()),
                'Số lượng': list(counts.values())
            })
            
            # Bar chart
            fig_bar = px.bar(
                df, x='Category', y='Số lượng', color='Category',
                color_discrete_map={
                    'Environmental': '#4CAF50',
                    'Social': '#2196F3',
                    'Governance': '#9C27B0',
                    'Irrelevant': '#FF5722'
                },
                title="📊 Phân bố ESG (số lượng câu)"
            )
            fig_bar.update_layout(height=280, showlegend=False)
            st.plotly_chart(fig_bar, use_container_width=True)
            
            # Pie chart
            fig_pie = px.pie(
                df, values='Số lượng', names='Category', color='Category',
                color_discrete_map={
                    'Environmental': '#4CAF50',
                    'Social': '#2196F3',
                    'Governance': '#9C27B0',
                    'Irrelevant': '#FF5722'
                },
                title="🥧 Phân bố ESG (%)"
            )
            fig_pie.update_layout(height=340)
            st.plotly_chart(fig_pie, use_container_width=True)
            
            # ESG score
            result = esg_score.calculate_company_esg_score(data, industry, model_score)
            
            st.markdown("#### 📈 Kết Quả ESG Score Chi Tiết")
            
            # Hiển thị tổng điểm ESG
            st.write(f"**Trọng số ngành {industry}:** {result['industry_weights']}")

            fig_sentiment_bar = px.bar(
                result["sentiment_df"],
                x="ESG Category",
                y="Count",
                color="Sentiment",
                barmode="group",
                title="📊 Phân Bổ Sentiment theo Danh Mục ESG"
            )
            fig_sentiment_bar.update_layout(height=400)
            st.plotly_chart(fig_sentiment_bar, use_container_width=True)

            
            # DataFrame cho weighted contributions (E, S, G)
            contributions_df = pd.DataFrame({
                'Category': ['Environmental', 'Social', 'Governance'],
                'Score Contribution': [
                    abs(result['weighted_e_contribution']),
                    abs(result['weighted_s_contribution']),
                    abs(result['weighted_g_contribution'])
                ]
            })
            
            fig_weights_pie = px.pie(
                contributions_df, values='Score Contribution', names='Category',
                title="🥧 Phân Bố Score"
            )
            fig_weights_pie.update_layout(height=340)
            st.plotly_chart(fig_weights_pie, use_container_width=True)
            
            # Results table
            st.markdown("#### 📋 Bảng Kết Quả ESG (Mở Rộng)")
            result_df = pd.DataFrame({
                'Danh mục ESG': [f"🌱 Environmental", f"👥 Social", f"⚖️ Governance"],
                'Điểm Sentiment Avg': [f"{result['e_sentiment_avg']:.2f}", f"{result['s_sentiment_avg']:.2f}", f"{result['g_sentiment_avg']:.2f}"],
                'Đóng Góp Weighted': [f"{result['weighted_e_contribution']:.2f}", f"{result['weighted_s_contribution']:.2f}", f"{result['weighted_g_contribution']:.2f}"],
            })
            
            st.dataframe(result_df, use_container_width=True)
            st.write(f"**Tổng Điểm ESG:** {result['company_esg_score']:.2f}")

elif text_to_analyze.strip() and len(text_to_analyze) < 10:
    st.warning("⚠️ Text quá ngắn. Cần ít nhất 10 ký tự để phân tích.")

# Footer
st.markdown("---")
st.markdown("**ESG PDF Text Classification** - Modular architecture with clean separation")

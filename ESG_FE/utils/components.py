"""
Component Utilities
Handles rendering of HTML components and templates
"""

import os
from pathlib import Path
import re
import fitz
import pdfplumber 

def smart_normalize_text(text, remove_single_chars=True):
    if not text:
        return "", []
    
    text = re.sub(r'\s+', ' ', text).strip()
    text = re.sub(r'([.%])\1{1,}', r'\1', text)
    text = re.sub(r"[#$^&(),]", "", text)
    text = re.sub(r'(?:\b[À-ỴA-Z]{2,}(?:\s+[À-ỴA-Z]{2,})*\b)', '', text)

    page_pattern = r'--- Page (\d+) ---'
    page_matches = list(re.finditer(page_pattern, text))
    
    if not page_matches:
        processed = process_page_content(text, remove_single_chars)
        return processed, [processed]
    
    normalized_pages = []
    for i, match in enumerate(page_matches):
        start_pos = match.end()
        if i + 1 < len(page_matches):
            end_pos = page_matches[i + 1].start()
        else:
            end_pos = len(text)
        
        content = text[start_pos:end_pos].strip()
        normalized_content = process_page_content(content, remove_single_chars)
        normalized_pages.append(normalized_content)
    
    full_text = '\n\n\n'.join(normalized_pages)
    return full_text, normalized_pages


def clean_artifacts(content):
    content = re.sub(r'[•]', '', content)
    pattern = r'\b(\w+)\b(?:\s+\1\b)+'
    content = re.sub(pattern, '', content, flags=re.IGNORECASE).strip()
    content = re.sub(r"[#$^&,]", "", content)
    content = re.sub(r'(?:\s*-\s*){2,}', '.', content)
    content = re.sub(r'([a-zA-ZÀ-ỹ])\d+([a-zA-ZÀ-ỹ])', r'\1\2', content)
    content = re.sub(r'\s*-\s*', ' ', content)
    content = re.sub(r'[-]{2,}|\.{2,}|…', '.', content)
    
    roman_numerals = r'(I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV)'
    upper_chars = r'[A-ZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßĂẰẮẲẴẶÂẤẦẨẪẬĐÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰỲỴỶỸẸẺẼỀỂỄ]'
    upper_pattern = rf'(?:{upper_chars}+\s*){{7,}}|\b{upper_chars}+\b(?:\s*{upper_chars}+\b){{2,}}' 
    content = re.sub(upper_pattern, '', content)
    
    dash_upper_pattern = r'(?:\s*-\s*){2,}\s*[A-ZÀ-ỸẸ\s]+'
    content = re.sub(dash_upper_pattern, '', content)
    
    pair_pattern = r'\b\w+\s+' + roman_numerals + r'\b(?:\s+\w+\s+' + roman_numerals + r'\b)*'
    content = re.sub(pair_pattern, '', content)
    
    content = re.sub(r'\b\d{1,3}\b(?:\s+\b\d{1,3}\b)?', '', content)
    content = re.sub(r'\s+', ' ', content).strip()
    return content


def process_page_content(content, remove_single_chars=True):
    if not content:
        return ""
    
    content = clean_artifacts(content)
    
    if remove_single_chars:
        content = re.sub(r'\b\w\b', '', content)
        content = re.sub(r'\s+', ' ', content).strip()
    
    lines = content.split('\n')
    processed_lines = []
    current_line = ""
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if not current_line:
            current_line = line
            continue
        
        last_char = current_line[-1] if current_line else ''
        
        if last_char in [':', ';', '.']:
            processed_lines.append(current_line)
            if last_char == '.':
                processed_lines.append('')
            current_line = line
            continue
        
        if last_char == '-':
            current_line = current_line[:-1] + line
            continue
        
        if current_line.startswith('*'):
            processed_lines.append(current_line)
            processed_lines.append('')
            current_line = line
            continue
        
        if '---' in current_line:
            processed_lines.append(current_line)
            processed_lines.append('')
            current_line = line
            continue
        
        first_char = line[0] if line else ''
        if first_char.isupper() or first_char in 'ÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞßĂẰẮẲẴẶÂẤẦẨẪẬĐÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰỲỴỶỸ':
            current_line += '. ' + line
        else:
            current_line += ' ' + line
    
    if current_line:
        processed_lines.append(current_line)
    
    return '\n'.join(processed_lines)

def clean_text_remove_intro_outro_add_dots(text):
    paragraphs = [p.strip() for p in text.strip().split('\n\n') if p.strip()]
    # print("đoạn 1:", paragraphs[0])
    # print("đoạn cuối:", paragraphs[-1])
    if len(paragraphs) >= 3:
        paragraphs = paragraphs[1:-1]
    def ensure_dot(p):
        return p if re.search(r'[.!?…]$', p) else p + '.'
    paragraphs = [ensure_dot(p) for p in paragraphs]

    return '\n'.join(paragraphs)

def normalize_full_text(raw_text):
    full_normalized, _ = smart_normalize_text(raw_text)
    cleaned_text = clean_text_remove_intro_outro_add_dots(full_normalized)
    return cleaned_text


def load_template(template_name):
    """Load HTML template from templates directory"""
    template_path = Path("templates") / template_name
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        raise FileNotFoundError(f"Template {template_name} not found")

def load_css(css_file):
    """Load CSS file from static directory"""
    css_path = Path("static/css") / css_file
    if css_path.exists():
        with open(css_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return ""

def load_js(js_file):
    """Load JavaScript file from static directory"""
    js_path = Path("static/js") / js_file
    if js_path.exists():
        with open(js_path, 'r', encoding='utf-8') as f:
            return f.read()
    else:
        return ""

def render_pdf_viewer(pdf_bytes):
    """Render PDF viewer with external CSS and JS"""
    try:
        # Load template
        template = load_template("components/pdf_viewer.html")
        
        # Load CSS and JS
        css_content = load_css("pdf_viewer.css")
        js_content = load_js("pdf_viewer.js")
        
        # Replace placeholders
        template = template.replace('<link rel="stylesheet" href="/static/css/pdf_viewer.css">', 
                                  f'<style>{css_content}</style>')
        template = template.replace('<script src="/static/js/pdf_viewer.js"></script>', 
                                  f'<script>{js_content}</script>')
        
        # Replace PDF data
        template = template.replace("PDF_DATA_PLACEHOLDER", str(list(pdf_bytes)))
        
        return template
    except Exception as e:
        print(f"Error rendering PDF viewer: {e}")
        return f"<div>Error loading PDF viewer: {e}</div>"

def get_custom_css():
    """Get custom CSS for Streamlit"""
    css_content = load_css("style.css")
    return f"""
    <style>
    {css_content}
    
    /* Additional Streamlit-specific styles */
    ::selection {{
        background: rgba(255, 255, 0, 0.8) !important;
        color: rgba(0, 0, 0, 1) !important;
    }}
    
    ::-moz-selection {{
        background: rgba(255, 255, 0, 0.8) !important;
        color: rgba(0, 0, 0, 1) !important;
    }}
    
    iframe ::selection {{
        background: rgba(255, 255, 0, 0.8) !important;
        color: rgba(0, 0, 0, 1) !important;
    }}
    </style>
    """ 
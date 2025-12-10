// PDF Viewer JavaScript
const pdfData = new Uint8Array(PDF_DATA_PLACEHOLDER);
let isReady = false;
let currentScale = 1.2;
let pdfDoc = null;
let pageElements = [];
let lastSelectedText = '';

pdfjsLib.getDocument(pdfData).promise.then(function(pdf) {
    pdfDoc = pdf;
    renderPages();
});

function renderPages() {
    document.getElementById('status').textContent = '✅ PDF sẵn sàng - Bôi đen text để lưu vào file';
    document.getElementById('status').style.background = '#d4edda';
    document.getElementById('status').style.color = '#155724';
    
    const container = document.getElementById('pdf-container');
    container.innerHTML = '';
    pageElements = [];
    
    // const maxPages = Math.min(pdfDoc.numPages, 10);
    const maxPages = pdfDoc.numPages;
    let pagesRendered = 0;
    
    for (let pageNum = 1; pageNum <= maxPages; pageNum++) {
        pdfDoc.getPage(pageNum).then(function(page) {
            const viewport = page.getViewport({scale: currentScale});
            
            const pageDiv = document.createElement('div');
            pageDiv.className = 'pdf-page';
            pageDiv.style.width = viewport.width + 'px';
            pageDiv.style.height = viewport.height + 'px';
            pageDiv.style.position = 'relative';
            pageDiv.setAttribute('data-page', pageNum);
            
            const canvas = document.createElement('canvas');
            const context = canvas.getContext('2d');
            canvas.height = viewport.height;
            canvas.width = viewport.width;
            
            const textLayerDiv = document.createElement('div');
            textLayerDiv.className = 'textLayer';
            textLayerDiv.style.width = viewport.width + 'px';
            textLayerDiv.style.height = viewport.height + 'px';
            
            pageDiv.appendChild(canvas);
            pageDiv.appendChild(textLayerDiv);
            container.appendChild(pageDiv);
            
            pageElements.push({
                page: page,
                pageDiv: pageDiv,
                canvas: canvas,
                context: context,
                textLayerDiv: textLayerDiv
            });
            
            page.render({ canvasContext: context, viewport: viewport }).promise.then(function() {
                return page.getTextContent();
            }).then(function(textContent) {
                pdfjsLib.renderTextLayer({
                    textContent: textContent,
                    container: textLayerDiv,
                    viewport: viewport,
                    textDivs: []
                });
                
                pagesRendered++;
                if (pagesRendered === maxPages) {
                    isReady = true;
                    setupSelectionHandlers();
                }
            });
        });
    }
}

function updateZoomLevel() {
    document.getElementById('zoom-level').textContent = Math.round(currentScale * 100) + '%';
    document.querySelector('button[onclick="zoomOut()"]').disabled = currentScale <= 0.5;
    document.querySelector('button[onclick="zoomIn()"]').disabled = currentScale >= 3.0;
}

function zoomIn() {
    if (currentScale < 3.0) {
        currentScale += 0.2;
        currentScale = Math.round(currentScale * 10) / 10;
        updateZoomLevel();
        renderPages();
    }
}

function zoomOut() {
    if (currentScale > 0.5) {
        currentScale -= 0.2;
        currentScale = Math.round(currentScale * 10) / 10;
        updateZoomLevel();
        renderPages();
    }
}

function resetZoom() {
    currentScale = 1.2;
    updateZoomLevel();
    renderPages();
}

updateZoomLevel();

// Helper function để expand selection đến word boundaries
function expandToWordBoundaries(range) {
    const startContainer = range.startContainer;
    const endContainer = range.endContainer;
    
    if (startContainer.nodeType === Node.TEXT_NODE) {
        const text = startContainer.textContent;
        let startOffset = range.startOffset;
        
        // Tìm word boundary ở đầu
        while (startOffset > 0 && /\w/.test(text[startOffset - 1])) {
            startOffset--;
        }
        range.setStart(startContainer, startOffset);
    }
    
    if (endContainer.nodeType === Node.TEXT_NODE) {
        const text = endContainer.textContent;
        let endOffset = range.endOffset;
        
        // Tìm word boundary ở cuối - bao gồm cả dấu câu
        while (endOffset < text.length && /[\w\s]/.test(text[endOffset])) {
            endOffset++;
        }
        range.setEnd(endContainer, endOffset);
    }
    
    return range;
}

document.addEventListener('keydown', function(e) {
    if (e.ctrlKey || e.metaKey) {
        if (e.key === '=' || e.key === '+') {
            e.preventDefault();
            zoomIn();
        } else if (e.key === '-') {
            e.preventDefault();
            zoomOut();
        } else if (e.key === '0') {
            e.preventDefault();
            resetZoom();
        } else if (e.key === 's') {
            // Ctrl+S để save selection hiện tại
            e.preventDefault();
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                document.dispatchEvent(new MouseEvent('mouseup'));
            }
        } else if (e.key === 'w') {
            // Ctrl+W để expand selection đến word boundaries
            e.preventDefault();
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                expandToWordBoundaries(range);
                selection.removeAllRanges();
                selection.addRange(range);
            }
        }
    }
});
function setupSelectionHandlers() {
    document.addEventListener('mouseup', function(e) {
        if (!isReady) return;

        setTimeout(function() {
            const selection = window.getSelection();
            let selectedText = '';

            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);

                // Sử dụng TreeWalker để lấy tất cả text nodes
                const walker = document.createTreeWalker(
                    range.commonAncestorContainer,
                    NodeFilter.SHOW_TEXT,
                    {
                        acceptNode: function(node) {
                            const nodeRange = document.createRange();
                            nodeRange.selectNodeContents(node);
                            
                            // Kiểm tra node có trong selection range không
                            if (!(range.compareBoundaryPoints(Range.END_TO_START, nodeRange) <= 0 ||
                                  range.compareBoundaryPoints(Range.START_TO_END, nodeRange) >= 0)) {
                                return NodeFilter.FILTER_ACCEPT;
                            }
                            return NodeFilter.FILTER_REJECT;
                        }
                    }
                );

                let textParts = [];
                let node;
                let previousElement = null;

                while ((node = walker.nextNode())) {
                    let nodeText = node.textContent;

                    // Xử lý start và end offset
                    if (node === range.startContainer) {
                        nodeText = nodeText.substring(range.startOffset);
                    }
                    if (node === range.endContainer) {
                        if (node === range.startContainer) {
                            nodeText = nodeText.substring(range.startOffset, range.endOffset);
                        } else {
                            nodeText = nodeText.substring(0, range.endOffset);
                        }
                    }

                    if (nodeText) {
                        const currentElement = node.parentElement;
                        
                        // Thêm dấu cách nếu cần thiết
                        if (previousElement && previousElement !== currentElement) {
                            const prevStyle = getComputedStyle(previousElement);
                            const currentStyle = getComputedStyle(currentElement);
                            
                            // Kiểm tra nếu elements khác nhau hoặc có line break
                            const isBlockElement = prevStyle.display === 'block' || 
                                                 currentStyle.display === 'block' ||
                                                 prevStyle.display === 'list-item' ||
                                                 currentStyle.display === 'list-item';
                            
                            if (isBlockElement) {
                                // Nếu là block element, thêm newline
                                if (textParts.length > 0 && !textParts[textParts.length - 1].endsWith(' ') && !textParts[textParts.length - 1].endsWith('\n')) {
                                    textParts.push('\n');
                                }
                            } else {
                                // Nếu không phải block, thêm space để tránh text bị dính
                                if (textParts.length > 0 && !textParts[textParts.length - 1].endsWith(' ')) {
                                    textParts.push(' ');
                                }
                            }
                        }

                        textParts.push(nodeText);
                        previousElement = currentElement;
                    }
                }

                selectedText = textParts.join('');
            }

            // Fallback methods
            if (!selectedText || selectedText.length < 3) {
                try {
                    const range = selection.getRangeAt(0);
                    const clonedRange = range.cloneRange();
                    const fragment = clonedRange.cloneContents();
                    const tempDiv = document.createElement('div');
                    tempDiv.appendChild(fragment);
                    
                    // Thêm space giữa các elements để tránh text dính nhau
                    const elements = tempDiv.querySelectorAll('*');
                    elements.forEach(el => {
                        if (getComputedStyle(el).display === 'block' || el.tagName === 'BR') {
                            el.after(document.createTextNode('\n'));
                        } else {
                            el.after(document.createTextNode(' '));
                        }
                    });
                    
                    selectedText = tempDiv.textContent || tempDiv.innerText || '';
                } catch (e) {
                    selectedText = selection.toString();
                }
            }

            // Normalize text: xử lý whitespace và newlines
            selectedText = selectedText
                .replace(/\s+/g, ' ')  // Collapse multiple spaces thành 1 space
                .replace(/\n\s+/g, '\n')  // Remove spaces after newlines
                .replace(/\s+\n/g, '\n')  // Remove spaces before newlines  
                .replace(/\n+/g, '\n')    // Collapse multiple newlines
                .trim();

            // Xử lý trường hợp đặc biệt: thêm space giữa các từ bị dính
            selectedText = selectedText.replace(/([a-zàáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ])([A-ZÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ])/g, '$1 $2');

            if (selectedText.length > 3 && selectedText !== lastSelectedText) {
                lastSelectedText = selectedText;

                // Update status UI
                const statusEl = document.getElementById('status');
                statusEl.textContent = '🔄 Đang lưu ' + selectedText.length + ' ký tự vào file...';
                statusEl.style.background = '#fff3cd';
                statusEl.style.color = '#856404';

                // Gửi POST với encoding utf-8
                fetch('http://localhost:8888/save-text', {
                    method: 'POST',
                    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
                    body: selectedText
                }).then(response => {
                    if (response.ok) {
                        statusEl.textContent = '✅ Đã lưu ' + selectedText.length + ' ký tự vào file!';
                        statusEl.style.background = '#d4edda';
                        statusEl.style.color = '#155724';
                        console.log('✅ Text saved to file successfully');
                    } else {
                        throw new Error('Server error');
                    }
                }).catch(error => {
                    statusEl.textContent = '❌ Lỗi lưu file - Server không hoạt động';
                    statusEl.style.background = '#f8d7da';
                    statusEl.style.color = '#721c24';
                    console.error('❌ Error saving text:', error);
                });

                console.log('✅ Selected text (' + selectedText.length + ' chars):', selectedText);
                console.log('📝 Preview:', selectedText.substring(0, 100) + (selectedText.length > 100 ? '...' : ''));
            }
        }, 100);
    });

    
    // Thêm double-click để select word hoàn chỉnh
    document.addEventListener('dblclick', function(e) {
        if (!isReady) return;
        
        setTimeout(function() {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                
                // Mở rộng selection để lấy word hoàn chỉnh
                const text = range.toString();
                if (text && text.length > 0) {
                    // Trigger save ngay lập tức cho double-click
                    document.dispatchEvent(new MouseEvent('mouseup'));
                }
            }
        }, 50);
    });
} 
import streamlit as st
import PyPDF2
import fitz
from fpdf import FPDF
from datetime import datetime
import io
import base64
import os
import tempfile
import re
import subprocess
from PIL import Image
import pdfplumber
from colormath.color_objects import sRGBColor, LabColor
from colormath.color_diff import delta_e_cie2000
from colormath.color_conversions import convert_color
from pdfminer.high_level import extract_pages
from pdfminer.layout import LTTextContainer, LTChar, LTPage
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfparser import PDFParser
import pikepdf

# Set UI
st.set_page_config(page_title="RN Preflight Fairy", page_icon="🧚‍♀️", layout="wide")

# Global padding style
st.markdown("""
    <style>
        .main .block-container {
            padding-right: 5rem;
        }
    </style>
""", unsafe_allow_html=True)

# Play sound
def play_sound(filename):
    try:
        path = os.path.join("assets", filename)
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.components.v1.html(f"""
                <audio autoplay>
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>""", height=0)
    except Exception:
        pass

# Style selection
style_mode = st.sidebar.radio("✨ UI Style", ["Sparkle Mode", "Studio Mode"], index=1)
output_mode = st.sidebar.radio("🎯 Preflight Target", ["Digital", "Print"])

# Play sparkle sound if mode is changed to Sparkle Mode and wasn't previously
if style_mode == "Sparkle Mode":
    play_sound("sparkle.mp3")

# Update the logo styling and display logic
st.sidebar.markdown("""
    <style>
        /* Container for the logo */
        .sidebar-logo {
            position: fixed;
            bottom: 0;
            padding: 2rem 0.5rem 2rem 0.5rem;
            z-index: 1000;
            width: calc(100% - 1rem); /* Account for total padding */
        }
        
        /* Logo image styling */
        .sidebar-logo img {
            width: calc(100% - 1rem); /* Ensure image stays within sidebar with padding */
            max-width: 200px; /* Prevent logo from getting too large */
            height: auto;
            display: block; /* Ensure proper margin handling */
        }

        /* Theme-aware logo display for Studio Mode */
        @media (prefers-color-scheme: light) {
            .studio-mode-logo.light { display: block; }
            .studio-mode-logo.dark { display: none; }
        }
        @media (prefers-color-scheme: dark) {
            .studio-mode-logo.light { display: none; }
            .studio-mode-logo.dark { display: block; }
        }
    </style>
""", unsafe_allow_html=True)

# Convert both logos to base64
logo_sparkle_path = "assets/logo sparkle.png"
logo_studio_path = "assets/logo studio.png"

with open(logo_sparkle_path, "rb") as f:
    logo_sparkle_base64 = base64.b64encode(f.read()).decode()

with open(logo_studio_path, "rb") as f:
    logo_studio_base64 = base64.b64encode(f.read()).decode()

# Insert the appropriate logo based on mode
if style_mode == "Sparkle Mode":
    st.sidebar.markdown(f"""
        <div class="sidebar-logo">
            <img src="data:image/png;base64,{logo_sparkle_base64}">
        </div>
    """, unsafe_allow_html=True)
else:
    # In Studio Mode, include both logos with theme-aware display
    st.sidebar.markdown(f"""
        <div class="sidebar-logo">
            <img src="data:image/png;base64,{logo_studio_base64}" class="studio-mode-logo light">
            <img src="data:image/png;base64,{logo_sparkle_base64}" class="studio-mode-logo dark">
        </div>
    """, unsafe_allow_html=True)

# Conditional styling based on mode
if style_mode == "Sparkle Mode":
    st.markdown("""
        <style>
            .stApp { 
                background-color: #2b1e66;
            }
            header[data-testid="stHeader"] {
                background-color: #f8d400;
            }
            section[data-testid="stSidebar"] {
                background-color: #d93ddb;
            }
            /* Add padding to main content area */
            section[data-testid="stAppViewContainer"] > div:first-child {
                padding-right: 50px !important;
            }
            /* Reduce main heading padding */
            section[data-testid="stAppViewContainer"] > div:first-child > div:first-child {
                padding-top: 1rem !important;
            }
            h1, h2, h3 {
                color: #f8d400;
            }
            p, span, div {
                color: white;
            }
            .stButton > button {
                background-color: #456df3;
                color: #2b1e66;
            }
            .stButton > button:hover {
                background-color: #01c5c7;
            }
            /* Radio button styling */
            [data-testid="stMarkdown"] label {
                color: #f8d400 !important;
            }
            div[role="radiogroup"] label {
                color: #f8d400 !important;
            }
            div[role="radiogroup"] div[data-baseweb="radio"] input:checked + div {
                background-color: #f8d400 !important;
                border-color: #f8d400 !important;
            }
            /* File upload styling */
            [data-testid="stFileUploadDropzone"],
            section[data-testid="stFileUploadDropzone"],
            .stFileUploader > section,
            .stFileUploader > section > div,
            .stFileUploader > section > div > div,
            div[data-testid="stFileUploader"] section {
                background-color: #456ef2 !important;
                border-color: #456ef2 !important;
            }
            div[data-testid="stFileUploadDropzone"] div[data-testid="stMarkdownContainer"] p {
                color: #2b1e66;
            }
            /* Remove any white backgrounds from inner elements */
            [data-testid="stFileUploadDropzone"] div {
                background-color: transparent !important;
            }
            /* Download button specific styling */
            .stDownloadButton button, 
            .stButton button[data-testid="stDownloadButton"] {
                background-color: #456ef2;
                border-color: #456ef2;
            }
            .stDownloadButton button:hover, 
            .stButton button[data-testid="stDownloadButton"]:hover {
                background-color: #00d98c;
                border-color: #00d98c;
            }
            .stDownloadButton button:active,
            .stButton button[data-testid="stDownloadButton"]:active {
                background-color: #f7d400;
                border-color: #f7d400;
            }
        </style>
    """, unsafe_allow_html=True)
    st.title("🧚‍♀️ RN Preflight Fairy – Sparkle Mode")
    st.balloons()
else:
    # Add Studio Mode padding and heading spacing
    st.markdown("""
        <style>
            section[data-testid="stAppViewContainer"] > div:first-child {
                padding-right: 50px !important;
            }
            /* Reduce main heading padding */
            section[data-testid="stAppViewContainer"] > div:first-child > div:first-child {
                padding-top: 1rem !important;
            }
        </style>
    """, unsafe_allow_html=True)
    st.title(f"🗂️ RN Preflight Scanner – Studio Mode ({output_mode})")

play_sound("digital.mp3" if output_mode == "Digital" else "print.mp3")
uploaded_file = st.file_uploader("", type="pdf")

results = []

def clean_line(text):
    """Clean text for PDF output by replacing Unicode characters with ASCII equivalents"""
    replacements = {
        '\u2013': '-',    # en dash
        '\u2014': '-',    # em dash
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u00a0': ' ',    # non-breaking space
        '\u200b': '',     # zero-width space
        '\u2026': '...',  # ellipsis
        '\u2122': '(TM)', # trademark
        '\u00ae': '(R)',  # registered trademark
        '\u00b0': 'deg',  # degree
        '\u274c': 'X',    # cross mark
        '\u2705': 'OK',   # check mark
        '✅': 'OK',       # check mark
        '❌': 'X',        # cross mark
        '✓': 'OK',       # check mark
        '⚠️': '!',       # warning
        '✨': '*'         # sparkle
    }
    return ''.join(replacements.get(c, c) if ord(c) < 128 else '?' for c in text).strip()

# === Core Preflight Checks ===

def check_metadata(reader):
    try:
        meta = reader.metadata
        if meta and "created by real nation" in str(meta).lower():
            return ["✅ Metadata: All key metadata present"]
        return ["❌ Metadata: Missing key metadata"]
    except Exception as e:
        return [f"❌ Metadata check failed – {e}"]

def check_bleed(reader):
    try:
        page = reader.pages[0]
        media = page.mediabox
        trim = getattr(page, 'trimbox', None) or getattr(page, 'cropbox', None)
        if not trim:
            return ["❌ Bleed: Not present"]
        has_bleed = (
            float(media.left) < float(trim.left) or
            float(media.bottom) < float(trim.bottom) or
            float(media.right) > float(trim.right) or
            float(media.top) > float(trim.top)
        )
        return ["✅ Bleed: Present"] if has_bleed else ["❌ Bleed: Not present"]
    except Exception as e:
        return [f"❌ Bleed check failed – {e}"]

def check_inch_marks(reader):
    found = {}
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if not text:
            continue
        for symbol, name in {
            "′": "prime", "″": "double prime", "´": "acute",
            "˝": "double acute", "ʹ": "modifier prime", "ˮ": "modifier double apostrophe"
        }.items():
            if symbol in text:
                found.setdefault(symbol, {"name": name, "pages": set()})["pages"].add(i + 1)
    if not found:
        return ["✅ Inch Marks: None found"]
    lines = ["❌ Inch Marks: Found unusual characters:"]
    for s, meta in found.items():
        pages = ", ".join(str(p) for p in sorted(meta["pages"]))
        lines.append(f"  - {repr(s)} – {meta['name']} (pages {pages})")
    return lines

# Accurate resolution checker
def check_resolution(doc):
    lines = []
    low_res_found = False
    low_res_details = []
    all_image_details = []
    
    for i, page in enumerate(doc):
        try:
            for img in page.get_images(full=True):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                bbox = page.get_image_bbox(img)
                if bbox:
                    width_pts = abs(bbox[2] - bbox[0])
                    width_in = width_pts / 72
                    dpi = round(pix.width / width_in) if width_in else 0
                    
                    # Store full details for PDF report
                    detail = f"  - Image {xref} (page {i+1}): {dpi} PPI"
                    all_image_details.append(detail)
                    
                    # If low resolution, store details for dashboard
                    if dpi < 150:
                        low_res_found = True
                        low_res_details.append(f"  - Image on page {i+1}: {dpi} PPI")
        except Exception as e:
            error_msg = f"  - Image (page {i+1}): resolution check failed – {e}"
            low_res_details.append(error_msg)
            all_image_details.append(error_msg)
            low_res_found = True
    
    # Create two different result sets
    dashboard_results = []
    pdf_results = []
    
    # Summary for both
    summary = "❌ Resolution: Suspected low-res image(s) below 150 PPI" if low_res_found else "✅ Resolution: All images above 150 PPI"
    dashboard_results.append(summary)
    pdf_results.append(summary)
    
    # Add details
    if low_res_found:
        dashboard_results.extend(low_res_details)  # Only low-res images for dashboard
    pdf_results.extend(all_image_details)  # All images for PDF report
    
    return dashboard_results, pdf_results

# Simple placeholder text detection
def placeholder_check(doc):
    flags = []
    terms = ["lorem ipsum", "placeholder", "your text here"]
    for i, page in enumerate(doc):
        try:
            text = page.get_text().lower()
            for t in terms:
                if t in text:
                    flags.append(f"❌ Placeholder Text: Placeholder text found on page {i + 1}: '{t}'")
        except Exception:
            continue
    return flags if flags else ["✅ Placeholder Text: None found"]

# Update the validation function to use clean_line for messages
def validate_with_pdfcpu(file_bytes):
    try:
        # Use PyPDF2 for structure checking
        reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
        
        # First check if this is a Canva PDF
        try:
            if "/Info" in reader.trailer:
                info = reader.trailer["/Info"]
                if "/Producer" in info:
                    producer = str(info["/Producer"])
                    if "Canva" in producer:
                        return [
                            "❌ PDF Structure: Canva PDFs are not properly tagged for accessibility",
                            "❌ Document Title: Canva PDFs require manual accessibility tagging"
                        ]
        except Exception:
            pass
        
        # Continue with normal validation for non-Canva PDFs
        has_tags = False
        has_content = False
        has_real_tags = False
        
        try:
            # Check for actual text content in the document
            for page in reader.pages:
                if page.extract_text().strip():
                    has_content = True
                    break
            
            # Get the root and check tag structure
            root = reader.trailer["/Root"]
            marked = False
            struct_tree_present = False
            
            # Check mark info
            if "/MarkInfo" in root:
                mark_info = root["/MarkInfo"]
                if "/Marked" in mark_info and mark_info["/Marked"]:
                    marked = True
            
            # Check structure tree and its content
            if "/StructTreeRoot" in root:
                struct_tree = root["/StructTreeRoot"]
                struct_tree_present = True
                
                # Check for actual tag content
                if "/K" in struct_tree:
                    k_content = struct_tree["/K"]
                    if isinstance(k_content, (dict, list)) and k_content:
                        has_real_tags = True
            
            # Document is only considered tagged if it:
            # 1. Claims to be tagged (marked)
            # 2. Has a structure tree
            # 3. Has actual content to tag
            # 4. Has real tag content in the structure tree
            has_tags = marked and struct_tree_present and has_content and has_real_tags
                
        except Exception:
            has_tags = False
            
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp:
            temp.write(file_bytes)
            temp.flush()
            
            # Get detailed info about the PDF
            info_result = subprocess.run(
                ["/Users/realnation/Downloads/pdfcpu_0.9.1_Darwin_arm64/pdfcpu", "info", temp.name],
                capture_output=True,
                text=True
            )
        
        os.unlink(temp.name)
        
        results = []
        
        # Report on structure based on all checks
        if has_tags:
            results.append("✅ PDF Structure: Document is tagged for accessibility")
        else:
            if not has_content:
                results.append("❌ PDF Structure: Document has no text content to tag")
            elif not marked:
                results.append("❌ PDF Structure: Document is not marked as tagged")
            elif not struct_tree_present:
                results.append("❌ PDF Structure: Document lacks structure tree")
            elif not has_real_tags:
                results.append("❌ PDF Structure: Document claims to be tagged but has no actual tag content")
            else:
                results.append("❌ PDF Structure: Document is not properly tagged for accessibility")
            
        # Check for document title
        title_match = re.search(r"Title:\s*(\S.*?)(?:\n|$)", info_result.stdout)
        if title_match and title_match.group(1).strip():
            results.append("✅ Document Title: Title is set")
        else:
            results.append("❌ Document Title: No title set - required for accessibility")
        
        return results
    except Exception as e:
        return [f"❌ PDF Structure check failed – {str(e)}"]

# Smart filename generator
def parse_filename_for_report_name(filename):
    name_only = os.path.splitext(filename)[0]
    normalized = name_only.replace("_", " ").replace("-", " ")
    match = re.search(r"\b(D\d{4})\b.*?\b((Print|Digital|Inhouse)?\s?(AW\d*|v\d+|AW|AW1|AW2))\b", normalized, re.IGNORECASE)
    if match:
        job = match.group(1)
        version = match.group(2).strip().replace(" ", "_")
        return f"{job} {version} Preflight Report.pdf"
    return f"{name_only} Preflight Report.pdf"

def get_file_metadata(reader, file_bytes):
    """Extract and format file metadata"""
    try:
        metadata = {}
        print("Starting metadata extraction...")
        
        # Get creation and modification dates
        if '/Info' in reader.trailer:
            info = reader.trailer['/Info']
            print(f"Found Info dictionary: {info}")
            
            # Try multiple ways to get dates
            created = None
            modified = None
            
            # Method 1: Direct from Info dictionary
            if '/CreationDate' in info:
                created = str(info['/CreationDate'])
            if '/ModDate' in info:
                modified = str(info['/ModDate'])
            
            # Method 2: From document info
            if not created and hasattr(reader, 'metadata'):
                created = reader.metadata.get('/CreationDate', '')
            if not modified and hasattr(reader, 'metadata'):
                modified = reader.metadata.get('/ModDate', '')
            
            print(f"Raw creation date: {created}")
            print(f"Raw modification date: {modified}")
            
            # Convert PDF date format (D:YYYYMMDDHHmmSS) to readable format
            def format_pdf_date(date_str):
                if not date_str:
                    return 'Not available'
                if isinstance(date_str, str):
                    # Handle different date formats
                    if date_str.startswith('D:'):
                        try:
                            # Extract date components
                            year = date_str[2:6]
                            month = date_str[6:8]
                            day = date_str[8:10]
                            return f"{day}/{month}/{year}"
                        except:
                            pass
                    # Try to find date pattern in string
                    import re
                    date_match = re.search(r'(\d{4})(\d{2})(\d{2})', date_str)
                    if date_match:
                        year, month, day = date_match.groups()
                        return f"{day}/{month}/{year}"
                return 'Not available'
            
            metadata['Created'] = format_pdf_date(created)
            metadata['Modified'] = format_pdf_date(modified)
            print(f"Formatted dates - Created: {metadata['Created']}, Modified: {metadata['Modified']}")
        else:
            print("No /Info dictionary found in trailer")
            metadata['Created'] = 'Not available'
            metadata['Modified'] = 'Not available'
        
        # Get file size
        size_bytes = len(file_bytes)
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            size_str = f"{size_bytes/1024:.1f} KB"
        else:
            size_str = f"{size_bytes/(1024*1024):.1f} MB"
        
        metadata['File Size'] = size_str
        print(f"File size: {size_str}")
        
        # Calculate size per page ratio for warning
        pages = len(reader.pages)
        size_per_page = size_bytes / pages
        metadata['Size Warning'] = size_per_page > 1024 * 1024  # Warning if > 1MB per page
        print(f"Number of pages: {pages}")
        print(f"Size per page: {size_per_page/1024/1024:.1f} MB")
        
        # Try to determine if PDF is interactive
        is_interactive = False
        root = reader.trailer.get('/Root', {})
        
        # Check for form fields
        if '/AcroForm' in root:
            is_interactive = True
            print("Found AcroForm - PDF is interactive")
        else:
            # Check each page for annotations or form fields
            for page in reader.pages:
                if '/Annots' in page:
                    is_interactive = True
                    print("Found annotations - PDF is interactive")
                    break
                
                # Check for JavaScript actions
                if '/AA' in page or '/OpenAction' in page:
                    is_interactive = True
                    print("Found JavaScript actions - PDF is interactive")
                    break
        
        metadata['Type'] = 'Interactive PDF' if is_interactive else 'Print PDF'
        metadata['Pages'] = str(pages)
        
        print("Final metadata:", metadata)
        return metadata
    except Exception as e:
        print(f"Metadata extraction error: {str(e)}")
        print(f"Error type: {type(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {
            'Created': 'Not available',
            'Modified': 'Not available',
            'File Size': 'Not available',
            'Type': 'Not available',
            'Pages': 'Not available',
            'Size Warning': False
        }

def generate_report(mode, lines, metadata):
    class PDF(FPDF):
        def header(self):
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(43, 30, 102)  # #2B1E66
            self.cell(0, 6, 'RN PREFLIGHT REPORT', 0, 1, 'R')
            self.line(10, 14, 200, 14)
            self.ln(2)  # Reduced from 4

        def footer(self):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f'Page {self.page_no()}/{{nb}}', 0, 0, 'C')
            self.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M")}', 0, 0, 'R')

        def add_separator(self):
            current_y = self.get_y()
            if current_y > 250:  # Don't draw separator if too close to bottom
                self.add_page()
                return
            self.set_draw_color(200, 200, 200)  # Light gray
            self.line(25, current_y + 2, 185, current_y + 2)  # Reduced from +4
            self.ln(4)  # Reduced from 8

        def add_metadata_box(self, metadata):
            # Calculate positions for a 3x2 grid
            cell_width = 60
            cell_height = 12  # Reduced from 14
            start_x = 15
            start_y = self.get_y()
            padding = 3
            
            # Set background color for metadata box
            self.set_fill_color(248, 249, 250)
            self.rect(start_x, start_y, 180, cell_height * 2 + padding * 2, 'F')
            
            # Add metadata in a grid layout
            self.set_font('Helvetica', 'B', 9)
            self.set_text_color(51, 51, 51)
            
            # First row
            self.set_xy(start_x + padding, start_y + padding)
            self.cell(cell_width, cell_height/2, 'Created', 0, 2, 'L')
            self.set_font('Helvetica', '', 9)
            self.cell(cell_width, cell_height/2, metadata.get('Created', 'Not available'), 0, 0, 'L')
            
            self.set_xy(start_x + cell_width + padding, start_y + padding)
            self.set_font('Helvetica', 'B', 9)
            self.cell(cell_width, cell_height/2, 'Modified', 0, 2, 'L')
            self.set_font('Helvetica', '', 9)
            self.cell(cell_width, cell_height/2, metadata.get('Modified', 'Not available'), 0, 0, 'L')
            
            self.set_xy(start_x + cell_width * 2 + padding, start_y + padding)
            self.set_font('Helvetica', 'B', 9)
            self.cell(cell_width, cell_height/2, 'File Size', 0, 2, 'L')
            self.set_font('Helvetica', '', 9)
            size_text = metadata.get('File Size', 'Not available')
            if metadata.get('Size Warning', False):
                size_text += ' !'
            self.cell(cell_width, cell_height/2, size_text, 0, 0, 'L')
            
            # Second row
            self.set_xy(start_x + padding, start_y + cell_height + padding)
            self.set_font('Helvetica', 'B', 9)
            self.cell(cell_width, cell_height/2, 'Type', 0, 2, 'L')
            self.set_font('Helvetica', '', 9)
            self.cell(cell_width, cell_height/2, metadata.get('Type', 'Not available'), 0, 0, 'L')
            
            self.set_xy(start_x + cell_width + padding, start_y + cell_height + padding)
            self.set_font('Helvetica', 'B', 9)
            self.cell(cell_width, cell_height/2, 'Pages', 0, 2, 'L')
            self.set_font('Helvetica', '', 9)
            self.cell(cell_width, cell_height/2, metadata.get('Pages', 'Not available'), 0, 0, 'L')
            
            # Move cursor below the metadata box with minimal padding
            self.ln(cell_height * 2 + padding * 2 - 4)  # Reduced padding after box

    pdf = PDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(12, 14, 12)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(43, 30, 102)  # #2B1E66
    pdf.cell(0, 12, clean_line("Preflight Report"), ln=True)  # Reduced from 14

    # Preflight Target
    pdf.set_font("Helvetica", "I", 12)
    pdf.set_text_color(128, 128, 128)
    pdf.cell(0, 6, f"Target: {output_mode}", ln=True)

    # Add metadata section with reduced spacing
    pdf.ln(2)  # Reduced from implicit ln(0)
    pdf.add_metadata_box(metadata)
    pdf.ln(-2)  # Create negative space to bring boxes closer

    # Summary box
    pdf.set_fill_color(245, 245, 245)
    pdf.set_text_color(51, 51, 51)
    
    # Create summary box background
    summary_start_y = pdf.get_y()
    pdf.rect(15, summary_start_y, 180, 20, 'F')  # Single height box for all content
    
    # Summary heading
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_xy(25, summary_start_y + 6)  # Adjusted position and added more vertical centering
    pdf.cell(40, 8, "Summary", 0, 0, 'L')
    
    # Count passes and fails
    passes = sum(1 for line in lines if line.startswith("✅"))
    fails = sum(1 for line in lines if line.startswith("❌"))
    
    # Calculate column widths and positions for even spacing
    total_width = 180 - 65  # Total width minus Summary label space
    col_width = total_width / 3
    start_x = 80  # Adjusted start position
    
    # Add summary statistics in columns with even spacing
    pdf.set_font("Helvetica", "", 10)
    
    # Total Checks
    pdf.set_xy(start_x, summary_start_y + 6)
    pdf.cell(col_width, 8, f"Total Checks: {passes + fails}", 0, 0, 'L')
    
    # Passed
    pdf.set_xy(start_x + col_width, summary_start_y + 6)
    pdf.cell(col_width, 8, f"Passed: {passes}", 0, 0, 'L')
    
    # Failed
    pdf.set_xy(start_x + col_width * 2, summary_start_y + 6)
    pdf.cell(col_width, 8, f"Failed: {fails}", 0, 0, 'L')
    
    # Move cursor below summary box
    pdf.ln(24)  # Adjusted spacing after summary box

    # Detailed Results
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(51, 51, 51)
    pdf.cell(0, 8, "Detailed Results:", ln=True)
    pdf.ln(2)

    current_section = None
    first_section = True
    in_general_checks = True  # Track if we're in general checks section
    
    for line in lines:
        try:
            # Clean and normalize the text
            txt = clean_line(str(line)).replace("\n", " ").replace("?", "")
            txt = txt.encode("latin1", errors="replace").decode("latin1")
            
            # Detect if this is a section header
            is_section = txt.startswith("✅") or txt.startswith("❌")
            
            # For Digital mode, check if we're transitioning to accessibility checks
            if output_mode == "Digital" and is_section:
                if in_general_checks and any(x in txt for x in [
                    "PDF Structure:", "Document Title:", "Alt Text:",
                    "Heading Structure:", "Reading Order:", "Color Contrast:",
                    "Accessible Tables:"
                ]):
                    in_general_checks = False
                    pdf.add_page()
                    pdf.set_font("Helvetica", "B", 16)
                    pdf.set_text_color(43, 30, 102)
                    pdf.cell(0, 10, "Accessibility Checks", ln=True)
                    pdf.ln(4)
                    first_section = True  # Reset first section flag for accessibility section
            
            if is_section:
                # Add separator between sections (except before first section)
                if not first_section:
                    pdf.add_separator()
                first_section = False
                
                # Create a rounded rectangle background
                pdf.set_fill_color(248, 249, 250)
                current_y = pdf.get_y()
                pdf.rect(15, current_y, 180, 10, 'F', corners='1234', radius=2)
                
                pdf.set_font("Helvetica", "B", 12)
                if txt.startswith("✅"):
                    pdf.set_text_color(0, 128, 0)
                    txt = txt.replace("✅", "PASS: ")
                else:
                    pdf.set_text_color(180, 0, 0)
                    txt = txt.replace("❌", "FAIL: ")
                
                pdf.set_xy(20, current_y + 1)
                pdf.cell(0, 8, txt.strip(), ln=True)
                pdf.ln(4)
                current_section = txt
            else:
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(51, 51, 51)
                
                if txt.strip().startswith("-"):
                    txt = "-" + txt.strip()[1:]
                    pdf.cell(15, 6, "", 0, 0)
                    pdf.multi_cell(0, 6, txt.strip())
                    pdf.ln(2)
                else:
                    pdf.cell(10, 6, "", 0, 0)
                    pdf.multi_cell(0, 6, txt.strip())
                    pdf.ln(2)
                
        except Exception as e:
            pdf.set_text_color(180, 0, 0)
            pdf.multi_cell(0, 6, f"    [Line skipped due to encoding error: {str(e)}]")

    # Add Tips section at the end
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(43, 30, 102)
    pdf.cell(0, 10, "Tips & Recommendations", ln=True)
    pdf.ln(5)

    # Get relevant tips based on mode and failed checks
    all_tips = get_tips()
    mode_tips = all_tips["digital"] if output_mode == "Digital" else all_tips["print"]
    
    # Find failed checks in results
    failed_checks = []
    for line in lines:
        if line.startswith("❌"):
            check_name = line.split(":")[0].replace("❌", "").strip()
            failed_checks.append(check_name)
    
    # Show relevant tips for failed checks
    relevant_tips = {k: v for k, v in mode_tips.items() 
                    if any(check in k for check in failed_checks)}
    
    if relevant_tips:
        pdf.set_font("Helvetica", "B", 12)
        pdf.set_text_color(51, 51, 51)
        pdf.cell(0, 10, "How to Fix Failed Checks:", ln=True)
        pdf.ln(2)
        
        for k, v in relevant_tips.items():
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, k, ln=True)
            pdf.set_font("Helvetica", "", 10)
            pdf.multi_cell(0, 6, clean_line(v))  # Clean the tip text
            pdf.ln(4)
    else:
        pdf.set_font("Helvetica", "", 12)
        pdf.set_text_color(0, 128, 0)
        pdf.cell(0, 10, "* All checks passed! No fixes needed.", ln=True)  # Using * instead of ✨

    return io.BytesIO(pdf.output(dest="S").encode("latin1"))

def check_alt_text(doc):
    """Check for images without alt text"""
    results = []
    images_without_alt = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        try:
            for img in page.get_images(full=True):
                xref = img[0]
                img_obj = doc.xref_object(xref, compressed=True)
                if isinstance(img_obj, dict) and '/Alt' not in img_obj:
                    images_without_alt.append(f"  - Image on page {page_num + 1}")
        except Exception as e:
            images_without_alt.append(f"  - Error checking image on page {page_num + 1} – {str(e)}")
    
    if images_without_alt:
        results.append("❌ Alt Text: Found images without alternative text")
        results.extend(images_without_alt)
    else:
        results.append("✅ Alt Text: All images have alternative text")
    
    return results

def check_heading_structure(doc):
    """Check for proper heading structure"""
    results = []
    heading_levels = []
    
    try:
        for page in doc:
            blocks = page.get_text("dict")["blocks"]
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            if span.get("size", 0) > 12:  # Potential heading
                                heading_levels.append({
                                    "size": span["size"],
                                    "text": span["text"].strip(),
                                    "page": page.number + 1
                                })
        
        # Analyze heading hierarchy
        if heading_levels:
            sizes = sorted(set(h["size"] for h in heading_levels), reverse=True)
            issues = []
            
            # Check for skipped levels and empty headings
            for i in range(len(heading_levels) - 1):
                current = heading_levels[i]
                next_heading = heading_levels[i + 1]
                
                # Skip empty or whitespace-only headings
                if not current["text"] or not next_heading["text"]:
                    continue
                    
                current_level = sizes.index(current["size"])
                next_level = sizes.index(next_heading["size"])
                if next_level - current_level > 1:
                    issues.append(f"  - Heading level skip on page {next_heading['page']}: '{next_heading['text']}'")
            
            # First add the main heading result
            if issues:
                results.append("❌ Heading Structure: Found inconsistent heading hierarchy")
                # Then add all the issues
                results.extend(issues)
            else:
                results.append("✅ Heading Structure: Proper heading hierarchy maintained")
        else:
            results.append("⚠️ Heading Structure: No clear headings detected")
    
    except Exception as e:
        results.append(f"❌ Heading Structure check failed – {str(e)}")
    
    return results

def check_reading_order(doc):
    """Check for potential reading order issues"""
    results = []
    issues = []
    
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            # Check for potential column issues
            columns = {}
            for block in blocks:
                if "lines" in block:
                    x0 = block["bbox"][0]
                    if x0 not in columns:
                        columns[x0] = []
                    columns[x0].append(block)
            
            # If multiple columns detected, check if they're properly marked
            if len(columns) > 1:
                try:
                    catalog = doc.pdf_catalog()
                    if isinstance(catalog, dict) and "/StructTreeRoot" in catalog:
                        struct_tree = catalog["/StructTreeRoot"]
                        if not any(tag in str(struct_tree) for tag in ["/Column", "/Art", "/Sect"]):
                            issues.append(f"  - Page {page_num + 1}: Multiple columns detected without proper structure tags")
                except:
                    issues.append(f"  - Page {page_num + 1}: Could not verify column structure")
    
        if issues:
            results.append("❌ Reading Order: Found potential reading order issues")
            results.extend(issues)
        else:
            results.append("✅ Reading Order: No obvious reading order issues detected")
            
    except Exception as e:
        results.append(f"❌ Reading Order check failed – {str(e)}")
    
    return results

def calculate_relative_luminance(r, g, b):
    """Calculate relative luminance according to WCAG 2.1 formula"""
    def adjust(value):
        # Ensure value is between 0-1
        value = max(0, min(1, value))
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    
    return 0.2126 * adjust(r) + 0.7152 * adjust(g) + 0.0722 * adjust(b)

def calculate_contrast_ratio(l1, l2):
    """
    Calculate contrast ratio with increased precision
    """
    lighter = max(l1, l2)
    darker = min(l1, l2)
    # Add extra precision to the calculation
    ratio = (lighter + 0.05) / (darker + 0.05)
    # Round to 3 decimal places for more accurate comparison
    return round(ratio, 3)

def unpack_color(color):
    """Convert a packed RGB integer or list to normalized RGB components"""
    if isinstance(color, list):
        # If it's already a list, ensure it has 3 components
        if len(color) == 3:
            return color
        return [0, 0, 0]  # Default to black if invalid
    elif isinstance(color, (int, float)):
        # Unpack integer color value to RGB
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        return [r/255, g/255, b/255]
    return [0, 0, 0]  # Default to black for any other case

def sample_background_color(page, bbox, matrix_size=5):
    """
    Sample background color from a region around text using a sampling matrix
    with improved accuracy and anti-aliasing handling
    Args:
        page: fitz.Page object
        bbox: text bounding box (x0, y0, x1, y1)
        matrix_size: size of sampling matrix (default increased to 5 for better averaging)
    Returns:
        Tuple of (r, g, b) normalized to 0-1 range
    """
    try:
        # Increase zoom factor for higher precision sampling
        zoom = 4.0  # Doubled from previous 2.0
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        
        # Calculate baseline y-coordinate (bottom of text)
        baseline_y = int((bbox[3] * zoom))
        x_center = int(((bbox[0] + bbox[2]) / 2) * zoom)
        
        # Initialize color accumulators and weights
        r_weighted_sum = g_weighted_sum = b_weighted_sum = 0
        total_weight = 0
        
        # Sample in a matrix pattern around the baseline
        offset = matrix_size // 2
        for y in range(baseline_y - offset, baseline_y + offset + 1):
            for x in range(x_center - offset, x_center + offset + 1):
                if 0 <= x < pix.width and 0 <= y < pix.height:
                    # Calculate distance from center for weighted average
                    distance = ((x - x_center) ** 2 + (y - baseline_y) ** 2) ** 0.5
                    # Gaussian-like weight based on distance from center
                    weight = 1 / (1 + (distance / (matrix_size / 2)) ** 2)
                    
                    pixel = pix.pixel(x, y)
                    
                    # Skip likely text pixels (very dark colors)
                    pixel_luminance = (pixel[0] + pixel[1] + pixel[2]) / (3 * 255)
                    if pixel_luminance < 0.2:  # Skip very dark pixels
                        continue
                    
                    r_weighted_sum += pixel[0] * weight
                    g_weighted_sum += pixel[1] * weight
                    b_weighted_sum += pixel[2] * weight
                    total_weight += weight
        
        if total_weight == 0:
            return (1, 1, 1)  # Default to white if sampling fails
        
        # Calculate weighted average and normalize to 0-1 range
        return (
            r_weighted_sum / (total_weight * 255),
            g_weighted_sum / (total_weight * 255),
            b_weighted_sum / (total_weight * 255)
        )
        
    except Exception:
        return (1, 1, 1)  # Default to white if sampling fails

def is_background_color(color):
    """
    Check if a color is likely to be a background color
    Args:
        color: tuple of (r, g, b) normalized to 0-1 range
    Returns:
        bool: True if color is likely background
    """
    # Calculate perceived brightness using relative luminance formula
    luminance = calculate_relative_luminance(*color)
    
    # Check if color is very light (likely background)
    return luminance > 0.8

def get_dominant_background(page, bbox, span_bg_color):
    """
    Get the dominant background color with improved accuracy
    Args:
        page: fitz.Page object
        bbox: text bounding box
        span_bg_color: background color from span properties
    Returns:
        tuple: (r, g, b) of the determined background color
    """
    # Sample actual background color with larger matrix for better accuracy
    sampled_color = sample_background_color(page, bbox, matrix_size=5)
    
    # If span has no explicit background color, use sampled color
    if not span_bg_color or span_bg_color == [1, 1, 1]:
        return sampled_color
    
    # Calculate luminance for both colors
    span_luminance = calculate_relative_luminance(*span_bg_color)
    sampled_luminance = calculate_relative_luminance(*sampled_color)
    
    # Enhanced background color detection
    if abs(span_luminance - sampled_luminance) < 0.1:
        # If colors are very similar, use the explicitly set color
        return span_bg_color
    elif sampled_luminance > span_luminance and is_background_color(sampled_color):
        # If sampled color is significantly lighter, use it
        return sampled_color
    elif span_luminance > 0.9 and sampled_luminance > 0.85:
        # For very light colors, use the lighter one to ensure we don't miss subtle contrast issues
        return span_bg_color if span_luminance > sampled_luminance else sampled_color
    
    # Default to span background color if no other conditions are met
    return span_bg_color

def check_color_contrast(doc):
    """Check text color against background according to WCAG standards"""
    dashboard_results = []
    pdf_results = []
    issues = []
    
    try:
        for page_num in range(len(doc)):
            page = doc[page_num]
            blocks = page.get_text("dict")["blocks"]
            
            for block in blocks:
                if "lines" not in block:
                    continue
                    
                # Get block background color
                block_bg = unpack_color(block.get("bgcolor", [1, 1, 1]))  # Default to white
                
                for line in block["lines"]:
                    for span in line["spans"]:
                        # Skip empty or whitespace-only text
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                            
                        # Skip checking contrast of the results text itself
                        if text.startswith("Color Contrast:") or text.startswith("✅") or text.startswith("❌"):
                            continue
                        
                        # Get text properties
                        font_size = span.get("size", 12)  # Font size in points
                        font_flags = span.get("flags", 0)  # Font flags
                        is_bold = bool(font_flags & 2**2)  # Check if bold flag is set
                        
                        # Get text color
                        text_color = unpack_color(span.get("color", 0))  # Default to black
                        
                        # Get span's bounding box for background sampling
                        bbox = span.get("bbox", None)
                        if not bbox:
                            continue
                        
                        try:
                            # Get background color by sampling and comparing with span background
                            span_bg = unpack_color(span.get("bgcolor", [1, 1, 1]))
                            bg_color = get_dominant_background(page, bbox, span_bg)
                            
                            # Calculate luminance values
                            text_luminance = calculate_relative_luminance(*text_color)
                            bg_luminance = calculate_relative_luminance(*bg_color)
                            
                            # Calculate contrast ratio
                            contrast_ratio = calculate_contrast_ratio(text_luminance, bg_luminance)
                            
                            # Convert normalized RGB to hex for reference
                            text_hex = "#{:02X}{:02X}{:02X}".format(
                                int(text_color[0] * 255),
                                int(text_color[1] * 255),
                                int(text_color[2] * 255)
                            )
                            bg_hex = "#{:02X}{:02X}{:02X}".format(
                                int(bg_color[0] * 255),
                                int(bg_color[1] * 255),
                                int(bg_color[2] * 255)
                            )
                            
                            # Determine text size category
                            is_large_text = (font_size >= 18) or (font_size >= 14 and is_bold)
                            
                            # Check against WCAG 2.1 requirements
                            if is_large_text:
                                if contrast_ratio < 3.0:  # Level AA for large text
                                    issues.append({
                                        'page': page_num + 1,
                                        'text': text[:50] + ('...' if len(text) > 50 else ''),
                                        'ratio': contrast_ratio,
                                        'size': font_size,
                                        'bold': is_bold,
                                        'colors': f"{text_hex} on {bg_hex}",
                                        'level': 'AA',
                                        'requirement': '3:1'
                                    })
                            else:  # Normal text
                                if contrast_ratio < 4.5:  # Level AA for normal text
                                    issues.append({
                                        'page': page_num + 1,
                                        'text': text[:50] + ('...' if len(text) > 50 else ''),
                                        'ratio': contrast_ratio,
                                        'size': font_size,
                                        'bold': is_bold,
                                        'colors': f"{text_hex} on {bg_hex}",
                                        'level': 'AA',
                                        'requirement': '4.5:1'
                                    })
                            
                        except Exception as e:
                            continue
        
        if issues:
            # Sort issues by page number
            issues.sort(key=lambda x: x['page'])
            
            # Add the main result to both dashboard and PDF
            dashboard_results.append("❌ Color Contrast: Found contrast ratio issues")
            pdf_results.append("❌ Color Contrast: Found contrast ratio issues")
            
            # Add detailed issues only to PDF results
            current_page = None
            for issue in issues:
                if current_page != issue['page']:
                    current_page = issue['page']
                    pdf_results.append(f"\n  Page {current_page}:")
                
                font_info = f"{issue['size']}pt"
                if issue['bold']:
                    font_info += " bold"
                
                pdf_results.append(
                    f"  - {issue['text']} ({font_info})\n"
                    f"    Contrast ratio: {issue['ratio']:.2f}:1 ({issue['requirement']} required)\n"
                    f"    Colors: {issue['colors']}"
                )
        else:
            dashboard_results.append("✅ Color Contrast: All text meets WCAG 2.1 AA contrast requirements")
            pdf_results.append("✅ Color Contrast: All text meets WCAG 2.1 AA contrast requirements")
            
    except Exception as e:
        error_msg = f"❌ Color Contrast check failed – {str(e)}"
        dashboard_results.append(error_msg)
        pdf_results.append(error_msg)
    
    return dashboard_results, pdf_results

# Add the new table accessibility check function
def check_for_table_tags(page):
    """Check for table-related tags in the PDF structure"""
    tags_found = {
        'table': False,
        'th': False,
        'header_text': [],
        'debug_info': []
    }
    
    # Get raw structure information in multiple formats
    raw_struct = page.get_text("rawdict")
    html_struct = page.get_text("html")
    xml_struct = page.get_text("xml")
    struct_text = f"{str(raw_struct)} {html_struct} {xml_struct}"
    
    # Check for TH tags
    header_markers = [
        '/TH', 'role="TH"', "type='TH'", '<th', 'TableHeader', 'HeaderCell',
        'Table.Head', 'Table.Header', 'TableHeaderCell'
    ]
    
    # If we find TH tags, we can infer a table is present
    th_matches = []
    for marker in header_markers:
        if marker in struct_text:
            th_matches.append(marker)
            try:
                start = struct_text.index(marker)
                end = struct_text.find('\n', start)
                if end > start:
                    header_text = struct_text[start:end].strip()
                    if header_text and len(header_text) > 1:
                        tags_found['header_text'].append(header_text)
            except:
                continue
    
    if th_matches:
        tags_found['th'] = True
        tags_found['table'] = True
        tags_found['debug_info'].append(f"Found TH markers: {th_matches}")
    
    return tags_found

def check_table_accessibility(doc):
    """Check tables for accessibility focusing on proper headers"""
    dashboard_results = []
    pdf_results = []
    debug_info = []
    
    try:
        tables_found = False
        tables_with_issues = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Run tag detection
            tag_results = check_for_table_tags(page)
            
            # If we found a table but no TH tags, we have an issue
            if tag_results['table'] and not tag_results['th']:
                tables_found = True
                tables_with_issues.append({
                    'page': page_num + 1,
                    'issues': ['missing table headers']
                })
            elif tag_results['table']:
                tables_found = True
                # Store debug info only if there's an issue
                if tag_results.get('debug_info'):
                    debug_info.extend([f"Page {page_num + 1}: {info}" for info in tag_results['debug_info']])
        
        # Generate results
        if not tables_found:
            dashboard_results.append("✅ Accessible Tables: No tables found in document")
            pdf_results.append("✅ Accessible Tables: No tables found in document")
        elif not tables_with_issues:
            dashboard_results.append("✅ Accessible Tables: All tables have proper headers")
            pdf_results.append("✅ Accessible Tables: All tables have proper headers")
        else:
            dashboard_results.append("❌ Accessible Tables: Found tables with accessibility issues")
            pdf_results.append("❌ Accessible Tables: Found tables with accessibility issues")
            
            # Add detailed results
            for issue in tables_with_issues:
                pdf_results.append(f"  - Table on page {issue['page']}: {', '.join(issue['issues'])}")
            
            # Add tips
            pdf_results.append("\nTips for fixing table accessibility:")
            pdf_results.append("1. Use Table → Header Rows to define table headers")
            pdf_results.append("2. Ensure 'Generate Tagged PDF' is enabled in Export Adobe PDF settings")
            pdf_results.append("3. Use proper table structure with header cells in InDesign")
            
            # Only include debug info if there were issues
            if debug_info:
                pdf_results.append("\nDebug Information:")
                pdf_results.extend(debug_info)
        
    except Exception as e:
        dashboard_results.append(f"❌ Accessible Tables check failed – {str(e)}")
        pdf_results.append(f"❌ Accessible Tables check failed – {str(e)}")
        # Include debug info on error
        if debug_info:
            pdf_results.append("\nDebug Information:")
            pdf_results.extend(debug_info)
    
    return dashboard_results, pdf_results

# First, define the tips dictionary outside of the main execution block
# Add this near the top of the file after imports

def get_tips():
    """Return dictionary of all available tips"""
    return {
        # Print-specific tips
        "print": {
            "Metadata": "See design department links and guides for instructions on adding metadata.",
            "Bleed": "Ensure trim box is smaller than media box. Add 3mm bleed to your layout.",
            "Inch Marks": "Replace typographic inch marks with straight quotes (\").",
            "Resolution": "Ensure linked images are at least 150 PPI. Check scaling!",
            "Placeholders": "Search for dummy text like 'Lorem ipsum' before exporting.",
        },
        # Digital-specific tips
        "digital": {
            "Metadata": "See design department links and guides for instructions on adding metadata.",
            "Resolution": "Ensure linked images are at least 150 PPI. Check scaling!",
            "Placeholders": "Search for dummy text like 'Lorem ipsum' before exporting.",
            "PDF Structure": "Use paragraph styles with Export Tagging in InDesign.",
            "Alt Text": "In InDesign: Select image → Object → Object Export Options → Alt Text. Add descriptive text that conveys the image's meaning.",
            "Heading Structure": "Use Paragraph Styles for headings. Set Export Tags to match heading levels (H1, H2, etc). Maintain proper hierarchy - don't skip levels.",
            "Reading Order": "Use Articles panel (Window → Articles) to define content flow. Drag content in the order it should be read. Check View → Structure → Show Structure to verify.",
            "Color Contrast": "Use high contrast colors. Check contrast ratios with the Color Theme tool. For accessibility:\n- Normal text (under 18pt): Must be at least 4.5:1\n- Large text (18pt+ or bold 14pt+): Must be at least 3:1\n- If under 14pt and contrast below 4.5:1, must be bold",
            "Document Title": "File → File Info → Basic → Title. Also check 'Display Document Title' in PDF Export → Advanced.",
            "Accessible Tables": "In InDesign: Use Table → Header Rows to define table headers. Add table summary in Object → Object Export Options → Alt Text. Use proper table structure with header cells.",
        }
    }

# ============= Main Run Block =============
if uploaded_file is not None:
    # Play upload sound only in Sparkle Mode
    if style_mode == "Sparkle Mode":
        play_sound("upload.mp3")
    
    try:
        # Read file once and keep in memory
        file_bytes = uploaded_file.getvalue()
        
        # Create a spinner for the scanning animation
        with st.spinner("🔍 Scanning document..."):
            # Create PDF reader once and reuse
            reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            
            # Extract metadata first
            metadata = {
                'Created': 'Not available',
                'Modified': 'Not available',
                'File Size': 'Not available',
                'Type': 'Not available',
                'Pages': 'Not available',
                'Size Warning': False
            }
            
            # Get basic file info
            size_bytes = len(file_bytes)
            if size_bytes < 1024:
                metadata['File Size'] = f"{size_bytes} B"
            elif size_bytes < 1024 * 1024:
                metadata['File Size'] = f"{size_bytes/1024:.1f} KB"
            else:
                metadata['File Size'] = f"{size_bytes/(1024*1024):.1f} MB"
            
            # Get page count
            metadata['Pages'] = str(len(reader.pages))
            
            # Calculate size warning
            size_per_page = size_bytes / len(reader.pages)
            metadata['Size Warning'] = size_per_page > 1024 * 1024
            
            # Get PDF type
            is_interactive = False
            try:
                root = reader.trailer.get('/Root', {})
                if isinstance(root, PyPDF2.generic.IndirectObject):
                    root = root.get_object()
                
                if '/AcroForm' in root:
                    is_interactive = True
                else:
                    for page in reader.pages:
                        if '/Annots' in page or '/AA' in page or '/OpenAction' in page:
                            is_interactive = True
                            break
            except:
                pass
            
            metadata['Type'] = 'Interactive PDF' if is_interactive else 'Print PDF'
            
            # Try to get dates from document info
            try:
                if '/Info' in reader.trailer:
                    info = reader.trailer['/Info']
                    if isinstance(info, PyPDF2.generic.IndirectObject):
                        info = info.get_object()
                    
                    for date_key, meta_key in [('/CreationDate', 'Created'), ('/ModDate', 'Modified')]:
                        try:
                            if date_key in info:
                                date_value = info[date_key]
                                if isinstance(date_value, PyPDF2.generic.IndirectObject):
                                    date_value = date_value.get_object()
                                date_str = str(date_value)
                                
                                if date_str.startswith('D:'):
                                    try:
                                        year = date_str[2:6]
                                        month = date_str[6:8]
                                        day = date_str[8:10]
                                        metadata[meta_key] = f"{day}/{month}/{year}"
                                    except:
                                        pass
                        except:
                            continue
            except:
                pass

            # Run checks
            results = []
            pdf_results = []

            # Add metadata check results
            metadata_check = check_metadata(reader)
            results.extend(metadata_check)
            pdf_results.extend(metadata_check)
            
            # Add bleed check if in Print mode
            if output_mode == "Print":
                bleed_check = check_bleed(reader)
                results.extend(bleed_check)
                pdf_results.extend(bleed_check)
            
            # Add inch marks check
            inch_marks = check_inch_marks(reader)
            results.extend(inch_marks)
            pdf_results.extend(inch_marks)
            
            # Add resolution check with separate dashboard and PDF results
            dashboard_res, pdf_res = check_resolution(doc)
            results.extend(dashboard_res)
            pdf_results.extend(pdf_res)
            
            # Add PDF validation if in Digital mode
            if output_mode == "Digital":
                # Get validation results
                validation = validate_with_pdfcpu(file_bytes)
                
                # Filter out title check and language check from general validation
                general_validation = [line for line in validation if not any(x in line for x in ["Document Title:", "Document Language:"])]
                title_check = [line for line in validation if "Document Title:" in line]
                language_check = [line for line in validation if "Document Language:" in line]
                
                # Separate general and accessibility checks
                general_checks = []
                accessibility_checks = []
                
                # Add general validation to general checks
                general_checks.extend([line for line in general_validation if "PDF Structure:" not in line])
                
                # Add metadata check to general checks
                metadata_check = check_metadata(reader)
                general_checks.extend(metadata_check)
                
                # Add inch marks check to general checks
                inch_marks = check_inch_marks(reader)
                general_checks.extend(inch_marks)
                
                # Add resolution check to general checks
                dashboard_res, pdf_res = check_resolution(doc)
                general_checks.extend(dashboard_res)
                
                # Add placeholder check to general checks
                placeholder = placeholder_check(doc)
                general_checks.extend(placeholder)
                
                # Build accessibility checks in specific order
                accessibility_checks.extend([line for line in general_validation if "PDF Structure:" in line])
                accessibility_checks.extend(title_check)
                accessibility_checks.extend(language_check)  # Add language check only once
                
                # Add accessibility-specific checks in order
                alt_text_results = check_alt_text(doc)
                accessibility_checks.extend(alt_text_results)
                
                heading_results = check_heading_structure(doc)
                accessibility_checks.extend([line for line in heading_results if not line.startswith("  - ")])
                
                reading_order_results = check_reading_order(doc)
                accessibility_checks.extend(reading_order_results)
                
                color_contrast_results, color_contrast_pdf_results = check_color_contrast(doc)
                accessibility_checks.extend(color_contrast_results)
                
                # Add table accessibility check after heading structure
                table_results, table_pdf_results = check_table_accessibility(doc)
                accessibility_checks.extend(table_results)
                
                # Combine for final results
                results = []
                results.extend(general_checks)
                results.extend(accessibility_checks)
                
                # Build PDF results separately to maintain detail
                pdf_results = []
                pdf_results.extend(metadata_check)
                pdf_results.extend(inch_marks)
                pdf_results.extend(pdf_res)  # Detailed resolution results
                pdf_results.extend(placeholder)
                pdf_results.extend([line for line in general_validation if "PDF Structure:" in line])
                pdf_results.extend(title_check)
                pdf_results.extend(alt_text_results)
                pdf_results.extend(heading_results)  # Full heading results with details
                pdf_results.extend(table_pdf_results)  # Add table results after heading structure
                pdf_results.extend(reading_order_results)
                pdf_results.extend(color_contrast_pdf_results)  # Use PDF-specific results for color contrast
            
            # Calculate statistics using dashboard results
            total_checks = len([line for line in results if line.startswith("✅") or line.startswith("❌")])
            passes = len([line for line in results if line.startswith("✅")])
            fails = total_checks - passes
            pass_percentage = (passes / total_checks * 100) if total_checks > 0 else 0

            # Display statistics with appropriate styling based on mode
            if style_mode == "Sparkle Mode":
                # Play celebration sound if 100% pass
                if pass_percentage == 100:
                    play_sound("celebration.mp3")

                stats_html = f"""
                <div class="stats-container" style="background: rgba(255, 255, 255, 0.1); padding: 1rem; border-radius: 8px; margin-bottom: 1rem;">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: #f8d400;">{total_checks}</div>
                            <div style="font-size: 0.8rem; opacity: 0.8;">TOTAL CHECKS</div>
                        </div>
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: #00d98c;">{passes}</div>
                            <div style="font-size: 0.8rem; opacity: 0.8;">PASSED</div>
                        </div>
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: #ff4b4b;">{fails}</div>
                            <div style="font-size: 0.8rem; opacity: 0.8;">FAILED</div>
                        </div>
                    </div>
                    <div style="background: rgba(255, 255, 255, 0.1); border-radius: 100px; height: 8px; overflow: hidden;">
                        <div style="background: linear-gradient(90deg, #00d98c, #456ef2); height: 100%; width: {pass_percentage}%;"></div>
                    </div>
                </div>
                """
            else:
                stats_html = f"""
                <div class="stats-container" style="background: var(--background-level-one); padding: 1rem; border-radius: 4px; margin-bottom: 1rem; border: 1px solid var(--background-level-two);">
                    <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: var(--text-color);">{total_checks}</div>
                            <div style="font-size: 0.8rem; opacity: 0.7;">TOTAL CHECKS</div>
                        </div>
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: var(--success-color);">{passes}</div>
                            <div style="font-size: 0.8rem; opacity: 0.7;">PASSED</div>
                        </div>
                        <div style="text-align: center; flex: 1;">
                            <div style="font-size: 1.5rem; font-weight: bold; color: var(--error-color);">{fails}</div>
                            <div style="font-size: 0.8rem; opacity: 0.7;">FAILED</div>
                        </div>
                    </div>
                    <div style="background: var(--background-level-two); border-radius: 100px; height: 6px; overflow: hidden;">
                        <div style="background: #2b1e66; height: 100%; width: {pass_percentage}%;"></div>
                    </div>
                </div>
                """

            st.markdown(stats_html, unsafe_allow_html=True)
            st.markdown("### ✅ Scan Complete! Summary of Findings:")

            # Modify the display section to properly separate general and accessibility checks
            if output_mode == "Digital":
                # General Checks
                st.markdown("#### General Checks")
                general_checks = [line for line in results if not any(x in line for x in [
                    "PDF Structure:", "Document Title:", "Document Language:",
                    "Alt Text:", "Heading Structure:", "Reading Order:", "Color Contrast:",
                    "Accessible Tables:"  # Add this to exclude from general checks
                ])]
                for line in general_checks:
                    st.markdown(line)

                # Add visual separator
                st.markdown("---")

                # Accessibility Checks
                st.markdown("#### Accessibility Checks")
                
                # Get all accessibility-related lines (now without heading warnings)
                accessibility_checks = [line for line in results if any(x in line for x in [
                    "PDF Structure:", "Document Title:", "Document Language:",
                    "Alt Text:", "Heading Structure:", "Reading Order:", "Color Contrast:",
                    "Accessible Tables:"  # Add this to include in accessibility checks
                ])]
                
                # Define the desired order of checks
                check_order = [
                    "PDF Structure:",
                    "Document Title:",
                    "Document Language:",
                    "Alt Text:",
                    "Heading Structure:",
                    "Accessible Tables:",
                    "Reading Order:",
                    "Color Contrast:"
                ]
                
                # Sort the checks according to the defined order
                sorted_checks = []
                for check in check_order:
                    matching_checks = [line for line in accessibility_checks if check in line]
                    sorted_checks.extend(matching_checks)
                
                # Display sorted checks
                for line in sorted_checks:
                    st.markdown(line)
            else:
                # For Print mode, show all checks without heading warnings
                for line in results:
                    if not line.startswith("  - "):
                        st.markdown(line)

            # Display download button
            buffer = generate_report(style_mode, pdf_results, metadata)  # Pass metadata to report generator
            report_name = parse_filename_for_report_name(uploaded_file.name)
            
            if style_mode == "Sparkle Mode":
                # Create a container for the download button to capture the click
                download_container = st.container()
                with download_container:
                    if st.download_button("📄 Download PDF Report", buffer, file_name=report_name):
                        play_sound("download.mp3")
            else:
                st.download_button("📄 Download PDF Report", buffer, file_name=report_name)

            # Optional thumbnail preview
            try:
                pix = doc[0].get_pixmap(dpi=60)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                st.markdown("---")
                st.image(img, caption="First Page Preview", width=150)
            except Exception:
                st.warning("Could not render preview.")

            # Markdown tooltip reference
            st.markdown("---")
            with st.expander("📎 Preflight Tip Sheet"):
                # Get all available tips
                all_tips = get_tips()
                
                # Determine which tips to show based on mode
                mode_tips = all_tips["digital"] if output_mode == "Digital" else all_tips["print"]
                
                # Find failed checks in results
                failed_checks = []
                for line in results:
                    if line.startswith("❌"):
                        # Extract the check name from the message
                        check_name = line.split(":")[0].replace("❌", "").strip()
                        failed_checks.append(check_name)
                
                # Show relevant tips for failed checks
                relevant_tips = {k: v for k, v in mode_tips.items() 
                               if any(check in k for check in failed_checks)}
                
                if relevant_tips:
                    st.markdown("### Fix Failed Checks:")
                    for k, v in relevant_tips.items():
                        st.markdown(f"**{k}** – {v}")
                else:
                    st.markdown("✨ All checks passed! No fixes needed.")

            # Development Pipeline section
            st.markdown("---")
            with st.expander("🚀 Development Pipeline"):
                st.markdown("""
                ### Upcoming Features

                #### Language Checks
                Confirms that either the document or all text blocks have a language properly assigned. Ensures screen readers pronounce text correctly and improves accessibility compliance.

                #### Table Summary Checker
                Identifies tables missing summary descriptions. Helps users create screen-reader friendly tables, explaining the table's purpose clearly.

                #### Alt Text Checker
                Verifies that every image has alternative text associated. Critical for accessibility; allows screen readers to describe images properly.

                #### Email Reports
                Sends scan results directly via email as a clean, branded PDF or HTML summary. Makes it easy to share accessibility scans with teams or clients instantly.

                #### Batch Checking
                Allows scanning the entire document at once (instead of page-by-page) for issues like contrast failures and metadata gaps. Provides a faster overview of all accessibility and quality concerns.

                #### File Size Optimizer Warning
                Warns if a file is unusually large or contains heavy, unoptimized images. Helps maintain fast-loading, accessible documents for all users, including those on slower networks.

                #### Reading Order Visual Map
                Creates a simple map of the document's detected reading order (for example: H1 → Paragraph → Image → H2…). Helps users confirm that screen readers will follow a logical flow across complex layouts.
                """)
    except Exception as e:
        st.error(f"An error occurred while processing the PDF: {str(e)}")
    finally:
        if 'doc' in locals():
            doc.close()
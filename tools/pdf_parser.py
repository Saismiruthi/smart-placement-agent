# tools/pdf_parser.py
# Responsible for reading PDF resume files and extracting clean text

from pypdf import PdfReader
from pathlib import Path
from loguru import logger


def extract_text_from_pdf(pdf_path: str) -> str:
    """
    Extract all text from a PDF file.
    
    Args:
        pdf_path: Path to the PDF file (string or Path object)
    
    Returns:
        Clean extracted text as a single string
    """
    pdf_path = Path(pdf_path)
    
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")
    
    if not pdf_path.suffix.lower() == ".pdf":
        raise ValueError(f"File is not a PDF: {pdf_path}")
    
    try:
        reader = PdfReader(str(pdf_path))
        full_text = []
        
        for page_num, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text.append(text)
                logger.debug(f"Extracted page {page_num + 1}: {len(text)} characters")
        
        combined = "\n".join(full_text)
        logger.info(f"PDF parsed successfully: {len(combined)} total characters from {len(reader.pages)} pages")
        return combined
    
    except Exception as e:
        logger.error(f"Failed to parse PDF {pdf_path}: {e}")
        raise


def extract_text_from_uploaded_file(uploaded_file) -> str:
    """
    Extract text from a Streamlit UploadedFile object directly.
    Used when file comes from st.file_uploader().
    
    Args:
        uploaded_file: Streamlit UploadedFile object
    
    Returns:
        Extracted text string
    """
    try:
        reader = PdfReader(uploaded_file)
        full_text = []
        
        for page in reader.pages:
            text = page.extract_text()
            if text:
                full_text.append(text)
        
        combined = "\n".join(full_text)
        logger.info(f"Uploaded PDF parsed: {len(combined)} characters")
        return combined
    
    except Exception as e:
        logger.error(f"Failed to parse uploaded file: {e}")
        raise
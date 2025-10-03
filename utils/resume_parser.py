from io import BytesIO
from typing import BinaryIO

from PyPDF2 import PdfReader
from pdfminer.high_level import extract_text as pdfminer_extract_text
from docx import Document


def parse_pdf(file_bytes: bytes) -> str:
    try:
        # Fast path with PyPDF2
        pdf_reader = PdfReader(BytesIO(file_bytes))
        text = []
        for page in pdf_reader.pages:
            text.append(page.extract_text() or "")
        out = "\n".join(text).strip()
        if out:
            return out
    except Exception:
        pass
    # Fallback to pdfminer
    try:
        return pdfminer_extract_text(BytesIO(file_bytes)) or ""
    except Exception:
        return ""


def parse_docx(file_bytes: bytes) -> str:
    try:
        bio = BytesIO(file_bytes)
        doc = Document(bio)
        return "\n".join(p.text for p in doc.paragraphs)
    except Exception:
        return ""


def parse_resume_file(uploaded_file) -> str:
    data = uploaded_file.read()
    name = uploaded_file.name.lower()
    if name.endswith(".pdf"):
        return parse_pdf(data)
    if name.endswith(".docx"):
        return parse_docx(data)
    return ""

"""
PDF 텍스트 추출 공통 모듈 (pdf_processor.py, src/chunking.py에서 사용)

PyMuPDF는 AGPL-3.0이라 .cursor/oss-policy.md(SaaS)에 따라 제거했습니다.
pdfplumber(MIT)로 추출하고, 텍스트가 없으면 pypdf(BSD-3-Clause)로 재시도합니다.
"""
import logging
import re

import pdfplumber
from pypdf import PdfReader

logger = logging.getLogger(__name__)

PAGE_MARKER = "\n--- Page {} ---\n"
PAGE_MARKER_RE = re.compile(r"--- Page \d+ ---")


def has_text(text: str) -> bool:
    """페이지 마커를 제외한 실제 텍스트가 있는지"""
    return bool(PAGE_MARKER_RE.sub("", text).strip())


def extract_with_pdfplumber(pdf_path: str) -> str:
    """페이지마다 마커를 붙여 pdfplumber로 추출"""
    with pdfplumber.open(pdf_path) as pdf:
        return "".join(PAGE_MARKER.format(i + 1) + (page.extract_text() or "")
                       for i, page in enumerate(pdf.pages))


def extract_with_pypdf(pdf_path: str) -> str:
    """페이지마다 마커를 붙여 pypdf로 추출"""
    return "".join(PAGE_MARKER.format(i + 1) + (page.extract_text() or "")
                   for i, page in enumerate(PdfReader(pdf_path).pages))


def extract_pdf_text(pdf_path: str) -> str:
    """pdfplumber로 추출하고, 텍스트가 없으면 pypdf로 재시도"""
    text = extract_with_pdfplumber(pdf_path)
    if not has_text(text):
        logger.info("pdfplumber returned no text, retrying with pypdf: %s", pdf_path)
        text = extract_with_pypdf(pdf_path)
    return text

"""Tests for metadata extraction helpers."""

from app.services.metadata_extractor import extract_metadata


def test_extract_pdf_minimal():
    from io import BytesIO

    from pypdf import PdfWriter

    w = PdfWriter()
    w.add_blank_page(width=100, height=100)
    buf = BytesIO()
    w.write(buf)
    content = buf.getvalue()
    meta = extract_metadata(
        content=content,
        original_name="t.pdf",
        declared_content_type="application/pdf",
    )
    assert meta["extension"] == ".pdf"
    assert meta["page_count"] >= 1
    assert len(meta["sha256"]) == 64

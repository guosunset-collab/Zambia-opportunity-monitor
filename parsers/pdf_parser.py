from pathlib import Path


def parse_pdf(path: str) -> str:
    pdf_path = Path(path)
    if not pdf_path.exists():
        return ""

    try:
        import pdfplumber

        parts = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                parts.append(page.extract_text() or "")
        return "\n".join(parts).strip()
    except Exception:
        pass

    try:
        import fitz

        parts = []
        with fitz.open(str(pdf_path)) as doc:
            for page in doc:
                parts.append(page.get_text())
        return "\n".join(parts).strip()
    except Exception:
        return ""

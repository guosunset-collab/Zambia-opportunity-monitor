from pathlib import Path


def ocr_image(path: str) -> str:
    image_path = Path(path)
    if not image_path.exists():
        return ""

    try:
        from PIL import Image
        import pytesseract

        return pytesseract.image_to_string(Image.open(str(image_path))).strip()
    except Exception:
        # TODO: Add cloud OCR or another local fallback for scanned notices when available.
        return ""

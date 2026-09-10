# src/ingestion/detect_scan.py
import fitz  # PyMuPDF


def is_scanned(pdf_path, char_threshold=50):
    """
    Detects whether a PDF is scanned (image-based) or native (selectable text).
    Tests page by page: if most pages contain very little extractable text,
    the document is considered scanned.
    """
    doc = fitz.open(pdf_path)
    total_pages = len(doc)
    empty_pages = 0

    for page in doc:
        text = page.get_text().strip()
        if len(text) < char_threshold:
            empty_pages += 1

    doc.close()

    empty_ratio = empty_pages / total_pages if total_pages > 0 else 1
    return empty_ratio > 0.5


if __name__ == "__main__":
    test_path = "data/raw/my_decree.pdf"  # adjust filename
    result = is_scanned(test_path)
    print(f"Scanned document: {result}")
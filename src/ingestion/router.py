# src/ingestion/router.py
from src.ingestion.detect_scan import is_scanned
from src.ingestion.extract_text import extract_text_from_pdf
from src.ingestion.ocr import ocr_pdf


def process_document(pdf_path, output_path):
    """
    Single entry point for ingestion: automatically detects whether
    the PDF is scanned or native, and applies the right processing.
    """
    if is_scanned(pdf_path):
        print(f"[{pdf_path}] detected as SCANNED -> OCR")
        ocr_pdf(pdf_path, output_path)
    else:
        print(f"[{pdf_path}] detected as NATIVE -> direct extraction")
        extract_text_from_pdf(pdf_path, output_path)


if __name__ == "__main__":
    pdf_source = "data/raw/Decret_marches_publics_n_2_22_431_du_09_03_2023_Fr.pdf"  # adjust filename
    output_file = "data/processed/Decret_marches_publics_n_2_22_431_du_09_03_2023_Fr.txt"

    process_document(pdf_source, output_file)
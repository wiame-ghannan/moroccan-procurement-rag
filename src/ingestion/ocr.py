# src/ingestion/ocr.py
import os

import numpy as np
import pytesseract
from pdf2image import convert_from_path

# Overridable via TESSERACT_PATH / POPPLER_PATH env vars (see .env.example).
# The defaults below only match the original dev machine's Windows install.
TESSERACT_PATH = os.getenv("TESSERACT_PATH", r"C:\Program Files\Tesseract-OCR\tesseract.exe")
POPPLER_PATH = os.getenv("POPPLER_PATH", r"C:\poppler\poppler-26.02.0\Library\bin")


def _check_ocr_dependencies():
    """
    Verifies Tesseract and Poppler are reachable before attempting OCR, so a
    missing install fails with a clear, actionable message instead of a
    cryptic error deep inside pytesseract/pdf2image.
    """
    missing = []
    if not os.path.isfile(TESSERACT_PATH):
        missing.append(f"Tesseract introuvable à TESSERACT_PATH={TESSERACT_PATH!r}")
    if not os.path.isdir(POPPLER_PATH):
        missing.append(f"Poppler introuvable à POPPLER_PATH={POPPLER_PATH!r}")

    if missing:
        raise RuntimeError(
            "OCR indisponible :\n  - " + "\n  - ".join(missing) +
            "\n\nCes chemins sont spécifiques à une installation locale de "
            "Tesseract/Poppler. Configure-les via des variables "
            "d'environnement (dans un fichier .env à la racine du projet, "
            "voir .env.example) :\n"
            "  TESSERACT_PATH=<chemin complet vers tesseract(.exe)>\n"
            "  POPPLER_PATH=<chemin vers le dossier bin de Poppler>"
        )

    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


def detect_columns(page_image, white_threshold=0.98):
    """
    Automatically detects whether an image page has 1 or 2 columns,
    and returns the split position if so, otherwise None.
    """
    gray_image = page_image.convert("L")
    image_array = np.array(gray_image)

    intensity_threshold = 200
    text_mask = image_array < intensity_threshold
    projection = text_mask.sum(axis=0)

    width = image_array.shape[1]
    height = image_array.shape[0]

    central_zone = projection[int(width * 0.35):int(width * 0.65)]
    min_relative_index = np.argmin(central_zone)
    min_value = central_zone[min_relative_index]

    if min_value < height * (1 - white_threshold):
        return int(width * 0.35) + min_relative_index

    return None


def ocr_page(page_image, language="fra"):
    """
    Performs OCR on a page, automatically handling 1 or 2 columns.
    """
    split_position = detect_columns(page_image)

    if split_position is None:
        return pytesseract.image_to_string(page_image, lang=language, config="--psm 3")

    width, height = page_image.size
    left_column = page_image.crop((0, 0, split_position, height))
    right_column = page_image.crop((split_position, 0, width, height))

    left_text = pytesseract.image_to_string(left_column, lang=language, config="--psm 6")
    right_text = pytesseract.image_to_string(right_column, lang=language, config="--psm 6")

    return left_text + "\n" + right_text


def ocr_pdf(pdf_path, output_path, language="fra"):
    """
    Performs OCR on a full scanned PDF, page by page, and saves the result.
    """
    _check_ocr_dependencies()

    print("Converting PDF to images...")
    pages = convert_from_path(pdf_path, dpi=300, poppler_path=POPPLER_PATH)
    total_pages = len(pages)
    print(f"{total_pages} pages to process")

    with open(output_path, "w", encoding="utf-8") as f:
        for i, page in enumerate(pages):
            text = ocr_page(page, language)
            f.write(f"\n--- PAGE {i + 1} ---\n")
            f.write(text)
            print(f"OCR: page {i + 1}/{total_pages}")

    print(f"OCR complete -> {output_path}")


if __name__ == "__main__":
    pdf_source = "data/raw/my_scanned_decree.pdf"  # adjust filename
    output_file = "data/processed/my_scanned_decree_text.txt"

    ocr_pdf(pdf_source, output_file)
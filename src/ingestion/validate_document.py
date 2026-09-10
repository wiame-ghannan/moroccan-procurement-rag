# src/ingestion/validate_document.py
import re
import fitz


def check_document_integrity(pdf_path, expected_document_number):
    """
    Scans a PDF for signs that it might contain more than one distinct
    legal text bundled together, which would corrupt citation accuracy.
    Returns a list of warnings (empty if the document looks clean).
    """
    doc = fitz.open(pdf_path)
    warnings = []

    bo_numbers_found = set()
    real_decree_titles = []

    for page in doc:
        text = page.get_text()

        for m in re.finditer(r"N[°º]\s*(\d{4})\s*[–-]", text):
            bo_numbers_found.add(m.group(1))

        for m in re.finditer(
            r"(?<!Vu le )(?<!Vu l')(Décret|Arrêté|Dahir)\s+n[°º]\s*([\d\-]+)\s+du[^.;]{0,80}?"
            r"(relatif|fixant|approuvant|portant)",
            text
        ):
            real_decree_titles.append(m.group(2))

    doc.close()

    if len(bo_numbers_found) > 1:
        warnings.append(
            f"Plusieurs numéros de Bulletin Officiel détectés : {bo_numbers_found}. "
            f"Le fichier contient peut-être des pages de plusieurs éditions du BO."
        )

    distinct_titles = set(real_decree_titles)
    unexpected_titles = distinct_titles - {expected_document_number}
    if unexpected_titles:
        warnings.append(
            f"D'autres numéros de texte que celui attendu ({expected_document_number}) "
            f"apparaissent comme titre principal : {unexpected_titles}."
        )

    return warnings


def validate_all_documents():
    from src.documents_registry import DOCUMENTS

    print("Validation de l'intégrité des documents du corpus...\n")
    all_clean = True

    for doc in DOCUMENTS:
        pdf_path = f"data/raw/{doc.get('category', '')}/{doc['pdf_filename']}"
        warnings = check_document_integrity(pdf_path, doc["document_number"])

        if warnings:
            all_clean = False
            print(f"⚠️  {doc['document_name']} ({pdf_path})")
            for w in warnings:
                print(f"    - {w}")
        else:
            print(f"✅ {doc['document_name']}")

    print()
    if all_clean:
        print("Tous les documents sont propres.")
    else:
        print("Des documents nécessitent une vérification manuelle.")


if __name__ == "__main__":
    validate_all_documents()
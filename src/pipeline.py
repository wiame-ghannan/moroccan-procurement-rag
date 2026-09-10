# src/pipeline.py
import os
import json
from src.ingestion.router import process_document
from src.ingestion.validate_document import check_document_integrity
from src.parsing.legal_parser import parse_legal_text, find_missing_articles
from src.documents_registry import DOCUMENTS


def run_full_pipeline(doc_config, force=False, skip_validation=False):
    category = doc_config["category"]
    pdf_path = f"data/raw/{category}/{doc_config['pdf_filename']}"
    base_name = os.path.splitext(doc_config['pdf_filename'])[0]
    processed_dir = f"data/processed/{category}"
    text_output_path = f"{processed_dir}/{base_name}_text.txt"
    json_output_path = f"{processed_dir}/{base_name}_structure.json"

    print(f"=== Processing: {doc_config['document_name']} ===")

    if not force and os.path.exists(json_output_path):
        print(f"  SKIPPED - already processed ({json_output_path})")
        return None

    if not os.path.exists(pdf_path):
        print(f"  SKIPPED - PDF not found at {pdf_path}")
        return None

    if not skip_validation:
        warnings = check_document_integrity(pdf_path, doc_config["document_number"])
        if warnings:
            print(f"  REJECTED - integrity check failed for {pdf_path}:")
            for w in warnings:
                print(f"    - {w}")
            return None

    print("  NEW - processing for the first time")
    os.makedirs(processed_dir, exist_ok=True)
    process_document(pdf_path, text_output_path)

    with open(text_output_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    results = parse_legal_text(
        raw_text,
        document_name=doc_config["document_name"],
        document_type=doc_config["document_type"],
        document_number=doc_config["document_number"],
    )

    with open(json_output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    missing = find_missing_articles(results, expected_max=doc_config["expected_max_articles"])
    print(f"  {len(results)} articles extracted -> {json_output_path}")
    if missing:
        print(f"  WARNING - missing: {missing}")
    else:
        print(f"  All {doc_config['expected_max_articles']} articles detected.")

    return results


if __name__ == "__main__":
    for doc_config in DOCUMENTS:
        run_full_pipeline(doc_config, force=False)
        print()
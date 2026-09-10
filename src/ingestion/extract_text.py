# src/ingestion/extract_text.py
import pdfplumber


def fix_mojibake(text):
    """
    Repairs UTF-8 text that was incorrectly decoded as Latin-1/Windows-1252
    (classic mojibake: 'é' becomes 'Ã©'). Safe no-op if text is already correct.
    """
    try:
        return text.encode("latin1").decode("utf-8")
    except (UnicodeDecodeError, UnicodeEncodeError):
        return text


def assemble_words(words):
    if not words:
        return ""

    sorted_words = sorted(words, key=lambda w: (round(w["top"]), w["x0"]))

    lines = []
    current_line = []
    current_top = None
    line_tolerance = 3

    for w in sorted_words:
        top = w["top"]
        if current_top is None or abs(top - current_top) <= line_tolerance:
            current_line.append(w)
            current_top = top if current_top is None else current_top
        else:
            lines.append(current_line)
            current_line = [w]
            current_top = top
    if current_line:
        lines.append(current_line)

    line_texts = []
    for line in lines:
        line_sorted = sorted(line, key=lambda w: w["x0"])
        raw_line = " ".join(w["text"] for w in line_sorted)
        line_texts.append(fix_mojibake(raw_line))

    return "\n".join(line_texts)


def detect_column_gap(words, page_width):
    """
    Detects the vertical whitespace separating two text columns.

    Scans a central vertical band and, for each candidate x, counts how many
    words are *crossed* by that x (i.e. x0 < x < x1). The column gap is the x
    that cuts through the fewest words. If that valley is much emptier than the
    surrounding text columns, the page is two-column and the split x is
    returned; otherwise the page is treated as single-column (None).

    Unlike a strict "empty column" test, minimising crossings stays robust to
    full-width headers, footers and page numbers that would otherwise make the
    gap never reach zero coverage.
    """
    if len(words) < 20:
        return None

    band_start = int(page_width * 0.42)
    band_end = int(page_width * 0.58)
    if band_end <= band_start:
        return None

    profile = [
        (x, sum(1 for w in words if w["x0"] < x < w["x1"]))
        for x in range(band_start, band_end)
    ]
    split_x, min_crossings = min(profile, key=lambda t: t[1])
    max_crossings = max(c for _, c in profile)

    # A genuine gap: columns are dense (high max) but the valley is near-empty.
    if max_crossings >= 8 and min_crossings < 0.25 * max_crossings:
        return split_x
    return None


def extract_page_native(page):
    words = page.extract_words()
    if not words:
        return ""
    split_x = detect_column_gap(words, page.width)
    if split_x is None:
        return assemble_words(words)
    # Assign each word by its horizontal centre so justified words whose left
    # edge sits just across the gap still land in the correct column.
    left_column = [w for w in words if (w["x0"] + w["x1"]) / 2 < split_x]
    right_column = [w for w in words if (w["x0"] + w["x1"]) / 2 >= split_x]
    return assemble_words(left_column) + "\n" + assemble_words(right_column)


def extract_text_from_pdf(pdf_path, output_path):
    with pdfplumber.open(pdf_path) as pdf:
        total_pages = len(pdf.pages)
        print(f"Document opened: {total_pages} pages")
        with open(output_path, "w", encoding="utf-8") as f:
            for i, page in enumerate(pdf.pages):
                text = extract_page_native(page)
                f.write(f"\n--- PAGE {i + 1} ---\n")
                f.write(text)
                if (i + 1) % 10 == 0 or (i + 1) == total_pages:
                    print(f"Processing: page {i + 1}/{total_pages}")
    print(f"Extraction complete -> {output_path}")


if __name__ == "__main__":
    pdf_source = "data/raw/Decret_marches_publics_n_2_22_431_du_09_03_2023_Fr.pdf"
    output_file = "data/processed/Decret_marches_publics_n_2_22_431_du_09_03_2023_Fr.txt"

    extract_text_from_pdf(pdf_source, output_file)
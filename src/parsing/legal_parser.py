# src/parsing/legal_parser.py
import re
import json
import hashlib

def clean_text(raw_text):
    """Removes common OCR/extraction noise before structural parsing."""
    lines = raw_text.split("\n")
    clean_lines = []
    for line in lines:
        l = line.strip()
        if l.startswith("--- PAGE"):
            continue
        if re.match(r"^N[o°º]\s*\d+.*BULLETIN", l, re.IGNORECASE):
            continue
        if re.match(r"^\d+\s+BULLETIN\s*(OFFICIEL)?", l, re.IGNORECASE):
            continue
        if re.match(r"^BULLETIN\s+OFFICIEL", l, re.IGNORECASE):
            continue
        if re.match(r"^OFFICIEL\s*\d*$", l, re.IGNORECASE):
            continue
        if len(l) < 60 and re.match(r"^[\sEeSsUuRr\-—=•.]{5,}$", l):
            continue
        clean_lines.append(line)
    return "\n".join(clean_lines)


def strip_marginal_article_notes(text):
    """
    Removes duplicate 'ART. N. - Title' references that appear mid-line
    (marginal running notes), keeping only real headings that start a line.
    """
    pattern = re.compile(r"\bART\.?\s*(premier|\d+)\.?\s*[–—-]\s*[A-ZÀ-Üa-zà-ü][^\n]{0,80}")
    lines = text.split("\n")
    cleaned_lines = []

    for line in lines:
        matches = list(pattern.finditer(line))
        if not matches:
            cleaned_lines.append(line)
            continue

        first_match = matches[0]
        if first_match.start() <= 5:
            cleaned_lines.append(line)
        else:
            new_line = line
            for m in reversed(matches):
                new_line = new_line[:m.start()] + new_line[m.end():]
            cleaned_lines.append(new_line.strip())

    return "\n".join(cleaned_lines)


def cut_before_decree_body(text):
    """
    Removes the table of contents (Sommaire) that precedes the actual
    decree text. The real body always starts after 'DECRETE' / 'DÉCRÈTE'.
    """
    match = re.search(r"D[ÉE]CR[ÈE]TE\s*:", text, re.IGNORECASE)
    if match:
        return text[match.end():]
    return text


def normalize_roman(raw_roman):
    return raw_roman.replace("T", "I")


def clean_title_capture(raw_text):
    """
    Truncates a captured title at the first sign of unrelated content:
    a paragraph marker like '5 –' or '1 -' that signals body text leaking in.
    """
    match = re.search(r"\s\d{1,3}\s*[–—-]\s", raw_text)
    if match:
        raw_text = raw_text[:match.start()]
    return raw_text.strip(" .;,'’—–-")


def extract_chapter_title(candidate_text):
    """
    Chapter titles appear as a plain line directly below the 'Chapitre X'
    heading (e.g. 'Dispositions générales') — normal title case, not
    all-caps — so we just take the line itself, guarding against picking up
    the next structural heading if the title line was blank/missing.
    """
    line = candidate_text.strip()
    if not line or re.match(r"^(art(?:icle)?\.?|section)\b", line, re.IGNORECASE):
        return ""
    return line.strip(" .;,'’")
def cut_before_document_body(text):
    """
    Removes any table of contents (Sommaire) that precedes the real body.
    Strategy: if 'Chapitre premier' (or its uppercase variant) appears more
    than once, the text before its LAST occurrence is treated as front
    matter (cover page, sommaire) and discarded. Falls back to the
    'DÉCRÈTE :' marker for decree-style documents if no duplicate chapter
    marker is found.
    """
    chapter_one_matches = list(re.finditer(r"chapitre\s+premier", text, re.IGNORECASE))
    if len(chapter_one_matches) > 1:
        return text[chapter_one_matches[-1].start():]

    decree_match = re.search(r"D[ÉE]CR[ÈE]TE\s*:", text, re.IGNORECASE)
    if decree_match:
        return text[decree_match.end():]

    return text


def looks_like_title_continuation(line):
    """
    True if `line` reads as the wrapped second line of a heading title rather
    than the start of the article's body text. Titles wrap onto a following
    line mid-phrase (lowercase continuation, no closing punctuation); real
    body text starts a new sentence (uppercase) or an enumeration (digit/dash).
    """
    if not line or len(line) >= 80:
        return False
    if line[-1] in ".;:!?":
        return False
    return line[0].islower()

def make_article_id(document_number, chapter, article):
    """Generates a short, stable unique identifier for each article chunk."""
    raw = f"{document_number}_{chapter}_{article}"
    return hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]


FRENCH_MONTHS = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4,
    "mai": 5, "juin": 6, "juillet": 7, "août": 8, "aout": 8,
    "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12,
}


def extract_signature_date(text):
    """
    Extracts the Gregorian signature date from the decree/arrêté heading,
    e.g. "... du 15 chaabane 1444 (8 mars 2023)" -> "2023-03-08".
    Only the first lines of the header are searched, since a later table of
    contents can repeat (and truncate) the same heading further down.
    """
    header = "\n".join(text.split("\n")[:20])
    month_names = "|".join(FRENCH_MONTHS.keys())
    pattern = re.compile(
        rf"\(\s*(\d{{1,2}})\s+({month_names})\s+(\d{{4}})\s*\)",
        re.IGNORECASE
    )
    match = pattern.search(header)
    if not match:
        return None

    day, month_name, year = match.groups()
    month = FRENCH_MONTHS.get(month_name.lower())
    if not month:
        return None
    return f"{int(year):04d}-{month:02d}-{int(day):02d}"


def parse_legal_text(raw_text, document_name="document", document_type="Document", document_number=""):
    text = clean_text(raw_text)
    text = strip_marginal_article_notes(text)
    signature_date = extract_signature_date(text)
    text = cut_before_document_body(text)

    chapter_pattern = re.compile(
        r"Chapitre\s+(premier|[IVXLCDMT]+)\s*([A-ZÀ-Ü][^\n]{0,80})?", re.MULTILINE
    )

    section_pattern = re.compile(
        r"Section\s+(premi[eè]re|[IVXLCDM]+)\.?\s*[–—-]?\s*([^\n]{0,100})", re.MULTILINE
    )

    article_pattern = re.compile(
        r"^\s*[^\w\n]{0,5}(?:Art(?:icle)?|ART)\.?\s+(premier|\d+)\.?\s*[–—-]?\s*(.*)$",
        re.MULTILINE | re.IGNORECASE
    )

    chapter_positions = []
    for m in chapter_pattern.finditer(text):
        title = extract_chapter_title(m.group(2) or "")
        chapter_positions.append((m.start(), normalize_roman(m.group(1)), title, "chapter"))

    section_positions = []
    for m in section_pattern.finditer(text):
        clean_section = clean_title_capture(m.group(2).strip(" –—-"))
        section_positions.append((m.start(), m.group(1), clean_section, "section"))

    article_positions = [
        (m.start(), m.group(1), clean_title_capture(m.group(2).strip()), "article")
        for m in article_pattern.finditer(text)
    ]

    all_positions = sorted(
        chapter_positions + section_positions + article_positions,
        key=lambda x: x[0]
    )

    results = []
    current_chapter = None
    current_chapter_title = ""
    current_section = None

    for i, (pos, number, inline_rest, block_type) in enumerate(all_positions):
        if block_type == "chapter":
            current_chapter = f"Chapitre {number}"
            current_section = None

            if inline_rest:
                current_chapter_title = inline_rest
            else:
                end = all_positions[i + 1][0] if i + 1 < len(all_positions) else len(text)
                block_lines = [l.strip() for l in text[pos:end].split("\n") if l.strip()]
                title = ""
                for line in block_lines[1:4]:
                    title = extract_chapter_title(line)
                    if title:
                        break
                current_chapter_title = title
            continue

        if block_type == "section":
            current_section = f"Section {number}" + (f" — {inline_rest}" if inline_rest else "")
            continue

        end = all_positions[i + 1][0] if i + 1 < len(all_positions) else len(text)
        block_text = text[pos:end].strip()
        block_lines = [l.strip() for l in block_text.split("\n") if l.strip()]

        article_title = inline_rest
        body_lines = block_lines[1:]
        if not article_title and body_lines and len(body_lines[0]) < 80 and not body_lines[0].endswith("."):
            article_title = body_lines[0]
            body_lines = body_lines[1:]

        while body_lines and looks_like_title_continuation(body_lines[0]):
            article_title = f"{article_title} {body_lines[0]}".strip()
            body_lines = body_lines[1:]

        num = "premier" if number.lower() == "premier" else number
        article_label = f"Article {num}"

        source = f"{document_type} n° {document_number}" if document_number else document_name

        results.append({
            "document": document_name,
            "document_type": document_type,
            "document_number": document_number,
            "source": source,
            "signature_date": signature_date,
            "unit_type": "article",
            "article_id": make_article_id(document_number, current_chapter, article_label),
            "chapter": current_chapter,
            "chapter_title": current_chapter_title,
            "section": current_section,
            "article": article_label,
            "article_title": article_title,
            "text": " ".join(body_lines).strip()
        })

    return results


def find_missing_articles(results, expected_max):
    found_numbers = set()
    for r in results:
        num_str = r["article"].replace("Article ", "")
        if num_str == "premier":
            found_numbers.add(1)
        elif num_str.isdigit():
            found_numbers.add(int(num_str))
    expected = set(range(1, expected_max + 1))
    return sorted(expected - found_numbers)


if __name__ == "__main__":
    input_path = "data/processed/Decret_marches_publics_n_2_22_431_du_09_03_2023_Fr.txt"
    output_path = "data/processed/Decret_marches_publics_n_2_22_431_du_09_03_2023_Fr.json"

    with open(input_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    results = parse_legal_text(
        raw_text,
        document_name="Décret relatif aux marchés publics",
        document_type="Décret",
        document_number="2-22-431"
    )

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    missing = find_missing_articles(results, expected_max=170)
    chapters_summary = []
    seen = set()
    for r in results:
        key = (r["chapter"], r["section"])
        if key not in seen:
            seen.add(key)
            chapters_summary.append(f'{r["chapter"]} / {r["section"]}: {r["chapter_title"]}')

    print(f"{len(results)} articles extracted -> {output_path}")
    print("Structure found:")
    for c in chapters_summary:
        print(f"  - {c}")
    if missing:
        print(f"WARNING - missing article numbers (out of 170): {missing}")
    else:
        print("All articles from 1 to 170 were detected.")
#!/usr/bin/env python3
import argparse, json, re, unicodedata, sys
try:
    import fitz  # PyMuPDF
except ImportError as e:
    print(json.dumps({"error": "PyMuPDF (fitz) is not installed. Run: pip install pymupdf"}))
    sys.exit(1)

def normalize(s: str, loosen: bool=False) -> str:
    if s is None: return ""
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"\s+", " ", s).strip()
    if loosen:
        s = s.replace("\u00AD", "").replace("\u200b","").replace("\ufeff","")
    return s

def find_span(page_text: str, query: str, loosen: bool=False):
    base = normalize(page_text, loosen)
    q = normalize(query, loosen)
    start = base.find(q)
    end = start + len(q) if start >= 0 else -1
    return start, end, q, base

def main():
    ap = argparse.ArgumentParser(description="Find (position_start, position_end) for selected text on a PDF page.")
    ap.add_argument("pdf_path", help="Path to PDF file")
    ap.add_argument("page_number", type=int, help="1-based page number")
    ap.add_argument("selected_text", help="The exact text you selected (paste it in quotes)")
    ap.add_argument("--loose", action="store_true", help="Looser matching (ignores zero-width chars & collapses whitespace)")
    args = ap.parse_args()

    doc = fitz.open(args.pdf_path)
    if args.page_number < 1 or args.page_number > len(doc):
        print(json.dumps({"error": f"page_number out of range (1..{len(doc)})"}))
        sys.exit(1)

    page = doc[args.page_number - 1]
    page_text = page.get_text()
    start, end, norm_q, norm_text = find_span(page_text, args.selected_text, args.loose)

    out = {
        "pdf": args.pdf_path,
        "page_number": args.page_number,
        "selected_text": args.selected_text,
        "position_start": start,
        "position_end": end,
        "length": len(norm_q),
        "note": "If position_start is -1, try adding --loose or adjust the selected_text."
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
    # Example usage:
        #python offset_from_pdf.py "C:\Book\CS 201 - Tin Hoc Ung Dung - 2020F - Lectures Slides - 8 - 1.pdf" 5 "Truy vấn là một công cụ mạnh của Access dùng để: Tổng hợp, sắp xếp và tìm kiếm dữ liệu" 
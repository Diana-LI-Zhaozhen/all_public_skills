#!/usr/bin/env python3
"""
OCR-based text extraction for problematic financial PDFs with Identity-H font encoding.

Works when standard extraction tools (pymupdf, pdfplumber) fail to extract numbers
from Chinese financial PDFs that use CJK fonts without ToUnicode mapping.

Requires:
    sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng
    pip install pytesseract Pillow pymupdf

Usage:
    python3 scripts/ocr_problematic_pdf.py <input.pdf> [output.txt] [--dpi 300] [--pages 50-55]
"""

import argparse
import re
import sys
from pathlib import Path


def extract_via_ocr(pdf_path: str, output_path: str, dpi: int = 300, page_range: str = None) -> str:
    """
    Extract text from a problematic PDF by rendering pages to images and OCR-ing them.
    
    Args:
        pdf_path: Path to the input PDF
        output_path: Path to save extracted text
        dpi: Resolution for page rendering (higher = better OCR, slower)
        page_range: Optional page range like "50-55" or "1,3,5"
    
    Returns:
        str: Extracted text content
    """
    import fitz
    import pytesseract
    from PIL import Image
    import io

    doc = fitz.open(pdf_path)
    total_pages = doc.page_count
    
    # Parse page range
    pages = list(range(total_pages))
    if page_range:
        pages = []
        for part in page_range.split(","):
            if "-" in part:
                start, end = part.split("-")
                pages.extend(range(int(start) - 1, int(end)))
            else:
                pages.append(int(part) - 1)
        pages = [p for p in pages if 0 <= p < total_pages]
    
    print(f"Processing {len(pages)} pages from {pdf_path} at {dpi} DPI...")
    
    full_text = []
    for i, page_num in enumerate(pages):
        page = doc[page_num]
        pix = page.get_pixmap(dpi=dpi)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        full_text.append(f"--- Page {page_num + 1} ---\n{text}")
        
        if (i + 1) % 10 == 0:
            print(f"  Processed {i + 1}/{len(pages)} pages...")
    
    doc.close()
    
    result = "\n\n".join(full_text)
    Path(output_path).write_text(result, encoding="utf-8")
    
    # Stats
    char_count = len(result)
    number_count = len(re.findall(r'\d+', result))
    print(f"Done. {len(pages)} pages processed: {char_count} chars, {number_count} numbers found.")
    print(f"Output: {output_path}")
    
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="OCR-based extraction for PDFs with Identity-H font encoding issues"
    )
    parser.add_argument("input_pdf", help="Path to the problematic PDF")
    parser.add_argument("output_txt", nargs="?", default=None, help="Output text file path")
    parser.add_argument("--dpi", type=int, default=300, help="Rendering DPI (default: 300)")
    parser.add_argument(
        "--pages",
        default=None,
        help="Page range: '50-55' or '1,3,5-10' (default: all pages)",
    )
    args = parser.parse_args()
    
    input_path = Path(args.input_pdf)
    if not input_path.exists():
        print(f"Error: File not found: {input_path}")
        sys.exit(1)
    
    output_path = args.output_txt or str(input_path.with_suffix(".ocr.txt"))
    
    extract_via_ocr(
        pdf_path=str(input_path),
        output_path=output_path,
        dpi=args.dpi,
        page_range=args.pages,
    )


if __name__ == "__main__":
    main()

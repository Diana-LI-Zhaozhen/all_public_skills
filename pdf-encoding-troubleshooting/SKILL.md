---
name: pdf-encoding-troubleshooting
description: Tools and workflows for extracting text from problematic financial PDFs — Identity-H CID font encoding (Chinese financial reports) and SEC EDGAR 40-F cover-only filings (Canadian issuers). Includes OCR fallback and exhibit discovery patterns.
---

# PDF Encoding & SEC Filing Troubleshooting

## Problem 1: Identity-H CID Font Encoding (Chinese Financial PDFs)

**Symptoms:**
- Chinese characters extracted but numbers are missing
- Font encoding shows `Identity-H` or `Identity-V`
- Zero `ToUnicode` CMap entries in the PDF
- Affected tools: pymupdf, pdfplumber, pypdf, pdfminer — all fail

**Root Cause:**
The PDF uses ONLY CJK fonts (e.g., MHeiPRC) with Identity-H CMap and NO ToUnicode mapping. Numbers (0-9) are stored as CID glyph indices that cannot be mapped to Unicode. This is a PDF generation quality issue.

Example inspection commands:
```bash
python3 -c "
import fitz
doc = fitz.open('problem.pdf')
page = doc[0]
fonts = page.get_fonts()
for f in fonts:
    print(f'Font: {f[3]}, Enc: {f[4]}')
doc.close()
"
```

**Confirmed triggers:** 
- Chinese annual reports created by certain iText/第三方PDF生成器 versions (PICC 2025 annual is a case)
- Fonts like `MHeiPRC`, `MSungPRC` with `Identity-H` encoding
- NO Latin font (e.g., Frutiger, Arial) embedded alongside CJK fonts

### Solution A: OCR with Tesseract (Recommended)

**Requirements:** tesseract + Chinese language pack
```bash
sudo apt-get install -y tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract Pillow
```

**Script:**
```python
import fitz
import pytesseract
from PIL import Image
import io

doc = fitz.open("problem.pdf")
text = ""
for page_num in range(doc.page_count):
    # Render page to image at 300 DPI
    pix = doc[page_num].get_pixmap(dpi=300)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    # OCR with Chinese simplified
    page_text = pytesseract.image_to_string(img, lang="chi_sim+eng")
    text += page_text + "\n"
doc.close()
```

**For batch processing:**
```bash
python3 scripts/ocr_problematic_pdf.py <input.pdf> <output.txt>
```

### Solution B: Use 2025 Semi-Annual Report as Proxy

If the annual report has encoding issues but the semi-annual report works:
- Extract full text from semi-annual (which has Latin fonts)
- Extract partial text (Chinese only) from annual
- Use semi-annual trends to estimate annual figures

### Solution C: Render-to-Image via pymupdf + OCR

```python
# Even without tesseract, render pages to images
doc = fitz.open("problem.pdf")
for i, page in enumerate(doc):
    pix = page.get_pixmap(dpi=200)
    pix.save(f"page_{i+1}.png")
# Then use any OCR tool on the images
```

---

## Problem 2: SEC EDGAR 40-F Cover-Only Filings (Canadian Issuers)

**Symptoms:**
- SEC 40-F filing is only ~1.8MB HTM but actual text is ~360KB
- Filing contains inline XBRL but only 27 metrics (entity identifiers, pension assumptions)
- No revenue, CSM, balance sheet, or net income data
- Affects: Canadian filers filing 40-F with SEC

**Root Cause:**
Canadian issuers file their annual reports on **Form 40-F** (not 10-K or 20-F). SEC EDGAR accepts 40-F filings where the **primary document is a cover page only**. The actual financial statements are filed as **exhibits** that may be:
1. Available through SEC's iXBRL viewer (`/ix?doc=...`)
2. Available as separate exhibit files (XML/XBRL format)
3. Only on **SEDAR+** (Canada's securities filing system)
4. Only on the **company's IR website**

**Affected companies:** Manulife (MFC), Sun Life (SLF) — both Canadian

### Solution A: Download Exhibits via SEC iXBRL Viewer

```bash
# Full annual report through ix viewer
curl -L "https://www.sec.gov/ix?doc=/Archives/edgar/data/{CIK}/{ACC}/slf-20251231.htm" \
  -H "User-Agent: YourCompanyName contact@example.com" \
  -o full_filing.htm
```

### Solution B: Download from SEDAR+ (Requires browser)

1. Go to https://www.sedarplus.ca/
2. Search for the issuer
3. Find the annual report/MD&A
4. SEDAR+ may require manual interaction (blocks automated access)

### Solution C: Download from Company Investor Relations

Most companies host annual report PDFs on their IR page:
- Sun Life: https://www.sunlife.com/en/investors/
- Manulife: https://www.manulife.com/en/investors.html
- Search for "Annual Reports" or "Financial Reporting" section

### Solution D: Use SEC EDGAR Filing Index to Find Exhibits

```bash
# Get filing index
curl -s "https://www.sec.gov/Archives/edgar/data/{CIK}/{ACC}/index.json" \
  -H "User-Agent: CompanyName contact@example.com"

# Check for index page to list all documents in the filing
curl -s "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={CIK}&type=40-F&count=10" \
  -H "User-Agent: CompanyName contact@example.com"
```

---

## Verification

After applying any solution, verify:
- [ ] Numbers are present and match expected scale
- [ ] Chinese characters decode correctly (no mojibake)
- [ ] Financial tables have readable column/row headers
- [ ] SEC exhibits contain actual financial data (not just pointers)

## Known Cases

| Company | Issue | PDF | Working Tool | Notes |
|---------|-------|-----|--------------|-------|
| PICC 2025 Annual (601319) | Identity-H no ToUnicode | 12MB, 278pp | OCR (Tesseract) | 2024 annual & 2025 semi work fine |
| Manulife SEC 40-F (MFC) | Cover-only filing | 160-195KB | HKEX annual reports | 00945.HK has full PDFs |
| Sun Life SEC 40-F (SLF) | Cover-only filing | 1.8MB iXBRL | Company IR or SEDAR+ | SLF not listed in HK |

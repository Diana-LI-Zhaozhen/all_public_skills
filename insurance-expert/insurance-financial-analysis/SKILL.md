---
name: insurance-financial-analysis
description: >-
  Systematic financial analysis of A-share/H-share listed insurance
  companies under IFRS 17 / IFRS 9 / C-ROSS / HKRBC. Fetches annual/semi-annual
  reports from CNInfo/ HKEX/ SEC EDGAR, extracts IFRS 17 key metrics (CSM, insurance service
  result, investment portfolio), and produces structured earnings-quality
  and investment-performance assessments. For life insurers listed in mainland China, Hong Kong and U.S..
metadata:
  related-skills:
    - ifrs17-agent        # IFRS 17 accounting standard knowledge base
    - all-market-fillings-fetch # Cross-market (A+H+US) report fetching
    - strategist-ariston  # asset-level trading decisions (complementary)
---

# Insurance Financial Analysis

## Data Source Integrity

**ALL data MUST come from annual/semi-annual report PDFs (年报/半年报) obtained via `all-market-fillings-fetch`.**
- Do NOT use web search for financial figures
- Do NOT use financial data APIs (yfinance, East Money, etc.)
- Do NOT use analyst reports or third-party summaries
- IFRS 17 footnotes (CSM, insurance finance, OCI) are ONLY in official PDFs

**After pymupdf extraction, ALWAYS verify text quality:**
- Search for numerical values — if only Chinese chars appear but table numbers are blank, the PDF has font encoding issues → use OCR fallback

## Overview

Analyze Chinese and Hong Kong Life insurance companies' financial reports under IFRS 17 and IFRS 9. This skill covers the end-to-end workflow: data acquisition, structured data extraction, IFRS 17 metric calculation, investment portfolio decomposition, and earnings-quality assessment.

**This is NOT about IFRS 17 accounting theory** — for that, load `ifrs17-agent` first, which has the full knowledge base (7 chapters, 25 formulas). This skill is about **applying that knowledge to real Chinese insurer filings**.

## When to Use

Trigger when the user asks to analyze:
- A life insurance company
- "分析xx保险的财报"/"投资表现"/"盈利能力"
- An insurer's investment portfolio or earnings quality under the new accounting rules
- CSM trends, insurance service results, or IFRS 17 profit decomposition
- Comparison between life insurers

## Prerequisites

- `all-market-fillings-fetch` skill available (for fetching A-share/HK/US annual/semi-annual reports)
- `pymupdf` or `marker-pdf` for extracting text from PDF annual reports
- Basic IFRS 17 knowledge — consider loading `ifrs17-agent` for formula/standard references
- Data sources: CNInfo for A-share, HKEX for H-share, SEC EDGAR for ADR filings

## Workflow

### Step 1: Data Acquisition

Use `cninfo-pdf-fetch` to fetch the annual reports:

```bash
python scripts/fetch_cninfo_notices.py \
  --company-query "<公司名称>" \
  --stock-code "<6位代码>" \
  --report-types "annual,semi_annual" \
  --time-mode "range" \
  --range-years 5 \
  --per-type-mode "all" \
  --output-json "/tmp/<company>_reports.json"
```

**Key stock codes for major life insurers operating in mainland China and Hong Kong:**

| Company | A-share | H-share | ADR | Remarks |
|---------|---------|---------|-----|---------|
| China Life Insurance (中国人寿) | 601628 | 2628 | LFC | 独立上市（A股、H股、ADR） |
| Ping An Insurance (中国平安) | 601318 | 2318 | PNGAY | 独立上市（A股、H股、ADR） |
| China Pacific Insurance (中国太保) | 601601 | 2601 | — | 独立上市（A股、H股） |
| New China Life Insurance (新华保险) | 601336 | 1336 | — | 独立上市（A股、H股） |
| PICC (中国人保) | 601319 | 1339 | — | 独立上市（A股、H股） |
| AIA (友邦保险) | — | 01299 | AAGIY | 独立上市（H股、ADR） |
| Prudential (保诚) | — | 02378 | PUK | 独立上市（H股、ADR） |
| Manulife (宏利金融) | — | 00945 | MFC | 独立上市（H股、ADR） |
| Sun Life (永明金融) | — | — | SLF | 独立上市（ADR，未在香港上市） |
| HSBC Life (汇丰人寿) | — | **00005** | **HSBC** | 未独立上市。此处列母公司汇丰控股（00005.HK）的H股及ADR（NYSE: HSBC）。汇丰人寿为汇丰控股旗下寿险板块 |
| BOC Life (中银人寿) | — | **02388** | — | 未独立上市。此处列母公司中银香港（02388.HK）的H股。中银人寿为中银香港全资附属公司 |

**For multi-market companies**, use `all-market-fillings-fetch` to fetch A+H simultaneously.

### Step 2: Text Extraction

Download PDFs and extract structured text. Store downloaded PDFs locally in `references/pdfs/<company>/` to avoid re-downloading.

```python
import fitz
doc = fitz.open("<pdf_path>")
text = ""
for i, page in enumerate(doc):
    text += page.get_text()
doc.close()
```

Insurer annual reports are typically 200-400 pages. Target extraction size: 200K-500K chars for a 2-year report.

**🔍 After extraction, ALWAYS verify text quality:**
1. Check that the extracted text file is a reasonable size (not empty, not just a few KB)
2. Search for key numerical sections — if Chinese text is present but numbers in tables are missing/blank, the PDF has font encoding issues
3. For problematic PDFs, try: `page.get_text("text")` with different parameters, or fall back to OCR

**To check extraction quality via terminal:**
```bash
# Check if numbers are present in key financial sections
grep -c '保险服务收入' extracted.txt   # Should find the section
grep -oP '[0-9,]+' extracted.txt | head -20  # Should show actual numbers
```
If `grep -oP '[0-9,]+'` returns dates (2024, 2025) but no large numbers, the PDF likely has font encoding issues.**

### Step 3: Extract IFRS 17 Key Metrics

Search the extracted text for these critical sections:

**a) Insurance Service Result (保险服务业绩):**
Look in the 合并利润表 (Consolidated Income Statement):
- 保险服务收入 (Insurance Revenue)
- 保险服务费用 (Insurance Service Expenses)
- 分出保费的分摊 / 摊回保险服务费用 (Ceded/reinsured portions)
- 承保财务损益 (Insurance Finance Income/Expenses)
- 保险服务业绩 = Insurance Revenue - Insurance Service Expenses + Net Reinsurance

**b) CSM (合同服务边际 - Contractual Service Margin):**
Look in the 保险合同附注 (Insurance Contract Notes):
- 期初CSM → 当期新增/摊销/调整 → 期末CSM
- CSM摊销金额 (released to P&L as insurance revenue)
- 新业务CSM (new business contribution) — key growth indicator
- 期末CSM余额 — "future profit reservoir"

**c) Investment Portfolio (投资资产):**
Look in the 管理层讨论与分析 or 投资组合附注:
- 总投资资产 (Total investment assets)
- 投资资产按类别分布: 固定到期日 / 权益类 / 投资性房地产 / 联营企业
- 固定收益: 债券 / 定期存款 / 债权型金融产品
- 权益: 股票 / 基金 / 其他权益投资
- 总投资收益 / 净投资收益 / 公允价值变动损益
- 总投资收益率 / 净投资收益率

**d) Balance Sheet Key Items:**
- 总资产 (Total Assets)
- 保险合同负债 (Insurance Contract Liabilities) — under IFRS 17
- 归属于母公司股东权益 (Equity attributable to parent)
- 偿付能力充足率 (Solvency ratios: comprehensive / core)

**e) Key Operating Metrics:**
- 总保费 (Total premiums)
- 一年新业务价值 (NBV / VNB — New Business Value)
- 内含价值 (Embedded Value)
- 加权平均净资产收益率 (Weighted average ROE)
- EPS

### Step 4: Profit Decomposition Analysis (IFRS 17 Framework)

Break down the insurer's profit into three layers:

```
Insurance Service Result
  = Insurance Revenue - Insurance Service Expenses ± Reinsurance
  → Indicates underwriting profitability (负值=承保亏损, typical for life insurers)

Investment Result
  = Investment Income + Fair Value Changes + Interest Income - Credit Impairments
  → The main profit driver for most Chinese life insurers

Insurance Finance Income/Expenses
  = Impact of interest rate changes on insurance liabilities
  → Under IFRS 17, rate cuts INCREASE liability values (negative P&L impact)
  → Rate cuts matched by FV gains on bonds (partial hedge)

Net Profit attributable to parent
  = Service Result + Investment Result + Insurance Finance ± Tax
```

**Key insight:** For most Chinese life insurers, the insurance service result is NEGATIVE under IFRS 17 because the liability discount unwinding is classified as insurance finance expense, not service expense. ALL profit comes from the investment spread.

### Step 5: Investment Performance Analysis

**a) Yield Analysis:**
- 总投资收益率 times = income / average investment assets
- Compare 总投资收益率 vs 净投资收益率 to see the "market return" portion
- Large gap between total yield and net yield → high dependence on realized gains / market appreciation
- 三年平均总投资收益率 → more representative of long-term capability

**b) Portfolio Structure:**
- Bond % (the anchor) — typically 55-60% for life insurers
- Equity % (the swing factor) — typically 15-25%, determines volatility
- Equity classified as FVTPL vs FVTOCI matters for P&L volatility
- 债权型金融产品 (debt-type structured products) — watch for non-standard credit risk

**c) Strategic Signals:**
- Increasing equity allocation → bullish on A-share market / "长期资金入市" policy response
- Decreasing 定期存款 → yield-seeking behavior in low-rate environment
- 浮动收益型业务 ratio → the product-side response to rate cuts (shifting interest rate risk to policyholders)

### Step 6: Earnings Quality Assessment

| Factor | Signal | What to question |
|--------|--------|-----------------|
| Profit growth vs CSM growth | Profit up 44%, CSM up 3.5% | Low-quality growth, investment-driven |
| Total yield vs net yield gap | Gap widening | Reliance on realized gains |
| New business CSM trend | Declining | Future profitability under pressure |
| OCI vs P&L | Large OCI movements | Volatility hidden in equity |
| 承保财务损益 | Large and volatile | IFRS 17 liability discounting noise |
| 所得税率变动 | Effective rate jumps | One-off tax effects masking core earnings |

### Step 7: Comparative Analysis (Two or More Insurers)

When comparing two insurers side-by-side, add this dimension:

**a) Normalize by business mix:**
- If one is a pure life insurer (中国人寿) and the other is a composite group (中国平安), extract insurance-segment data separately. NEVER compare group-level figures without noting which segments are included.
- Key normalization: Insurance-only investment assets vs total group financial assets; insurance-only revenue vs group revenue; insurance-only equity contribution vs group equity.

**b) Identify structural ROE differences:**
- Pure life insurers typically show HIGHER ROE (20-28%) because capital is concentrated in one business with high leverage
- Composite groups typically show LOWER ROE (12-14%) because banking consumes capital at lower returns
- A higher ROE does NOT mean better management; it reflects a different capital structure

**c) Analyze CSM trajectory as the #1 comparison metric:**
- CSM growing + new business CSM healthy → future profit growth assured
- CSM declining (even if profit is high) → watch for structural erosion

**d) Investment portfolio structure comparison:**
- Classify both insurers' portfolios into comparable categories (bond/equity/cash/other)
- Note differences in classification: Ping An uses 债权型/股权型 while 中国人寿 uses 固定到期日/权益类
- Compare equity allocation change (YoY) as a strategy signal

**e) Profit sustainability comparison:**
- For each insurer, calculate: What portion of profit growth came from investment transactions vs core operations?
- Check one-time items, tax rate changes, and fair value gains that may not recur

**f) Produce side-by-side comparison tables:**
Include radar-dimension scoring (see examples in references/) with clear labeling of the evaluative dimension.

### Step 8: Synthesis

Output a structured report covering:
1. **Key Financial Snapshot** (table: total assets, premiums, profit, CSM, ROE, EPS)
2. **Investment Performance** (yields, portfolio structure, strategy signals)
3. **IFRS 17 Profit Decomposition** (service result, investment result, finance result)
4. **CSM Analysis** (trend, new business, release pattern)
5. **Earnings Quality** (sustainability, risks, one-off items)
6. **Risk Assessment** (solvency, credit quality, asset-liability matching)
7. **Comparative Analysis** (if comparing two+ insurers)
8. **Conclusion & Forward View**

## Pitfalls to Avoid

### Data Extraction
- ❌ **Don't use accountant-alice for insurers** — it's inventory/COGS-based, completely wrong for insurance
- ❌ **Don't rely only on 利润表 summary numbers** — IFRS 17 requires reading the notes (附注) for CSM, insurance finance splits, and investment portfolio detail
- ❌ **Don't assume "投资收益" in the P&L is the same as "总投资收益"** — the P&L line only shows a portion; total investment income adds fair value changes, interest income, and subtracts impairments
- ❌ **Some companies have life insurance as only one part of a larger, diversified financial group (e.g., Ping An, PICC, Xinhua Insurance). Do not use their consolidated market data (e.g., total assets, ROE, asset classification) as a proxy for the life insurance segment without adjustment.**
- ❌ **Don't rely on HKEX feed for historical annual reports** — the HKEXNews feed API (used by `fetch_hkex_notices.py`) only returns filings from the last ~7 days. Annual reports filed months ago are not accessible through this feed. Use HKEX披露易 historical search or company IR websites instead.
- ❌ **Don't expect full IFRS 17 data from SEC for Canadian 40-F filers** — Manulife (MFC) and Sun Life (SLF) file cover-only iXBRL documents (~160-200KB) with SEC. The full financial statements are submitted as separate exhibits not captured in the primary text. Use SEDAR+ or company IR websites for these.
- ❌ **Don't assume a single HKEX filing is the annual report** — Companies like AIA file TWO PDFs on the same date: a notification letter (~300KB, telling shareholders the report is available online) AND the actual annual report (3-8MB). The letter-only PDF has ~14KB of text, while the real report has hundreds of pages. If the extracted text is only ~10KB, check for a second filing.
- ❌ **Don't assume pymupdf can extract all PDF content** — Some Chinese insurer PDFs (e.g., PICC 2025 annual report 12MB) have font encoding issues where pymupdf extracts Chinese characters but NOT the numerical table data. After extraction, verify that numbers are present. If missing, use OCR (pytesseract) as fallback.
- ❌ **Don't trust SEC EDGAR ticker resolution for OTC ADRs** — AIA's ADR (AAGIY) and other OTC symbols are NOT in SEC's company_tickers.json. The resolver will silently fail. Use HKEX, the company's home exchange, or primary listing instead.
- ✅ Always extract both the income statement and the insurance contract notes (保险合同附注)
- ✅ After pymupdf text extraction, always verify: (1) Chinese text present, (2) numerical values present, (3) key sections like profit table and CSM note are recognizable. If numbers are missing from tables → font encoding issue → need OCR.
- ✅ For a **pure‑play life insurer** (e.g., China Life, AIA, Prudential, Manulife, Sun Life), fill in its own stock codes under **A‑share**, **H‑share**, or **ADR** as applicable. In the `Remarks` column, briefly state the listing status, e.g., *"Listed on A‑share, H‑share, and ADR (OTC/NYSE)"*.
- ✅ If the life insurance entity is **not independently listed** but is a wholly owned subsidiary / business segment of a listed parent company (e.g., HSBC Life, BOC Life), **fill the parent company's stock codes** into the corresponding market columns. In `Remarks`, explicitly note: *"Not independently listed. Parent company [Name] (code) is shown instead."*

### IFRS 17 Interpretation
- ❌ **Don't read "保险服务业绩" as "underwriting profit"** — it's not the same as old GAAP "承保利润". IFRS 17 splits insurance finance differently.
- ❌ **Don't compare insurance service results across insurers without checking** 采用保费分配法 vs GMM mix — different measurement models create different revenue patterns
- ✅ Remember that IFRS 17 insurance revenue is **not** premiums received — it's the release of the liability for remaining coverage
- ✅ The CSM is the best single metric for future profit trajectory

### Company-Specific
| Company | Warning |
|---------|---------|
| **Xinhua Insurance (新华保险)** & **PICC (中国人保)** | Their business mix differs significantly from pure life insurers. PICC has large health and property/casualty exposure; Xinhua's composition also includes group/health business. **Always check segment reporting before using consolidated figures.** |
| **Ping An Insurance (中国平安)** | A composite of insurance + banking + asset management. The consolidated group data **cannot** be treated as insurance‑only data. |
| | – Group total assets (~13.9T RMB) include ~3.4T bank loans and ~3.6T deposits → **not insurance assets**. |
| | – The insurance investment portfolio is ~6.49T RMB, **not** the group's total financial assets (~7.82T). |
| | – Group ROE (~14%) is diluted by banking; the insurance segment ROE is higher (~21%). |
| | – Ping An uses **债权型/股权型** (debt/equity‑style) asset classification, while pure insurers use **固定到期日/权益类** (fixed maturity/equity). This difference matters when comparing portfolio structures directly. |

## Verification

After analysis, verify:
- [ ] CSM trend direction confirmed (growing/shrinking?)
- [ ] Total investment yield > net investment yield gap explained
- [ ] Insurance service result sign and trend understood
- [ ] Profit attribution to investment vs underwriting clear
- [ ] Solvency ratios checked (comprehensive + core)
- [ ] Earnings quality assessed (not just headline profit growth)
- [ ] IFRS 17 transition adjustments noted (2023 adoption impact)

## References

See `references/` directory per-company analysis files:
- `china-life.md` — Full analysis of 中国人寿 under IFRS 17. Income statement, balance sheet, CSM, investment portfolio, yields, and analytical insights.
- `ping-an.md` — Full analysis of 中国平安 under IFRS 17. Consolidated + segment data, CSM decline analysis, 营运利润 concept, investment portfolio analysis.
- `cpic.md`, `xinhua.md`, `picc.md`, `aia.md`, `prudential.md`, `manulife.md`, `sun-life.md`, `hsbc-life.md`, `boc-life.md` — Company profiles with stock codes and listing status. Analysis summaries populated after PDF extraction.

PDFs are stored locally in `references/pdfs/<company>/` to avoid re-downloading.

## See Also

- `ifrs17-agent` — IFRS 17 standard knowledge base (formulas, models, accounting entries)
- `all-market-fillings-fetch` — Cross-market (A+H+US) report fetching

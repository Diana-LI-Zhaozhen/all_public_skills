---
name: insurance-financial-analysis
description: >-
  Systematic financial analysis of Chinese A-share/H-share listed insurance
  companies under IFRS 17 / IFRS 9 / C-ROSS. Fetches annual/semi-annual
  reports from CNInfo, extracts IFRS 17 key metrics (CSM, insurance service
  result, investment portfolio), and produces structured earnings-quality
  and investment-performance assessments. For life insurers, P&C insurers,
  and re-insurers listed in China.
metadata:
  related-skills:
    - ifrs17-agent        # IFRS 17 accounting standard knowledge base
    - accountant-alice    # manufacturing/retail financial analysis (NOT for insurers)
    - strategist-ariston  # asset-level trading decisions (complementary)
---

# Insurance Financial Analysis

## Overview

Analyze Chinese insurance companies' financial reports under IFRS 17 and IFRS 9. This skill covers the end-to-end workflow: data acquisition (CNInfo PDFs), structured data extraction, IFRS 17 metric calculation, investment portfolio decomposition, and earnings-quality assessment.

**This is NOT about IFRS 17 accounting theory** — for that, load `ifrs17-agent` first, which has the full knowledge base (7 chapters, 25 formulas). This skill is about **applying that knowledge to real Chinese insurer filings**.

## When to Use

Trigger when the user asks to analyze:
- A Chinese insurance company (life, P&C, or health)
- "分析xx保险的财报"/"投资表现"/"盈利能力"
- An insurer's investment portfolio or earnings quality under the new会计准则
- CSM trends, insurance service results, or IFRS 17 profit decomposition
- Comparison between Chinese insurers (e.g., 中国人寿 vs 中国平安 vs 中国太保 vs 新华保险)

## Prerequisites

- `cninfo-pdf-fetch` skill available (for fetching A-share annual/semi-annual reports)
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
  --range-years 2 \
  --per-type-mode "all" \
  --output-json "/tmp/<company>_reports.json"
```

**Key stock codes for major Chinese insurers:**
| Company | A-share | H-share | ADR |
|---------|---------|---------|-----|
| 中国人寿 | 601628 | 2628 | LFC |
| 中国平安 | 601318 | 2318 | PNGAY |
| 中国太保 | 601601 | 2601 | — |
| 新华保险 | 601336 | 1336 | — |
| 中国人保 | 601319 | 1339 | — |
| 中国再保险 | — | 1508 | — |

**For multi-market companies**, use `all-market-fillings-fetch` to fetch A+H simultaneously.

### Step 2: Text Extraction

Download PDFs and extract structured text:

```python
import fitz
doc = fitz.open("<pdf_path>")
text = ''
for i, page in enumerate(doc):
    text += page.get_text()
doc.close()
```

Chinese insurer annual reports are typically 200-400 pages. Target extraction size: 200K-500K chars for a 2-year report.

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
- Key insight from this session: 中国人寿 CSM +3.5% vs 中国平安 CSM -0.8%. Despite Ping An's operating profit growing, its future profit reservoir is shrinking.

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
- ❌ **Don't rely only on利润表 summary numbers** — IFRS 17 requires reading the notes (附注) for CSM, insurance finance splits, and investment portfolio detail
- ❌ **Don't assume "投资收益" in the P&L is the same as "总投资收益"** — the P&L line only shows a portion; total investment income adds fair value changes, interest income, and subtracts impairments
- ✅ Always extract both the income statement and the insurance contract notes (保险合同附注)

### IFRS 17 Interpretation
- ❌ **Don't read "保险服务业绩" as "underwriting profit"** — it's not the same as old GAAP "承保利润". IFRS 17 splits insurance finance differently.
- ❌ **Don't compare insurance service results across insurers without checking** 采用保费分配法 vs GMM mix — different measurement models create different revenue patterns
- ✅ Remember that IFRS 17 insurance revenue is **not** premiums received — it's the release of the liability for remaining coverage
- ✅ The CSM is the best single metric for future profit trajectory

### Company-Specific
- ❌ **Don't use 新华保险 or 中国人保 market data without checking** they have different business mixes (more group/health insurance)
- ✅ 中国平安 is a composite insurer+bank+asset manager — its insurance segment analysis requires extra decomposition
  - Group total assets (13.9T) include ~3.4T bank loans and ~3.6T deposits — these are NOT insurance assets
  - Insurance investment portfolio is ~6.49T, NOT the same as total group financial assets (~7.82T)
  - Group ROE (~14%) is dragged down by banking; insurance-segment ROE is higher (~21%)
  - Ping An uses 债权型/股权型 asset classification, while pure insurers use 固定到期日/权益类 — this classification difference matters when comparing portfolio structures directly
- ✅ **Ping An's 营运利润 (Operating Profit) is a trademark concept** not used by other Chinese insurers. It strips out short-term investment volatility by locking life investment returns at 4.0%. Do NOT compare it to competitors' "operating profit" — they don't have the same concept.
- ✅ **CSM trajectory divergence**: As of 2025, 中国人寿 CSM is growing (+3.5%) while 中国平安 CSM is declining (-0.8%). This is a critical comparative metric that signals different futures despite similar current profit levels.
- ✅ Always check if the company adopted IFRS 17 / IFRS 9 from 2023 (CTA 기준) — some figures need restatement adjustments

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

See `references/` directory for worked examples:
- `china-life-2024-2025.md` — Full analysis of 中国人寿 under IFRS 17 (2024-2025). Income statement, balance sheet, CSM, investment portfolio, yields, and analytical insights.
- `ping-an-2024-2025.md` — Full analysis of 中国平安 under IFRS 17 (2024-2025). Consolidated + segment data, CSM decline analysis, 营运利润 concept, investment portfolio analysis.
- `multi-insurer-reference-2021-2025.md` — **Comprehensive multi-insurer reference dataset** covering 9 insurers (中国人寿, 中国平安, CPIC, 新华保险, 中国太平, AIA, Prudential, Manulife, FWD) for 5 years (2021-2025). Sources explicitly stated: CNInfo A-share, HKEX H-share, yfinance, annual reports. Currency and IFRS 17/IFRS 4 basis noted per data point. Cross-company comparison tables included. Data gaps explicitly flagged for IFRS 17 specific metrics (CSM, NBV, EV, yields) that require PDF annual report extraction.

## See Also

- `ifrs17-agent` — IFRS 17 standard knowledge base (formulas, models, accounting entries)
- `cninfo-pdf-fetch` — Fetch Chinese insurer annual/semi-annual PDFs
- `all-market-fillings-fetch` — Cross-market (A+H+US) report fetching

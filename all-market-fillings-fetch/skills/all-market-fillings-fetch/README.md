# Cross-Market Scripts

## run_cross_market_financial_reports.py

一次请求同时跑 A 股 CNInfo、港股 HKEX 与美股 SEC EDGAR 的财报抓取下载，并输出统一汇总。

### 适用场景
- 例如：阿里巴巴在港股+美股，或者中芯国际在 A+H，要求最近三年财报同时获取。
- 结果中需要明确：
  - 请求了几个市场
  - 成功获取了几个市场
  - 每个市场获取了哪些文件

### HKEX 执行来源说明
- HKEX 在本脚本中默认调用外部仓库 `tmp/Claw/skills/hkex-pdf-downloader` 的现有 CLI（`annual-url` 工作流）。
- 当前跨市场编排里 HKEX 仅启用年报口径（annual）。

### 示例

```powershell
python .github/skills/scripts/run_cross_market_financial_reports.py \
  --name Alibaba \
  --cninfo-company-query 阿里巴巴 \
  --hkex-stocks 09988 \
  --hkex-report-types annual \
  --hkex-repo-root tmp/Claw/skills/hkex-pdf-downloader \
  --sec-companies BABA \
  --sec-report-kind annual \
  --years 3 \
  --summary-json tmp/cross-market/alibaba-3y-summary.json
```

### 输出
- 汇总 JSON：`tmp/cross-market/*.json`
- A 股下载目录：`downloads/cninfo`
- 港股下载目录：`downloads/hkex`
- 美股下载目录：`downloads/sec-edgar`

汇总 JSON 中关键字段：
- `totals.requestedMarkets`
- `totals.fetchedMarkets`
- `totals.fetchedMarketNames`
- `markets.CNINFO`
- `markets.HKEX`
- `markets.SEC`
- `files[]`（两地文件清单）

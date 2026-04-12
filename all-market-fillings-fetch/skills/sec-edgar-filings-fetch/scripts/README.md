# SEC EDGAR Scripts

## 脚本
- fetch_sec_edgar_filings.py
- download_sec_edgar_docs.py
- run_sec_edgar_batch.py

## 功能
- 输入 ticker / 公司名 / CIK。
- 拉取 SEC submissions JSON。
- 按报表类型和最近 N 年筛选。
- 输出结构化 JSON。
- 基于抓取结果批量下载 primaryDocument 到本地。
- 一键批量执行：多公司抓取 + 下载 + 汇总。

## 参数
- --query: 公司标识（必填）
- --report-kind: annual | quarterly | all | 自定义 form 列表
- --years: 最近 N 年（默认 3）
- --user-agent: SEC 请求头（建议填写真实联系信息）
- --output-json: 输出文件（必填）

下载脚本参数：
- --input-json: 抓取结果 JSON（必填）
- --output-dir: 下载根目录（默认 ./downloads/sec-edgar）
- --summary-json: 下载摘要输出（可选）
- --timeout: 单文件超时秒数
- --user-agent: 请求头

批处理脚本参数：
- --companies: 逗号分隔公司列表
- --companies-json: 公司列表 JSON（字符串数组）
- --report-kind: annual | quarterly | all | 自定义 form 列表
- --years: 最近 N 年
- --fetch-output-dir: 抓取 JSON 输出目录
- --download-output-dir: 文档下载目录
- --download-summary-dir: 下载摘要目录
- --batch-summary-json: 批处理总摘要文件

## 示例

```powershell
python .github/skills/sec-edgar-filings-fetch/scripts/fetch_sec_edgar_filings.py \
  --query BRK.B \
  --report-kind annual \
  --years 3 \
  --output-json tmp/berkshire-annual-3y.json
```

```powershell
python .github/skills/sec-edgar-filings-fetch/scripts/fetch_sec_edgar_filings.py \
  --query BABA \
  --report-kind annual \
  --years 3 \
  --output-json tmp/baba-annual-3y.json
```

```powershell
python .github/skills/sec-edgar-filings-fetch/scripts/download_sec_edgar_docs.py \
  --input-json tmp/baba-annual-3y.json \
  --output-dir downloads/sec-edgar \
  --summary-json tmp/baba-annual-3y-download-summary.json
```

```powershell
python .github/skills/sec-edgar-filings-fetch/scripts/run_sec_edgar_batch.py \
  --companies "Berkshire Hathaway,BABA" \
  --report-kind annual \
  --years 3 \
  --batch-summary-json tmp/sec-edgar/batch-summary-smoke.json
```
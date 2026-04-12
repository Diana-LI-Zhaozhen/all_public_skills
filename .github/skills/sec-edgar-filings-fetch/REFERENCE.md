# SEC EDGAR 参考说明

## 常用入口
- 公司页：https://www.sec.gov/edgar/browse/?CIK={CIK}
- 搜索页：https://www.sec.gov/edgar/search/
- 公司提交数据 JSON：https://data.sec.gov/submissions/CIK{10位补零CIK}.json
- Ticker 映射：https://www.sec.gov/files/company_tickers.json

## 报表类型
- 10-K：美国公司年度报告
- 10-Q：美国公司季度报告
- 20-F：外国发行人年度报告
- 6-K：外国发行人当前报告
- 8-K：重大事项报告

## 字段说明
- filingDate：向 SEC 提交日期
- reportDate：报告期截止日期
- accessionNumber：备案编号
- primaryDocument：主文档文件名

## 直达链接构造
- Filing index：
  - https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zero}/{accession_no_dash}/
- 主文档：
  - https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zero}/{accession_no_dash}/{primary_document}

## 查询建议
- 已知 CIK 时优先直接查询，稳定性更高。
- 年报查询可按 form 列表回退：
  - 美国公司：先 10-K，再 20-F
  - 外国发行人：先 20-F，再 10-K

## 限流与稳定性
- 每次请求都要携带明确 User-Agent。
- 批量抓取时建议增加间隔并限制并发。
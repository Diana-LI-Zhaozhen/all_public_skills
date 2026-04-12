---
name: "HKEX 请求参数标准化"
description: "将中文自然语言请求标准化为 HKEX 检索与下载参数。用于提取代码、报告类型、时间范围、分页与下载策略。"
argument-hint: "例如: 下载 00700 最近三年的年报和业绩公告"
agent: "agent"
---

将用户请求标准化为可执行的 HKEX 参数。

任务要求:
- 仅输出一个 JSON 对象。
- 不输出 Markdown 代码块。
- 无法确定的信息填默认值，并在 notes 写明。

标准化规则:
1. 标的识别
- 提取 stock_code_raw（原始输入）
- 生成 stock_code（5 位左侧补零，如 700 -> 00700）
- 若不是纯数字代码，stock_code 置为 null 并说明

2. 报告类型映射
- 年报 -> annual
- 中报/半年报 -> interim
- 季报 -> quarterly
- 业绩公告/业绩 -> results
- ESG/可持续发展 -> esg
- 未细分“公告/披露” -> annual, interim, results

3. 时间与分页
- 最新 -> time_mode: latest
- 指定年份 -> time_mode: year, year: YYYY
- 最近 N 年 -> time_mode: range, range_years: N
- 未指定 -> latest
- pages 默认 10

4. 下载默认
- output_mode 默认 links_and_download
- download_dir 默认 ./downloads/hkex
- pdf_only 默认 true
- language 默认 zh-CN

返回 JSON 结构:
{
  "stock_code_raw": "",
  "stock_code": null,
  "report_types": ["annual", "interim", "results"],
  "time_mode": "latest",
  "year": null,
  "range_years": null,
  "pages": 10,
  "pdf_only": true,
  "output_mode": "links_and_download",
  "download_dir": "./downloads/hkex",
  "language": "zh-CN",
  "notes": []
}

质量检查:
- stock_code 若非 null 必须是 5 位数字。
- report_types 不为空且去重。
- time_mode=year 时 year 必填。
- time_mode=range 时 range_years 必填。

现在处理这条用户请求（原样）:

{{input}}

---
name: "SEC EDGAR 请求参数标准化"
description: "将用户请求标准化为 SEC EDGAR 查询参数，提取公司标识、form 类型、时间范围与下载策略。"
argument-hint: "例如: 给我伯克希尔和阿里巴巴最近三年的年报"
agent: "agent"
---

将用户请求标准化为可执行 SEC EDGAR 参数。

任务要求:
- 仅输出一个 JSON 对象。
- 不输出代码块。
- 缺失信息使用默认值并写入 notes。

标准化规则:
1. 公司与标识
- companies: 数组，每项包含 query、ticker、cik（未知则 null）
- 支持多公司输入

2. 报表类型映射
- 年报 -> forms: [10-K, 20-F]
- 季报 -> forms: [10-Q]
- 临时公告 -> forms: [8-K, 6-K]
- 用户明确指定 form 时优先使用用户值

3. 时间范围
- 最新 -> time_mode: latest
- 指定年份 -> time_mode: year
- 最近 N 年 -> time_mode: range
- 未指定 -> latest

4. 下载默认
- output_mode 默认 links_only
- download_docs 默认 false
- download_dir 默认 ./downloads/sec
- language 默认 zh-CN

返回 JSON 结构:
{
  "companies": [
    {
      "query": "",
      "ticker": null,
      "cik": null
    }
  ],
  "forms": ["10-K", "20-F"],
  "time_mode": "latest",
  "year": null,
  "range_years": null,
  "max_per_company": 5,
  "output_mode": "links_only",
  "download_docs": false,
  "download_dir": "./downloads/sec",
  "language": "zh-CN",
  "notes": []
}

质量检查:
- companies 至少一项。
- forms 不为空且仅包含允许值。
- time_mode=year 时 year 必填。
- time_mode=range 时 range_years 必填。

现在处理这条用户请求（原样）:

{{input}}

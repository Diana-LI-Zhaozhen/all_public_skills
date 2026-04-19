---
name: "CNInfo 请求参数标准化"
description: "将中文自然语言请求标准化为 CNInfo 查询参数。用于提取公司、报告类型、时间范围、输出模式与下载策略。"
argument-hint: "例如: 给我茅台最新的年报/半年报/季度报告"
agent: "agent"
---

将用户的中文请求标准化为可执行的 CNInfo 查询参数。

任务要求:
- 只做参数提取与标准化，不输出长解释。
- 输出必须是 JSON 对象，不要使用 Markdown 代码块。
- 只能输出一个 JSON 对象，不要追加任何前后缀文本。
- 允许 `notes` 字段记录假设和歧义处理。
- 若信息缺失，给出合理默认值并写入 `notes`。

标准化规则:
1. 公司识别
- 提取 `company_query`（原始公司关键词）
- 若可确定证券代码，填 `security_code`，否则为 `null`
- 若名称可能歧义，`ambiguity` 设为 `true`，并在 `notes` 说明

2. 报告类型映射
- 年报 -> `annual`
- 半年报 -> `semi_annual`
- 季度报告 -> 同时包含 `q1` 与 `q3`
- 一季报 -> `q1`
- 三季报 -> `q3`
- 若用户说“财报/定期报告”但未细分，默认 `annual`, `semi_annual`, `q1`, `q3`
- 去重并保持顺序：`annual`, `semi_annual`, `q1`, `q3`

3. 时间范围
- 最新 -> `time_mode: "latest"`
- 指定年份（如 2023 年报）-> `time_mode: "year"`, `year: 2023`
- 指定区间（如最近三年）-> `time_mode: "range"`, `range_years: 3`
- 未指定 -> 默认 `latest`
- 若年份与“最新”同时出现，以显式年份/区间为准，并在 `notes` 说明冲突处理

4. 输出与下载默认
- `output_mode` 默认 `links_and_download`
- `download_dir` 默认 `./downloads/cninfo`
- `language` 默认为 `zh-CN`

5. 返回格式
返回如下 JSON 结构:
{
  "company_query": "",
  "security_code": null,
  "report_types": ["annual", "semi_annual", "q1", "q3"],
  "time_mode": "latest",
  "year": null,
  "range_years": null,
  "output_mode": "links_and_download",
  "download_dir": "./downloads/cninfo",
  "language": "zh-CN",
  "ambiguity": false,
  "notes": [],
  "assumptions": {
    "auto_pick_a_share_main_listing": true,
    "quarterly_includes_q1_q3": true
  }
}

质量检查:
- `report_types` 不为空
- 枚举值只能来自允许集合
- `time_mode=year` 时必须有 `year`
- `time_mode=range` 时必须有 `range_years`
- `notes` 简短且可执行
- 若无法解析公司，`company_query` 保留原文并在 `notes` 写明待确认项

现在处理这条用户请求（原样）:

{{input}}

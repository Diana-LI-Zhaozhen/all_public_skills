---
name: "跨市场财报输出格式规范"
description: "Use when returning mixed CNInfo/HKEX/SEC results in one response."
---

# Financial Report Unified Output Format

用于多市场混合请求时的统一输出。

适用场景:
- 同一请求同时包含 CNInfo、HKEX、SEC 目标。

输出语言:
- 中文请求默认中文。

必选结构:
1. 执行结果：按市场统计命中/下载/失败，并给出 requestedMarkets / fetchedMarkets。
2. 结果表：统一列。
3. 说明：仅记录假设、回退、失败。

结果表列顺序:
- 来源市场
- 公司
- 查询标识
- 报告类型
- 标题
- 日期
- 文档链接
- 本地文件路径
- 状态

状态字段:
- 已下载
- 已匹配未下载
- 未找到
- 下载失败

规范要求:
- 保留原市场字段语义，不伪造链接。
- 必须显示失败项。
- 多市场结果按日期倒序展示。

推荐执行结果模板:
- 执行结果：请求市场 X 个，成功获取 Y 个，识别文件 Z 个。

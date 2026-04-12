---
name: "SEC EDGAR 输出格式规范"
description: "Use when returning SEC EDGAR filing search results and optional document download outcomes."
---

# SEC EDGAR Output Format

用于约束 SEC EDGAR 检索任务的输出格式。

适用场景:
- 用户请求 10-K/10-Q/20-F/6-K/8-K。
- 输出包含 filing 链接、主文档链接与可选下载结果。

输出语言:
- 中文请求默认中文输出。

必选结构:
1. 执行结果：按公司统计命中/失败
2. 结果表：固定列
3. 说明：假设、回退、失败

结果表列顺序:
- 公司
- 查询标识（ticker/CIK）
- 报表类型
- 财年截止
- 提交日期
- Filing 链接
- 主文档链接
- 本地文件路径
- 状态

状态字段:
- 已匹配未下载
- 已下载
- 未找到
- 下载失败

说明区规范:
- 外国发行人自动优先 20-F 时要说明。
- ticker 未命中改用 CIK 的回退要说明。
- 失败项要列出简短原因。

禁止项:
- 不伪造 SEC 链接。
- 不忽略未命中公司。

---
name: "财报请求路由参数标准化"
description: "将自然语言财报请求拆分为 CNInfo/HKEX/SEC 子任务参数，支持混合市场输入。"
argument-hint: "例如: 给我茅台最新年报、00700 最近三年业绩公告、AAPL 最新 10-K"
agent: "agent"
---

将用户请求标准化为跨市场子任务列表。

任务要求:
- 仅输出一个 JSON 对象。
- 不输出 Markdown 代码块。
- 允许一个请求拆分为多个 tasks。
- 如果请求体现“一次执行并统一汇总”，设置 execution_mode 为 cross_market_script。

路由与拆分规则:
1. market 取值仅允许 cninfo, hkex, sec, unknown。
2. 单条子任务只包含一个 market。
3. 混合输入按实体拆分（公司/代码/form）。
4. 不确定 market 时设为 unknown 并在 notes 说明。
5. 当 execution_mode=cross_market_script 且 HKEX 请求类型不含 annual 时，在 notes 记录“跨市场脚本下 HKEX 仅支持 annual，需降级或分市场执行”。

返回 JSON 结构:
{
  "execution_mode": "route_only",
  "tasks": [
    {
      "market": "cninfo",
      "query": "茅台最新年报",
      "params": {}
    }
  ],
  "language": "zh-CN",
  "notes": []
}

质量检查:
- tasks 不为空。
- 每个 task 必有 market、query、params。
- 若 market=unknown，必须在 notes 写明原因。
- execution_mode 仅允许 route_only 或 cross_market_script。

现在处理这条用户请求（原样）:

{{input}}

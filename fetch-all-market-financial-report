# 财报检索工作流总览

本文件用于快速选择并调用你已配置的财报工作流（CNInfo / HKEX / SEC / 跨市场路由）。

## 1. 能力映射

| 场景 | Agent | Prompt | Output Instructions |
|---|---|---|---|
| A 股 CNInfo 年报/半年报/季度报告 | `.github/agents/cninfo-fetch-download.agent.md` | `.github/prompts/cninfo-parse-request.prompt.md` | `.github/instructions/cninfo-output-format.instructions.md` |
| 港股 HKEX 公告 PDF（年报/中报/季报/业绩/ESG） | `.github/agents/hkex-fetch-download.agent.md` | `.github/prompts/hkex-parse-request.prompt.md` | `.github/instructions/hkex-output-format.instructions.md` |
| 美股 SEC EDGAR（10-K/10-Q/20-F/6-K/8-K） | `.github/agents/sec-edgar-fetch.agent.md` | `.github/prompts/sec-edgar-parse-request.prompt.md` | `.github/instructions/sec-output-format.instructions.md` |
| 混合市场统一路由与汇总 | `.github/agents/financial-report-router.agent.md` | `.github/prompts/financial-report-parse-request.prompt.md` | `.github/instructions/financial-report-output-format.instructions.md` |

## 2. 快速调用模板

### CNInfo
- 例 1：给我茅台最新年报并下载
- 例 2：下载宁德时代最近三年的年报和半年报
- 例 3：给我比亚迪最新季度报告（含一季报和三季报）

### HKEX
- 例 1：下载 00700 最近三年的年报
- 例 2：给我 09988 最新中报和业绩公告 PDF
- 例 3：下载 02318 最近两年的 ESG 报告

### SEC
- 例 1：给我 AAPL 最近三年的 10-K
- 例 2：给我阿里巴巴最近三年的 20-F
- 例 3：查询 NVDA 最新 10-Q 并给出主文档链接

### 混合市场
- 例 1：给我茅台最新年报、00700 最近三年年报、BABA 最近两年 20-F
- 例 2：一次性抓取阿里在 CNInfo/HKEX/SEC 的最近三年年报并统一汇总

## 3. 输出约定

所有工作流统一遵循：
1. 执行结果（命中/下载/失败摘要）
2. 结果表（固定列）
3. 说明（仅在有假设/回退/失败时）

状态字段统一使用：
- 已下载
- 已匹配未下载
- 未找到
- 下载失败

## 4. 路由与回退规则（简版）

- CNInfo：公司歧义默认选 A 股主上市，并在说明写明。
- CNInfo：季度报告默认包含 q1 + q3。
- HKEX：代码可自动补零（700 -> 00700）。
- SEC：外国发行人年报优先 20-F，美国公司年报优先 10-K。
- 混合请求：按实体拆分后并行执行，不丢失败项。

## 5. 跨市场脚本模式说明

当请求明确为“一次执行并统一汇总”时，可走跨市场编排：
- 参考：`.github/skills/all-market-fillings-fetch/README.md`
- 脚本：`.github/skills/all-market-fillings-fetch/run_cross_market_financial_reports.py`

当前限制：
- 跨市场脚本模式下，HKEX 仅支持 annual 口径。
- 若用户要求 HKEX interim/quarterly/results/esg：
  - 方案 A：提示降级到 annual；
  - 方案 B：改为分市场工作流执行（推荐）。

## 6. 维护建议

当新增 skill 时，按以下顺序补齐：
1. 新增/更新对应 agent
2. 新增/更新对应 prompt
3. 新增/更新输出 instructions
4. 在本总览表追加一行映射

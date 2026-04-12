---
name: sec-edgar-filings-fetch
description: "Search SEC EDGAR filings by ticker/company/CIK and return recent annual or quarterly filings (10-K/10-Q/20-F/6-K/8-K) with direct document links."
argument-hint: "例如: 给我伯克希尔和阿里巴巴最近三年的年报"
user-invocable: true
disable-model-invocation: false
---

# SEC EDGAR 财报搜索技能

## 能力范围
- 公司检索：支持股票代码、公司名、CIK。
- 报表筛选：支持 10-K、10-Q、20-F、6-K、8-K。
- 历史区间：支持按最近 N 年筛选。
- 链接输出：返回 Filing 链接与主文档链接。

## 适用场景
- 用户要美国上市公司最近几年年报/季报。
- 用户要中概股最近几年 20-F。
- 用户要按 CIK 直接查询 SEC EDGAR。

## 默认规则
- 美国公司年报默认使用 10-K。
- 外国发行人（如中概股）年报默认使用 20-F。
- 返回最近记录时，按 filing date 倒序。

## 标准流程
1. 解析用户输入中的公司和年限。
2. 解析报表类型：年报优先 10-K/20-F，季报优先 10-Q。
3. 调用脚本获取并筛选最近 N 年数据。
4. 输出结构化结果：公司、form、财年、提交日期、链接。
5. 如未命中，给出回退说明（例如改用 CIK 或替代 form）。

## 脚本
- 主脚本：scripts/fetch_sec_edgar_filings.py
- 下载脚本：scripts/download_sec_edgar_docs.py
- 脚本说明：scripts/README.md
- 参考文档：REFERENCE.md

## 输出建议
- 中文请求优先中文回复。
- 表格字段建议：
  - 公司
  - 查询标识（ticker/CIK）
  - 报表类型
  - 财年截止
  - 提交日期
  - Filing 链接
  - 主文档链接

## 注意事项
- SEC 数据接口建议带 User-Agent，避免被限流。
- 中概股年报通常使用 20-F，不是 10-K。
- ADR / OTC 代码不一定能直接由 SEC ticker 映射解析；部分非保荐 ADR 可能根本没有 SEC 定期申报。
- 不要伪造链接，未命中应明确写未找到。
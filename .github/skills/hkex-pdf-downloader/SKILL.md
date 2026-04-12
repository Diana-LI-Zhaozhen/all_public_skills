---
name: hkex-pdf-downloader
description: "Fetch and download HKEX disclosure PDFs (annual/interim/quarterly/results/ESG) by stock code from HKEXnews feeds."
argument-hint: "例如: 下载 00700 最近三年的年报和业绩公告"
user-invocable: true
disable-model-invocation: false
---

# HKEX PDF 下载技能

## 能力范围
- 从 HKEXnews 最新公告 JSON feed 拉取披露记录。
- 按股票代码、报告类型筛选（年报/中报/季报/业绩/ESG）。
- 构造并返回可下载 PDF 链接。
- 按统一命名下载到本地目录。

## 适用场景
- 用户要求下载港股公司年报、财务报表、业绩公告 PDF。
- 用户给出股票代码（如 `00700`、`09988`）要批量拉取。
- 用户要“最新一条”或“最近 N 页公告”检索。

## 标准流程
1. 解析股票代码与报告类型。
2. 调用 `scripts/fetch_hkex_notices.py` 拉取并筛选记录。
3. 如需下载，先可选调用 `scripts/build_download_items_json.py` 归一化。
4. 调用 `scripts/download_hkex_pdfs.py` 批量下载。
5. 输出结果表（公司、代码、类型、时间、链接、本地路径、状态）。

## 脚本
- 抓取脚本：scripts/fetch_hkex_notices.py
- 归一化脚本：scripts/build_download_items_json.py
- 下载脚本：scripts/download_hkex_pdfs.py
- 脚本说明：scripts/README.md
- 参考文档：REFERENCE.md

## 注意事项
- HKEX feed 可能调整字段，若失败先检查 `webPath/ext/newsInfoLst`。
- 部分公告不是 PDF；默认仅保留 PDF。
- 不要伪造下载链接，未命中需明确返回“未找到”。
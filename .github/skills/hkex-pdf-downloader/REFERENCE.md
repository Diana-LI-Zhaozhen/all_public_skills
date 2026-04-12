# HKEX 披露检索参考

## 数据源
- 基础站点：https://www1.hkexnews.hk
- feed 路径模式：`/ncms/json/eds/lci{board}{window}relsd{lang}_{page}.json`

示例：
- 主板最新中文第 1 页：
  - https://www1.hkexnews.hk/ncms/json/eds/lcisehk1relsdc_1.json
- 主板最近 7 天英文第 1 页：
  - https://www1.hkexnews.hk/ncms/json/eds/lcisehk7relsde_1.json

## 关键字段
- `newsInfoLst`: 公告列表
- `stock[].sc` / `stock[].sn`: 股票代码/简称
- `title`: 公告标题
- `relTime`: 披露时间
- `ext`: 附件后缀（常见 `pdf`）
- `webPath`: 文档相对路径
- `t1Code` / `t2Code`: 分类编码（财务相关常见 `t1Code=40000`）

## URL 拼接
- 文档绝对链接：`https://www1.hkexnews.hk{webPath}`

## 类型映射建议
- annual: 年报 / annual report
- interim: 中期报告 / interim report
- quarterly: 季度报告 / quarterly report
- results: 业绩公告 / final/interim/quarterly results
- esg: ESG / 环境社会管治

## 可靠性建议
- 分页抓取时从 1 页开始，按需增加 `pages`。
- 下载时保留失败项并继续后续任务。
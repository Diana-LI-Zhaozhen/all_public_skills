# 交付记录

## 交付时间
2026-05-17

## 交付物
| 文件 | 说明 | 路径 |
|------|------|------|
| hk-insurer-asset-allocation-trend.md | 资产配置与经营分析报告，覆盖7家公司<br>含估值框架、汇率调整、压力测试、利率敏感性 | deliverables/hk-insurer-asset-allocation-trend.md |
| hk-asset-allocation-fy2025.html | 内部参考演示文稿（HTML，Bold Signal风格，10页） | deliverables/hk-asset-allocation-fy2025.html |

## 需求梳理
**用户要求：**
1. 分析香港寿险公司最近一年的资产配置趋势
2. 结合公司整体经营（CSM、利润质量、ROE、NBV等）细化分析
3. 替换公司：去掉中国平安和中国太保，改为AIA、HSBC Life、BOC Life、Manulife
4. 最终覆盖7家公司：中国人寿、AIA、Prudential、Sun Life、Manulife、HSBC Life、BOC Life
5. 生成内部参考PPT（使用frontend-slides技能制作HTML演示文稿）

**后续调整（2026-05-17）：**
- 字体调大：body-size从clamp(0.7rem,1.3vw,1rem) → clamp(0.8rem,1.5vw,1.1rem)
- 新增估值框架（P/CSM、股息率、总股东回报率）
- 新增汇率调整后的CSM增长
- 新增A股跌20%压力测试
- AIA权益分类拆细（纯股票 vs 参与式基金）
- 新增利率敏感性量化
- 新增资本回报对比表
- Prudential CSM分解分析
- 政策可逆性尾部风险分析

## 数据来源
各公司FY2024-FY2025年度官方报告（CNInfo / HKEX披露易 / SEC EDGAR / 公司IR网站）

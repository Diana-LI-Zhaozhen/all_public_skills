#!/usr/bin/env python3
"""
IFRS 17 Variable Dictionary (based on lifelib data model)

This module defines the structured variable mappings used in IFRS 17
financial reporting — covering EstimateType, AocType, LiabilityType,
PnlVariableType, and AmountType dimensions.

Usage (from skill):
    from ifrs17_variables import (
        ESTIMATE_TYPES, AOC_TYPES, PNL_VARIABLES,
        get_pnl_mapping, get_estimate_type_desc
    )
"""

# ============================================================
# C.1 Core Entity Dimensions
# ============================================================

LIABILITY_TYPES = {
    "LRC": "Liability for Remaining Coverage — 未到期责任负债, FCF + CSM (IFRS 17 ¶B96–B100)",
    "LIC": "Liability for Incurred Claims — 已发生赔款负债, FCF only (无CSM)",
}

VALUATION_APPROACHES = {
    "BBA": "Building Block Approach = GMM 通用模型 — 默认计量模型",
    "VFA": "Variable Fee Approach — 浮动收费法，直接参与特征合同",
    "PAA": "Premium Allocation Approach — 保费分配法，覆盖期≤1年",
}

ECONOMIC_BASIS = {
    "L": "Locked-in rate — 初始确认时锁定的折现率 (GMM CSM计息用)",
    "C": "Current rate — 当期市场即期利率 (FCF计量、VFA调整用)",
}

NOVELTY = {
    "N": "New — 当期新确认合同",
    "C": "Current — 当期存续合同",
    "P": "Prior — 前期已存在合同",
}

# ============================================================
# C.2 Estimate Types
# ============================================================

ESTIMATE_TYPES = {
    "BE":  {"name": "Best Estimate",         "desc": "最佳估计负债BEL，概率加权折现现金流的无偏估计"},
    "RA":  {"name": "Risk Adjustment",        "desc": "风险调整，非金融风险补偿"},
    "C":   {"name": "CSM",                    "desc": "合同服务边际，未实现利润储备"},
    "L":   {"name": "Loss Component",         "desc": "亏损部分，亏损合同的单独跟踪 (IFRS 17 ¶47–52)"},
    "LR":  {"name": "Loss Recovery",          "desc": "亏损恢复，再保险分出对应亏损恢复"},
    "A":   {"name": "Actual Cash Flows",      "desc": "实际现金流，当期实际发生的现金流入/流出"},
    "AA":  {"name": "Advanced Actual",        "desc": "预付实际，预收保费等提前收到的现金流"},
    "OA":  {"name": "Overdue Actual",         "desc": "逾期实际，已到期未收的现金流"},
    "DA":  {"name": "Deferral Amortization",  "desc": "递延摊销，保险获取现金流(IACF)的摊销"},
    "APA": {"name": "Actual Premium Allocation",  "desc": "实际保费分配，PAA下按已赚保费确认收入"},
    "BEPA":{"name": "Best Estimate Premium Allocation", "desc": "最佳估计保费分配，PAA下预计保费分配"},
}

# ============================================================
# C.3 Analysis of Change Types (AocType)
# ============================================================

AOC_TYPES = {
    "BOP": {"name": "Beginning of Period",       "desc": "期初余额",                        "affects": "All"},
    "EOP": {"name": "End of Period",             "desc": "期末余额",                        "affects": "All"},
    "NF":  {"name": "Non-Financial Change",       "desc": "非金融假设变动（死亡率/发病率/退保率等）", "affects": "FCF"},
    "F":   {"name": "Financial Change",           "desc": "金融假设变动（折现率变动）",          "affects": "FCF"},
    "IA":  {"name": "Interest Accretion",         "desc": "利息计息 (GMM: CSM锁定利率; BEL:当期利率)", "affects": "CSM, BEL"},
    "YCU": {"name": "Yield Curve Update",         "desc": "收益率曲线更新",                   "affects": "BEL/FCF"},
    "CRU": {"name": "Credit Risk Update",         "desc": "信用风险更新",                     "affects": "RA"},
    "FX":  {"name": "Foreign Exchange",           "desc": "汇率变动",                        "affects": "FCF/CSM"},
    "AM":  {"name": "Amortization",               "desc": "CSM按覆盖单元摊销至保险收入",       "affects": "CSM"},
    "CF":  {"name": "Cash Flow",                  "desc": "实际现金收付",                     "affects": "Actuals"},
    "WO":  {"name": "Write-Off",                  "desc": "核销，已逾期未收款的核销",           "affects": "Actuals"},
}

# ============================================================
# C.4 P&L Variable Types (PnlVariableType)
# ============================================================

PNL_VARIABLES = {
    # Insurance Revenue (IRn)
    "IR1":  {"parent": "IR",  "name": "保费收入"},
    "IR2":  {"parent": "IR",  "name": "已发生赔款回收"},
    "IR3":  {"parent": "IR",  "name": "CSM摊销"},
    "IR4":  {"parent": "IR",  "name": "获取成本摊销"},
    "IR5":  {"parent": "IR",  "name": "非金融风险调整(RA)释放"},
    "IR6":  {"parent": "IR",  "name": "经验调整/保费分配"},
    # Insurance Service Expenses (ISEn)
    "ISE1": {"parent": "ISE", "name": "分出再保险保费"},
    "ISE2": {"parent": "ISE", "name": "净已发生赔款"},
    "ISE3": {"parent": "ISE", "name": "费用"},
    "ISE4": {"parent": "ISE", "name": "佣金"},
    "ISE5": {"parent": "ISE", "name": "已发生其他赔款"},
    "ISE6": {"parent": "ISE", "name": "获取成本摊销(费用)"},
    "ISE7": {"parent": "ISE", "name": "分出再保险CSM摊销"},
    "ISE8": {"parent": "ISE", "name": "亏损恢复摊销"},
    "ISE9": {"parent": "ISE", "name": "亏损部分摊销"},
    "ISE10":{"parent": "ISE", "name": "分出再保险RA释放"},
    "ISE11":{"parent": "ISE", "name": "亏损部分/恢复变动"},
    "ISE12":{"parent": "ISE", "name": "分出再保险非金融变动"},
    # Insurance Finance Income/Expense (IFIEn)
    "IFIE1":{"parent": "IFIE","name": "保险财务费用——FCF/CSM计息"},
    "IFIE2":{"parent": "IFIE","name": "保险财务费用——LIC计息"},
    "IFIE3":{"parent": "IFIE","name": "保险财务费用——汇率变动"},
    # OCI
    "OCI1": {"parent": "OCI", "name": "计入OCI的保险合同金融变动——LRC"},
    "OCI2": {"parent": "OCI", "name": "计入OCI的保险合同金融变动——LIC"},
}

# ============================================================
# C.5 Amount Types
# ============================================================

AMOUNT_TYPES = {
    "PR":  {"name": "保费 Premium",                      "direction": "inflow"},
    "NIC": {"name": "净已发生赔款 Net Incurred Claims",    "direction": "outflow"},
    "ICO": {"name": "已发生其他赔款 Incurred Claims Other","direction": "outflow"},
    "AEA": {"name": "实际分配费用 Allocated Expense Actual","direction": "outflow"},
    "AEM": {"name": "维持分配费用 Allocated Expense Maint", "direction": "outflow"},
    "ACA": {"name": "实际分配佣金 Allocated Comm Actual",   "direction": "outflow"},
    "ACM": {"name": "维持分配佣金 Allocated Comm Maint",    "direction": "outflow"},
}

# ============================================================
# C.6 PnlType (CSM/LC/LR change classification)
# ============================================================

PNL_TYPES = {
    "NF": {"name": "Non-Financial — 非金融变动", "pnl": "IR / ISE"},
    "F":  {"name": "Financial — 金融变动",       "pnl": "IFIE"},
    "AM": {"name": "Amortization — 摊销",        "pnl": "IR / ISE"},
    "FX": {"name": "Foreign Exchange — 汇率",     "pnl": "IFIE"},
}

# ============================================================
# C.7 Mapping Builders (for lifelib-style P&L assembly)
# ============================================================

def get_fcf_pnl_mapping():
    """
    Build the FCF-to-P&L mapping (template_example2 logic).
    
    Returns:
        pd.DataFrame with columns:
        LiabilityType, IsReinsurance, PnlVariableType
    """
    import pandas as pd
    return pd.DataFrame.from_records([
        # Non-Financial FCF changes
        ["LRC", False, "IR5"],
        ["LRC", True,  "ISE10"],
        ["LIC", False, "ISE12"],
        ["LIC", True,  "ISE12"],
        # Financial FCF changes (lockin & current)
        ["LRC", None,  "IFIE1"],
        ["LIC", None,  "IFIE2"],
        # Financial FCF → OCI
        ["LRC", None,  "OCI1"],
        ["LIC", None,  "OCI2"],
    ], columns=["LiabilityType", "IsReinsurance", "PnlVariableType"])


def get_csm_pnl_mapping():
    """
    Build CSM change → P&L mapping.
    
    Returns:
        pd.DataFrame with columns:
        PnlType, IsReinsurance, PnlVariableType
    """
    import pandas as pd
    return pd.DataFrame.from_records([
        ["NF", False, "IR5"],    # Non-fin, direct  → IR
        ["NF", True,  "ISE10"],  # Non-fin, reins   → ISE
        ["F",  False, "IFIE1"],  # Fin, direct      → IFIE
        ["F",  True,  "IFIE1"],  # Fin, reins       → IFIE
        ["AM", False, "IR3"],    # Amort, direct    → IR
        ["AM", True,  "ISE7"],   # Amort, reins     → ISE
        ["FX", False, "IFIE3"],  # FX, direct       → IFIE
        ["FX", True,  "IFIE3"],  # FX, reins        → IFIE
    ], columns=["PnlType", "IsReinsurance", "PnlVariableType"])


def get_loss_component_mapping():
    """Build Loss Component (LC/LR) → P&L mapping."""
    import pandas as pd
    mappings = {
        "L": {  # Loss Component
            "NF": "ISE11", "F": "IFIE1", "AM": "ISE9", "FX": "IFIE3"
        },
        "LR": {  # Loss Recovery
            "NF": "ISE11", "F": "IFIE1", "AM": "ISE8", "FX": "IFIE3"
        },
    }
    records = []
    for est_type, pnl_map in mappings.items():
        for pnl_type, pnl_var in pnl_map.items():
            records.append([est_type, pnl_type, pnl_var])
    return pd.DataFrame.from_records(records, columns=["EstimateType", "PnlType", "PnlVariableType"])


def get_actuals_pnl_mapping():
    """Build Actual Cash Flows → P&L mapping."""
    import pandas as pd
    return pd.DataFrame.from_records([
        # Premiums
        ["PR",  False, "IR1"],
        ["PR",  True,  "ISE1"],
        # Claims
        ["NIC", None,  "ISE2"],
        ["ICO", None,  "IR2"],   # IR side
        ["ICO", None,  "ISE5"],  # ISE side (negated)
        # Expenses
        ["AEA", None,  "ISE3"],
        ["AEM", None,  "ISE3"],
        # Commissions
        ["ACA", None,  "ISE4"],
        ["ACM", None,  "ISE4"],
    ], columns=["AmountType", "IsReinsurance", "PnlVariableType"])


# ============================================================
# Quick Lookup Utilities
# ============================================================

def describe_estimate_type(code: str) -> str:
    """Return human-readable description of an EstimateType code."""
    info = ESTIMATE_TYPES.get(code)
    return f"{info['name']}: {info['desc']}" if info else f"Unknown: {code}"

def describe_aoc_type(code: str) -> str:
    """Return human-readable description of an AocType code."""
    info = AOC_TYPES.get(code)
    return f"{info['name']} → {info['desc']}" if info else f"Unknown: {code}"

def describe_pnl_variable(code: str) -> str:
    """Return human-readable description of a PnlVariableType."""
    info = PNL_VARIABLES.get(code)
    return f"[{info['parent']}] {info['name']}" if info else f"Unknown: {code}"

def list_all_pnl_by_parent() -> dict:
    """Group PNL variables by parent category."""
    result = {}
    for code, info in PNL_VARIABLES.items():
        parent = info["parent"]
        result.setdefault(parent, []).append(f"{code}: {info['name']}")
    return result


if __name__ == "__main__":
    print("=== IFRS 17 Variable Dictionary ===")
    print(f"\nEstimate Types: {len(ESTIMATE_TYPES)}")
    for k, v in ESTIMATE_TYPES.items():
        print(f"  {k}: {v['name']}")
    print(f"\nAoc Types: {len(AOC_TYPES)}")
    for k, v in AOC_TYPES.items():
        print(f"  {k}: {v['name']}")
    print(f"\nPNL Variables: {len(PNL_VARIABLES)}")
    print("\n# By Parent:")
    for parent, vars_list in list_all_pnl_by_parent().items():
        print(f"  {parent}: {', '.join(v.split(':')[0] for v in vars_list)}")

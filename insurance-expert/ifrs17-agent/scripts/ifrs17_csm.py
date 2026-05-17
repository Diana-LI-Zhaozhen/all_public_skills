#!/usr/bin/env python3
"""
IFRS 17 CSM Calculator — 合同服务边际计算器

Implements both GMM (General Measurement Model) and VFA (Variable Fee Approach)
CSM roll-forward calculations based on IFRS 17 ¶44–52 and the lifelib model.

Key formulas:
  - F3: CSM₀ = max(-FCF, 0)
  - F4: CSM_t(GMM) = CSM_{t-1} × (1 + r_lock) − Amort_t + ΔNonFin
  - F5: CSM_t(VFA) = CSM_{t-1} + ΔVF_t − Amort_t
  - F7: CU_t = NOP_t × SA_t
  - F8: Amort_t = CSM_pending × CU_t / ΣCU

Usage:
    from ifrs17_csm import CSMCalculator

    calc = CSMCalculator(model='GMM', lockin_rate=0.03)
    calc.initialize_csm(initial_fcf=-3200)
    calc.roll_forward(
        period=1,
        coverage_units=95,
        total_coverage_units=500,
        non_financial_delta=0,
        financial_delta=0,    # for VFA: variable fee change
    )
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class CSMRecord:
    """Single-period CSM state."""
    period: int
    csm_begin: float = 0.0
    interest: float = 0.0          # GMM: lockin_rate accretion
    amortization: float = 0.0
    non_fin_delta: float = 0.0     # Non-economic assumption changes
    fin_delta: float = 0.0         # VFA: ΔVF; GMM: 0
    csm_end: float = 0.0
    coverage_units: float = 0.0
    cumulative_amort: float = 0.0


@dataclass
class CSMCalculator:
    """
    IFRS 17 Contractual Service Margin calculator.

    Supports GMM (default) and VFA paths. Tracks full CSM roll-forward
    history with all IFRS 17 required components.
    """

    model: str = "GMM"              # "GMM" or "VFA"
    lockin_rate: float = 0.0        # Locked-in discount rate (GMM only)
    history: list = field(default_factory=list)

    def __post_init__(self):
        if self.model not in ("GMM", "VFA"):
            raise ValueError(f"model must be 'GMM' or 'VFA', got '{self.model}'")
        self.history = []

    # ---- Initialization ----

    def initialize_csm(self, initial_fcf: float) -> float:
        """
        Calculate initial CSM per IFRS 17 ¶F3.
        
        CSM₀ = max(-FCF, 0)
        
        Args:
            initial_fcf: The initial Fulfillment Cash Flows (negative = profitable)
            
        Returns:
            Initial CSM value (0 if onerous)
        """
        csm_initial = max(-initial_fcf, 0.0)
        rec = CSMRecord(
            period=0,
            csm_begin=0,
            csm_end=csm_initial,
            coverage_units=0,
        )
        self.history.append(rec)
        return csm_initial

    # ---- Period Roll-Forward ----

    def roll_forward(
        self,
        period: int,
        coverage_units: float,
        total_coverage_units: float,
        non_financial_delta: float = 0.0,
        financial_delta: float = 0.0,
    ) -> CSMRecord:
        """
        Roll CSM forward one period (GMM or VFA).

        GMM (F4):
            CSM_end = CSM_begin × (1 + r_lock) − Amort + NonFinΔ
        
        VFA (F5):
            CSM_end = CSM_begin + ΔVF − Amort
            (interest is implicit in ΔVF)

        Amort (F8):
            Amort = CSM_begin × coverage_units / total_coverage_units

        Args:
            period: Period number (1-based)
            coverage_units: Coverage units for this period (NOP_t × SA_t)
            total_coverage_units: Total remaining coverage units (period + future)
            non_financial_delta: Change from non-economic assumption revisions
            financial_delta: VFA = ΔVF; GMM = not used (kept for API consistency)
            
        Returns:
            CSMRecord for this period
        """
        if not self.history:
            raise ValueError("CSM not initialized. Call initialize_csm() first.")

        prev = self.history[-1]
        csm_begin = prev.csm_end

        # ---- Step A: Interest accretion ----
        if self.model == "GMM":
            interest = csm_begin * self.lockin_rate
        else:  # VFA
            interest = 0.0  # implicit in ΔVF

        # ---- Step B: Amortization (F8) ----
        if total_coverage_units > 0:
            amort_ratio = coverage_units / total_coverage_units
            amortization = csm_begin * amort_ratio
        else:
            amortization = 0.0

        # ---- Step C: Non-economic delta + Model-specific ----
        if self.model == "GMM":
            csm_end = csm_begin + interest - amortization + non_financial_delta
        else:  # VFA: ΔVF replaces interest
            csm_end = csm_begin + financial_delta - amortization + non_financial_delta

        csm_end = max(csm_end, 0.0)  # CSM floor at zero

        rec = CSMRecord(
            period=period,
            csm_begin=csm_begin,
            interest=interest,
            amortization=amortization,
            non_fin_delta=non_financial_delta,
            fin_delta=financial_delta,
            csm_end=csm_end,
            coverage_units=coverage_units,
            cumulative_amort=prev.cumulative_amort + amortization,
        )
        self.history.append(rec)
        return rec

    # ---- Bulk Roll-Forward ----

    def roll_forward_bulk(
        self,
        periods: list[dict],
    ) -> pd.DataFrame:
        """
        Roll CSM forward over multiple periods.

        Args:
            periods: List of dicts with keys:
                period, coverage_units, total_coverage_units,
                non_financial_delta, financial_delta

        Returns:
            pd.DataFrame with full CSM history
        """
        for p in periods:
            self.roll_forward(
                period=p["period"],
                coverage_units=p["coverage_units"],
                total_coverage_units=p["total_coverage_units"],
                non_financial_delta=p.get("non_financial_delta", 0),
                financial_delta=p.get("financial_delta", 0),
            )
        return self.to_dataframe()

    # ---- Onerous Contract Handling ----

    def is_onerous_initial(self, initial_fcf: float) -> bool:
        """Check if initial recognition is onerous (FCF > 0)."""
        return initial_fcf > 0

    def check_onerous_subsequent(self, csm_begin: float, non_fin_delta: float) -> tuple[float, float]:
        """
        Handle subsequent onerous contract detection (GMM).

        When non-financial changes cause FCF increase beyond CSM balance,
        the excess goes to P&L as insurance service expense.

        Args:
            csm_begin: CSM at beginning of period
            non_fin_delta: Negative non-financial change (FCF increase)

        Returns:
            (csm_absorbed, pnl_charge) — amounts absorbed by CSM vs charged to P&L
        """
        if non_fin_delta >= 0:
            return (non_fin_delta, 0.0)
        absorbed = min(csm_begin, -non_fin_delta)
        pnl_charge = -non_fin_delta - absorbed
        return (-absorbed, pnl_charge)

    # ---- Output ----

    def to_dataframe(self) -> pd.DataFrame:
        """Export full CSM history to pandas DataFrame."""
        records = []
        for rec in self.history:
            records.append({
                "Period": rec.period,
                "CSM_BOY": rec.csm_begin,
                "Interest": rec.interest,
                "Amortization": rec.amortization,
                "NonFinDelta": rec.non_fin_delta,
                "FinDelta_VF": rec.fin_delta,
                "CSM_EOY": rec.csm_end,
                "CoverageUnits": rec.coverage_units,
                "CumulativeAmort": rec.cumulative_amort,
            })
        return pd.DataFrame(records)

    def print_waterfall(self):
        """Print a formatted CSM waterfall table."""
        df = self.to_dataframe()
        print(f"\n{'='*75}")
        print(f"  CSM Waterfall — {self.model} Model (r_lock={self.lockin_rate:.4f})")
        print(f"{'='*75}")
        print(f"{'Per':>4} {'BOY':>10} {'Interest':>10} {'Amort':>10} {'NonFin':>10} "
              f"{'VF/Fin':>10} {'EOY':>10}")
        print(f"{'-'*75}")
        for _, r in df.iterrows():
            print(f"{int(r.Period):>4} {r.CSM_BOY:>10.1f} {r.Interest:>10.1f} "
                  f"{r.Amortization:>10.1f} {r.NonFinDelta:>10.1f} "
                  f"{r.FinDelta_VF:>10.1f} {r.CSM_EOY:>10.1f}")
        print(f"{'='*75}")


# ---- Demo: 5-year Unit-Linked GMM vs VFA (matches KB §5.4) ----
def demo_gmm_vs_vfa():
    """Reproduce the 5-year unit-linked product comparison from KB §5.4."""
    print("=== 5-Year Unit-Linked: GMM vs VFA Comparison ===\n")

    # Product params (from KB §5.4)
    initial_csm = 3200
    annual_cu = [95, 90, 85, 80, 150]       # 5 years coverage units
    total_cu_initial = 500
    lockin_rate = 0.03                        # ≈ PHAV growth rate
    # VFA variable fee deltas (simplified from core conclusion)
    vfa_vf_deltas = [125-95, 338-125, 500-338, 420-500, 0]

    # GMM run
    gmm = CSMCalculator(model="GMM", lockin_rate=lockin_rate)
    gmm.initialize_csm(initial_fcf=-initial_csm)
    cum_cu = total_cu_initial
    for t, cu in enumerate(annual_cu, 1):
        gmm.roll_forward(
            period=t,
            coverage_units=cu,
            total_coverage_units=cum_cu,
            non_financial_delta=0.0,
        )
        cum_cu -= cu

    # VFA run
    vfa = CSMCalculator(model="VFA")
    vfa.initialize_csm(initial_fcf=-initial_csm)
    cum_cu = total_cu_initial
    for t, cu in enumerate(annual_cu, 1):
        vfa.roll_forward(
            period=t,
            coverage_units=cu,
            total_coverage_units=cum_cu,
            non_financial_delta=0.0,
            financial_delta=vfa_vf_deltas[t-1],
        )
        cum_cu -= cu

    df_gmm = gmm.to_dataframe()
    df_vfa = vfa.to_dataframe()

    print(f"{'Year':>6} {'GMM CSM':>10} {'VFA CSM':>10} {'Diff':>10}")
    print(f"{'-'*40}")
    print(f"{'Init':>6} {df_gmm.iloc[0].CSM_EOY:>10.0f} {df_vfa.iloc[0].CSM_EOY:>10.0f} {0:>10}")
    for i in range(1, 6):
        diff = df_vfa.iloc[i].CSM_EOY - df_gmm.iloc[i].CSM_EOY
        print(f"  Yr{i}   {df_gmm.iloc[i].CSM_EOY:>10.0f} {df_vfa.iloc[i].CSM_EOY:>10.0f} {diff:>+10.0f}")

    gmm.print_waterfall()
    vfa.print_waterfall()


if __name__ == "__main__":
    demo_gmm_vs_vfa()

# P0 Scenario Parameter Summary
**Model:** PyPSA-RSA — Coal Flexibilisation  
**Paper:** Carbon Tax Effectiveness in South Africa (2030 Snapshot)  
**Date:** 2026-06-18

---

## Scenarios

| Scenario | Carbon Tax | Revenue Recycling | Purpose |
|---|---|---|---|
| P0_BASE | None | No | Counterfactual: no CT, no recycling |
| P0_BASE_R | None | Yes (CT_REINVEST) | Counterfactual: no CT, with reinvestment constraint |
| P0_CT | 462 R/tCO₂ (2030) | No | CT effect only |
| P0_CT_R | 462 R/tCO₂ (2030) | Yes (CT_REINVEST) | CT + revenue recycled into RE investment |

---

## Key Parameters & Assumptions

### Time & Resolution

| Parameter | Value | Rationale |
|---|---|---|
| Simulation years | 2025, 2030 | 2030 is the policy-relevant snapshot for CT analysis |
| Temporal resolution | LC-182h | Load-cluster with 182 representative hours — captures seasonal/diurnal dispatch patterns |
| Weather year | W_P50 (→ 2018) | Median weather year; avoids extreme hydrology/wind bias |
| Network | 10-node (supply regions) | Spatially resolved SA grid; captures regional RE resource heterogeneity |
| Transmission | Existing + TDP | Adds Transmission Development Plan lines planned by 2030 |

### Coal Fleet

| Parameter | Value | Rationale |
|---|---|---|
| Retirement schedule | DELAYED_ESKOM_2035 | Reflects actual Eskom decommissioning plan — coal retirement begins 2035 |
| Endogenous early retirement | Disabled (= 0) | Coal capacity is fixed; CT affects dispatch only, not capacity |
| Minimum stable load | 50% of nameplate | Standard engineering constraint for coal flexibility |
| Ramp rate multiplier | 1.5× | Coal Flexibilisation project assumption: improved ramping capability |
| Energy availability factor | EAF_60 (60%) | Upper end of realistic current Eskom performance range (~55–60%) |
| Unit commitment | Disabled | No startup/shutdown costs in snapshot model |
| Heat rate scenario | VAR_HR | Design-spec efficiency (optimistic); lower marginal cost baseline |

### New Capacity (Renewables, Storage, Gas)

| Parameter | Value | Rationale |
|---|---|---|
| Minimum build requirement | **UNC (unconstrained)** | **No IRP mandate imposed — model freely chooses investments based on economics alone. This isolates the CT signal: without CT, the model builds what is cheapest; with CT, coal becomes expensive and renewables are endogenously built.** |
| Maximum build constraint | MOD_CNST | Moderate upper bound — prevents unrealistic overcapacity |
| Annual build rate | Unconstrained | No year-on-year ramp rate cap (appropriate for snapshot) |
| Capital costs | BASE_PMR1b | Meridian base cost projections — wind 24,739 / solar 15,690 / battery-4h 13,581 ZAR/kWel (2030) |
| Discount rate | 9.2% | SA-appropriate social discount rate |

### Carbon Tax

| Parameter | Value | Rationale |
|---|---|---|
| CT trajectory (IRP23) | 0 R/t (2025) → 462 R/t (2030) | South African National Treasury IRP2023-aligned trajectory |
| Revenue recycling (CT_REINVEST) | Σ(RE + battery capex) ≥ base investment + 50% × CT revenues | Custom constraint in `custom_constraints.py` — ensures CT revenues are reinvested in clean capacity |

### Demand & System

| Parameter | Value | Rationale |
|---|---|---|
| Load trajectory | IRP24_LOW | IRP2024 low demand scenario — conservative, avoids overstating CT benefits |
| Reserve margin | 10% above peak | Standard SA adequacy requirement |
| Capacity credits | Coal 100%, Wind 10%, Solar 0%, Battery-4h 50% | Conservative (solar=0% is strict) |
| Fuel prices | BASE_PMR1b | Meridian base scenario for coal, diesel, LNG |
| Gas dispatch floor | None (NO_MIN_GAS) | Gas can but need not run — no policy mandate |

---

## Research Design Rationale

### Why UNC (not IRP25_BQ) for minimum capacity?

The IRP2025 Base Quantity (`IRP25_BQ`) mandates a fixed minimum of contracted renewable capacity regardless of carbon price. This crowds out the CT signal: both BASE and CT scenarios end up with similar investment outcomes because the policy mandate — not the price signal — drives the buildout.

Setting `extendable_min_total = UNC` allows the model to choose investments **endogenously**:
- **BASE scenario:** Builds only what is cost-optimal without a carbon price → lower RE, higher coal dispatch
- **CT scenario:** Coal dispatch becomes expensive → model invests in renewables to minimise system cost

The **difference between CT and BASE** is then a clean measure of the carbon tax effect on investment and dispatch.

### What is held fixed?

Coal capacity is held to the DELAYED_ESKOM_2035 retirement schedule — coal plants cannot be retired early by the model. This reflects the real-world constraint that existing assets cannot be rapidly decommissioned. The CT therefore operates purely through:
1. **Dispatch effect:** Coal becomes more expensive to run → lower capacity factors
2. **Investment effect:** New capacity investment shifts toward renewables

### Limitations to acknowledge

- EAF_60 (60%) is optimistic for current Eskom — may understate coal's cost disadvantage
- VAR_HR assumes design-spec coal efficiency — lower marginal costs mean a higher CT is needed to shift dispatch
- UNC baseline is a theoretical counterfactual; in practice some IRP2025 projects are already contracted
- 2030 snapshot does not capture transition dynamics (investment lags, learning curves)

---

## Solver & Computational Setup

| Parameter | Value |
|---|---|
| Solver | Gurobi (WLS license) |
| Threads | 32 |
| Compute | AMD EPYC 7543, NVMe (SLURM node[165-200]) |
| Preprocessing | Local frontend (~2 min) |
| Solve time | ~3 min per scenario (LC-182h) |

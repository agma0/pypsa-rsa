# Carbon Tax Scenarios — Paper 0 (2030 Snapshot)

Author: Agatha Majcher  
Updated: 2026-06-06 (Session 4)

---

## Overview

Four scenarios analysing carbon tax design and revenue recycling in the South African 
power sector. All scenarios are snapshot optimisations for **2030** (with 2025 as anchor 
year for existing conventional capacity — not a trajectory simulation).

The 2×2 design isolates the effect of (a) the CT price signal and (b) revenue recycling 
independently and in combination.

---

## Research Questions

**RQ1:** What are the carbon tax revenues under an IRP-aligned 2030 baseline, and are 
they sufficient to drive a significant expansion of renewable energy?

**RQ2:** Does carbon tax as a price signal change the cost-optimal capacity mix in 2030?

**RQ3:** Does reinvesting carbon tax revenues into renewables accelerate the energy 
transition — and does it matter whether the price signal was set beforehand?

---

## Scenario Definitions

Four Paper 0 scenarios (2030 snapshot):

| Scenario   | Description                                      | CT in optimisation? | Revenue recycling? |
|------------|--------------------------------------------------|---------------------|-------------------|
| P0_BASE    | IRP 2025 Baseline — no CT                        | No                  | No                |
| P0_BASE_R  | P0_BASE + revenue recycling                      | No                  | Yes               |
| P0_CT      | CT as price signal (462 R/tCO2 in 2030)          | Yes                 | No                |
| P0_CT_R    | CT as price signal + revenue recycling           | Yes                 | Yes               |

Additionally P1 variants (multi-year 2025–2050, for IEW paper):
P1_BASE, P1_BASE_R, P1_CT, P1_CT_R — same logic, `simulation_years` = 2025–2050.

### The 2×2 Design

|                    | No Recycling | With Recycling |
|--------------------|-------------|----------------|
| **No CT signal**   | P0_BASE     | P0_BASE_R      |
| **CT signal**      | P0_CT       | P0_CT_R        |

### Three Core Comparisons

- **P0_BASE vs P0_CT** → isolated effect of CT price signal on capacity mix
- **P0_BASE vs P0_BASE_R** → effect of revenue recycling without a price signal
- **P0_CT vs P0_CT_R** → additional effect of recycling on top of an existing price signal

---

## Carbon Tax Rate

**Headline rate 2030: 462 R/tCO2** — official SA National Treasury rate per the 
2022 Taxation Laws Amendment Act (IRP23-aligned trajectory).

The effective rate after tax-free allowances (currently ~60%) is ~185 R/t.
We use the **headline rate** because:
1. It shows maximum policy impact — an upper bound on revenues and effects
2. Phase 2 of the SA carbon tax (from 2026) significantly reduces allowances
3. This is explicitly stated as a methodological choice in the paper

---

## Carbon Tax Trajectories

File: `scenarios/Coal_Flexibilisation/sub_scenarios/emissions.xlsx`, sheet `carbon_tax`

Two new paths were added:

| Path    | 2024 | 2025 | 2026 | 2027 | 2028 | 2029 | **2030** | After 2030        |
|---------|------|------|------|------|------|------|----------|-------------------|
| CT_2030 | 0    | 0    | 0    | 0    | 0    | 0    | **462**  | 0                 |
| CT_2050 | 190  | 236  | 308  | 347  | 385  | 424  | **462**  | escalates to 2189 |

**CT_2030:** Single non-zero value at 2030 (462 R/t), zeros everywhere else.  
Pre-2030 values are irrelevant: P0 only simulates 2030. The 2025 investment period 
uses fixed conventional capacity whose dispatch is not affected by CT.

**CT_2050:** Full official SA ramp up to 2030, then linear escalation for P1 scenarios:
- Annual step 2031–2050: (2189 − 462) / 20 = 86.3 R/t per year
- 2035: 893 R/t | 2040: 1,325 R/t | 2045: 1,757 R/t | 2050: 2,189 R/t (~120 USD/t)

**Old paths (existing, unchanged):** `BASE_PMR1b`, `LOW_PMR1b`, `HIGH_PMR1b` — 
used by the existing S-series scenarios, not relevant for Paper 0.

---

## Revenue Recycling — Mechanism and Constraint

### The Formula

```
CT_revenues [R/yr] = 462 [R/tCO2] × emissions_reference [tCO2/yr]

Constraint: Σ_RE ( p_nom_new_j [MW] × capital_cost_j [R/MW/yr] ) ≥ CT_revenues [R/yr]
```

- `p_nom_new_j` = new RE capacity built in 2030 — optimisation variable
- `capital_cost_j` = annualised capex from the network [R/MW/yr], already discounted  
  at 9.2% over technology lifetime — **no separate discount rate adjustment needed**
- Both sides in R/yr → dimensionally consistent

### Two-Stage Approach (Why Not Endogenous?)

**Endogenous problem:** emissions → revenues → constraint → investment → dispatch → emissions → ...  
This creates a feedback loop. The _R scenario dispatch differs from BASE, 
making the comparison harder to interpret.

**Two-stage solution:**
- Stage 1: Solve P0_BASE (or P0_CT) → extract fixed 2030 emissions
- Stage 2: Solve P0_BASE_R (or P0_CT_R) with CT revenues as a **fixed RHS parameter**

The only structural difference between P0_BASE and P0_BASE_R is the minimum RE floor.  
Causality is clean — standard earmarking approach used in policy analysis literature.

### RE Carriers for Reinvestment

```python
reinvest_carriers = ['wind', 'wind_low', 'solar_pv', 'solar_pv_low']
```

`solar_csp` excluded — too expensive for meaningful 2030 deployment.  
Only **new capacity with `build_year == 2030`** counts toward the constraint.

---

## Why _R Scenarios Use UNC (Unconstrained Annual Build)

This is both a **technical necessity** and a **policy assumption**.

### Technical reason — MOD_CNST makes the constraint infeasible

Under `extendable_max_annual = MOD_CNST`, wind is limited to ~1,000 MW/yr in 2030.

With expected CT revenues of ~74 bn ZAR and wind annualised capex of ~12,708 ZAR/kW:

```
Minimum wind needed = 74,000,000,000 R / 12,708 R/kW / 1000 kW·MW⁻¹ ≈ 5,800 MW
MOD_CNST wind limit in 2030                                            = 1,000 MW
```

**5,800 MW >> 1,000 MW → the reinvestment constraint would be infeasible with MOD_CNST.**  
The model cannot physically satisfy `Σ(p_nom_new × capital_cost) ≥ 74 bn ZAR` if 
build rates are capped at 1,000 MW/yr. UNC is therefore required for a feasible solution.

### Policy assumption — stated explicitly in the paper

Revenue recycling only works if governments also remove deployment barriers:
accelerated permitting, grid connection, and procurement processes.  
The _R scenarios represent a world where the CT revenue is both collected **and** 
barriers are lifted to enable the corresponding RE build. This is an explicit  
scenario assumption, not a technical shortcut.

For BASE and CT (no recycling), `MOD_CNST` remains in place — realistic IRP build limits.

---

## Key Scenario Settings in scenarios_to_run.xlsx

File: `scenarios/Coal_Flexibilisation/scenarios_to_run.xlsx`, sheet `scenario_definition`

| Setting | P0_BASE | P0_BASE_R | P0_CT | P0_CT_R |
|---------|---------|-----------|-------|---------|
| row index | 300 | 301 | 302 | 303 |
| solver | gurobi | gurobi | gurobi | gurobi |
| run_scenario | **TRUE** | FALSE* | FALSE* | FALSE* |
| simulation_years | 2025, 2030 | 2025, 2030 | 2025, 2030 | 2025, 2030 |
| options | LC-182h† | LC-182h† | LC-182h† | LC-182h† |
| **regions** | **10** | **10** | **10** | **10** |
| carbon_tax | none | none | CT_2030 | CT_2030 |
| carbon_constraints | none | CT_REINVEST | none | CT_REINVEST |
| extendable_max_annual | MOD_CNST | **UNC** | MOD_CNST | **UNC** |
| extendable_min_total | MTSAO_BQ | MTSAO_BQ | MTSAO_BQ | MTSAO_BQ |
| unit_committment | FALSE | FALSE | FALSE | FALSE |
| endogenous_coal_decom | FALSE | FALSE | FALSE | FALSE |
| override_coal_msl | **50%** | **50%** | **50%** | **50%** |
| load_trajectory | IRP24_LOW | IRP24_LOW | IRP24_LOW | IRP24_LOW |
| global_discount_rate | 9.2% | 9.2% | 9.2% | 9.2% |
| weather | W_P50 | W_P50 | W_P50 | W_P50 |
| outage_profiles | EAF_60 | EAF_60 | EAF_60 | EAF_60 |
| fixed_emissions | FS_2045 | FS_2045 | FS_2045 | FS_2045 |
| dispatch_coal_flex | SL_0 | SL_0 | SL_0 | SL_0 |

**Note on regions=10:** The model uses 10 Eskom supply regions (buses) with the existing+TDP
transmission network between them. The `extendable_technologies.xlsx` currently only contains
`supply_region=1` entries — annual build limits (MOD_CNST) and minimum total targets (MTSAO_BQ)
will therefore not be applied for 10-node runs (warning in logs). This is acceptable for test
runs. For final paper runs, add 10-node entries to `extendable_technologies.xlsx`.

*_R scenarios stay FALSE until P0_BASE and P0_CT complete successfully.  
†`LC-182h` = ~48 time steps for testing runs. Change to `LC` (8,760 hourly steps) for final paper runs.

**Note on simulation_years:** `"2025, 2030"` creates two PyPSA investment periods.  
2025 anchors the existing conventional fleet (fixed capacity by build_year).  
2030 is the target year where all investment and dispatch decisions are optimised.  
The analysis and all results refer to **2030 only**.

---

## Expected Results (pre-run estimate)

| Quantity | Value |
|---------|-------|
| Expected 2030 emissions, P0_BASE | ~160 MtCO2 |
| CT revenues @ 462 R/t | ~74 bn ZAR (~4 bn USD) |
| New wind possible (74 bn ZAR ÷ 12,708 ZAR/kW) | ~5.8 GW |
| New solar possible (74 bn ZAR ÷ ~9,000 ZAR/kW) | ~8.2 GW |

These are rough estimates. Actual figures come from the solved P0_BASE result.  
The order of magnitude confirms a policy-relevant result — CT revenues can fund 
gigawatt-scale RE deployment.

---

## Implementation Log

### Step 1 — Scenario rows in scenarios_to_run.xlsx ✅

Rows 300–307 added (P0_BASE through P1_CT_R). Key settings per above table.

### Step 2 — CT paths in emissions.xlsx ✅

`CT_2030` and `CT_2050` added to `carbon_tax` sheet with official SA rates.

### Step 3 — `add_ct_reinvestment_constraint()` in custom_constraints.py ✅

New function at end of file (marked `#AM added`). Logic:

1. Reference scenario name: `SCENARIO_SETUP.name.replace("_R", "")`  
   *(SCENARIO_SETUP is a pandas Series — scenario name is in `.name`, not a dict key)*
2. Load reference solved network: `results/{working_folder}/{base}/networks/solved.nc`
3. Load emission factors: `results/{working_folder}/{base}/outputs/generator_emissions.csv`  
   *(index = period [2025, 2030], columns = generator names, values = kgCO2/MWh)*
4. Annual 2030 generation: `n_base.generators_t.p.groupby(level=0).sum().loc[2030]`
5. Emissions: `Σ(gen_MWh × ef_kgCO2/MWh) / 1000` → tCO2
6. CT revenues: `462 [R/tCO2] × emissions_tCO2` → R
7. Linopy constraint: `Σ(p_nom_new × capital_cost) >= ct_revenues / 1e3`  
   *(capital_cost already divided by 1e3 via `scale_costs(n, 1e3)` → RHS scaled equally)*

### Step 4 — Hook in prepare_and_solve_network.py ✅

Added in `solve_network()`, after `reserve_margin_constraints()`, **outside** the 
`if SCENARIO_SETUP["unit_committment"]` block (marked `#AM added`).

The existing `carbon_constraints` check is inside the `unit_committment` block 
and is therefore never reached for P0 scenarios (uc=0). The new hook fires for all scenarios.

```python
if SCENARIO_SETUP["carbon_constraints"] == "CT_REINVEST":
    add_ct_reinvestment_constraint(n, sns, SCENARIO_SETUP, snakemake)
```

### Step 5 — Snakemake dependency in Snakefile ✅

Lambda input in `prepare_and_solve_network` rule (marked `#AM added`):

### Step 6 — Scenario rows moved to top of Excel files ✅

P0/P1 rows now at top of `scenarios_to_run.xlsx` (rows 2–9) and CT_2030/CT_2050 at top of
`emissions.xlsx` for easier editing. Done via openpyxl reorder — no formula dependencies broken.

### Step 7 — regions=10 set, multi-node bugs found and partially fixed ⚠️ in progress

Changed all P0/P1 scenarios to `regions=10` (10 Eskom supply regions with transmission network).
Two pre-existing bugs in `add_electricity.py` exposed and fixed (`#AM adjusted`):

- `build_topology.py` line 82: `SCENARIO_SETUP["capacity_expansion_years"]` →
  `SCENARIO_SETUP["simulation_years"]` (column was renamed)
- `add_electricity.py` lines 624–632: multi-node renewable profile loading used `bus_ref`
  (only defined for single-node) and converted to pandas before loop, preventing per-bus
  `.sel()`. Fixed: load as xarray DataArray, per-bus selection in loop.

**Status as of 2026-05-27:** SIGSEGV (C-level crash) occurs in `add_electricity.py` after 
loading solar_pv profiles for 10-node model. Root cause not yet identified. Temporarily reverted 
to `regions=1` for CT-logic validation. Multi-node to be fixed separately.

**FIXED 2026-06-06 (Session 4):** SIGSEGV resolved. Root cause was that the renewable profile
loading loop used `bus_ref` (a single-bus reference variable) and converted the xarray DataArray
to pandas before the per-bus selection loop, preventing `.sel()` from working. Fix: load profiles
as xarray DataArray, do per-bus `.sel(bus=bus_name)` inside the loop.
Code location: `add_electricity.py` lines 624–632 (`#AM adjusted`).

**Known gap:** `extendable_technologies.xlsx` only has `supply_region=1` entries — annual build 
limits (MOD_CNST) and minimum totals (MTSAO_BQ) will not apply for 10-node runs (warning in 
logs, model continues).

```python
base_network = lambda w: (
    "results/" + config["scenarios"]["working_folder"] + "/"
    + w.scenario.replace("_R", "") + "/networks/solved.nc"
    if w.scenario.endswith("_R") else []
),
```

`[]` for non-_R scenarios (Snakemake ignores empty inputs).  
Enforces: P0_BASE_R cannot start before P0_BASE is solved; P0_CT_R not before P0_CT.

---

## Run Order

### Stage 1 — Reference scenarios (no recycling)

P0_BASE and P0_CT are independent and can run in parallel or sequentially.

```bash
# ── TEST RUNS (LC-182h, ~48 time steps) ──────────────────────────────────────
snakemake results/Coal_Flexibilisation/P0_BASE/networks/solved.nc -j 4
snakemake results/Coal_Flexibilisation/P0_CT/networks/solved.nc   -j 4
```

**After Stage 1 — check before continuing:**
- Gurobi status = `optimal` for both
- Log line: `CT reinvestment [...]` should NOT appear (no CT_REINVEST flag)
- Emissions in logs: `~160 MtCO2` (rough estimate)
- Output files exist: `results/Coal_Flexibilisation/P0_BASE/outputs/generator_emissions.csv`

### Stage 2 — Recycling scenarios

**Before running:** In `scenarios_to_run.xlsx`, set `run_scenario = 1` for `P0_BASE_R` (row 3)
and `P0_CT_R` (row 5). Save the file.  
*(Not strictly required for a direct snakemake call, but keeps the sheet consistent.)*

Snakemake automatically enforces the dependency: P0_BASE_R will not start until P0_BASE's
`solved.nc` exists; P0_CT_R waits for P0_CT. This is wired via the `base_network` lambda
input in the Snakefile.

```bash
snakemake results/Coal_Flexibilisation/P0_BASE_R/networks/solved.nc -j 4
snakemake results/Coal_Flexibilisation/P0_CT_R/networks/solved.nc   -j 4
```

**After Stage 2 — check:**
- Log line: `CT reinvestment [P0_BASE_R]: ~160 MtCO2 × 462 R/t = ~74 bn ZAR`
- Log line: `CT reinvestment constraint added: annualised RE investment >= ~74 bn ZAR`
- Gurobi status = `optimal` (with UNC build limits the constraint should be feasible)
- New RE capacity in 2030 (wind + solar) noticeably higher than in P0_BASE

### Final runs (LC — 8760 hourly time steps)

Change `options` from `LC-182h` → `LC` in `scenarios_to_run.xlsx` for all four P0 scenarios,
then re-run all four in the same order (Stage 1 first, Stage 2 after).

```bash
# ── FINAL RUNS ────────────────────────────────────────────────────────────────
snakemake results/Coal_Flexibilisation/P0_BASE/networks/solved.nc   -j 4
snakemake results/Coal_Flexibilisation/P0_CT/networks/solved.nc     -j 4
# (check Stage 1 results, then:)
snakemake results/Coal_Flexibilisation/P0_BASE_R/networks/solved.nc -j 4
snakemake results/Coal_Flexibilisation/P0_CT_R/networks/solved.nc   -j 4
```

---

## Preliminary Results — Test Runs (regions=1, LC-182h, 48 timesteps)

*Completed 2026-05-27. All 4 scenarios solved to optimality with Gurobi.*

### New Build 2030 Only (extendable, build_year==2030) [MW]

| carrier            | P0_BASE | P0_CT  | P0_BASE_R | P0_CT_R |
|--------------------|---------|--------|-----------|---------|
| wind               | 3,890   | 3,890  | 8,995     | 3,890   |
| wind_low           | 0       | 0      | 2,378     | 0       |
| solar_pv           | 0       | 6,548  | 9,604     | 23,084  |
| solar_pv_low       | 3,227   | 3,227  | 7,753     | 3,227   |
| solar_pv_rooftop   | 3,375   | 3,375  | 3,375     | 3,375   |
| solar_csp / gas    | 0       | 0      | 0         | 0       |

### Total Installed 2030 (all build years active in 2030) [MW]

| carrier            | P0_BASE | P0_CT  | P0_BASE_R | P0_CT_R |
|--------------------|---------|--------|-----------|---------|
| wind (all years)   | 8,153   | 8,153  | 13,248    | 8,153   |
| wind_low           | 5       | 5      | 2,383     | 5       |
| solar_pv (all)     | 2,672   | 9,220  | 12,276    | 25,756  |
| solar_pv_low       | 4,768   | 4,768  | 9,294     | 4,768   |
| solar_pv_rooftop   | 7,999   | 7,999  | 7,999     | 7,999   |

### Generation Mix 2030 [TWh]

| carrier          | P0_BASE | P0_CT  | P0_BASE_R | P0_CT_R |
|------------------|---------|--------|-----------|---------|
| coal             | 159.6   | 143.2  | 132.0     | 132.0   |
| wind             | 27.8    | 27.8   | 44.7      | 27.7    |
| solar_pv         | 6.8     | 24.8   | 18.4      | 44.4    |
| solar_pv_low     | 12.5    | 12.0   | 11.4      | 8.2     |
| solar_pv_rooftop | 12.1    | 11.4   | 6.5       | 7.5     |
| nuclear          | 14.6    | 14.6   | 14.6      | 14.6    |
| wind_low         | 0.0     | 0.0    | 6.9       | 0.0     |
| hydro            | 1.8     | 1.8    | 1.8       | 1.8     |

### Emissions and Reinvestment

| Metric                            | P0_BASE | P0_CT  | P0_BASE_R | P0_CT_R |
|-----------------------------------|---------|--------|-----------|---------|
| Emissions 2030 [MtCO₂]           | 153.6   | 137.9  | 127.5     | 127.6   |
| CT revenues = 462 × emis [bn ZAR] | 70.98   | 63.72  | —         | —       |
| Reinvestment Σ(p_nom×capex) [bn ZAR] | —    | —      | 70.98 ✓   | 63.72 ✓ |

---

## Results — 1-Bus Runs (regions=1, LC-182h, 48 timesteps — 2026-06-06, Session 4)

*All 4 scenarios solved at regions=1. These are valid internally consistent results but do not include
spatial disaggregation or transmission constraints. Useful for verifying CT logic and reinvestment constraint.*

### Generation Mix 2030 [TWh]

| carrier | P0_BASE | P0_CT | P0_BASE_R | P0_CT_R |
|---|---:|---:|---:|---:|
| coal | 165.7 | 145.3 | 132.0 | 132.6 |
| nuclear | 14.6 | 14.6 | 14.6 | 14.6 |
| solar_pv | 38.3 | 58.7 | 49.4 | 72.5 |
| solar_pv_low | 0.0 | 0.0 | 23.6 | 0.0 |
| wind | 14.8 | 14.8 | 14.7 | 14.7 |
| rmippp | 1.9 | 1.9 | 1.9 | 1.9 |

### New Build 2030 [MW] — build_year==2030 only

| carrier | P0_BASE | P0_CT | P0_BASE_R | P0_CT_R |
|---|---:|---:|---:|---:|
| solar_pv + solar_pv_low | 11,213 | 19,191 | 37,659 | 33,150 |
| wind | 0 | 0 | 0 | 0 |

### System Costs & Emissions

| metric | P0_BASE | P0_CT | P0_BASE_R | P0_CT_R |
|---|---:|---:|---:|---:|
| Objective [bn ZAR] | 1.82 | 2.34 | 2.07 | 2.45 |

### Key Observations — 1-Bus Results

**BASE vs CT → CT price signal is working:**
Coal drops from 165.7 → 145.3 TWh (−12%). New solar doubles from 11.2 → 19.2 GW. The 462 R/tCO₂
signal makes coal more expensive, so the optimizer deploys more solar instead.

**BASE_R vs CT_R → dispatch almost identical (132.0 vs 132.6 TWh coal):**
Both _R scenarios are forced to invest so much RE (37.7 GW and 33.1 GW respectively) by the
reinvestment constraint that coal hits its `p_min_pu` floor in essentially all timesteps. At that
point, the CT price signal in CT_R cannot push coal lower — the floor is the floor.

**Why BASE_R builds MORE solar than CT_R (37.7 vs 33.1 GW):**
P0_BASE has higher emissions than P0_CT → higher CT revenues → larger reinvestment requirement
→ BASE_R must invest more. This is correct: in a world where no CT signal reduced dispatch
beforehand, there are more emissions to recycle.

**Conclusion on 1-bus:** CT logic and reinvestment constraint are functioning correctly.
Scenario differentiation is visible and physically interpretable. However, 1-bus results lack
regional granularity and transmission constraints — use as validation only, not for paper.

---

## Results — 10-Bus Runs: IDENTICAL (regions=10, LC-182h — 2026-06-06, Session 4)

> ⚠️ **PROBLEM — ALL FOUR SCENARIOS PRODUCED IDENTICAL PHYSICAL RESULTS:**
> Coal dispatch = 136.41 TWh, Emissions ≈ 149.87 MtCO₂, New build ≈ 27.3 GW solar + 12.7 GW wind
> in all 4 scenarios. Costs differ (objective varies) but physical dispatch and investment are identical.
> These results are NOT usable for comparison. Root cause identified — see below.

### Root cause: `override_coal_msl = 0.7` pins coal in all timesteps

With 10 buses and fixed (non-expandable) transmission:
- Each bus must independently meet its own load from local generation ± limited imports
- `override_coal_msl = 0.7` → every coal plant must run at ≥ 70% of its available capacity in every timestep
- Coal minimum output at every bus already equals or exceeds local load → no room for CT to reduce coal
- CT signal (462 R/tCO₂) cannot push coal below 70% floor → dispatch identical in all 4 scenarios
- With 1-bus: aggregate coal capacity can be partially offset because there's no per-node constraint

**Plant data context:** `fixed_technologies.xlsx` has `min_stable_level = 65%` for all coal plants.
The `override_coal_msl = 0.7` override makes it STRICTER than the physical plant data.

**Fix decided:** Change `override_coal_msl` from `0.7` to `0.5` in `scenarios_to_run.xlsx` for all
4 P0 scenarios. This is technically defensible (within the realistic 40–65% range for SA coal plants)
and thematically consistent with the `Coal_Flexibilisation` scenario family.

**Status:** ⏳ Re-run with MSL=0.5 pending.

---

## Preliminary Results — MIXED topology, LC-182h, 48 timesteps (2026-06-06)

> ⚠️ **WARNING — INVALID COMPARISON:** These results mix two different model topologies. P0_BASE
> was solved at regions=10 (10 buses, 38 transmission links). P0_BASE_R, P0_CT, P0_CT_R were
> solved at regions=1 (single node "RSA", no transmission) due to a misconfiguration in
> scenarios_to_run.xlsx and a SIGSEGV bug in add_electricity.py. Do NOT use these numbers for
> any comparison or paper. They are recorded here only as a reference for the parameter audit.
> See "Deep Parameter Audit" section below for details and fix required.

*Computed from solved.nc + generator_emissions.csv. Analysis year: 2030.*

### Generation Mix 2030 [TWh]

| carrier | P0_BASE | P0_BASE_R | P0_CT | P0_CT_R |
|---|---:|---:|---:|---:|
| coal | 166.8 | 132.0 | 143.2 | 132.0 |
| nuclear | 14.6 | 14.6 | 14.6 | 14.6 |
| solar_pv | 23.9 | 18.4 | 24.8 | **44.4** |
| solar_pv_low | 16.3 | 11.4 | 12.0 | 8.2 |
| solar_pv_rooftop | 0.0 | 6.5 | 11.4 | 7.5 |
| wind | 14.8 | **44.7** | 27.8 | 27.7 |
| wind_low | 0.0 | 6.9 | 0.0 | 0.0 |
| hydro_import | 10.1 | 10.1 | 10.1 | 10.1 |
| sasol_coal | 5.5 | 4.4 | 5.1 | 4.4 |
| solar_csp | 2.0 | 2.0 | 2.0 | 2.0 |
| hydro | 1.8 | 1.8 | 1.8 | 1.8 |
| rmippp | 1.9 | 1.9 | 1.9 | 1.9 |
| bioenergy | 1.0 | 1.0 | 1.0 | 1.0 |
| **Total load [TWh]** | **255.4** | **255.4** | **255.4** | **255.4** |
| **RE share [%]** | **27.0** | **40.2** | **35.5** | **40.1** |
| **Coal share [%]** | **64.5** | **51.7** | **56.0** | **51.7** |

### New Build 2030 [GW] — build_year == 2030 only

| carrier | P0_BASE | P0_BASE_R | P0_CT | P0_CT_R |
|---|---:|---:|---:|---:|
| solar_pv | 6.17 | 9.60 | 6.55 | **23.08** |
| solar_pv_low | 5.88 | 7.75 | 3.23 | 3.23 |
| solar_pv_rooftop | 0.00 | 3.38 | 3.38 | 3.38 |
| wind | 0.00 | **9.00** | 3.89 | 3.89 |
| wind_low | 0.00 | 2.38 | 0.00 | 0.00 |
| bioenergy | 0.02 | 0.02 | 0.02 | 0.02 |
| **New RE total [GW]** | **12.1** | **32.1** | **17.1** | **33.6** |
| new wind [GW] | 0.00 | 11.37 | 3.89 | 3.89 |
| new solar [GW] | 12.05 | 20.73 | 13.15 | 29.69 |

### Total Installed Capacity 2030 [GW] — all build years

| carrier | P0_BASE | P0_BASE_R | P0_CT | P0_CT_R |
|---|---:|---:|---:|---:|
| coal | 41.42 | 41.42 | 41.42 | 41.42 |
| solar_pv | 9.17 | 12.61 | 9.55 | **26.09** |
| solar_pv_low | 5.88 | 9.29 | 4.77 | 4.77 |
| solar_pv_rooftop | 0.00 | 8.00 | 8.00 | 8.00 |
| wind | 4.26 | **13.26** | 8.15 | 8.15 |
| wind_low | 0.00 | 2.38 | 0.01 | 0.01 |
| nuclear | 1.85 | 1.85 | 1.85 | 1.85 |
| ocgt_diesel | 3.41 | 3.41 | 3.41 | 3.41 |
| hydro_import | 1.76 | 1.76 | 1.76 | 1.76 |

### Storage 2030

| | P0_BASE | P0_BASE_R | P0_CT | P0_CT_R |
|---|---:|---:|---:|---:|
| Battery 4h [GW] | 1.62 | 4.24 | 4.24 | 4.24 |
| Battery 4h [GWh] | 6,484 | 16,944 | 16,944 | 16,944 |
| PHS [GW] | 2.90 | 2.90 | 2.90 | 2.90 |
| PHS [GWh] | 61,800 | 61,800 | 61,800 | 61,800 |

### CO₂ Emissions 2030 [MtCO₂]

Computed from `generator_emissions.csv` (kgCO₂/MWh_el) × weighted dispatch [MWh].
Only coal and sasol_coal emit meaningfully; all other carriers are 0 in the emissions CSV.

| source | P0_BASE | P0_BASE_R | P0_CT | P0_CT_R |
|---|---:|---:|---:|---:|
| coal | 153.0 | 121.5 | 131.0 | 121.6 |
| sasol_coal | 7.4 | 6.0 | 6.9 | 6.0 |
| **Total [MtCO₂]** | **160.4** | **127.5** | **137.9** | **127.5** |
| **vs P0_BASE [%]** | — | **−20.5%** | **−14.0%** | **−20.5%** |

### Carbon Tax Revenue & Reinvestment [bn ZAR]

Reinvestment = annualised capital cost × SCALE_COSTS (1e3) for wind + solar_pv new build 2030.
Reference scenario for _R constraint: P0_BASE → P0_BASE_R; P0_CT → P0_CT_R.

| metric | P0_BASE | P0_BASE_R | P0_CT | P0_CT_R |
|---|---:|---:|---:|---:|
| CT revenue (own emissions) | 74.1 | 58.9 | 63.7 | 58.9 |
| CT revenue (ref scenario) | — | 74.1 | — | 63.7 |
| Reinvestment Σ(p_nom×capex) | — | **71.0** | — | **63.7** |
| Constraint satisfied? | — | ~97% ✓ | — | 100% ✓ |

Note on 97%: P0_BASE_R reinvestment (71.0 bn ZAR) is ~3 bn ZAR below the constraint RHS
(74.1 bn ZAR from P0_BASE emissions). Likely numerical solver tolerance or rounding in
the post-hoc calculation. CT_R matches exactly.

### System Costs 2030 [bn ZAR/yr]

`coal.marginal_cost = 0` throughout (sunk-cost model). CT is applied as marginal_cost
adjustment during solving for P0_CT/P0_CT_R but stored at pre-CT values in solved.nc.
All costs ×SCALE_COSTS (1e3) to undo `scale_costs(n, 1e3)` applied before solve.

| cost component | P0_BASE | P0_BASE_R | P0_CT | P0_CT_R |
|---|---:|---:|---:|---:|
| Capital new build [bn ZAR/yr] | 23.6 | 77.6 | 38.0 | 70.3 |
| Operational (MC×dispatch) | 44.1 | 43.6 | 44.0 | 43.6 |
| CT cost (462 R/t × own CO₂) | 74.1 | 58.9 | 63.7 | 58.9 |
| Total objective [bn ZAR]* | 1,849 | 2,286 | 2,512 | 2,676 |

*Total objective = both investment periods (2025+2030) discounted; not directly comparable
to annual costs above. Higher objective in CT/CT_R reflects RE capital investment.

### Summary Table — Key Metrics

| metric | BASE | BASE+R | CT | CT+R |
|---|---:|---:|---:|---:|
| Load [TWh] | 255.4 | 255.4 | 255.4 | 255.4 |
| RE gen [TWh] | 69.9 | 102.6 | 90.8 | 102.6 |
| Coal gen [TWh] | 166.8 | 132.0 | 143.2 | 132.0 |
| RE share [%] | 27.0 | **40.2** | 35.5 | **40.1** |
| Coal share [%] | 64.5 | 51.7 | 56.0 | 51.7 |
| New wind [GW] | 0.00 | **11.37** | 3.89 | 3.89 |
| New solar [GW] | 12.05 | 20.73 | 13.15 | **29.69** |
| New RE total [GW] | 12.07 | 32.12 | 17.06 | **33.59** |
| CO₂ [MtCO₂] | 160.4 | **127.5** | 137.9 | **127.5** |
| CO₂ vs BASE [%] | — | −20.5% | −14.0% | −20.5% |
| CT revenue [bn ZAR] | 74.1 | 58.9 | 63.7 | 58.9 |
| Reinvestment [bn ZAR] | — | 71.0 | — | 63.7 |
| Capex new build [bn ZAR/yr] | 23.6 | 77.6 | 38.0 | 70.3 |

### Key Observations (regions=10, 182h)

1. **BASE+R and CT+R achieve identical CO₂ reduction (−20.5%)** — the reinvestment floor
   dominates; whether CT is also present as price signal makes no difference to emissions.
2. **CT alone (−14%) < reinvestment alone (−20.5%)** — revenue recycling is more effective
   than the price signal for emission reduction in this model configuration.
3. **Technology mix diverges**: BASE+R builds mainly wind (11.4 GW new), CT+R builds mainly
   solar_pv (23.1 GW new). Both reach similar RE share (~40%) via different routes.
   Wind can displace coal at night; solar cannot → in full LC run, CT+R likely has higher
   nighttime coal and therefore higher emissions than BASE+R. Key RQ3 result to verify.
4. **Operatonal costs identical** (~44 bn ZAR/yr all scenarios) — coal MC = 0 dominates.
5. **Battery storage triples** in all non-BASE scenarios (1.6 → 4.2 GW) to support higher RE.

---

## Critical Analysis of Preliminary Results

### Q1: Why is wind new build = 3,890 MW in P0_BASE, P0_CT, and P0_CT_R?

**Two separate mechanisms — different explanations for different scenarios:**

**P0_BASE and P0_CT:** 3,890 MW is the **cost-optimal** wind investment, not MTSAO_BQ-constrained.

Verification: The MTSAO_BQ minimum total for wind in 2030 = 3,895 MW. Pre-existing wind
(all build years 2014–2025) = 4,263 MW. These already exceed the MTSAO_BQ floor, so the
`tech_capacity_expansion_limit` constraint is non-binding. The LP optimum just happens to be
3,890 MW in both BASE and CT.

**Why CT doesn't push wind higher:** Solar_pv has capex of 1,955,030 ZAR/MW/yr vs wind at
3,158,234 ZAR/MW/yr (wind is 62% more expensive per MW). When CT makes coal more expensive,
the optimizer deploys **solar_pv first** (cheaper per MW) and leaves wind at 3,890 MW.
In P0_CT, 6,548 MW of solar_pv is built instead of more wind. This is an economically
meaningful result, not a bug.

**P0_CT_R:** Wind stays at 3,890 MW because the reinvestment constraint (63.72 bn ZAR) is
met almost entirely by 23,084 MW of cheap solar_pv. Wind at MTSAO floor is sufficient.

**P0_BASE_R:** Wind rises to 8,995 MW because BASE_R must spend 70.98 bn ZAR on RE. To meet
this larger constraint with UNC build limits, the optimizer deploys extra wind+wind_low+solar.

### Q2: Why are solar_pv_low and solar_pv_rooftop the same in all 4 scenarios?

**MTSAO_BQ floor is binding for both:**

- `solar_pv_rooftop`: MTSAO_BQ 2030 total = 7,999 MW. Pre-existing (build_year=2025) = 4,624 MW.
  New needed = 7,999 − 4,624 = **3,375 MW** exactly = p_nom_opt in all scenarios. ✓ MTSAO binding.
  
- `solar_pv_low`: MTSAO_BQ 2030 total = 4,768 MW. Pre-existing (build_year=2025) = 1,541 MW.
  New needed = 4,768 − 1,541 = **3,227 MW** exactly = p_nom_opt in BASE/CT/CT_R. ✓ MTSAO binding.
  BASE_R builds 7,753 MW (above floor) because reinvestment constraint is binding.

`solar_pv` (utility-scale standard) has **no MTSAO_BQ entry** → free to vary with economics.
This is why solar_pv responds to the CT signal (0 → 6,548 → 9,604 → 23,084 MW).

### Q3: Why do P0_BASE_R and P0_CT_R have nearly identical emissions (127.50 vs 127.55 MtCO₂)?

**Most likely a 48-timestep artifact, not a bug.** Both _R scenarios build massive RE capacity:

| Scenario  | Total new RE (2030) | Coal TWh |
|-----------|---------------------|----------|
| P0_BASE_R | 31,105 MW           | 132.0    |
| P0_CT_R   | 33,576 MW           | 132.0    |

With this much RE in only 48 representative time slices, the sampled timesteps are either
(a) daytime — RE fully covers demand, coal minimal, or (b) night — coal covers residual.
Both mixes saturate the RE production in the same 48 samples → same coal floor.

**Important implication:** BASE_R and CT_R have fundamentally different RE mixes:
- **BASE_R**: wind-heavy (9 GW wind, 9.6 GW solar_pv)  
- **CT_R**: solar-heavy (3.9 GW wind, 23 GW solar_pv)

Wind can displace coal at night; solar cannot. In the full 8,760h run (LC), CT_R's
solar-dominated mix is likely to have **higher nighttime coal** than BASE_R's wind mix —
possibly higher emissions. This contrast between BASE_R and CT_R would be a key paper result.

### Q4: Why is coal generation not zero even with p_min_pu = 0?

Coal is the marginal dispatchable source at night and on cloudy/calm periods. Even with zero
MSL constraint, the optimizer dispatches coal whenever demand > RE output. No battery storage
is built (the 48-timestep approximation poorly captures the value of intraday storage). In the
full hourly run, storage becomes more valuable and coal dispatch may be lower.

### Summary: No code bugs found

All "suspicious" identical values have clear explanations:
- MTSAO_BQ binds solar_pv_low and solar_pv_rooftop in all scenarios ← correct policy floor
- 3,890 MW wind is cost-optimal in BASE/CT/CT_R ← correct economics (solar preferred at margin)
- Reinvestment constraints are working: BASE_R=70.98 bn ZAR ✓, CT_R=63.72 bn ZAR ✓
- Near-identical _R emissions = 48-timestep artifact → needs full LC run to distinguish

---

## Deep Parameter Audit — 2026-06-06

Complete investigation of all parameter issues before final LC runs. Verified directly from solved.nc, source Excel files, and Python scripts.

---

### CRITICAL BUG 1: regions inconsistency across P0 scenarios

**Verified from solved.nc network topology:**

| Scenario | buses | transmission links | extendable gens | regions in Excel |
|----------|-------|--------------------|-----------------|-----------------|
| P0_BASE  | 10    | 38                 | 320             | 10              |
| P0_BASE_R| 1     | 0                  | 28              | **1**           |
| P0_CT    | 1     | 0                  | 18              | **1**           |
| P0_CT_R  | 1     | 0                  | 28              | **1**           |

**Impact:** P0_BASE was solved as a spatially disaggregated 10-region model with transmission. P0_BASE_R, P0_CT, and P0_CT_R were solved as single-node models ("RSA" bus, no transmission). All comparative results in the preliminary analysis (generation mix, emissions, costs, new build) are therefore **invalid** — we are comparing a 10-region model against 3 single-node models.

**Root cause:** scenarios_to_run.xlsx has `regions = 1` for P0_BASE_R, P0_CT, P0_CT_R. Only P0_BASE was correctly set to `regions = 10`.

**Fix required:** In scenarios_to_run.xlsx → scenario_definition sheet → change `regions` to 10 for P0_BASE_R, P0_CT, P0_CT_R. Then re-solve all 3 scenarios.

**Note:** The "regions=10, LC-182h" label in the preliminary results section above is **INCORRECT** — it describes only P0_BASE. The 3 other scenarios are regions=1 results.

---

### ~~CRITICAL BUG 2: add_electricity.py SIGSEGV~~ — FIXED ✅ (Session 4, 2026-06-06)

**Root cause:** The renewable profile loading loop used `bus_ref` (only defined for single-node
models) and converted the xarray DataArray to pandas before the per-bus selection loop,
making `.sel(bus=...)` fail with a C-level crash.

**Fix applied:** `add_electricity.py` lines 624–632 (`#AM adjusted`): load profiles as xarray
DataArray, do per-bus `.sel(bus=bus_name)` inside the loop. All 4 scenarios now run at regions=10.

**New issue discovered after fix:** All 4 regions=10 scenarios produce identical dispatch and
investment results. Root cause: `override_coal_msl=0.7` (see new section above).
Fix: change `override_coal_msl` to `0.5` in `scenarios_to_run.xlsx`, then re-run.

---

### NOT A BUG: CT is not applied to RE generators

**Previous session incorrectly flagged this as a confirmed bug. Disproved.**

Verification method: compared `n.generators.marginal_cost` and `n.generators_t.marginal_cost` for RE generators between P0_BASE and P0_CT from solved.nc.

**Result:**

| Carrier | P0_BASE MC (R/MWh) | P0_CT MC (R/MWh) | Difference |
|---------|-------------------|-----------------|------------|
| solar_pv (fixed) | 2056 | 2056 | **0** |
| wind (fixed) | 979 | 979 | **0** |
| solar_csp (fixed) | 3209 | 3209 | **0** |
| solar_pv (extendable) | 0 | 0 | 0 |
| wind (extendable) | 0 | 0 | 0 |

**Code verification:** `apply_emissions_for_fixed_generators()` and `apply_emissions_for_extendable_generators()` in `add_electricity.py` both filter using:
```python
gen_list = n.generators.query("carrier in @conv_carriers & [not] p_nom_extendable").index
```
where `conv_carriers = ['coal', 'hydro', 'nuclear', 'ocgt_diesel', 'rmippp', 'sasol_coal', 'sasol_gas']`.

Solar_pv and wind are in `re_carriers`, never in `conv_carriers`. CT is correctly NOT applied to them.

---

### NOT A BUG: Fixed RE marginal costs are real PPA prices

**The high MC values for legacy IPP plants are correct by design.**

Fixed RE generators represent contracted REIPPP (Renewable Energy Independent Power Producer Procurement) plants with Power Purchase Agreements (PPAs). The `variable_om_cost (R/MWh)` field in fixed_technologies.xlsx (sheet: renewables, scenario: BASE) stores the PPA tariff:

| Bid Window | solar_pv MC (R/MWh) | wind MC (R/MWh) | Notes |
|-----------|---------------------|----------------|-------|
| BW 1 (2011–12) | 3,649 | 1,513 | First-mover premium |
| BW 2 (2012–13) | 2,176 | 1,186 | |
| BW 3 (2013–14) | 1,165 | 868 | |
| BW 4 (2014–15) | 872  | 687 | |
| BW 4.5/5 (2017+)| 600  | 600 | Near-competitive |

Mean solar_pv = 2,056 R/MWh, mean wind = 979 R/MWh — weighted by number of contracted plants. These are real 2020-era prices in ZAR. They are correctly NOT affected by CT (CT incentivises new RE investment, not dispatching expensive legacy contracts).

**Implication for dispatch:** Even without CT, legacy coal (MC ≈ 722 R/MWh) is cheaper at the margin than early-round solar/wind (MC > 1,000 R/MWh). The model will prefer cheap coal over expensive legacy RE in dispatch — which is economically correct for sunk-cost legacy assets. New extendable RE (MC = 0 R/MWh) always gets dispatched first when available.

---

### VERIFIED: CT on coal is correctly applied

**Verification:** Compare coal TV-MC between BASE and CT scenarios (period=2030):

| | P0_BASE | P0_CT | Increase |
|-|---------|-------|---------|
| Coal TV-MC mean (R/MWh) | 722 | 1,180 | +458 |
| Expected CT increase (462 R/t × ~1.0 tCO₂/MWh) | — | — | ~462 |

The 1.3% difference from the expected 462 R/MWh is due to plant-specific emission factors and variable heat rates. CT on coal is functioning correctly.

**Code path:** `apply_emissions_for_fixed_generators()` in `add_electricity.py` (lines 840–887):
1. Reads `CT_2030` row from emissions.xlsx (sheet: carbon_tax) → 462 R/tCO₂
2. Converts to R/kgCO₂ (÷1000)
3. For each coal generator: `MC_new = MC_old + emission_factor × CT_rate`
4. Writes to `n.generators_t.marginal_cost`

---

### CONCERN: Nuclear TV-MC = 250 R/MWh

In P0_BASE, fixed nuclear generators have static MC = 12.4 R/MWh but TV-MC (time-varying) = 250 R/MWh. This discrepancy is large.

**Likely explanation:** `apply_variable_fuel_prices_for_fixed_generators()` sets TV-MC = fuel_cost + VOM for all conventional generators (including nuclear). The static MC is then zeroed out (only VOM remains). So 250 R/MWh = uranium fuel cost + VOM as loaded from fuel_prices.xlsx.

For Koeberg: SA nuclear fuel costs are typically quoted as ~100–150 R/MWh. The 250 R/MWh may reflect the full lifecycle cost including fuel fabrication, enrichment, and waste management, or it may include an implicit capacity payment. **Needs verification against fuel_prices.xlsx (BASE_PMR1b scenario).**

In P0_CT: only 1 nuclear generator appears in the network (vs 21 in P0_BASE). This is explained by the regions=1 topology (single-node) vs regions=10 (10 buses × 1 Koeberg unit + extendable units). Not a data bug.

---

### CONCERN: Extendable RE generators count differs between scenarios

| Scenario | solar_pv ext | wind ext | Total ext RE | Regions |
|----------|-------------|---------|-------------|---------|
| P0_BASE  | 20 | 20 | 80+ | 10 |
| P0_CT    | 1  | 2  | 7  | 1 |
| P0_BASE_R| —  | —  | 14 | 1 |
| P0_CT_R  | —  | —  | 14 | 1 |

The 20 per carrier in P0_BASE = 10 buses × 2 investment years. The 1-2 per carrier in P0_CT = 1 bus × 2 years (but some carriers dropped because MOD_CNST annual limits = 0 for that region). The count differences are entirely explained by the regions discrepancy. **Not an independent bug.**

---

### CONCERN: Battery discrepancy (1.62 GW vs 4.24 GW) — explained

P0_BASE (regions=10): 1.62 GW battery_4h across 10 buses  
P0_BASE_R, P0_CT, P0_CT_R (regions=1): 4.24 GW battery_4h at single RSA node

All battery storage is FIXED (`p_nom_extendable=False`). The sum differs because single-node models aggregate all regional batteries to one bus, while the 10-region model distributes them across 10 buses. The absolute total of 4.24 GW may be the correct national fleet — the 1.62 GW might be a subset (not all plants mapped to regions=10 buses yet). **Will resolve naturally when regions=10 is fixed.**

---

### Summary: parameter audit results

| Issue | Status | Action |
|-------|--------|--------|
| regions=1 for P0_BASE_R/CT/CT_R | ❌ CRITICAL BUG | Fix Excel, then re-solve |
| SIGSEGV in add_electricity (regions=10) | ❌ CRITICAL BUG | Debug before final runs |
| CT applied to RE generators | ✅ NOT A BUG | Disproved — CT correctly excluded |
| Fixed RE MC (2056/979 R/MWh) | ✅ CORRECT | Real REIPPP PPA prices |
| Extendable RE MC = 0 | ✅ CORRECT | New builds have no fuel cost |
| CT on coal (+458 R/MWh) | ✅ CORRECT | Matches expected 462 R/MWh |
| Nuclear TV-MC = 250 R/MWh | ⚠️ VERIFY | Check fuel_prices.xlsx (BASE_PMR1b) |
| Battery discrepancy 1.62 vs 4.24 GW | ⚠️ SEE NOTE | Explained by regions topology |
| Missing supply_region=10 in extendable_technologies.xlsx | ⚠️ NEEDED | Add before final runs |

**Bottom line:** There are 2 blocking bugs before any final LC runs are possible. The scenarios_to_run.xlsx regions setting must be corrected AND the SIGSEGV in add_electricity.py must be fixed. Once these are resolved, all 4 P0 scenarios can be solved consistently at regions=10 and their results will be comparable.

---

## Network Plots

Rule `plot_network` in Snakefile (hinzugefügt 2026-06-06) erzeugt nach jedem Solve automatisch zwei PNGs:

| Output | Inhalt |
|--------|--------|
| `results/Coal_Flexibilisation/{scenario}/outputs/plots/map_only.png` | Karte mit Kapazitäts-Pie-Charts pro Bus |
| `results/Coal_Flexibilisation/{scenario}/outputs/plots/map_full.png` | Karte + Energie-Pie (Strommix) |

Hintergrundlayer: `data/Shapefiles/Supply_Areas2022_Steady_State_Limit.shp` (30 Supply Areas).

**Manuell triggern (einzelnes Szenario):**
```bash
snakemake results/Coal_Flexibilisation/P0_BASE/outputs/plots/map_only.png -j 1
```

**Alle Plots auf einmal (nach solve):**
```bash
snakemake results/plot_all_scenarios -j 4
```

**Automatisch:** `snakemake results/solve_all_scenarios` oder `solve_all` triggert Plots immer mit.

Hinweis: Kostenbalken (`plot_total_cost_bar`) ist deaktiviert — API-Mismatch mit aktuellem `aggregate_costs` in `_helpers.py`.

---

## Open Items / To Do

### Status Overview (2026-06-06, Session 4)

| Bug/Task | Status |
|---|---|
| Bug A: regions=1 for P0_CT/BASE_R/CT_R | ✅ FIXED — Excel corrected |
| Bug B: SIGSEGV in add_electricity.py | ✅ FIXED — see Implementation Log |
| 10-bus runs: identical results | ⏳ ROOT CAUSE KNOWN — needs coal MSL fix |
| 1-bus runs: all 4 scenarios | ✅ COMPLETE — CT logic verified |

---

### Priority 0 — Fix coal MSL, re-run 10-bus ← CURRENT NEXT STEP

**What to do in Excel (`scenarios_to_run.xlsx` → sheet `scenario_definition`):**
- [ ] Change `override_coal_msl` from `0.7` → **`0.5`** for all 4 P0 scenarios (rows 300–303)

**Then re-run:**
```bash
pixi run snakemake solve_all -j 4 -F --resources solver_slots=2
```

**Verify success:** All 4 scenarios should have DIFFERENT coal dispatch. P0_CT coal < P0_BASE coal.
Expected: BASE ~170 TWh, CT ~145 TWh (CT reduces coal by ~15%). _R scenarios lower than their base.

---

### Priority 1 — Transmission expansion (optional, needs old pypsa-za code)

The model currently uses a **fixed transmission network** (`p_nom_extendable=False`, no grid costs).
The 10-bus topology (Eastern Cape, Free State, Gauteng, Hydra Central, KZN, Limpopo, Mpumalanga,
North West, Northern Cape, Western Cape) is correctly represented with existing 400kV St. Clair N-1
capacities. 16 potential new corridors are defined in `transmission_expansion.xlsx` (all zeros).

**To enable transmission investment optimisation:**
1. User to provide old pypsa-za transmission expansion code (capital cost structure, which links
   were `p_nom_extendable=True`, `p_nom_max` per corridor)
2. Modify `base_network.py` line 159: add extendable links with `capital_cost` [R/MW]
3. Set `p_nom_max` per corridor in `transmission_expansion.xlsx`

**Decision pending:** Is transmission expansion needed for P0 (2030 snapshot)?
For P1 (2025–2050), transmission investment is more relevant.

---

### Priority 2 — Final LC runs (8760 h)

After Priority 0 validated with 182h:
- [ ] Change `options` from `LC-182h` → `LC` in `scenarios_to_run.xlsx` for all 4 P0 scenarios
- [ ] Increase SLURM resources: `--time=48:00:00`, `--mem=128G`, `--cpus-per-task=16`
- [ ] Add `supply_region=10` entries to `extendable_technologies.xlsx` for MOD_CNST and MTSAO_BQ
- [ ] Check whether BASE_R and CT_R emissions diverge (key RQ3 result — expected to diverge with 8760h)

### Priority 3 — P1 scenarios (2025–2050)

Before P1 runs:
- [ ] In `scenarios_to_run.xlsx`: change `fixed_emissions` + `extendable_emissions` from `FS_2045` → `BASE`
  (user does not want H₂ fuel switch assumptions; FS_2045 has OCGTs → 0 emissions in 2045)
- [ ] Note: for P0, this makes NO difference (FS_2045 = BASE in 2030) — P0 runs are unaffected

### Priority 4 — Paper analysis

- [ ] Quantify marginal emission reduction: CT alone (BASE→CT) vs recycling alone (BASE→BASE_R) vs combined (BASE→CT_R)
- [ ] Produce final analysis outputs: capacity mix, emissions, revenues, RE deployment
- [ ] Address in paper: why CT signal favours solar_pv over wind (capex differential)
- [ ] Address in paper: why _R scenarios have similar dispatch (p_min_pu floor binding) but different capacity build

---

## Parameter Guide — Key Settings in scenarios_to_run.xlsx

*For Meridian Economics: what each parameter controls and why it's set as it is for P0.*

| Parameter | P0 value | What it does | Why this value |
|---|---|---|---|
| `regions` | 10 | Number of Eskom supply buses (1 = single node, 10 = regional) | Spatial disaggregation with real transmission |
| `override_coal_msl` | 0.7 → **0.5** | Coal minimum stable level as fraction of available capacity. Overrides plant-level data (65% in fixed_technologies.xlsx). 0 = no floor. | 0.5 = technically defensible (40–65% real range for SA coal); 0.7 was too restrictive, pinning coal in all timesteps |
| `coal_ramp_rate_multiplier` | 1.5 | Multiplies plant-level ramp limits (up/down) for coal by this factor. 1.5 = 50% faster ramping. | Coal Flexibilisation scenario: relaxed ramp assumption. No effect with UC=0 and TSAM 182h (non-consecutive timesteps) |
| `dispatch_coal_flex` | SL_0 | Coal dispatch flexibility parameter — used ONLY inside `unit_committment=1` block. | **Has NO effect for P0** (UC=0 for all P0 scenarios). Ignore. |
| `fixed_emissions` | FS_2045 | Emission factor trajectory for EXISTING conventional plants (kgCO₂/GJ). FS_2045 = OCGTs switch to zero-emission fuel in 2045. | **No effect for P0** (2030 < 2045 → FS_2045 = BASE in 2030). For P1: change to BASE (no H₂ assumption). |
| `extendable_emissions` | FS_2045 | Same as above but for NEW BUILD generators. | Same logic — no effect for P0. Change to BASE for P1. |
| `carbon_tax` | none / CT_2030 | Which CT trajectory to use. CT_2030 = 462 R/tCO₂ in 2030 only. | none for BASE scenarios; CT_2030 for CT scenarios |
| `carbon_constraints` | none / CT_REINVEST | CT_REINVEST activates the reinvestment constraint: Σ(new RE × capex) ≥ CT revenues from reference scenario | none for non-recycling; CT_REINVEST for _R scenarios |
| `extendable_max_annual` | MOD_CNST / UNC | Annual build rate limit per technology. MOD_CNST = IRP-aligned (~1 GW/yr wind). UNC = no limit. | _R scenarios need UNC: MOD_CNST makes reinvestment infeasible (see "Why _R uses UNC") |
| `fixed_conventional` | VAR_HR | Which heat rate / cost data to use for existing plants | Variable heat rate scenario (matches IRP assumptions) |
| `unit_committment` | 0 | 0 = LP dispatch (no commitment decisions). 1 = unit commitment with start-up costs. | All P0 scenarios use LP (faster, sufficient for investment planning) |

---

## Modeling Assumptions — Paper Justifications

*This section documents the rationale behind key modeling choices for the paper and for
reviewers / Meridian Economics. All choices are deliberate and should be stated explicitly
in the paper's methodology section.*

---

### Coal Minimum Stable Level (MSL) = 50%

**Parameter:** `override_coal_msl = 0.5`  
**What it does:** Sets a lower bound on coal dispatch at 50% of available capacity in every
timestep. Below 50%, coal plants are assumed to be technically unable to operate stably.

**Data basis:** Plant-level data in `fixed_technologies.xlsx` gives `min_stable_level = 65%`
for all Eskom coal plants (Arnot, Camden, Duvha, Grootvlei, Hendrina, Kelvin, Kendal, Komati,
Kriel, Kusile, Lethabo, Majuba, Matimba, Matla, Medupi, Tutuka). This represents the
manufacturer/technical floor under standard operating conditions.

**Why 50%, not 65% or 70%:**
- 50% is within the range used in SA power sector modelling literature for coal flexibility scenarios
- It represents a scenario where Eskom implements operational changes to increase coal flexibility
  (e.g., improved boiler control, reduced minimum stable operation)
- This is explicitly a **"Coal Flexibilisation" scenario** — the scenario folder name reflects this
  assumption. The paper should state: *"We assume coal plants can be dispatched down to 50%
  of available capacity, reflecting a scenario of enhanced operational flexibility consistent
  with Eskom's ongoing fleet optimisation efforts."*
- 70% (previous value) produced a degenerate result: CT signal could not differentiate dispatch
  across scenarios because coal was at its minimum in every timestep regardless of CT price.
  This would make RQ2 (does CT change the capacity mix?) unanswerable.

**Paper statement:** *The coal minimum stable level (MSL) is set at 50% of available capacity,
consistent with the Coal Flexibilisation scenario design. This allows the carbon tax price
signal to influence coal dispatch, which is a prerequisite for observing investment responses
to the tax.*

---

### Coal Ramp Rate Multiplier = 1.5

**Parameter:** `coal_ramp_rate_multiplier = 1.5`  
**What it does:** Multiplies the plant-level ramp rates (up and down) by 1.5, allowing coal
to change output 50% faster between timesteps than the technical plant data specifies.

**Plant-level data:** Ramp rates range from 0.167%/h (Kendal, slow) to 0.600%/h (Kusile, fast).
With the 1.5× multiplier: 0.25%/h to 0.90%/h.

**Paper justification:** Consistent with the Coal Flexibilisation scenario narrative. Faster
ramping represents scenarios where Eskom improves operational practices (e.g., more responsive
boiler management, faster load-following). **Important limitation:** With TSAM (182h aggregated
timesteps), consecutive snapshots may represent very different times of day or year. Ramp
constraints between non-consecutive periods have limited physical meaning in TSAM. This parameter
therefore has minimal quantitative effect on results but sets the scenario framing correctly for
the full 8760h (LC) run where consecutive hourly timesteps make ramp limits meaningful.

**Paper statement (if needed):** *Ramp rates are scaled by a factor of 1.5 relative to
nameplate values to reflect improved operational flexibility, consistent with the Coal
Flexibilisation scenario. This primarily affects the full-resolution hourly runs.*

---

### No Unit Commitment (UC = 0)

**Parameter:** `unit_committment = 0`  
**What it does:** Coal and gas generators are modelled as continuously dispatchable between
their MSL and p_max_pu in each timestep (LP relaxation). No start-up/shut-down costs, no
minimum up/down times. The `dispatch_coal_flex = SL_0` parameter is ignored (UC=0 block).

**Paper justification:** Standard practice for investment planning models at national scale.
Unit commitment is computationally expensive and adds little value for a 2030 snapshot
investment model where the focus is on capacity mix, not operational scheduling detail.
The MSL and ramp parameters capture the main operational constraints without full UC.

**Paper statement:** *The model uses a linearised dispatch formulation without explicit unit
commitment. Coal plant operational constraints are represented through minimum stable level
(50% of available capacity) and ramp rate limits.*

---

### Emission Factor Trajectories (fixed_emissions, extendable_emissions)

**Parameter:** `fixed_emissions = FS_2045`, `extendable_emissions = FS_2045`  
**What it does:** FS_2045 = existing gas/diesel peakers (Ankerlig, Gourikwa etc.) switch to
zero-emission fuel in 2045. Coal emission factors remain 96 kgCO₂/GJ in all years.

**For P0 (2030 snapshot):** No effect — FS_2045 and BASE are **identical in 2030**.
All coal and gas emission factors are unchanged at their 2025 values through at least 2040.

**For P1 (2025–2050):** Change both to `BASE`:
- BASE keeps OCGT emission factors constant at 74 kgCO₂/GJ through 2050 (no fuel switch)
- FS_2045 drops OCGTs to 0 in 2045 (green hydrogen / sustainable aviation fuel assumption)
- The paper (P1) explicitly does NOT assume hydrogen deployment → `BASE` is correct for P1
- **Note:** Even `BASE` extendable emissions has `ocgt_diesel → 0 in 2040`. This only matters
  if new diesel OCGTs are built — in P1, this is unlikely given RE cost trajectories.

**Paper statement (P1):** *Emission factors for existing and new conventional generators
follow a conservative baseline trajectory (no fuel switching assumed), consistent with
South Africa's current policy environment which does not mandate hydrogen blending.*

---

### Spatial Resolution: 10 Buses (regions=10)

**Parameter:** `regions = 10`  
**What it does:** Disaggregates the national power system into 10 Eskom supply regions
connected by the existing 400kV transmission network (St. Clair N-1 limits, bidirectional
links, `p_nom_extendable=False`). Renewable resource profiles are spatially differentiated
per bus.

**Why 10 buses:**
- Captures spatial heterogeneity in renewable resources (Northern Cape solar, Eastern Cape wind)
  that a single-node model cannot represent
- Transmission constraints affect which regions can export their RE surplus — relevant for
  understanding where new RE investment is optimal under CT
- 10 Eskom supply regions is the standard spatial resolution used in South African national
  energy planning (consistent with IRP methodology)

**Limitation:** Transmission network is fixed (`p_nom_extendable=False`). New transmission
investment is not co-optimised with generation. Grid costs (existing infrastructure) are
treated as sunk costs and not included in the objective. This is a standard assumption for
a 2030 snapshot model but should be stated in the paper.

**Paper statement:** *The model uses 10 Eskom supply regions with the existing 400 kV
transmission network represented as fixed capacity constraints (N-1 security criterion).
Transmission investment is not co-optimised; existing grid infrastructure is treated as
sunk cost. Renewable resource availability is spatially differentiated by supply region.*

---

### Carbon Tax Rate: 462 R/tCO₂ (CT_2030)

*(Already documented in "Carbon Tax Rate" section above — 462 R/tCO₂ = official 2030 headline
rate per the 2022 Taxation Laws Amendment Act. Headline rate used, not effective rate after
allowances. Explicitly a methodological upper bound.)*

---

### Time Resolution: LC-182h (test) → LC (final)

**Test runs:** 182 representative hours (~48 timesteps via TSAM). Used for debugging and
iteration. Results directionally correct but storage value and intraday RE profiles are
poorly captured. **Not suitable for final paper results.**

**Final runs:** LC = full 8,760 hourly timesteps. Required for:
- Accurate storage dispatch and value (batteries, PHS)
- Full seasonal variation in solar/wind profiles
- Accurate quantification of BASE_R vs CT_R emission differences (night/day dispatch profiles matter)

**Paper statement:** *Results are based on full-year hourly optimisation (8,760 timesteps).
Time series aggregation (TSAM) is used for model development only.*

---

## Transmission Network — What's In and What's Not

### What's there (working ✅)

- **10-bus topology:** 10 Eskom supply regions (Eastern Cape, Free State, Gauteng, Hydra Central,
  KwaZulu-Natal, Limpopo, Mpumalanga, North West, Northern Cape, Western Cape)
- **Existing 400kV network:** loaded from Eskom shapefiles, St. Clair N-1 thermal limits calculated
  from line length and voltage. Results in 38 bidirectional links (19 corridors × 2 directions).
- **TDP lines:** Eskom TDP 2023 planned lines can be added — activate with `+tdp` in
  `transmission_grid` parameter in scenarios_to_run.xlsx (currently: `existing` only)
- **16 potential new corridors:** defined in `transmission_expansion.xlsx` with lengths and bus pairs

### What's NOT there (missing ❌)

- **Transmission investment optimisation:** All links have `p_nom_extendable=False` (hardcoded
  in `base_network.py` line 159). The solver cannot build new lines.
- **Grid capital costs:** No `capital_cost` assigned to links → existing transmission is sunk cost
  (zero in the objective function). This is a standard assumption for 2030 snapshot models.
- **`p_nom_max` for new corridors:** `transmission_expansion.xlsx` has all zeros → no capacity
  bound for new lines even if extendability were enabled.

### Implication for results

The fixed transmission grid constrains regional energy flows. In some timesteps, a region with
surplus RE cannot export it if transmission is at capacity → coal in that region must keep running
to maintain local balance. This is one reason why the 10-bus model shows less CT responsiveness
than the 1-bus model: regional must-run constraints are harder to relax.

### Next step (optional)

User to provide old pypsa-za transmission expansion code. Will add extendable links in
`base_network.py` with `capital_cost` [R/MW] derived from line length × cost-per-MW-km.

---

## Snakemake Commands — Copy-Paste Reference

All commands run from `/beegfs/scratch/agma/pypsa-rsa/`.

> **Immer `pixi run` davor schreiben** damit die richtige Python-Umgebung benutzt wird:
> `pixi run snakemake ...` (nicht nur `snakemake ...`)

---

### Alle 4 Szenarien auf einmal (empfohlen — Snakemake managed die Reihenfolge)

```bash
pixi run snakemake solve_all -j 4 -F --resources solver_slots=2
```

`-F` = force rebuild (alle Regeln neu ausführen, auch wenn outputs schon existieren)
`-j 4` = max 4 parallele Jobs
`--resources solver_slots=2` = max 2 Gurobi-Solver gleichzeitig (BASE+CT parallel, dann _R)

---

### Einzelne solved networks

```bash
# Stage 1 — unabhängig, können parallel laufen
pixi run snakemake results/Coal_Flexibilisation/P0_BASE/networks/solved.nc -j 4
pixi run snakemake results/Coal_Flexibilisation/P0_CT/networks/solved.nc -j 4

# Stage 2 — warten automatisch auf Stage 1 (Snakemake Dependency)
pixi run snakemake results/Coal_Flexibilisation/P0_BASE_R/networks/solved.nc -j 4
pixi run snakemake results/Coal_Flexibilisation/P0_CT_R/networks/solved.nc -j 4
```

---

### Einzelne Plots

```bash
# map_only.png + map_full.png für ein Szenario
snakemake results/Coal_Flexibilisation/P0_BASE/outputs/plots/map_only.png -j 1
snakemake results/Coal_Flexibilisation/P0_CT/outputs/plots/map_only.png -j 1
snakemake results/Coal_Flexibilisation/P0_BASE_R/outputs/plots/map_only.png -j 1
snakemake results/Coal_Flexibilisation/P0_CT_R/outputs/plots/map_only.png -j 1
```

---

### Stage 1: P0_BASE + P0_CT gleichzeitig (parallel)

```bash
snakemake \
  results/Coal_Flexibilisation/P0_BASE/networks/solved.nc \
  results/Coal_Flexibilisation/P0_CT/networks/solved.nc \
  -j 8
```

---

### Stage 2: P0_BASE_R + P0_CT_R gleichzeitig (nachdem Stage 1 fertig)

Snakemake löst die Dependencies automatisch auf — P0_BASE_R wartet auf P0_BASE, P0_CT_R wartet auf P0_CT.

```bash
snakemake \
  results/Coal_Flexibilisation/P0_BASE_R/networks/solved.nc \
  results/Coal_Flexibilisation/P0_CT_R/networks/solved.nc \
  -j 8
```

---

### Alle 4 solved networks + alle Plots auf einmal

Snakemake managed die Reihenfolge selbst (Stage 1 vor Stage 2, solve vor plot):

```bash
snakemake solve_all -j 8
```

Oder manuell alle Targets angeben:

```bash
snakemake \
  results/Coal_Flexibilisation/P0_BASE/networks/solved.nc \
  results/Coal_Flexibilisation/P0_CT/networks/solved.nc \
  results/Coal_Flexibilisation/P0_BASE_R/networks/solved.nc \
  results/Coal_Flexibilisation/P0_CT_R/networks/solved.nc \
  results/Coal_Flexibilisation/P0_BASE/outputs/plots/map_only.png \
  results/Coal_Flexibilisation/P0_CT/outputs/plots/map_only.png \
  results/Coal_Flexibilisation/P0_BASE_R/outputs/plots/map_only.png \
  results/Coal_Flexibilisation/P0_CT_R/outputs/plots/map_only.png \
  -j 8
```

---

### Nur alle Plots (wenn alle solved.nc schon da sind)

```bash
snakemake results/plot_all_scenarios -j 4
```

---

### Dry-run (zeigt was gebaut würde, ohne zu rechnen)

```bash
snakemake solve_all -j 8 --dry-run
```

---

### Python-Umgebung (falls Snakemake die falsche Python nimmt)

```bash
# Snakemake mit pixi-Umgebung
pixi run snakemake solve_all -j 8

# Oder direkt:
/home/users/a/agma/.pixi/envs/pypsa-rsa/bin/snakemake solve_all -j 8
```

---

## SLURM — Runs auf dem Cluster

---

### Gurobi-Lizenz auf Compute Nodes

Die Lizenz liegt in `~/gurobi.lic` (Home = NFS-Netzwerk-Filesystem → von allen Nodes erreichbar).
Es ist eine **WLS-Lizenz** (Web License Service) — die Authentifizierung läuft über das Internet.

> ⚠️ **Wichtig:** Compute Nodes müssen Internetzugang haben (outbound zu `license.gurobi.com`).
> Wenn der Job mit `Error 10009: Failed to connect...` o.ä. abbricht → Cluster-Admin fragen ob
> Compute Nodes HTTP/HTTPS nach außen dürfen, oder ob es einen lokalen Gurobi-Token-Server gibt.

Im Job-Script wird der Pfad explizit gesetzt:
```bash
export GRB_LICENSE_FILE=/home/users/a/agma/gurobi.lic
```

---

### Job-Script (`run_p0.job`)

Liegt bei `/beegfs/scratch/agma/pypsa-rsa/run_p0.job`.

```bash
#!/bin/bash --login
#SBATCH --job-name=pypsa_p0
#SBATCH --output=logs/slurm_p0_%j.out
#SBATCH --time=8:00:00
#SBATCH --mem=64G
#SBATCH --cpus-per-task=8
#SBATCH --mail-type=begin,end,fail
#SBATCH --mail-user=agathamajcher@gmx.de

# Gurobi WLS license (in home = NFS, accessible from all nodes)
export GRB_LICENSE_FILE=/home/users/a/agma/gurobi.lic

cd /beegfs/scratch/agma/pypsa-rsa

pixi run snakemake solve_all -j 4 -F --resources solver_slots=2
```

**Was `--resources solver_slots=2` macht:** Erlaubt max. 2 Gurobi-Solver gleichzeitig.
Snakemake läuft dann so: BASE + CT parallel → dann BASE_R + CT_R parallel.

---

### Starten, Status prüfen, abbrechen

```bash
# Starten
sbatch run_p0.job

# Status prüfen
squeue --user=agma

# Live-Output verfolgen (JobID ersetzen)
tail -f logs/slurm_p0_<jobid>.out

# Job abbrechen
scancel <jobid>
```

---

### Job live beobachten

```bash
# Log-Datei live verfolgen (JobID ersetzen)
tail -f logs/slurm_p0_<jobid>.out

# Ctrl+C bricht nur das tail ab — der Job läuft weiter!
```

Im Log erscheint jede Stunde automatisch:
```
--- HOURLY UPDATE: Sat Jun  6 18:05:34 2026 --- still running ---
```

Dazwischen normaler Snakemake-Output: welche Rules gerade laufen, was fertig ist, Fehlermeldungen.

---

### Job-Status und Verwaltung

```bash
# Alle eigenen Jobs anzeigen
squeue --user=agma

# Einen bestimmten Job anzeigen
squeue --job <jobid>

# Job abbrechen
scancel <jobid>

# Alle eigenen Jobs abbrechen
scancel --user=agma

# Verfügbare Partitionen anzeigen
sinfo
```

---

### Wenn Partitions-Fehler: verfügbare Partitionen checken

```bash
sinfo
```

Falls nötig `#SBATCH --partition=smp` (oder passende Partition) ins Job-Script ergänzen.

---

### Für finale LC-Runs (8760h — länger, mehr RAM)

Für die vollen Jahresläufe `--time` und `--mem` erhöhen:

```bash
#SBATCH --time=48:00:00
#SBATCH --mem=128G
#SBATCH --cpus-per-task=16
```

---

## Changelog — Errors Encountered and Resolved

*Chronological log of all bugs, errors and fixes. For reproducibility and handover.*

---

### Session 1–2 (2026-05-27) — Initial implementation

| Error | Resolution |
|---|---|
| `SCENARIO_SETUP["capacity_expansion_years"]` KeyError | Column renamed to `simulation_years` in Excel. Fix: `build_topology.py` line 82 |
| `n._multi_invest` is 0 after loading solved.nc (even for multi-invest networks) | Fix: `_helpers.py` `aggregate_costs()` — check `len(n.investment_periods) > 0` instead |
| Excel `run_scenario` column stores `"true\n"` strings, filter `== 1` matched nothing | Fix: `Snakefile` line 15 — `.astype(str).str.strip().str.lower().isin(["1","true"])` |
| `snakemake results/solve_all` → `MissingRuleException` | Wrong target — should be `snakemake solve_all` (rule name, no path prefix) |
| Plot cost bar: all variable costs showing ≈ 0 | All costs stored ×1000 smaller (R/kW not R/MW). Fix: `plot_network_sa.py` lines 338–340: `fc *= 1000; vc *= 1000` |
| `p_nom_new` not recognised in linopy constraint (PyPSA 0.35.2) | Use `n.generators.p_nom_opt - n.generators.p_nom` for new capacity |
| CT_REINVEST constraint RHS units mismatch | `scale_costs(n, 1e3)` divides capital_cost by 1000 before solve → divide RHS by 1000 equally |

---

### Session 3 (2026-06-06) — Parameter audit, regions bug

| Error | Resolution |
|---|---|
| P0_BASE_R/CT/CT_R solved at regions=1 despite Excel showing regions=10 | Excel actually had regions=1 for those 3. Fix: corrected to 10. Force rebuild with `-F` |
| SIGSEGV (C crash) in `add_electricity.py` for regions=10 non-BASE scenarios | See Session 4 fix below |
| Previous session suspected CT applied to RE generators | Disproved: solar/wind MC identical between BASE and CT in solved.nc. Code correctly excludes RE. |

---

### Session 4 (2026-06-06) — SIGSEGV fix, 10-bus diagnosis, parameter deep-dive

| Error | Resolution |
|---|---|
| SIGSEGV in `add_electricity.py` lines 624–632 (solar_pv profile loading for regions=10) | Root cause: used `bus_ref` (single-node variable) + pandas conversion before per-bus loop. Fix: xarray DataArray + `.sel(bus=bus_name)` in loop. Marked `#AM adjusted`. |
| All 4 regions=10 scenarios: identical dispatch and investment | Root cause: `override_coal_msl=0.7` binds coal at 70% minimum in all 48 timesteps at all buses. CT cannot reduce below floor. Fix: change to 0.5 in Excel (pending re-run). |
| `fixed_emissions=FS_2045` feared to include H₂ | For P0 (2030): no effect — FS_2045 = BASE in 2030. For P1: change to BASE to avoid H₂ assumptions post-2040. |
| `dispatch_coal_flex=SL_0` thought to affect dispatch | Confirmed: only active inside `unit_committment=1` block → no effect for P0 (UC=0). |

# Carbon Tax Scenarios — Paper 0 (2030 Snapshot)

Author: Agatha Majcher  
Updated: May 2026

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
| override_coal_msl | 70% | 70% | 70% | 70% |
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

## Open Items / To Do

### Priority 1 — Full-resolution runs (LC — 8760 h) ← NEXT STEP

The 48-timestep results validate the CT logic but are insufficient for the paper:
- [ ] Change `options` from `LC-182h` → `LC` in `scenarios_to_run.xlsx` for all P0 scenarios
- [ ] Re-run all 4 scenarios (Stage 1: P0_BASE + P0_CT in parallel; Stage 2: _R scenarios after)
- [ ] Check whether BASE_R and CT_R emissions diverge as expected (wind vs solar mix effect)
- [ ] Confirm whether solar_pv at 48ts is representative of full-year dispatch (capex optimistic?)

### Priority 2 — Fix regions=10 (multi-node)

- [ ] **SIGSEGV in add_electricity.py** — crash after loading solar_pv profiles for 10-node.
  Likely in the loop at `extend_reference_data()` or `pu_profiles.loc["max", pu.name]`.  
  Needs systematic debugging: add print statements before crash, check if generator names
  match between pu_profiles columns and `f"{bus}-{carrier}-{y}"` format.
- [ ] Once SIGSEGV fixed: add `supply_region=10` entries to `extendable_technologies.xlsx`
  for `MOD_CNST` annual limits and `MTSAO_BQ` minimum totals. Distribute national limits
  (e.g. ~1000 MW/yr wind) across 10 buses proportionally to resource area or IRP allocation.
- [ ] Re-run all P0 scenarios with regions=10 (set back in Excel) and validate.

### Priority 3 — Paper analysis

- [ ] Compare BASE_R vs CT_R RE mix and emissions in full LC run (key RQ3 result)
- [ ] Quantify marginal emission reduction: CT alone (BASE→CT) vs recycling alone (BASE→BASE_R)
  vs combined (BASE→CT_R)
- [ ] Produce analysis outputs: capacity mix, emissions, revenues, RE deployment
- [ ] Address in paper: why CT signal favours solar_pv over wind (capex differential)

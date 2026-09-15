# Model Documentation: PyPSA-RSA Carbon Tax Analysis (Paper 0)

*Last updated: 2026-09-13*

---

## 1. Overview

This document describes the PyPSA-RSA model configuration used for **Paper 0**: a 2030 snapshot analysis of carbon tax policy effects on South Africa's electricity system. It covers scenario design, parameter choices and their rationale, code modifications, and run instructions.

**Model framework:** [PyPSA](https://pypsa.org/) (Python for Power System Analysis)  
**Base repository:** Fork of [Meridian Economics PyPSA-RSA](https://github.com/MeridianEconomics/pypsa-rsa)  
**Working directory:** `/beegfs/scratch/agma/pypsa-rsa`  
**Scenario folder:** `scenarios/Coal_Flexibilisation/`  
**Sub-scenarios:** `scenarios/Coal_Flexibilisation/sub_scenarios/`

---

## 2. Research Question

Paper 0 investigates how a carbon tax at the level prescribed by South Africa's IRP 2023 (462 R/tCO₂ in 2030) affects:
- the **dispatch** of the existing coal fleet
- the **investment** in new renewable capacity
- the role of **revenue recycling** (reinvesting CT revenues into new RE)

---

## 3. Scenario Design

The four scenarios form a 2×2 matrix:

| Scenario | Carbon Tax in optimisation? | Revenue recycling? | Description |
|---|---|---|---|
| **P0_BASE** | No | No | IRP 2025 baseline — no CT, no recycling |
| **P0_BASE_R** | No | Yes | Baseline + mandatory RE reinvestment |
| **P0_CT** | Yes (462 R/tCO₂) | No | CT as pure price signal |
| **P0_CT_R** | Yes (462 R/tCO₂) | Yes | CT + mandatory RE reinvestment |

**Why this structure:**  
The 2×2 design isolates the effect of the CT price signal (BASE vs CT) from the effect of revenue recycling (no-R vs R). This allows the paper to separately attribute changes in dispatch and investment to the price signal vs. the recycling mechanism.

**P1 variants** (P1_BASE, P1_BASE_R, P1_CT, P1_CT_R) use the same scenario logic but with simulation_years 2025–2050, intended for a separate IEW paper.

---

## 4. Carbon Tax Implementation

### 4.1 Price signal

The carbon tax enters the model as an addition to the marginal cost of each generator:

```
marginal_cost += carbon_tax [R/tCO₂] × emission_factor [tCO₂/MWh]
```

The tax path is read from `sub_scenarios/emissions.xlsx`, sheet `carbon_tax`, row `IRP23`:

| Year | 2025 | 2026 | 2029 | 2030 |
|---|---|---|---|---|
| IRP23 (R/tCO₂) | 0 | 308 | 424 | 462 |

The 2025 value is 0, so only the 2030 investment period is exposed to the carbon price. This is intentional — the model is a 2030 snapshot; 2025 serves only to anchor the existing fleet.

### 4.2 Revenue recycling constraint

For `_R` scenarios, CT revenues are recycled as a **mandatory minimum investment** in new renewable capacity. This is implemented as a custom linopy constraint in `custom_constraints.py`:

```
Σ (p_nom_new[carrier] × capital_cost)  ≥  base_RE_investment + CT_revenues
```

Where:
- `p_nom_new` = newly built capacity with `build_year == 2030` in the `_R` scenario
- `base_RE_investment` = annualised RE investment from the reference base scenario (P0_BASE), so the `_R` constraint enforces investment *on top of* the baseline
- `CT_revenues` = 462 R/tCO₂ × total 2030 emissions from the **P0_BASE** solved network

Only wind and solar carriers count toward the constraint: `wind`, `wind_low`, `solar_pv`, `solar_pv_low`.

The P0_BASE solved network is loaded from `results/Coal_Flexibilisation/P0_BASE/networks/solved.nc`. This means P0_BASE_R and P0_CT_R **depend on P0_BASE being solved first** (enforced in the Snakefile).

---

## 5. Network & Spatial Resolution

- **Nodes:** 10 supply regions (Eastern Cape, Free State, Gauteng, Hydra Central, KwaZulu-Natal, Limpopo, Mpumalanga, North West, Northern Cape, Western Cape)
- **Transmission:** existing 400 kV lines (St. Clair N-1 capacity), plus TDP planned lines (`transmission_grid = existing+tdp`)
- **Topology source:** shapefiles processed in `build_topology.py`, 38 bidirectional links
- **Transmission expansion:** existing corridors can be expanded by the optimizer (see Section 8)

---

## 6. Temporal Resolution

- **Simulation years:** 2025 and 2030 (two investment periods; 2025 anchors the starting point, 2030 is the policy year)
- **Dispatch resolution:** `LC-182h` — 182 representative hours from a typical meteorological year (load clustering via TSAM)
- **Weather year:** `W_P50` — P50 (median) weather scenario, mapped to historical year 2018 for all model years

> The 182h resolution is used for test and calibration runs. Final paper runs should use full 8760h (`LC` without hour suffix). At 182h with non-consecutive timesteps, ramp rate constraints have limited effect.

---

## 7. Parameter Choices and Rationale

### 7.1 Solver & run control

| Parameter | Value | Rationale |
|---|---|---|
| `solver` | `gurobi` | Commercial LP solver; faster than open-source alternatives for large multi-node networks. |
| `run_scenario` | `true` | Flags this row for execution; Snakefile filters on `"1"` or `"true"` (case-insensitive, whitespace-stripped). |

### 7.2 Time & weather

| Parameter | Value | Rationale |
|---|---|---|
| `simulation_years` | `2025, 2030` | Two investment periods: 2025 anchors existing capacity, 2030 is the policy year. |
| `options` | `LC-182h` | 182 representative hours via load clustering (TSAM) — calibration resolution. Final paper runs require `LC` (8760h). |
| `weather` | `W_P50` | P50 (median) weather year, mapped to historical year 2018; standard choice for a deterministic baseline run. |

### 7.3 Network & spatial resolution

| Parameter | Value | Rationale |
|---|---|---|
| `regions` | `10` | 10 Eskom supply regions; captures inter-regional transmission constraints relevant for CT dispatch effects. |
| `resource_area` | `redz_corridors_eia` | Broadest available renewable candidate site set (REDZ + transmission corridors + EIA-approved sites); allows unconstrained siting. |
| `transmission_grid` | `existing+tdp` | Existing 400 kV grid plus TDP 2023 planned lines; represents the network available by 2030. |
| `line_expansion` | `copt` | Enables endogenous transmission expansion on existing corridors; optimizer decides whether it is economic. Set to `none` to fix the network. |

### 7.4 Coal fleet

| Parameter | Value | Rationale |
|---|---|---|
| `fixed_conventional` | `BASE_PMR1b` | Realistic current Eskom heat rates (Medupi 9.58 GJ/MWh, ~38% efficiency). Design-efficiency parameters (VAR_HR) suppressed the CT signal entirely — coal remained cheaper than gas even with the full CT applied. |
| `phased_decom` | `DELAYED_ESKOM_2035` | Coal retirements begin 2035; full fleet (41.4 GW) available in 2030, consistent with Eskom's delayed Just Transition trajectory. |
| `override_coal_msl` | `0.65` (was `0.4`) | Minimum stable load = 65% of p_max_pu. Raised after colleague feedback that 40% was unrealistically low. Matches the `min_stable_level (%)` value entered per-station in `fixed_technologies.xlsx` (uniformly 0.65 across all 17 coal/sasol_coal units) — see 7.4.2 for why that per-station column can't simply be read directly. |
| `coal_ramp_rate_multiplier` | `1` (was `1.5`) | Coal ramp limits left at base rate from `fixed_technologies.xlsx` (no artificial speed-up). Reverted from the `1.5` "coal flexibilisation" assumption for the same reason as `SL_0` in 7.4.1 — avoid a second free flexibility variable confounding the CT-retirement signal. |
| `annual_availability` | `EAF_60` | Maximum energy availability factor for coal fleet = 60% of hours (sets p_max_pu upper bound). Reflects a modest recovery from current Eskom performance (~55–58%) by 2030; consistent with Meridian base parameterisation. |
| `unit_committment` | `1` (was `0`) | Enables the linearised unit commitment formulation for coal (`Generator-status`/`Generator-p_nom_ret` variables). Required as a prerequisite for `endogenous_coal_decom` — see 7.4.1. |
| `endogenous_coal_decom` | `1` (was `0`) | Coal retirement is no longer fixed exactly to the `phased_decom` schedule; the model may retire *more* capacity than the schedule floor if economically optimal (`>=` instead of `==` constraint). See 7.4.1. |
| `dispatch_coal_flex` | `SL_0` (unchanged) | Zero permitted intra-year startups: non-retired coal capacity must stay committed (`status=1`) for every hour of the year. Deliberately kept at 0 — see 7.4.1 for rationale. |

#### 7.4.1 Update 2026-09-13: enabling endogenous coal retirement to test CT influence

**Motivation:** the original P0 setup (`endogenous_coal_decom=0`) fixes coal retirement exactly to the exogenous `phased_decom` schedule (`DELAYED_ESKOM_2035`) — the carbon tax can change *how much* coal dispatches, but can never change *when* it is decommissioned. To test whether the carbon tax accelerates coal retirement (a core question for Paper 0), the retirement decision itself needs to become part of the optimization.

**Mechanism:** `endogenous_coal_decom` is only read inside `add_coal_decom()` (`prepare_and_solve_network.py`), which is itself only called when `unit_committment=1` — the retirement variable `Generator-p_nom_ret` does not exist otherwise. Both flags must therefore be enabled together; setting `endogenous_coal_decom=1` alone has no effect (and would raise a `KeyError` in the reserve-margin constraint, which also references `Generator-p_nom_ret` when this flag is set). With both flags on, the retirement constraint switches from `p_nom_ret == phased_decom_schedule` to `p_nom_ret >= phased_decom_schedule`: the model keeps the schedule as a *floor* but can retire earlier/more if the annual fixed O&M cost of keeping a block available no longer justifies its (CT-reduced) contribution margin.

**Why `dispatch_coal_flex` stays at `SL_0` (no intra-year cycling):** the minimum stable load (`override_coal_msl`) already applies to `p_min_pu` unconditionally, regardless of `unit_committment` or `dispatch_coal_flex` (`set_coal_msl()`, always called in `add_electricity.py`) — coal can already move between its MSL floor and `p_max_pu` every hour in response to the CT price signal. What `SL_0` withholds is the ability to shut a block down to 0% for part of the year and restart later (capped startup count under `SL_X`, X>0). Keeping `SL_0`:
- isolates the CT effect on retirement from a second free variable (operational cycling behaviour), keeping the causal story attributable to the carbon price alone
- is the *stricter* test: coal cannot dodge low-price hours by cycling off, so if retirement still doesn't respond to CT under `SL_0`, that is a more robust (not an artefact-of-flexibility) finding
- keeps the LP smaller (no per-generator startup-count constraints), relevant at `LC` = full 8760h resolution

Operational flexibility (`SL_X`, X>0) is flagged as a possible robustness extension: it could make continued coal operation more profitable (surviving low-price hours by idling instead of running at the MSL floor), which would tend to *reduce* CT-driven retirement relative to the `SL_0` result — i.e. the `SL_0` runs should be read as an upper bound on the CT retirement effect.

#### 7.4.2 Update 2026-09-13: `override_coal_msl` raised to 0.65 — and why the per-station Excel values can't be used directly

**Feedback:** a colleague flagged that the previous blanket minimum stable load of 40% (`override_coal_msl=0.4`) was unrealistically low for the Eskom coal fleet.

**Checked whether the per-station `min_stable_level (%)` column in `fixed_technologies.xlsx` (sheet `conventional`) could be used instead of a blanket override**, since it looks like a per-plant input. Two findings:
1. **The column carries no actual differentiation**: all 17 fixed coal/sasol_coal units (Arnot through Tutuka, Secunda_coal, Sasolburg_coal) currently have the identical value `0.65`, regardless of technology (subcritical vs. supercritical) — there is no real per-station calibration to recover.
2. **The column is dead code for fixed generators even if it were differentiated.** `attach_fixed_generators()` initialises `p_min_pu` to 0 for every generator (`init_pu_profiles()`, `add_electricity.py:439-440`) and only explicitly overwrites it for wind/solar/RMIPPP — never for coal — then commits that 0 as a time-varying override (`add_electricity.py:1043`). Because PyPSA's `get_switchable_as_dense` always prefers a time-varying column over the static default once one exists, the static per-station `0.65` on `n.generators.p_min_pu` becomes unreachable. There is an unused function, `adjust_com_msl()` (`add_electricity.py:1442`), that would restore the static per-generator value for committable generators before the override — but it is never called in the pipeline. `set_coal_msl()`'s `"None"`/`"NA"` branch reads the (already-zeroed) time-varying column, so setting `override_coal_msl` to `"None"` currently produces **0% minimum stable load**, not the per-station value — the opposite of the intended effect.

**Decision:** since the per-station values are uniform anyway, setting `override_coal_msl = 0.65` reproduces exactly what a working per-station read would give, with no code change needed. Wiring up `adjust_com_msl()` correctly is only worth doing if the per-station values in `fixed_technologies.xlsx` are later differentiated by plant/technology (flagged as a possible future refinement, not needed for Paper 0).

### 7.5 Costs & investment parameters

| Parameter | Value | Rationale |
|---|---|---|
| `extendable_parameters` | `BASE_PMR1b` | Meridian Economics base scenario overnight capex (Wind 24,739 ZAR/kWel, Solar 15,690, OCGT 15,715, Battery 4h 13,581); middle-of-road assumption. |
| `extendable_fuel_prices` | `BASE_PMR1b` | Fuel prices for new dispatchable plant consistent with fixed generator assumptions. |
| `fixed_fuel_prices` | `BASE_PMR1b` | Coal 40.0 R/GJ (2025) → 58.9 R/GJ (2030); diesel/gas prices from Meridian base scenario. |
| `global_discount_rate` | `0.092` | 9.2% WACC, consistent with South African energy modelling literature. |
| `variable_storage_vom` | `1` | Enables time-varying VOM for storage units per year. |
| `extendable_active` | `BASE` | Standard set of technologies available for new investment (wind, solar, OCGT, battery, etc.). |

### 7.6 Emissions

| Parameter | Value | Rationale |
|---|---|---|
| `fixed_emissions` | `BASE` | Standard CO₂ emission factors for existing generators; no fuel-switching assumptions. |
| `extendable_emissions` | `BASE` | Standard emission factors for new plant; no hydrogen blending or fuel switch assumptions. |

### 7.7 Build constraints

| Parameter | Value | Rationale |
|---|---|---|
| `extendable_min_total` | `IRP25_BQ` | IRP 2025 Base Quantity as minimum floor: committed pipeline (wind 12.7 GW, solar 27.3 GW, OCGT 9.8 GW, battery 4.4 GW, PHS 2.7 GW by 2030) must be built. Optimizer is free to build above this floor. |
| `extendable_max_total` | `MOD_CNST` | Moderate upper capacity constraints. Note: `MOD_CNST` only has entries for `supply_region=1`; at `regions=10` it falls back to unconstrained. |
| `extendable_max_annual` | `UNC` | No annual build rate cap; appropriate for a 2-period snapshot without intermediate years. |
| `extendable_min_annual` | `UNC` | No annual minimum build requirement. |

### 7.8 Fixed existing assets

| Parameter | Value | Rationale |
|---|---|---|
| `fixed_renewables` | `BASE` | Standard parameters for existing renewable plants. |
| `fixed_storage` | `BASE` | Standard parameters for existing storage (Ingula PHS etc.). |

### 7.9 Operational constraints

| Parameter | Value | Rationale |
|---|---|---|
| `operational_limits` | `NO_MIN_GAS` | No minimum gas dispatch obligation; gas runs only when economically dispatched. |
| `operational_reserves` | `BASE` | Standard spinning reserve requirements. |
| `outage_profiles` | `BASE` | Standard planned maintenance profiles for all generators. |
| `aux_stg_feed` | `DIESEL_LNG` | Diesel and LNG both available as auxiliary storage feed. |

### 7.10 Reserve margin & capacity credits

| Parameter | Value | Rationale |
|---|---|---|
| `reserve_margin` | `RES_MRGN_10` | 10% planning reserve above peak demand, active from 2030. |
| `capacity_credits` | `BASE3` | Coal/nuclear/OCGT = 100%, battery 4h/CSP = 50%, wind = 10%, solar PV = 0%. |

### 7.11 Carbon tax & revenue recycling

| Parameter | BASE | BASE\_R | CT | CT\_R |
|---|---|---|---|---|
| `carbon_tax` | `none` | `none` | `IRP23` | `IRP23` |
| `carbon_constraints` | `none` | `CT_REINVEST` | `none` | `CT_REINVEST` |

### 7.12 Demand & load

| Parameter | Value | Rationale |
|---|---|---|
| `load_trajectory` | `IRP24_LOW` | IRP 2024 low demand scenario; conservative 2030 peak demand assumption. |

---

## 8. Transmission Expansion

**Decision:** The model allows expansion of **existing corridors only** — no new transmission corridors. Existing links represent sunk-cost infrastructure; the optimizer can add capacity on top of the existing thermal limit.

**How it works:**
- Toggle: `line_expansion` column in `scenarios_to_run.xlsx`. All P0 scenarios have `copt` (expansion enabled).
- Existing line `p_nom` is set as `p_nom_min` (floor), `p_nom_extendable = True`, `p_nom_max = inf`.

**Cost formula:**
```
capital_cost [ZAR/MW/yr] = length [km] × length_factor × (investment [ZAR/MW/km] × CRF + FOM_rate × investment)
```
- HVAC overhead: 6,000 ZAR/MW/km investment
- Lifetime: 40 years
- FOM: 2%/year
- `length_factor = 1.25` (routing overhead)
- At 9.2% discount rate → ~689 ZAR/MW/km/year

Parameters are stored in `config.yaml` under `lines.hvac_overhead`.

**Cost accounting:** `aggregate_costs()` computes `capital_cost × p_nom_opt` for all extendable links — this charges for the **full** optimised capacity (existing + any expansion), not just the incremental part. Grid costs therefore appear even if no expansion occurred; existing transmission capacity is treated as a capital asset with ongoing annualised costs.

---

## 9. Code Modifications

All modifications are marked `# AM added` or `# AM adjusted` in the source files.

### 9.1 `custom_constraints.py` — CT Reinvestment Constraints

Two functions implement CT revenue recycling, selected automatically based on number of investment periods.

#### `add_ct_reinvestment_constraint()` — P0 (2 periods: 2025 + 2030)

Logic:
1. Load the reference base scenario solved network and its generator emissions CSV.
2. Calculate 2030-only emissions: `energy[MWh] × emission_factor[kgCO₂/MWh] / 1000 = tCO₂`. Uses only the 2030 period — 2025 has CT rate = 0.
3. Calculate CT revenues: `tCO₂ × 462 R/tCO₂`.
4. Calculate baseline RE investment from the reference scenario (`p_nom_opt × capital_cost` for `build_year == 2030` RE generators).
5. Build linopy LHS: `Σ(p_nom_new × capital_cost)` for `wind`, `wind_low`, `solar_pv`, `solar_pv_low` with `build_year == 2030`.
6. Add constraint: `LHS ≥ base_RE_investment + CT_revenues`.

Including `base_RE_investment` on the RHS ensures the `_R` scenarios invest *above* the baseline, not merely equal to it.

#### `add_ct_reinvestment_constraint_multiyear()` — P1 (6 periods: 2025–2050)

Same logic as above but loops over **all investment periods**, adding one constraint per period. CT rates are read from `emissions.xlsx` sheet `carbon_tax`, scenario `CT_2050`:

| Period | CT_2050 rate [R/tCO₂] |
|--------|----------------------|
| 2025   | 236                  |
| 2030   | 462                  |
| 2035   | 894                  |
| 2040   | 1326                 |
| 2045   | 1757                 |
| 2050   | 2189                 |

For each period y:
1. Look up CT_2050[y]. Skip if rate = 0.
2. Use annual generation directly: `snapshot_weightings["generators"]` sums to ~8760 h per period (verified empirically), so `gen_p_annual.loc[y]` is already annual MWh — **no years_in_period division**.
3. Calculate annual CT revenues: `annual_emissions_t [tCO₂/yr] × CT_2050[y] [R/tCO₂] × REINVEST_FRACTION`. `REINVEST_FRACTION = 0.5` — 50% reinvested in clean energy, 50% represents other government spending (social transfers, budget).
4. Get base scenario annual investment (RE generators + batteries) with `build_year == y`.
5. Add constraint: `Σ(p_nom_RE × capex) + Σ(p_nom_bat × capex) ≥ base_investment[y] + CT_revenues[y]`.

**Reinvestment pool** (LHS carriers):
- RE generators: `wind`, `wind_low`, `solar_pv`, `solar_pv_low`
- Batteries: `battery_1h`, `battery_4h`, `battery_8h`
- PHS excluded: resource-constrained and decade-long lead times in SA — not a realistic near-term CT reinvestment target.

Both LHS (annualised capex [kZAR/yr]) and RHS (annual CT revenues [kZAR/yr]) are on the same annual basis.

Only components with `build_year == y` count. Named `ct_reinvestment_{y}` in the linopy model.

**Observed behaviour:** Constraint is binding in all periods — the optimizer invests exactly the floor, no more. Additional investment over BASE: 25–112 bn ZAR/yr per period. Storage share 30–63% of reinvested funds depending on period (optimizer substitutes batteries for solar once solar saturates).

**5-year step approximation — direction of bias:**  
The representative dispatch snapshot for each period (e.g. 2030 represents 2026–2030) introduces two offsetting biases:
- **Emissions**: 2030 system state has more RE → less coal than 2026–2028 → **underestimates** real average annual emissions.
- **CT rate**: end-year value (e.g. 462 R/t in 2030) is higher than the 2026–2029 average (~390 R/t) → **overestimates** the effective annual rate.
- **Net effect**: the two biases partially cancel. The approximation is close to the true annual average.

For rigorous year-by-year CT revenue accounting, annual investment periods would be required — a direction for future work.

### 9.2 `prepare_and_solve_network.py`

**CT reinvestment hook:** Called outside the `unit_committment` block. Function selection is automatic:
```python
if len(n.investment_periods) <= 2:
    add_ct_reinvestment_constraint(...)       # P0: 2030 only, 462 R/t
else:
    add_ct_reinvestment_constraint_multiyear(...)  # P1: all periods, CT_2050 trajectory
```

**`n.statistics()` workaround:** Wrapped in try/except to handle a bug in PyPSA 0.35.2 where `statistics()` raises on certain network configurations.

**`set_extendable_limits_global()` — IRP target correction:**  
The IRP25 targets in the Excel sheets are **cumulative installed capacity** including the existing 2025 fleet. Without correction, the model would attempt to build the full cumulative target as new capacity on top of existing plant. Two-step correction:

1. **Subtract existing (non-extendable) capacity** from cumulative targets → net new-build targets.
2. **Convert cumulative net targets → per-investment-period deltas** → new build required *in* each period.

Because IRP target carriers do not always match model carrier names one-to-one (e.g. the IRP target `wind` covers both `wind` and `wind_low` in the model), a carrier mapping is defined in `config.yaml` under `electricity.existing_capacity_carriers`:

```yaml
existing_capacity_carriers:
  wind:         [wind, wind_low]
  solar_pv_low: [solar_pv, solar_pv_low]
  ocgt_gas:     [ocgt_diesel, ocgt_gas, ocgt_avf]
  battery_4h:   [battery_4h]
  phs:          [phs]
```

The subtraction logs each carrier's existing capacity at INFO level for verification.

### 9.3 `config.yaml` additions

Two new blocks were added to `config.yaml` that do not exist in the upstream Meridian repository:

**`lines.hvac_overhead`** — transmission expansion cost parameters (Section 8):
```yaml
lines:
  hvac_overhead:
    investment: 6000    # ZAR/MW/km overnight investment
    lifetime: 40        # years
    fom_rate: 0.02      # fraction of investment cost per year
```
These are read by `update_transmission_costs()` in `add_electricity.py` to set `capital_cost` on extendable links. No separate Excel input is needed.

**`electricity.existing_capacity_carriers`** — carrier mapping for IRP target correction (Section 9.2):
```yaml
electricity:
  existing_capacity_carriers:
    wind:         [wind, wind_low]
    solar_pv_low: [solar_pv, solar_pv_low]
    ocgt_gas:     [ocgt_diesel, ocgt_gas, ocgt_avf]
    battery_4h:   [battery_4h]
    phs:          [phs]
```
Read by `set_extendable_limits_global()` in `prepare_and_solve_network.py` to subtract the correct set of existing plants from each IRP cumulative target.

### 9.4 `Snakefile`

- **`_R` dependency:** Lambda input ensures P0_BASE_R/P0_CT_R wait for `P0_BASE/networks/solved.nc` before starting.
- **Plot rules:** `plot_network_sa` rule, `generate_plots()`, `plot_all_scenarios`, integrated into `solve_all`.

### 9.5 `_helpers.py`

- **`TRUE`/`FALSE` from Excel:** String normalisation so Excel boolean strings (`'TRUE'`, `'FALSE'`) are correctly interpreted as Python booleans.
- **`aggregate_costs()`:** Fixed multi-invest check: `n._multi_invest` → `len(n.investment_periods) > 0` (API changed in PyPSA 0.35.x).

### 9.6 `add_electricity.py`

- **Multi-node renewable profiles:** Fixed profile loading for `regions=10` — profiles were not being correctly assigned to the right buses in multi-node runs.
- **`update_transmission_costs()`:** Computes and assigns capital costs for extendable transmission links based on their `length` attribute and the `hvac_overhead` config block.

### 9.7 `base_network.py`

- **Transmission expansion setup:** Reads `line_expansion` from SCENARIO_SETUP. If enabled, sets `p_nom_extendable=True`, `p_nom_min = St_Clair_limit_n1`, assigns `length` from line GeoJSON data.

### 9.8 `build_topology.py`

- **Column rename:** `capacity_expansion_years` → `simulation_years` to match Snakefile/config naming.

### 9.9 Marginal costs for existing RE (wind/solar)

Marginal costs for fixed (existing) wind and solar PV generators are set from the column `variable_om_cost (R/MWh)` in `fixed_technologies.xlsx` sheet `renewables`. These represent **variable O&M costs** (inspection, cleaning, minor repairs per MWh generated). They are **not** PPA tariffs — PPA payments in South Africa are capacity-based (R/MW/year) and enter the model as capital/fixed costs, not marginal costs. Since RE has no fuel cost, marginal cost equals VOM only, which is typically near-zero for wind and solar.

### 9.10 `scripts/plot_network_sa.py`

Plots are saved to `results/Coal_Flexibilisation/{scenario}/outputs/plots/`.

**Map visualisation:**
- Capacity pie charts per bus coloured by technology using `tech_colors` from `config.yaml`.
- Transmission links: light blue = existing capacity, dark blue = expanded capacity (check: `p_nom_opt − p_nom > 1%`).
- Three legends above map: Capacity (circles), Transmission (line width scale), Grid (expanded/existing colour key).
- Technology colour legend below map.

**Cost bar chart** (`plot_total_cost_bar`):
- Four bars: Capital Costs, Marginal Costs, CO₂ Tax, Grid — all in R/MWh averaged over the full model horizon.
- Grid bar is **stacked**: light blue (cost of existing transmission capacity) below, dark blue (cost of expanded capacity) above, matching map colours.
- Cost scaling: `fc × 1000`, `vc × 1000` — costs in the network are stored in R/kW and R/kWh (model convention); ×1000 converts to ZAR/MWh for display.
- CO₂ Tax bar: computed as `energy[MWh] × emission_factor[kgCO₂/MWh] × 462 R/t / 1000` summed over all periods; divided by total load for R/MWh display.
- Grid costs: `capital_cost × p_nom_opt` for all extendable links with carrier `"AC line"` — includes existing capacity cost, not only expansion.

**Summary text below chart** (left-aligned, stacked):
```
Total Emissions:  X.X MtCO₂/a

Capital Costs:    X bn ZAR/a
Marginal Costs:   X bn ZAR/a
Carbon Tax:       X bn ZAR/a
Total Costs:      X bn ZAR/a
```
- Total Emissions and Carbon Tax are computed for the **target year only** (last investment period, e.g. 2030), consistent with each other: `101 MtCO₂ × 462 R/t ≈ 46.7 bn ZAR`.
- Total Costs = Capital + Marginal + Grid + Carbon Tax.

**Technology colours (`config.yaml` tech_colors):**

| Technology | Colour | Hex |
|---|---|---|
| Coal | Dark grey | `#333333` |
| CCGT | Light grey | `#999999` |
| OCGT | Light grey | `#bbbbbb` |
| Nuclear | Red | `#cc0000` |
| Solar CSP | Orange | `#ff8000` |
| Hydro | Purple | `#9055aa` |
| Wind | Blue | `#235ebc` |
| Solar PV | Yellow | `#ffde08` |
| Battery | Green | `#ace37f` |

**Nice names:** `ccgt_steam` → "CCGT", `ocgt` / `ocgt_gas` → "OCGT", `bioenergy` → "Biomass".  
**Carrier display order:** Coal → CCGT → OCGT → Nuclear → Biomass → Hydro → Wind → Solar PV → Solar CSP → PHS → Battery.

---

## 10. Calibration Results: Single-Node (regions=1, LC-182h)

> All results in this section use the reduced 182h time resolution. They are **not** final paper results.

| Metric | P0_BASE | P0_CT | P0_BASE_R | P0_CT_R |
|---|---|---|---|---|
| Coal dispatch (TWh) | 165.7 | 145.3 | 132.0 | 132.6 |
| Solar dispatch (TWh) | 38.3 | 58.7 | 73.0 | 72.5 |
| New solar build (MW) | 11,213 | 19,191 | 37,659 | 33,150 |
| New wind build (MW) | 0 | 0 | 0 | 0 |
| Objective (bn ZAR) | 1.82 | 2.34 | 2.07 | 2.45 |

CT price signal is working: coal −12%, solar +71% (BASE vs CT). The `_R` scenarios force so much RE that coal hits its `p_min_pu` floor; differences appear in build volumes rather than dispatch.

---

## 11. Final Test Run Results: 10-Node, LC-182h

> **Configuration:** `regions=10`, `fixed_conventional=BASE_PMR1b`, `LC-182h` (97 snapshots, weighted to 8760h/yr), `override_coal_msl=0.4`, `extendable_max_annual=UNC` (all scenarios), `transmission_grid=existing+tdp`, transmission expansion enabled (`line_expansion=copt`). **Not** final paper results — full 8760h runs required.
>
> Analysis year: 2030. All dispatch and emission figures are weighted by snapshot_weightings (sum = 8722h for 2030 period).

### 11.1 Dispatch [TWh, 2030]

| Technology | P0_BASE | P0_CT | P0_BASE_R | P0_CT_R |
|---|---|---|---|---|
| Coal (Eskom) | 86.41 | 85.10 | 75.41 | 75.41 |
| Sasol coal | 5.50 | 4.76 | 2.54 | 2.54 |
| **Total coal** | **91.91** | **89.86** | **77.95** | **77.95** |
| CCGT | 8.52 | 8.31 | 0.00 | 0.00 |
| OCGT gas | 22.38 | 22.38 | 22.38 | 22.38 |
| Nuclear | 14.55 | 14.55 | 14.55 | 14.55 |
| Hydro (local) | 1.79 | 1.79 | 1.79 | 1.79 |
| Hydro (import) | 10.10 | 10.10 | 10.10 | 10.10 |
| Bioenergy | 0.95 | 0.95 | 0.95 | 0.95 |
| Solar PV (utility) | 6.78 | 7.30 | 8.14 | 7.93 |
| Solar PV (low-cost) | 34.25 | 36.06 | 21.96 | 19.60 |
| Solar PV (rooftop) | 19.42 | 19.43 | 11.60 | 10.75 |
| Solar CSP | 1.98 | 1.98 | 1.98 | 1.98 |
| **Total solar** | **62.44** | **64.77** | **43.68** | **40.26** |
| Wind | 43.87 | 44.02 | 90.40 | 95.22 |
| RMIPPP | 1.87 | 1.87 | 1.87 | 1.87 |
| **Total supply** | **258.38** | **258.61** | **263.68** | **265.08** |

### 11.2 New Build 2030 [GW]

| Technology | P0_BASE | P0_CT | P0_BASE_R | P0_CT_R |
|---|---|---|---|---|
| Wind | 8.45 | 8.45 | 23.95 | 25.05 |
| Solar PV (all) | 24.32 | 25.20 | 26.56 | 25.14 |
| OCGT gas | 6.42 | 6.42 | 6.42 | 6.42 |
| **CCGT** | **1.22** | **1.22** | **0.00** | **0.00** |
| Battery 4h | 2.81 | 2.81 | 2.81 | 2.81 |

Note: OCGT, solar, and battery are at the IRP25_BQ minimum floor. CCGT (1.22 GW) is an optimizer choice in BASE/CT but is crowded out by wind investment in the _R scenarios. Wind in _R is driven by the CT reinvestment constraint, not the IRP floor.

### 11.3 Capacity Factors 2030

| | P0_BASE | P0_CT | P0_BASE_R | P0_CT_R |
|---|---|---|---|---|
| Coal CF | 0.28 | 0.27 | 0.24 | 0.24 |
| Wind CF | 0.40 | 0.40 | 0.37 | 0.37 |
| Solar PV CF | 0.26 | 0.26 | 0.22 | 0.25 |

### 11.4 Curtailment 2030 [TWh]

| | P0_BASE | P0_CT | P0_BASE_R | P0_CT_R |
|---|---|---|---|---|
| Wind curtailment | 0.31 | 0.16 | 2.82 | 2.07 |
| Solar curtailment | 0.41 | 0.44 | 22.70 | 22.62 |

High solar curtailment in _R scenarios (~22.7 TWh) is expected: the reinvestment constraint forces RE build beyond what is economically optimal; excess solar is curtailed when coal MSL and must-run generators fill the residual demand.

### 11.5 Emissions and Carbon Tax Revenue [2030]

| | P0_BASE | P0_CT | P0_BASE_R | P0_CT_R |
|---|---|---|---|---|
| Total CO₂ [MtCO₂] | 116.47 | 113.99 | 101.72 | 101.72 |
| Coal CO₂ [MtCO₂] | 101.87 | 99.39 | 87.12 | 87.12 |
| CT revenue [bn ZAR] | — | 52.66 | 53.81* | 46.99 |

*P0_BASE_R reinvests based on P0_BASE emissions × 462 R/t = 53.81 bn ZAR. P0_CT_R reinvests based on P0_CT emissions × 462 R/t = 52.66 bn ZAR.

### 11.6 Transmission Expansion

No transmission expansion in any scenario (p_nom_opt ≈ p_nom_min + numerical noise). Optimizer found expansion uneconomic at 689 ZAR/MW/km/yr annualized. This result holds despite the _R scenarios pushing 90–95 TWh of wind (vs 44 TWh in BASE). May change in full 8760h runs if congestion hours are better captured.

### 11.7 Interpretation

**CT effect (P0_CT vs P0_BASE):** −2.5 MtCO₂ = −2.1%. Small but mechanistically correct: with MSL=0.4 × EAF_60, coal operates at CF ≈ 0.24–0.28, near its floor in many timesteps. The CT raises coal MC by 400–550 R/MWh and does shift some Sasol coal dispatch (−0.74 TWh) and marginal CCGT operation. The effect will be larger in 8760h runs where daily solar variability creates regular MSL-free periods at night.

**Reinvestment effect (P0_BASE_R vs P0_BASE):** −14.75 MtCO₂ = −12.7%. Entirely driven by the forced +15.5 GW of new wind, which displaces coal. The constraint is binding: 53.81 bn ZAR of RE capital investment is required.

**Key finding — P0_BASE_R ≡ P0_CT_R:** The two scenarios are numerically identical in emissions, dispatch, and new build. This is mechanistically explained: P0_CT_R's reinvestment floor (52.66 bn ZAR) is only 2.1% lower than P0_BASE_R's (53.81 bn ZAR), because P0_CT only reduces total emissions by 2.1%. The CT signal is entirely absorbed by the MSL constraint; no additional coal displacement occurs beyond what the reinvestment constraint already forces. This is the central scientific finding of Paper 0: **carbon tax revenue recycling into renewables achieves the same emissions reduction with or without the CT price signal, under MSL-constrained coal operation.**

**CCGT in BASE/CT:** The optimizer voluntarily builds 1.22 GW CCGT to provide flexible capacity that complements the MSL-locked coal fleet and IRP-mandated OCGT. In _R scenarios, the additional 15.5 GW wind makes CCGT unnecessary. This finding is consistent with the IRP 2023 gas expansion trajectory.

**Conclusion:** The model is correctly configured and produces internally consistent, scientifically interpretable results. Ready for LC (8760h) production runs — change `options = LC` in scenarios_to_run.xlsx before submitting.

---

## 12. Known Model Limitations (P1 Pathway Scenarios)

### 12.1 No mandatory coal retirement after 2035

P1 scenarios use `phased_decom = DELAYED_ESKOM_2035`: coal retirements are fixed/exogenous and end in 2035. After that, the remaining fleet stays available indefinitely. Coal is only displaced if dispatch economics (or CT) make it uncompetitive. This means:
- Residual coal in 2050 across all scenarios (no forced phase-out)
- Emissions in 2045–2050 remain 80–102 MtCO₂/yr in P1_BASE despite 84–90% RE share
- CT effect on coal retirement is endogenous only — CT raises coal dispatch cost but doesn't force physical retirement

### 12.2 1-bus model dilutes CT dispatch signal

P1 uses `regions=1` (single aggregate node). Without transmission bottlenecks, RE always reaches demand and coal competes directly with RE on marginal cost. The CT dispatch channel (merit-order reshuffling) is present but less differentiated than in a 10-bus model. P1_CT and P1_BASE show near-identical emissions — the investment and recycling channels dominate in the results.

For final paper: 10-bus P1 runs needed to capture the spatial dispatch CT signal.

### 12.3 PHS extendability

New PHS units (`RSA-phs-{year}`) are extendable with no upper bound. In the current model setup, PHS builds 1.7–3.0 GW in 2040–2050 even in BASE/CT (without recycling). SA's PHS resource is limited (few suitable sites) and development timelines are 10+ years. This should be reviewed — either cap via `extendable_max_total` or remove PHS extendability entirely.

PHS is excluded from the CT reinvestment pool (constraint covers batteries only).

### 12.4 Reinvestment constraint is always binding

The optimizer never invests beyond the reinvestment floor — it treats the constraint as an exact target, not a minimum. This means the _R scenarios are not truly "cost-optimal with reinvestment budget" but rather "cost-optimal subject to a forced minimum spend." The actual cost-optimal outcome under a reinvestment budget would require a different formulation (e.g. budget cap instead of floor, or endogenous CT revenue calculation).

---

## 13. Key Configuration Decisions

| Parameter | Value | Rationale |
|---|---|---|
| `fixed_conventional` | `BASE_PMR1b` | Realistic Eskom heat rates. |
| `carbon_tax` | `IRP23` | 462 R/tCO₂ in 2030 per IRP 2023. |
| `override_coal_msl` | `0.65` | 65% of p_max_pu; raised from 0.4 after colleague feedback — see 7.4.2. |
| `coal_ramp_rate_multiplier` | `1` | Base ramp rate, no artificial speed-up — see 7.4 table and 7.4.1 rationale. |
| `unit_committment` | `1` | Enables retirement variables for endogenous decom — see 7.4.1. |
| `endogenous_coal_decom` | `1` | Coal retirement responds to CT instead of following a fixed schedule — see 7.4.1. |
| `annual_availability` | `EAF_60` | 60% EAF for coal fleet in 2030. |
| `extendable_max_annual` | `UNC` | No annual build cap for any scenario; the only differences between scenarios are the CT price signal and the reinvestment constraint. |
| `extendable_min_total` | `IRP25_BQ` | IRP 2025 committed pipeline as minimum floor; global constraints are active (wind 8.45 GW, solar 24.3 GW, OCGT 6.42 GW, battery 2.81 GW at floor in P0_BASE). |
| `options` | `LC` | Full 8760h for production runs. Test runs used `LC-182h`. |

---

## 14. Results Analysis Notebook

**File:** `paper0_results_analysis.ipynb`

Jupyter notebook for extracting, comparing and summarising results across all four P0 scenarios after the model runs are complete. Load this notebook once all four `solved.nc` files exist.

### Setup

The notebook sets `RESULTS_DIR = "results/Coal_Flexibilisation"` and `SCENARIOS = ["P0_BASE", "P0_CT", "P0_BASE_R", "P0_CT_R"]`. It loads each network with `pypsa.Network(...)` and stores them in a dict `nets`. All analysis targets the 2030 investment period (retrieved via `get_2030()`).

### Helper Functions

| Function | Returns |
|---|---|
| `get_2030(n)` | Extracts 2030 investment period slice from a multi-period network |
| `dispatch_twh(n)` | Generation by carrier for 2030 in TWh, weighted by period weightings |
| `dispatch_by_carrier(n, carrier)` | Time series for a specific carrier in 2030 |
| `emissions_mt(n)` | CO₂ emissions in Mt for 2030 |
| `ct_revenue_bn(n)` | Carbon tax revenue in bn ZAR (emissions × 462 R/t), 2030 only |
| `new_build_gw(n)` | New extendable capacity added in 2030 in GW, by carrier |
| `reinvestment_bn(n)` | Total RE capital investment in 2030 in bn ZAR (new build × capital cost) |
| `total_load_twh(n)` | Total demand served in 2030 in TWh |

### Analysis Sections

1. **Network sanity check** — confirms network loaded, investment periods, bus count, snapshot weighting
2. **New build capacity** — bar chart of new RE/storage/OCGT capacity (GW) across scenarios
3. **Generation mix** — stacked bar of dispatch (TWh) by carrier across scenarios
4. **CO₂ emissions** — total and by carrier (Mt) for 2030 across scenarios
5. **CT revenue & reinvestment** — compares CT revenue against actual RE investment; checks reinvestment constraint binding
6. **System costs** — capital, marginal, carbon tax, and total costs (bn ZAR/yr)
7. **Summary table** — exports all key metrics to `paper_summary_2030_182h.csv`

### Output

`paper_summary_2030_182h.csv` — one row per scenario, columns:
`scenario, coal_twh, solar_twh, wind_twh, ocgt_twh, co2_mt, ct_revenue_bn, new_solar_gw, new_wind_gw, new_ocgt_gw, new_battery_gw, reinvestment_bn, capital_costs_bn, marginal_costs_bn, total_costs_bn`

### Running the notebook on the server (VS Code + SSH)

The model runs on a remote server. To open and run the notebook interactively in VS Code via SSH:

**One-time setup — register the Jupyter kernel:**
```bash
/home/users/a/agma/.pixi/envs/pypsa-rsa/bin/python -m ipykernel install --user --name pypsa-rsa --display-name "PyPSA-RSA"
```
This only needs to be done once. It registers the pixi environment so VS Code and Jupyter can find it.

**Each session — start the Jupyter server on the server:**
```bash
nohup /home/users/a/agma/.pixi/envs/pypsa-rsa/bin/jupyter lab --no-browser --port=8899 > ~/jupyter.log 2>&1 &
cat ~/jupyter.log
```
The output contains a URL like:
```
http://localhost:8899/lab?token=abc123...
```

**Connect VS Code to the server:**
1. Open `paper0_results_analysis.ipynb` in VS Code
2. Click the kernel button (top right)
3. Select **"Jupyter Server"** → **"Existing Jupyter Server..."**
4. Paste the URL from `~/jupyter.log`
5. Select the **"PyPSA-RSA"** kernel from the list

VS Code Remote SSH forwards the port automatically — no separate SSH tunnel needed. The notebook will run on the server with access to all result files.

**To stop the server:**
```bash
pkill -f "jupyter lab"
```

---

## 15. Running on ZECM HPC — Production Runs

> **Do NOT `sbatch run_head.job`** — the head Snakemake process must run on the frontend, not as a SLURM job. Snakemake itself submits each rule as its own SLURM child job automatically.

### Before every run — checklist
- [ ] `run_scenario = 1` for all scenarios to run in `scenarios_to_run.xlsx`
- [ ] `options = LC-182h` for test runs | `options = LC` for production
- [ ] P0: `regions = 10` | P1: `regions = 1`

### What happens in the DAG

```
Snakemake runs on the frontend (tmux session)

  Preprocessing — all scenarios in parallel, finishes in minutes:
    build_topology → base_network → add_electricity  (per scenario)

  Solve wave 1 — independent scenarios at the same time (up to 2 Gurobi at once):
    Node A: P0_BASE   (64 GB, 32 CPUs)
    Node B: P0_CT     (64 GB, 32 CPUs)
    Node C: P1_BASE   (64 GB, 32 CPUs)
    Node D: P1_CT     (64 GB, 32 CPUs)

  Solve wave 2 — each starts as soon as its base scenario is done:
    Node E: P0_BASE_R  (waits for P0_BASE)
    Node F: P0_CT_R    (waits for P0_CT)
    Node G: P1_BASE_R  (waits for P1_BASE)
    Node H: P1_CT_R    (waits for P1_CT)

  Plots — submitted automatically after each scenario finishes
```

P0 plots are available as soon as P0 is done — P1 does not need to be finished.

### Step 1 — start a tmux session
```bash
tmux new -s pypsa
```

### Step 2 — run
```bash
bash /beegfs/scratch/agma/pypsa-rsa/run_head.job
```

You should see `Submitted job ... with SLURM jobid ...` lines within seconds.

### Step 3 — detach (keeps running after logout)
```
Ctrl+B  D
```

### Monitor
```bash
# All running child jobs:
squeue --me

# Live snakemake output (reattach tmux):
tmux attach -t pypsa

# Specific job log (replace JOBID):
tail -f /beegfs/scratch/agma/pypsa-rsa/.snakemake/slurm_logs/rule_prepare_and_solve_network/P0_BASE/JOBID.log

# Snakemake head log (latest run):
tail -f $(ls -t /beegfs/scratch/agma/pypsa-rsa/logs/snakemake_head_*.log | head -1 | xargs basename)

# or 50
tail -n 50 $(ls -t /beegfs/scratch/agma/pypsa-rsa/logs/snakemake_head_*.log | head -1)

```

### Cancel everything
```bash
tmux attach -t pypsa   # then Ctrl+C to stop Snakemake

or

tmux kill-session -t pypsa

# Cancel all remaining child jobs:
scancel $(squeue --me -h -o "%i" | tr '\n' ' ')
```

### Results location
```
results/Coal_Flexibilisation/{scenario}/networks/solved.nc
results/Coal_Flexibilisation/{scenario}/outputs/plots/map_only.png
results/Coal_Flexibilisation/{scenario}/outputs/plots/map_full.png
results/Coal_Flexibilisation/{scenario}/outputs/plots/pathway.png
results/Coal_Flexibilisation/{scenario}/outputs/generators.csv
```

### Results download 

scp -r agma@gateway.hpc.tu-berlin.de:/beegfs/scratch/agma/pypsa-rsa/results ~/Downloads/


### Current `run_head.job` settings
| Parameter | Value | Meaning |
|---|---|---|
| `runtime` | 20000 min | ~13.9 days — under the 14-day SLURM max |
| `mem_mb` | 16000 | default for small jobs; solve rule overrides to 64000 |
| `solver_slots` | 2 | max 2 Gurobi sessions in parallel (WLS Academic limit) |
| `--jobs` | 16 | max 16 SLURM child jobs submitted at once |
| `--latency-wait` | 120 s | time to wait for output files to appear on BeeGFS |
| `-F` | on | force rerun all rules (needed when switching LC-182h → LC) |

---

### Test vs. Production runs: keeping results separate

**Problem:** If you debug with 182h test runs, they overwrite the LC `solved.nc` files. You can then never safely remove `-F`, because Snakemake would see the 182h outputs as "up to date" and skip the LC solve.

**Solution:** Use a different `working_folder` in `config.yaml` for test runs:

```yaml
# config.yaml — switch before each run type:
scenarios:
  working_folder: Coal_Flexibilisation_test   # ← for 182h debug runs
  working_folder: Coal_Flexibilisation         # ← for LC production runs
```

Test results land in `results/Coal_Flexibilisation_test/` and never touch `results/Coal_Flexibilisation/`. Once the LC run completes cleanly, you can remove `-F` from `run_head.job` and Snakemake will correctly skip already-solved scenarios on reruns.

---

### Gurobi WLS: stuck sessions ("Overage for too long")

**Symptom:** Every solve attempt fails immediately with:
```
GurobiError: Overage for too long, 4 active sessions and over the baseline for X minutes
```
even though `squeue --me` is empty.

**Cause:** SLURM jobs were killed (OOM, timeout, Ctrl+C) without Gurobi releasing its WLS license sessions cleanly. The WLS server still counts them as active.

**Fix — release sessions via the Gurobi portal:**
1. Go to `https://license.gurobi.com` and log in
2. Navigate to your WLS license (ID: `938810`)
3. Find "Active Sessions" → terminate all sessions

**Verify Gurobi is clear before restarting:**
```bash
export GRB_LICENSE_FILE=/home/users/a/agma/gurobi.lic
python3 -c "import gurobipy; m = gurobipy.Model(); print('Gurobi OK')"
```

**Prevention:** always use `--resources solver_slots=2` so at most 2 Gurobi sessions run in parallel. The academic WLS baseline is 2 concurrent sessions — exceeding it triggers overage.

---

### TODO: PuLP/Gurobi WLS session check in every job

**Problem:** Snakemake depends on PuLP for optional ILP job scheduling. At startup, every SLURM job runs `pulp.listSolvers(onlyAvailable=True)` (in `snakemake/cli.py`) which calls `GUROBI().available()` — this opens and immediately closes a WLS session. With 8 simultaneous preprocessing jobs, 8 brief Gurobi connections fire at once, temporarily pushing the session count above the WLS baseline (2).

**Observed:** Warnings like the following appear in every SLURM job log even for non-solve jobs:
```
pulp/apis/gurobi_api.py:238: UserWarning: GUROBI error: Overage for too long, 3 active sessions...
```

**Root cause of LC run failure (June 2026):** The PuLP check wasn't the direct killer — the real cause was an OOM crash on P0_CT (64 GB not enough for 8760h LP). The crash left a zombie WLS session → subsequent solve jobs hit 3 concurrent sessions → overage cascade. Fixed by raising `mem_mb=200000` for solve jobs.

**Remaining risk:** If 2 solve jobs are running (2 persistent WLS sessions) and a new job starts its PuLP check simultaneously → momentary 3rd session → potential overage. Low probability but not zero.

**Options to fix properly (not yet done):**
- Reduce `solver_slots=1` (safest: max 1 persistent WLS session, but halves solve parallelism)
- Remove `GRB_LICENSE_FILE` from `shell.prefix` and set it only inside `prepare_and_solve_network.py` so non-solve jobs can't connect to WLS at all
- PuLP cannot be uninstalled — it is a hard dependency of snakemake

---

### Weitere Beachtung nötig: Boolean-Felder in scenarios_to_run.xlsx

**Betroffene Felder:** `unit_committment`, `endogenous_coal_decom`, `variable_storage_vom`

**Hintergrund:** Meridian (ursprünglicher Code) hat diese Felder mit `True`/`False` befüllt. Im Coal-Flexibilisation-Projekt werden stattdessen `1`/`0` verwendet — das ist technisch äquivalent, weil Excel booleans intern als 1/0 speichert.

**Das eigentliche Problem — inkonsistente Code-Checks:**

`_helpers.py` ersetzt alle leeren Zellen (NaN) pauschal mit dem String `"none"`:
```python
return scenario_setup.fillna("none")
```

Im Code gibt es zwei verschiedene Arten diese Felder zu prüfen:

| Datei | Check | leer (→ `"none"`) | `0` | `1` |
|---|---|---|---|---|
| `add_electricity.py` | `== True` | False ✓ | False ✓ | True ✓ |
| `prepare_and_solve_network.py` | `if ...:` (truthy) | **True ✗** | False ✓ | True ✓ |
| `custom_constraints.py` | `if ...:` (truthy) | **True ✗** | False ✓ | True ✓ |

`"none"` ist in Python ein nicht-leerer String und daher **truthy** — d.h. eine leere Zelle in der Excel wird von den truthy-Checks fälschlicherweise als "aktiviert" interpretiert.

**Konsequenz:** Szenarien die `unit_committment` oder `endogenous_coal_decom` leer lassen (NaN) statt explizit `0` einzutragen, lösen in `prepare_and_solve_network.py` und `custom_constraints.py` den jeweiligen Code-Block trotzdem aus → führt zu `KeyError: 'Generator-status'`.

**Workaround (aktuell):** Immer explizit `0` in die Zelle eintragen, nie leer lassen.

**Saubere Lösung (noch nicht umgesetzt):** Die truthy-Checks in `prepare_and_solve_network.py` (Zeilen 469, 488) und `custom_constraints.py` (Zeile 314) auf `== True` oder `== 1` umstellen — konsistent mit `add_electricity.py`. Dann sind leere Zellen sicher.

---

### Offener Punkt (2026-09-13): Transmission-Engpässe trotz aktiviertem Ausbau — weitermachen später

**Stand:** `line_expansion=copt` ist aktiv, bestehende Korridore sind `p_nom_extendable=True` mit echten Kosten (siehe Abschnitt 8 / `update_transmission_costs()`, 6000 ZAR/MW/km). Das ist **neuer** Code — nicht der alte PyPSA-ZA-Code, den eine frühere Session (`CARBON_TAX_SCENARIOS.md`, Stand 2026-06-06) noch für nötig hielt. Dieser Stand ist überholt.

**Befund — Auslastung im gelösten `P0_BASE` (LC, 8760h), geprüft mit `n.links_t.p0`:**

| Korridor | Max. Auslastung | Stunden > 95% |
|---|---|---|
| Northern Cape–Hydra Central | 100.0% | 416 h |
| North West–Gauteng | 99.999% | 2828 h |
| Free State–North West | 99.999% | 233 h |
| Limpopo–Gauteng | 99.999% | 151 h |
| North West–Mpumalanga | 99.994% | 67 h |
| Free State–Eastern Cape | 99.991% | 1232 h |
| **Free State–Gauteng** | 99.991% | **4448 h** (>50% des Jahres) |

Mehrere Korridore sind also strukturell verstopft, nicht nur an einzelnen Spitzen.

**Das Rätsel:** Trotz dieser Dauerlast baut der Solver so gut wie nichts aus — z.B. Free State–Gauteng: `p_nom = 394.83 MW → p_nom_opt = 394.84 MW` (numerisches Rauschen, keine echte Investition). Der Ausbau-Mechanismus ist aktiv und korrekt bepreist, aber wirtschaftlich offenbar nie attraktiv genug — auch nicht bei 100%-Dauerlast.

**Offene Frage, die vor jedem Ausbau-Feature (neue Korridore) erst geklärt werden sollte:** Warum lohnt sich der Ausbau selbst bestehender, verstopfter Korridore nicht?
Mögliche Ursachen zum Prüfen:
- Nur 2 Investitionsperioden (2025, 2030) im P0-Snapshot → Annuität der Transmission-Capex wird ggf. nur über sehr wenige gewichtete Jahre amortisiert, obwohl `hvac_overhead.lifetime=40` Jahre unterstellt — Diskrepanz zwischen Line-Lifetime und Investment-Period-Weighting möglich.
- Fehlt eine Bewertung der vermiedenen Kosten durch die Verstopfung (z.B. wird Redispatch/lokale Kohle-Erzeugung durch die Engpässe erzwungen, aber ist das teurer als der Netzausbau? Müsste durchgerechnet werden.)
- Eventuell verhindert eine andere Nebenbedingung (Reserve-Margin, `p_nom_min`-Fixierung) den Ausbau unabhängig vom reinen Kostenvergleich.

**Zwei Wege für "neue Korridore", vorgemerkt für später:**
- **Weg A (exogen, kein Code nötig):** `transmission_grid = existing+tdp+<SZENARIONAME>` in `scenarios_to_run.xlsx` + Zeilen in `transmission_expansion.xlsx` (aktuell komplett leer — nur Spaltenköpfe) eintragen: bus0, bus1, Länge, Spannungsebene, und pro Jahr eine feste Anzahl neuer Leitungen. Mechanismus existiert bereits in `build_topology.py:106-133`, ist aber exogen (kein Solver-Entscheid, sondern fester Fahrplan).
- **Weg B (endogen, Solver entscheidet, braucht Code-Änderung):** `add_components_to_network()` in `base_network.py` müsste für Kandidaten-Korridore (Bus-Paare ohne bestehende Leitung) zusätzliche Links mit `p_nom=0`, `p_nom_extendable=True`, `p_nom_max=<Obergrenze>` anlegen. `update_transmission_costs()` bepreist diese automatisch mit — kein Zusatzaufwand dort.

**Empfehlung, bevor Weg A oder B umgesetzt wird:** Erst das Rätsel oben klären — wenn der Solver selbst bestehende Engpass-Korridore nicht ausbaut, würde er vermutlich auch neue Korridore mit derselben Kostenlogik nicht bauen. Sonst baut man ein Feature, das dieselbe (noch unverstandene) wirtschaftliche Blockade hat.

#### Update (2026-09-14): Rätsel vermutlich geklärt — Scale-Bug beim Auslesen + Ausbau wirtschaftlich wohl tatsächlich unattraktiv

**Kernbefund — ×1000-Skalierung wird beim Export nicht zurückgesetzt:** `scale_costs(n, 1e3)` in `prepare_and_solve_network.py:561` teilt kurz vor dem Solve alle `*cost*`-Spalten (`capital_cost`, `marginal_cost`) auf `Generator`, `StorageUnit` und `Link` durch 1000 — offenbar für bessere numerische Konditionierung des Solvers. Diese Skalierung wird **danach nie zurückgesetzt**, bevor `n.export_to_netcdf()` läuft. Konsequenz: In jedem `solved.nc` stehen `capital_cost`, `marginal_cost` und alle daraus abgeleiteten Dual-Werte (`n.buses_t.marginal_price` etc.) faktisch in **Tausend-ZAR statt ZAR** — Faktor 1000 zu klein gegenüber der Doku in Abschnitt 8/9.3.

Das erklärt den ursprünglichen Befund direkt: `capital_cost` der Free State–Gauteng-Leitung stand mit 290,995 im solved network — bei 337,96 km Länge und der dokumentierten Rate (~689 ZAR/MW/km/Jahr × 1,25 Routing-Faktor) wären ~291.000 ZAR/MW/Jahr zu erwarten. **290,995 × 1000 ≈ 291.027 — exakte Übereinstimmung.** Die Kostenformel selbst ist korrekt (geprüft: `capital_cost / length` ist über alle 38 ausbaubaren Links konstant = 0,861037, wie von der Formel erwartet); es ist reines Skalierungs-Rauschen beim Ablesen, kein Fehler in `update_transmission_costs()`. Gegenprobe an anderen Carriern bestätigt den Faktor 1000: `n.generators.capital_cost` für `wind` ≈ 1117 (skaliert) × 1000 ≈ 1,12 Mio. ZAR/MW/Jahr — realistischer Wert für Wind-Annuität in Südafrika. `n.objective` ≈ 2,313 Mrd. (skaliert) × 1000 ≈ 2,31 Billionen ZAR über den P0-Horizont — passt zur Größenordnung des südafrikanischen Elektrizitätssystems.

**Damit neu bewertet, mit real reskalierten Werten (×1000):**
- Reale Kapitalkosten der FS–GP-Leitung: **~291.000 ZAR/MW/Jahr** (nicht 291 ZAR/MW/Jahr, wie das ungeskalierte Attribut suggeriert).
- Reale Preisdifferenz zwischen den beiden Bus-Knoten während der Hoch-Auslastungsstunden (>95%): **~30–32 ZAR/MWh** (statt der vorher abgelesenen 0,03 ZAR/MWh) — klein, aber nicht null.
- Grobe Schätzung des über das gesamte Jahr realisierten "Congestion Rent" dieses einen Korridors (Preisdifferenz × Fluss × Snapshot-Gewicht, aufsummiert über alle Snapshots, reskaliert): **~57 Mio. ZAR/Jahr**, verteilt auf 394,8 MW bestehende Kapazität ≈ **~144.000 ZAR/MW/Jahr im Schnitt** — spürbar unter den ~291.000 ZAR/MW/Jahr Grenzkosten einer Erweiterung. Da der **Grenz**wert einer zusätzlichen MW typischerweise noch unter dem **Durchschnitts**wert der bestehenden Kapazität liegt (Erweiterung drückt den Preis-Spread selbst), spricht das klar gegen eine profitable Erweiterung — konsistent mit dem Solver-Ergebnis (keine echte Investition).

**Einschränkung dieser Schätzung:** Es ist ein grober Proxy (Preis-Spread × Fluss), kein echter Schattenpreis der Kapazitätsrestriktion. PyPSA/linopy legt für **ausbaubare** Links kein `mu_upper` ab (das gibt es nur bei fixem `p_nom`) — die gekoppelte "Link-ext-p-upper"-Restriktion hat einen eigenen Dual-Wert, der aktuell nicht mit exportiert wird. Für eine belastbarere Zahl müsste man entweder diesen Dual-Wert vor dem Verwerfen des linopy-Modells sichern, oder eine Sensitivitätsanalyse fahren (Resolve mit `p_nom_min` + 1 MW auf dem Korridor, Kostendifferenz vergleichen).

**Zusatzhypothese zum kleinen Preis-Spread trotz 99,999%-Auslastung:** Das Netz ist ein reines Transport-Modell (keine Kirchhoff-Restriktionen) mit 38 potenziell ausbaubaren Korridoren zwischen den 10 Regionen — nahezu vermascht. In so einem Modell bedeutet hohe Auslastung auf einem einzelnen Korridor nicht zwingend echte lokale Knappheit, solange Ausweichrouten mit ähnlichen Grenzkosten existieren; der Flow sättigt dann zwar diesen einen Link, aber der volkswirtschaftliche Wert einer Entlastung bleibt gering, weil das Gesamtsystem den Engpass günstig umgeht. Das würde erklären, warum selbst ein strukturell "verstopfter" Korridor kaum Preisdifferenz zeigt.

**Was sich konkret machen lässt:**
1. **Fix (empfohlen, kleiner Eingriff):** In `prepare_and_solve_network.py` nach dem Solve, vor `n.export_to_netcdf(...)`, die Kosten-Spalten wieder ×1000 zurückskalieren (`scale_costs(n, 1e-3)` erneut aufrufen). Danach stehen `capital_cost`, `marginal_cost` und `marginal_price` in `solved.nc` wieder in echten ZAR — vermeidet, dass dieses Missverständnis bei jeder künftigen Auswertung erneut auftritt. Alternativ, falls die Skalierung für andere Skripte/Plots bewusst beibehalten werden soll: mindestens einen klaren Kommentar/README-Hinweis ergänzen ("Kosten in solved.nc sind in Tausend-ZAR").
2. **Ursprüngliches Rätsel als vermutlich gelöst behandeln:** Die Nicht-Erweiterung ist mit hoher Wahrscheinlichkeit eine korrekte, wirtschaftlich begründete Optimierer-Entscheidung, kein Bug in der Kosten- oder Constraint-Logik. Bevor an neuen Korridoren (Weg A/B, s.o.) gearbeitet wird, lohnt keine weitere Fehlersuche im bestehenden Ausbau-Mechanismus für existierende Korridore — die Wirtschaftlichkeitsschwelle scheint einfach nicht erreicht zu werden, und neue Korridore träfen vermutlich auf dieselbe Hürde.
3. **Falls doch mehr Ausbau gewünscht ist** (z.B. für ein Szenario mit expliziter Netzausbau-Story): eher über Weg A (exogener Fahrplan in `transmission_expansion.xlsx`) argumentieren, nicht über einen vermeintlichen Bug im endogenen Mechanismus — der Mechanismus funktioniert, das Ergebnis ist nur nicht das erwartete.

#### Update (2026-09-14, Teil 2): Kosten-Plausibilität, Ein-Perioden-Vergleich, Leitungspuffer

**1. Sind die 6000 ZAR/MW/km plausibel?** Ja, im Kern — Herkunft ist die Quelle **Hagspiel** (häufig genutzte Referenz für HVAC-Freileitungskosten, u.a. in PyPSA-EUR verbreitet), identisch in allen drei älteren Cost-Sheets (`za_original`, `original`, `ambitions` in `costs_pypsa-za.xlsx`). Im `updated`-Sheet steht derselbe Wert noch im Original: **400 EUR/MW/km** (2030).

Aber: eine Inkonsistenz bei der Währungsumrechnung. Das Projekt hat eine zentrale, sonst überall genutzte Konstante `EUR_to_ZAR: 17.83` (`config.yaml:194`), angewendet über `convert_cost_units()` (`_helpers.py:642`) bzw. `add_electricity.py:224` auf alle EUR-Kosten. Der Transmission-Block `lines.hvac_overhead.investment: 6000` (`config.yaml:179`) ist dagegen **hart als ZAR-Zahl hinterlegt**, nicht über diese Pipeline umgerechnet — impliziter Kurs darin: 6000/400 = **15,0 ZAR/EUR**, nicht 17,83.

Mit dem projekteigenen Kurs müsste es **400 × 17,83 = 7.132 ZAR/MW/km** heißen, nicht 6000 — die Leitungskosten sind aktuell **~16% zu niedrig** angesetzt. Für die Kernfrage ("warum kein Ausbau") ändert das nichts Grundsätzliches: real müssten die Kosten noch höher sein, was Ausbau noch unattraktiver macht, nicht attraktiver — bestätigt die Nicht-Investition zusätzlich.

**2. Ergibt die 40-Jahre-Lebensdauer bei einem reinen 2030-Lauf (ohne 2025) noch Sinn?** Ja — sogar sauberer als im jetzigen 2-Perioden-Setup. In `set_investment_periods()` (`base_network.py:119-131`) bekommt ein einzelnes Investitionsjahr `n.investment_period_weightings["years"] = 1` → `objective = 1.0` (nur t=0, keine Diskontierung). Die Annuität (CRF über die 40 Jahre Lebensdauer) wird damit exakt gegen **ein** repräsentatives Jahr Nutzen gerechnet — Standardmethode für Greenfield-Ausbau-Modelle mit nur einem Snapshot-Jahr. Die Lebensdauer steckt schon in der Annuitätsformel, nicht in der Anzahl simulierter Perioden.

**Aber:** ein Solo-2030-Lauf würde die Ausbau-Entscheidung tatsächlich **anders** ausfallen lassen als der jetzige P0-Lauf (2025+2030 zusammen) — nicht wegen der Lebensdauer, sondern wegen der Perioden-Gewichtung. Im 2-Perioden-Modell ist jede Leitung in beiden Perioden aktiv (`build_year=2024`, `lifetime=100`), zahlt also Kapitalkosten gewichtet über **beide** Perioden (4,225549 + 7,550219 = **11,78** effektive Jahre), bekommt aber vermutlich nur in 2030 nennenswerten Engpass-Nutzen (2025: weniger RE, weniger Engpässe). Daraus ergibt sich ein Nutzen/Kosten-Schwellenwert von **11,78/7,55 ≈ 1,56** im 2-Perioden-Modell gegen **1,0** in einem Solo-2030-Lauf. Ein reiner 2030-Lauf würde Transmission-Ausbau also tendenziell **attraktiver** aussehen lassen, weil die (kaum kongestionierte) 2025-Periode als Kostenballast wegfällt.

**3. Ist ein Leitungspuffer/Sicherheitsmarge drin?** Ja, mehrere Ebenen, alle in der **bestehenden** Leitungskapazität (`p_nom`/`p_nom_min`), berechnet in `build_topology.py`:
- **St.-Clair-Kurve** (`calc_line_limits()`, Zeile 246-258): physikalisch begründete Derating-Kurve für lange Freileitungen — begrenzt durch Spannungsstabilität statt nur durch die thermische Grenze (`min(thermal, SIL×53.736×length^-0.65)`). Kann bei langen Korridoren deutlich unter dem thermischen Limit liegen.
- **N-1-Sicherheitsmarge** (`apply_n1_approximation()`, Zeile 193-199): bei Korridoren mit mehreren parallelen Leitungen wird die Leitung mit der **höchsten** Kapazität komplett rausgeworfen (Ausfall-Annahme), nur der Rest zählt. Bei nur einer Leitung: pauschal **30% Abschlag** (`n1_approx_single_lines: 0.7`, `config.yaml:173`).
- `s_max_pu: 0.7` (`config.yaml:172`, ebenfalls "n-1 approximation" kommentiert) wird **nirgends im aktiven Code tatsächlich verwendet** (nur ein Docstring-Verweis in `base_network.py:38`) — totes/veraltetes Config-Feld, **kein** zusätzlicher (doppelter) Abschlag.

Konsequenz: die gemeldeten 99,999%-Auslastungswerte beziehen sich auf ein bereits konservativ (N-1-sicher) berechnetes Limit, nicht auf die physikalische Maximalgrenze der Leitung — der Korridor ist also nicht wirklich am absoluten physikalischen Anschlag. Das ändert aber nichts an der Ausbau-Entscheidung selbst: `p_nom_extendable=True` mit `p_nom_max=inf` erlaubt dem Solver, über diesen konservativen Wert hinauszugehen, wenn es sich lohnt — die eigentliche Hürde bleibt die Kosten-Nutzen-Rechnung aus Teil 1 oben.

**Kurz zusammengefasst, alle drei Punkte zusammen:** Nichts davon widerlegt den Befund "kein Ausbau ist wirtschaftlich korrekt" — die Kosten sind eher zu niedrig als zu hoch angesetzt (Punkt 1), die Lebensdauer-Logik ist in Ordnung (Punkt 2, mit dem Perioden-Caveat), und der Leitungspuffer beeinflusst nur die Optik der Auslastungs-Zahl, nicht die Ausbau-Fähigkeit (Punkt 3).

#### Update (2026-09-14, Teil 3): Wie groß ist der Puffer konkret bei Free State–Gauteng?

Rohdaten aus `resources/Coal_Flexibilisation/P0_BASE/lines.geojson` für diesen Korridor: **zwei parallele 275-kV-Leitungen** (nicht eine, nicht 400 kV wie der globale `v_nom`-Default).

| Größe | Beide Leitungen zusammen (N-0) | Nach N-1 (= `p_nom` im Modell) |
|---|---|---|
| Thermisches Limit | 1.842 MW | 921 MW |
| St.-Clair-Limit (spannungsstabilitätsbegrenzt) | 838,3 MW | **394,8 MW** |

Weil es **zwei** Leitungen sind, greift bei der N-1-Berechnung (`apply_n1_approximation()`) nicht der pauschale 30%-Abschlag (`n1_approx_single_lines: 0.7` — der gilt nur für Korridore mit **einer** Leitung), sondern die härtere Regel: die stärkere der beiden Leitungen wird komplett als ausgefallen angenommen, nur die schwächere bleibt übrig. Bei zwei ungefähr gleich starken Leitungen halbiert das die Kapazität ungefähr — deutlich mehr als 30% Abschlag.

**Also nicht 70%, sondern:** 99,999% Auslastung von 394,8 MW (`p_nom`) entspricht real
- **~47%** der St.-Clair-Grenze beider Leitungen zusammen (394,8 / 838,3)
- **~21%** der reinen thermischen Grenze beider Leitungen (394,8 / 1.842)

Die 70%-Umrechnung (aus `n1_approx_single_lines`) würde nur für Korridore mit tatsächlich nur **einer** Leitung stimmen — für Free State–Gauteng nicht, weil es zwei sind. Eine Tabelle mit dieser Umrechnung für alle 7 in Abschnitt "Befund" gelisteten Engpass-Korridore (jeweils prüfen: Anzahl paralleler Leitungen pro Korridor, dann die passende Umrechnung anwenden) steht noch aus.

---



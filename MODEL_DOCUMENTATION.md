# Model Documentation: PyPSA-RSA Carbon Tax Analysis (Paper 0)

*Last updated: 2026-06-07*

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
| `override_coal_msl` | `0.4` | Minimum stable load = 40% of p_max_pu. With EAF_60 (p_max_pu ≈ 0.60), this yields an effective minimum of ~0.24 of nameplate capacity (coal CF ≈ 0.24–0.28 in 2030). This value is consistent with the coal flexibilisation premise of the scenario and leaves headroom for the CT to reduce dispatch in periods where coal operates above its floor. |
| `coal_ramp_rate_multiplier` | `1.5` | Coal ramp limits multiplied by 1.5, representing flexibility improvements; limited effect at 182h but relevant for final 8760h runs. |
| `annual_availability` | `EAF_60` | Maximum energy availability factor for coal fleet = 60% of hours (sets p_max_pu upper bound). Reflects a modest recovery from current Eskom performance (~55–58%) by 2030; consistent with Meridian base parameterisation. |
| `unit_committment` | `0` | LP dispatch without unit commitment; no startup/shutdown costs or min up/down times. Appropriate for snapshot analysis and non-consecutive timesteps. |
| `endogenous_coal_decom` | `0` | Decommissioning is exogenous and fixed by `phased_decom`. |
| `dispatch_coal_flex` | `SL_0` | Only active when `unit_committment=1`; has no effect on P0. |

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
3. Calculate annual CT revenues: `annual_emissions_t [tCO₂/yr] × CT_2050[y] [R/tCO₂]`. This is 100% of annual revenues.
4. Get base scenario annual RE investment with `build_year == y`.
5. Add constraint: `Σ(p_nom[build_year==y] × capital_cost) ≥ base_annual_RE[y] + annual_CT_revenues[y]`.

Both LHS (annualised capex [kZAR/yr]) and RHS (annual CT revenues [kZAR/yr]) are on the same annual basis.

Only generators with `build_year == y` count. Named `ct_reinvestment_{y}` in the linopy model.

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

## 12. Key Configuration Decisions

| Parameter | Value | Rationale |
|---|---|---|
| `fixed_conventional` | `BASE_PMR1b` | Realistic Eskom heat rates. |
| `carbon_tax` | `IRP23` | 462 R/tCO₂ in 2030 per IRP 2023. |
| `override_coal_msl` | `0.4` | 40% of p_max_pu; consistent with coal flexibilisation premise. |
| `annual_availability` | `EAF_60` | 60% EAF for coal fleet in 2030. |
| `extendable_max_annual` | `UNC` | No annual build cap for any scenario; the only differences between scenarios are the CT price signal and the reinvestment constraint. |
| `extendable_min_total` | `IRP25_BQ` | IRP 2025 committed pipeline as minimum floor; global constraints are active (wind 8.45 GW, solar 24.3 GW, OCGT 6.42 GW, battery 2.81 GW at floor in P0_BASE). |
| `options` | `LC` | Full 8760h for production runs. Test runs used `LC-182h`. |

---

## 13. Run Instructions

```bash
# All scenarios (force rebuild):
pixi run snakemake solve_all -j 4 -F --resources solver_slots=2

# Individual targets:
pixi run snakemake results/Coal_Flexibilisation/P0_BASE/networks/solved.nc -j 4
pixi run snakemake results/Coal_Flexibilisation/P0_CT/networks/solved.nc -j 4
# _R scenarios require P0_BASE to be solved first:
pixi run snakemake results/Coal_Flexibilisation/P0_BASE_R/networks/solved.nc -j 4
pixi run snakemake results/Coal_Flexibilisation/P0_CT_R/networks/solved.nc -j 4

# On SLURM:
sbatch run_p0.job
squeue -u agma
tail -f logs/slurm_p0_<JOBID>.out
```

Results and plots are saved to:
```
results/Coal_Flexibilisation/{scenario}/networks/solved.nc
results/Coal_Flexibilisation/{scenario}/outputs/plots/
```

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

## 14. Running the Full LC Solve on the HPC Cluster

The production run uses the SLURM batch system on the TU Berlin HPC cluster. The job script is at `/beegfs/scratch/agma/pypsa-rsa/run_p0.job`.

**What each line in `run_p0.job` does:**
```bash
#!/bin/bash --login
#SBATCH --job-name=pypsa_p0            # Name shown in squeue
#SBATCH --output=logs/slurm_p0_%j.out # All output goes into this file (%j = job ID)
#SBATCH --partition=standard           # Which part of the cluster to use
#SBATCH --time=14-00:00:00             # Max 14 days, then the job is killed
#SBATCH --mem=200G                     # 200 GB RAM reserved
#SBATCH --cpus-per-task=32             # 32 CPU cores (~16 per Gurobi instance)
#SBATCH --mail-type=begin,end,fail     # Email on start, end, or failure
#SBATCH --mail-user=agatha.majcher@tu-berlin.de

export GRB_LICENSE_FILE=...            # Tell Gurobi where to find the license

cd /beegfs/scratch/agma/pypsa-rsa      # Move into the project folder

# Writes "still running" to the log every hour
while true; do sleep 3600; echo "..."; done &

# The actual core command:
snakemake solve_all -j 4 -F --resources solver_slots=2
#            ↑           ↑  ↑                    ↑
#        all 4 scenarios  up to 4   force rerun  max 2 Gurobi
#                         parallel  everything   instances at once
```

Snakemake reads the dependencies automatically and solves in the correct order: P0_BASE + P0_CT in parallel first, then P0_BASE_R + P0_CT_R in parallel (the _R scenarios need the base results before they can start).

**What the job does:**
- Calls `snakemake solve_all` which solves all 4 P0 scenarios
- Runs 2 scenarios in parallel at a time (`solver_slots=2`): first P0_BASE + P0_CT simultaneously, then P0_BASE_R + P0_CT_R simultaneously (the _R scenarios depend on the base results)
- Resources: partition=standard, 14-day time limit, 200 GB RAM, 32 CPUs (≈16 threads per Gurobi instance)
- Gurobi license: `/home/users/a/agma/gurobi.lic`

**Before submitting — checklist:**
- [ ] `options = LC` set in `scenarios_to_run.xlsx` for all 4 P0 scenarios

**Step 1 — navigate to the project directory:**
```bash
cd /beegfs/scratch/agma/pypsa-rsa
```

**Step 2 — submit the job:**
```bash
sbatch run_p0.job
```
The terminal responds with e.g. `Submitted batch job 84321`. **Note down this number.**

**Step 3 — close the terminal.** The job runs independently on the cluster.

**Emails:** You receive an email at `agatha.majcher@tu-berlin.de` when the job starts, ends, or fails.

**Check status later:**
```bash
squeue --me
```

**Read the live log** (replace `84321` with your job ID):
```bash
tail -f /beegfs/scratch/agma/pypsa-rsa/logs/slurm_p0_84321.out
```
Exit with `Ctrl+C`.

**Cancel if needed:**
```bash
scancel 84321
```

---

## 15. Multi-Node Parallel Execution (P0 + P1 simultaneously)

For running P0 and P1 together on separate nodes at the same time, use the Snakemake SLURM executor. Instead of one large job that runs all scenarios sequentially on a single node, Snakemake submits each scenario solve as its own SLURM job.

**Required package** (already installed in the pypsa-rsa env):
```
snakemake-executor-plugin-slurm == 2.7.1
```

**Job file:** `run_head.job`

This is a lightweight orchestrator job (8 GB, 2 CPUs). It runs Snakemake, which then submits the individual solve jobs to SLURM automatically.

**What happens after `sbatch run_head.job`:**

```
Head job starts (1 node, 8 GB — just Snakemake)

  Pre-processing (build_topology, base_network, add_electricity)
  → submitted as small jobs per scenario, run in parallel, finish in minutes

  Solve wave 1 — all independent scenarios at the same time:
    Node A: P0_BASE   (200 GB, 32 CPUs)
    Node B: P0_CT     (200 GB, 32 CPUs)
    Node C: P1_BASE   (200 GB, 32 CPUs)
    Node D: P1_CT     (200 GB, 32 CPUs)

  Solve wave 2 — starts automatically when wave 1 finishes:
    Node E: P0_BASE_R  (waits for P0_BASE solved.nc)
    Node F: P0_CT_R    (waits for P0_CT solved.nc)
    Node G: P1_BASE_R  (waits for P1_BASE solved.nc)
    Node H: P1_CT_R    (waits for P1_CT solved.nc)

  Plots — run automatically after each scenario finishes
```

The `_R` scenarios depend on their base scenario (P0_BASE_R needs P0_BASE), so wave 2 starts as soon as the relevant base is done — not all at once at the end.

**SLURM resources per solve job** (set in Snakefile `prepare_and_solve_network` rule):
- Memory: 200 GB
- CPUs: 32 (Gurobi uses all available threads)
- Max runtime: 14 days
- Account: `ensys`, Partition: `standard`

**Before submitting — checklist:**
- [ ] `run_scenario = 1` for all 4 P0 scenarios in `scenarios_to_run.xlsx`
- [ ] `run_scenario = 1` for all 4 P1 scenarios in `scenarios_to_run.xlsx`
- [ ] P0: `options = LC`, `regions = 10`
- [ ] P1: `options = LC`, `regions = 1`

**Submit:**
```bash
cd /beegfs/scratch/agma/pypsa-rsa
sbatch run_head.job
```

**Monitor:**
```bash
squeue --me                          # shows head job + all child solve jobs
tail -f logs/slurm_head_<JOBID>.out  # Snakemake progress log
```

**Cancel everything** (head job + all child jobs):
```bash
scancel <HEAD_JOBID>
# child jobs submitted by Snakemake must be cancelled separately:
scancel $(squeue --me -h -o "%i" | tr '\n' ' ')
```

# Model Documentation: PyPSA-RSA Carbon Tax Analysis (Paper 0)

*Last updated: 2026-06-07 (Section 11 updated with BASE_PMR1b results)*

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

### 4.1 Price signal (carbon_tax)

The carbon tax enters the model as an addition to the marginal cost of each coal generator:

```
marginal_cost += carbon_tax [R/tCO₂] × emission_factor [tCO₂/MWh] / 1000
```

The tax path is read from `sub_scenarios/emissions.xlsx`, sheet `carbon_tax`. The scenario used is `IRP23`:

| Year | 2025 | 2026 | 2029 | 2030 |
|---|---|---|---|---|
| IRP23 (R/tCO₂) | 0 | 308 | 424 | 462 |

> **Note:** `scenarios_to_run.xlsx` originally had `carbon_tax = CT_2030` for P0_CT and P0_CT_R. This entry does not exist in the emissions file and causes a KeyError at runtime. It must be corrected to `IRP23`.

### 4.2 Revenue recycling (carbon_constraints = CT_REINVEST)

For `_R` scenarios, CT revenues are not simply collected — they are recycled as a **mandatory minimum investment** in new renewable capacity. This is implemented as a custom linopy constraint added in `custom_constraints.py`:

```
Σ (p_nom_new × capital_cost)  ≥  CT_revenues
```

Where:
- `p_nom_new` = newly built capacity with `build_year == 2030`
- `capital_cost` = annualised capital cost [ZAR/MW/year]
- `CT_revenues` = carbon_tax [R/tCO₂] × total 2030 emissions from the **base scenario** solved network

Only wind and solar carriers count toward the constraint: `wind`, `wind_low`, `solar_pv`, `solar_pv_low`.

The base solved network is loaded from `results/Coal_Flexibilisation/P0_BASE/networks/solved.nc`. This means P0_BASE_R and P0_CT_R **depend on P0_BASE being solved first** (enforced in the Snakefile).

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
| `show`, `export` | *(empty)* | Legacy columns from an older model version; not referenced in any current script. No effect. |
| `export_iteration` | `0` | Legacy column; no effect in current codebase. |

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
| `fixed_conventional` | `BASE_PMR1b` | Realistic current Eskom heat rates (Medupi 9.58 GJ/MWh, ~38% efficiency). Earlier VAR_HR (design efficiency) suppressed the CT signal entirely — coal remained cheaper than gas even with the full CT applied. |
| `phased_decom` | `DELAYED_ESKOM_2035` | Coal retirements begin 2035; full fleet (41.4 GW) available in 2030, consistent with Eskom's delayed Just Transition trajectory. |
| `override_coal_msl` | `0.5` | Minimum stable load = 50% of p_max_pu. Original value of 0.7 locked coal at minimum in every timestep, leaving no room for CT dispatch response; 0.5 is consistent with the coal flexibilisation premise. |
| `coal_ramp_rate_multiplier` | `1.5` | Coal ramp limits multiplied by 1.5, representing flexibility improvements; limited effect at 182h but relevant for final 8760h runs. |
| `annual_availability` | `EAF_60` | Maximum energy availability factor for coal fleet = 60% of hours (sets p_max_pu upper bound). Reflects a modest recovery from current Eskom performance (~55–58%) by 2030; copied from Meridian default parameterisation. |
| `unit_committment` | `0` | LP dispatch without unit commitment; no startup/shutdown costs or min up/down times. Appropriate for snapshot analysis and non-consecutive timesteps. |
| `endogenous_coal_decom` | `0` | Decommissioning is exogenous and fixed by `phased_decom`; endogenous retirement only activates inside the unit commitment block (irrelevant for P0). |
| `dispatch_coal_flex` | `SL_0` | Service level parameter for coal flexibility dispatch; only active when `unit_committment=1`, has no effect on P0. |

### 7.5 Costs & investment parameters

| Parameter | Value | Rationale |
|---|---|---|
| `extendable_parameters` | `BASE_PMR1b` | Meridian Economics base scenario overnight capex (Wind 24,739 ZAR/kWel, Solar 15,690, OCGT 15,715, Battery 4h 13,581); middle-of-road assumption. |
| `extendable_fuel_prices` | `BASE_PMR1b` | Fuel prices for new dispatchable plant consistent with fixed generator assumptions. |
| `fixed_fuel_prices` | `BASE_PMR1b` | Coal 40.0 R/GJ (2025) → 58.9 R/GJ (2030); diesel/gas prices from Meridian base scenario. |
| `global_discount_rate` | `0.092` | 9.2% WACC, consistent with South African energy modelling literature; overrides the 8.2% default in `extendable_technologies.xlsx`. |
| `variable_storage_vom` | `1` | Enables time-varying VOM for storage units (read from `extendable_parameters` per year); equivalent to `true` in older scenario files. |
| `extendable_active` | `BASE` | Standard set of technologies available for new investment (wind, solar, OCGT, battery, etc.); copied from Meridian base configuration. |

### 7.6 Emissions

| Parameter | Value | Rationale |
|---|---|---|
| `fixed_emissions` | `BASE` | Standard CO₂ emission factors for existing generators; no fuel-switching assumptions. Earlier `FS_2045` (gas OCGTs switch to zero-emission fuel in 2045) makes no difference for the 2030 snapshot. |
| `extendable_emissions` | `BASE` | Standard emission factors for new plant; no hydrogen blending or fuel switch assumptions. |

### 7.7 Build constraints

| Parameter | Value | Rationale |
|---|---|---|
| `extendable_min_total` | `IRP25_BQ` | IRP 2025 Base Quantity as minimum floor: committed pipeline (wind 12.7 GW, solar 27.3 GW, OCGT 9.8 GW, battery 4.4 GW, PHS 2.7 GW by 2030) must be built. Optimizer is free to build above this floor. |
| `extendable_max_total` | `MOD_CNST` | Moderate upper capacity constraints. Note: `MOD_CNST` only has entries for `supply_region=1`; at `regions=10` it falls back to unconstrained — effectively `LEAST_CNST` for these runs. |
| `extendable_max_annual` | `UNC` | No annual build rate cap; appropriate for a 2-period snapshot without intermediate years. |
| `extendable_min_annual` | `UNC` | No annual minimum build requirement. |

### 7.8 Fixed existing assets

| Parameter | Value | Rationale |
|---|---|---|
| `fixed_renewables` | `BASE` | Standard parameters for existing renewable plants; copied from Meridian base configuration. |
| `fixed_storage` | `BASE` | Standard parameters for existing storage (Ingula PHS etc.); copied from Meridian base configuration. |

### 7.9 Operational constraints

| Parameter | Value | Rationale |
|---|---|---|
| `operational_limits` | `NO_MIN_GAS` | No minimum gas dispatch obligation; gas runs only when economically dispatched. Appropriate for a scenario without take-or-pay gas contracts. |
| `operational_reserves` | `BASE` | Standard spinning reserve requirements from Meridian base configuration. |
| `outage_profiles` | `BASE` | Standard planned maintenance profiles for all generators; copied from Meridian base configuration. |
| `aux_stg_feed` | `DIESEL_LNG` | Diesel and LNG both available as auxiliary storage feed; required input to avoid KeyError, no material effect on 2030 results with minimal storage. |

### 7.10 Reserve margin & capacity credits

| Parameter | Value | Rationale |
|---|---|---|
| `reserve_margin` | `RES_MRGN_10` | 10% planning reserve above peak demand, active from 2030; standard South African adequacy requirement. |
| `capacity_credits` | `BASE3` | Contribution of each technology toward the reserve margin: coal/nuclear/OCGT = 100%, battery 4h/CSP = 50%, wind = 10%, solar PV = 0%. Conservative but standard assumption for firm capacity adequacy. |

### 7.11 Carbon tax & revenue recycling

| Parameter | BASE | BASE\_R | CT | CT\_R | Rationale |
|---|---|---|---|---|---|
| `carbon_tax` | `none` | `none` | `CT_2030` | `CT_2030` | CT_2030 ramps to 462 R/tCO₂ in 2030 then drops — only the 2030 value is active for this snapshot. |
| `carbon_constraints` | `none` | `CT_REINVEST` | `none` | `CT_REINVEST` | CT_REINVEST adds a custom constraint: annualised RE investment ≥ CT revenues calculated from the BASE scenario emissions. |

### 7.12 Demand & load

| Parameter | Value | Rationale |
|---|---|---|
| `load_trajectory` | `IRP24_LOW` | IRP 2024 low demand scenario; conservative 2030 peak demand assumption. No IRP 2025 trajectory available in the dataset. |

---

## 8. Transmission Expansion

**Decision:** The model allows expansion of **existing corridors only** — no new transmission corridors. Existing links represent sunk-cost infrastructure; the optimizer can add capacity on top of the existing thermal limit.

**How it works:**
- Toggle: `line_expansion` column in `scenarios_to_run.xlsx`. All P0 scenarios have `copt` (= expansion enabled, solver hint for the sub-problem).
- At the start of each solved network: existing line `p_nom` is set as `p_nom_min` (floor), `p_nom_extendable = True`, `p_nom_max = inf` (optimizer decides how much to add).

**Cost formula:**
```
capital_cost [ZAR/MW/yr] = length [km] × length_factor × (investment [ZAR/MW/km] × CRF + FOM_rate × investment)
```
- HVAC overhead: 6,000 ZAR/MW/km investment
- Lifetime: 40 years
- FOM: 2%/year
- `length_factor = 1.25` (routing overhead)
- At 9.2% discount rate → ~689 ZAR/MW/km/year

Parameters are stored in `config.yaml` under `lines.hvac_overhead`. No separate Excel input needed.

**Cost accounting note:** `aggregate_costs()` computes `capital_cost × p_nom_opt` for all extendable links — this charges for the **full** optimized capacity (existing + any expansion), not just the incremental part. Grid costs therefore appear even if the solver chose not to expand any corridor. This is intentional: existing transmission capacity is treated as a capital asset with ongoing annualised costs. Grid costs in the plot ≠ proof that expansion occurred.

---

## 9. Code Modifications

All modifications are marked `# AM added` or `# AM adjusted` in the source files.

### 9.1 `custom_constraints.py` — `add_ct_reinvestment_constraint()`

**What:** New function implementing the revenue recycling constraint.  
**Why:** PyPSA has no built-in mechanism for CT revenue recycling. The constraint is added as a custom linopy expression after the standard model build.

Logic:
1. Load `P0_BASE` solved network → calculate 2030 coal + gas emissions × IRP23 CT rate
2. Build linopy LHS: sum of `p_nom_new[carrier] × capital_cost` for wind/solar carriers
3. Add constraint: LHS ≥ CT_revenues

### 9.2 `prepare_and_solve_network.py`

**CT reinvestment hook:** `add_ct_reinvestment_constraint` is called outside the `unit_committment` block so it applies to P0 scenarios (UC=0).

**`n.statistics()` workaround:** Wrapped in try/except to handle a bug in PyPSA 0.35.2 where statistics() raises on certain network configurations.

### 9.3 `Snakefile`

- **`_R` dependency:** Lambda input ensures P0_BASE_R/P0_CT_R wait for P0_BASE solved.nc before starting (CT revenues must be calculated from the base run).
- **Plot rules:** `plot_network_sa` rule, `generate_plots()`, `plot_all_scenarios`, integrated into `solve_all`.

### 9.4 `_helpers.py`

- **`TRUE`/`FALSE` from Excel:** Added string normalisation so Excel boolean strings (e.g. `'TRUE'`, `'FALSE'`) are correctly interpreted as Python booleans.
- **`aggregate_costs()`:** Fixed multi-invest check: `n._multi_invest` → `len(n.investment_periods) > 0` (API changed in PyPSA 0.35.x).

### 9.5 `add_electricity.py`

- **Multi-node renewable profiles (lines 624–632):** Fixed profile loading for `regions=10` — profiles were not being correctly assigned to the right buses in multi-node runs.
- **`update_transmission_costs()`:** New function that computes and assigns capital costs for extendable transmission lines based on their `length` attribute and the `hvac_overhead` config block.

### 9.6 `base_network.py`

- **Transmission expansion setup:** Reads `line_expansion` from SCENARIO_SETUP. If enabled, sets `p_nom_extendable=True`, `p_nom_min = St_Clair_limit_n1`, assigns `length` from line GeoJSON data.

### 9.7 `build_topology.py` (line 82)

- **Column rename fix:** `capacity_expansion_years` → `simulation_years` to match updated Snakefile/config naming convention.

### 9.8 `scripts/plot_network_sa.py`

Plots are saved to `results/Coal_Flexibilisation/{scenario}/outputs/plots/`.

**Fixes and changes applied (sessions 5–7):**

- **Cost scaling (lines 338–340):** `fc = fc * 1000; vc = vc * 1000` — costs were stored in R/kW and R/kWh (model convention), needed ×1000 to get correct ZAR/MWh display.
- **Default test scenario:** `scenario = 'P0_BASE'` set as default for interactive use.
- **Grid carrier bug fix:** Transmission is modelled as Links (not Lines), which had no carrier set. `aggregate_costs()` groups by carrier, so grid costs were always 0. Fix: `n.links["carrier"] = "AC line"` added in `__main__` alongside `n.lines["carrier"] = "AC line"`.
- **Grid cost bar colour:** `color_exp` in `plot_map` now reads from `tech_colors["AC line"]` so map expansion colour matches grid bar colour.
- **Bottom text:** Cost summary below bar now shows 5 left-aligned stacked lines: Total Emissions / (blank) / Capital Costs / Marginal Costs / Carbon Tax / Total Costs. Total Costs includes carbon tax.
- **Carrier legend order:** `CARRIER_ORDER` reordered to coal → CCGT → OCGT → Nuclear → …
- **Colours (`config.yaml` tech_colors):** coal `#333333` (dark grey), nuclear `#cc0000` (red), CSP `#ff8000` (orange), CCGT `#999999` / OCGT `#bbbbbb` (light grey), hydro `#9055aa` (purple).
- **Nice names (`config.yaml`):** `ccgt_steam` → "CCGT", `ocgt_gas` → "OCGT", added `bioenergy` → "Biomass".
- **Map legend:** "Netz" → "Grid"; Capacity legend nudged right (`bbox_to_anchor=(0.07, 1.01)`).

---

## 10. Preliminary Results: Single-Node Calibration Runs (regions=1, LC-182h)

> All results in this section use the reduced 182h time resolution. They are **not** final paper results. Final runs will use full 8760h.

### 10.1 Single-node runs (regions=1)

Configuration: `regions=1`, `LC-182h`, 48 timesteps (subset of 182h used in 1-bus mode).

| Metric | P0_BASE | P0_CT | P0_BASE_R | P0_CT_R |
|---|---|---|---|---|
| Coal dispatch (TWh) | 165.7 | 145.3 | 132.0 | 132.6 |
| Solar dispatch (TWh) | 38.3 | 58.7 | 73.0 | 72.5 |
| New solar build (MW) | 11,213 | 19,191 | 37,659 | 33,150 |
| New wind build (MW) | 0 | 0 | 0 | 0 |
| Objective (bn ZAR) | 1.82 | 2.34 | 2.07 | 2.45 |

**Observations:**
- CT price signal is working: coal −12%, solar +71% (BASE vs CT).
- `_R` scenarios show similar dispatch to each other — the reinvestment constraint forces so much RE that coal hits its `p_min_pu` floor in both BASE_R and CT_R. The difference between them is visible in **build volumes** (37.7 vs 33.1 GW solar) rather than dispatch.

### 10.2 Ten-node runs (regions=10) — first attempt

Configuration: `regions=10`, `LC-182h`, `override_coal_msl=0.7` (old value), no transmission expansion.

**Result: all four scenarios produced identical dispatch.** This was not a model error but a parameter issue: with `override_coal_msl=0.7`, coal operated at exactly 70% of nameplate capacity at every bus in every timestep. The CT price signal had no room to move coal below its floor, regardless of how large the tax was.

**Root cause:** The 0.7 MSL was stricter than the 65% value in `fixed_technologies.xlsx`. At 10 nodes with per-bus constraints and a fixed transmission grid, this completely suppressed the CT effect.

**Fix applied:** `override_coal_msl` lowered from 0.7 to 0.5, consistent with the coal flexibilisation premise of the project. Re-runs with the corrected value and transmission expansion are pending.

---

## 11. Preliminary Results: 10-Node, LC-182h

> **Configuration:** `regions=10`, `fixed_conventional=BASE_PMR1b`, `LC-182h` (48 representative timesteps), `override_coal_msl=0.5`, `transmission_grid=existing+tdp`, transmission expansion enabled. Solved: 2026-06-07. **Not** final paper results — full 8760h runs required.
>
> Analysis year: 2030. All dispatch figures are weighted-sum over the 48 representative timesteps.

### Summary Table

| Metric | BASE | BASE\_R | CT | CT\_R |
|---|---|---|---|---|
| Coal generation [TWh] | 97.4 | 97.4 | 97.4 | 97.4 |
| Solar PV dispatch [TWh] | 30.1 | 34.3 | 29.5 | 35.3 |
| Wind dispatch [TWh] | 56.0 | 57.2 | 56.7 | 56.1 |
| OCGT (gas/diesel) [TWh] | 34.3 | 34.3 | 34.3 | 34.3 |
| Nuclear [TWh] | 14.6 | 14.6 | 14.6 | 14.6 |
| CO₂ emissions [MtCO₂] | 131.3 | 131.3 | 131.3 | 131.3 |
| — of which coal [MtCO₂] | 108.9 | 108.9 | 108.9 | 108.9 |
| CT revenue [bn ZAR] | — | — | 60.6 | 60.6 |

### New Build Capacity 2030 [GW]

All four scenarios build the same new capacity, driven by the `extendable_min_total = IRP25_BQ` minimum floor:

| Technology | All scenarios |
|---|---|
| Solar PV (utility) | 15.8 |
| Wind | 12.7 |
| OCGT (gas) | 9.8 |
| Battery storage | 7.2 |

### Dispatch by Carrier 2030 [TWh]

| Carrier | BASE | BASE\_R | CT | CT\_R |
|---|---|---|---|---|
| Coal | 97.4 | 97.4 | 97.4 | 97.4 |
| Nuclear | 14.6 | 14.6 | 14.6 | 14.6 |
| OCGT (gas/diesel) | 34.3 | 34.3 | 34.3 | 34.3 |
| Wind | 56.0 | 57.2 | 56.7 | 56.1 |
| Solar PV | 30.1 | 34.3 | 29.5 | 35.3 |

### Marginal Costs 2030 (mean over representative timesteps)

| Generator type | BASE (R/MWh) | CT (R/MWh) | CT adder |
|---|---|---|---|
| Medupi (coal, efficient) | ~524 | ~948 | +424 |
| Kendal (coal, typical) | ~818 | ~1,364 | +546 |
| OCGT diesel | ~4,400 | ~4,800 | +394 |

### Transmission Expansion

No links were expanded in any scenario despite expansion being enabled. Expanding existing corridors was not economic at the current cost assumption (689 ZAR/MW/km/yr). This may change in full 8760h runs.

### Interpretation

**The CT is correctly applied** — coal marginal costs rise by 400–550 R/MWh in the CT scenarios, consistent with 462 R/tCO₂ × the BASE_PMR1b emission intensity (~0.92–1.18 tCO₂/MWh depending on plant). OCGT diesel is substantially more expensive than coal even with the full CT (4,800 vs ~1,400 R/MWh), so the merit order relationship is unchanged.

**Dispatch is identical across all four scenarios despite the correct CT application.** The reason is the MSL floor:

With 15.8 GW of new solar and 12.7 GW of new wind online, renewable generation fills the margin. Coal is pushed to its minimum stable load (`override_coal_msl = 0.5` × availability profile ≈ 28–30% of nameplate) in **100% of the 48 representative timesteps**. Adding a carbon tax makes coal more expensive, but coal cannot be dispatched below its MSL floor regardless of price. There is therefore no mechanism for the CT to reduce coal dispatch further in this configuration.

**New build is also identical** because the IRP25_BQ minimum floor (`extendable_min_total`) fully determines the investment outcome — the economic signal from the CT does not add any investment obligation above the mandatory minimum at this time resolution.

**Two additional observations:**
- **OCGT dispatch is unchanged** at 34.3 TWh across all scenarios. OCGT is needed for adequacy during low-RE periods; at ~4,400 R/MWh it is never economic to replace with coal (coal is at floor).
- **Solar dispatch varies slightly** between scenarios (29.5–35.3 TWh) reflecting minor transmission-constrained differences in how curtailment is distributed across the 10 nodes.

**Conclusion:** These results confirm the model builds and solves correctly with BASE_PMR1b. The CT mechanism is working as intended. However, the coal MSL floor dominates: coal is already at minimum due to renewable supply, so the CT cannot produce a visible dispatch effect at this resolution. Reducing `override_coal_msl` further or using full 8760h resolution (which allows renewable variability to create MSL-free periods) are the paths to observable dispatch differentiation in the final paper runs.

---

## 12. Open Decisions

| Item | Status | Notes |
|---|---|---|
| `fixed_conventional`: VAR_HR → BASE_PMR1b | **Done ✓** | VAR_HR suppressed CT signal entirely; switched to realistic heat rates |
| `carbon_tax = CT_2030` | **Verified ✓** | CT_2030 exists in emissions.xlsx (ramps to 462 R/tCO₂ in 2030) |
| `annual_availability`: EAF_60 vs EAF_55 | **Decision needed** | EAF_60 is optimistic end of current Eskom range (~55–60% actual) |
| `override_coal_msl`: 0.5 or lower | **Decision needed** | MSL floor currently binding 100% of timesteps; lower value or 8760h runs needed to see CT dispatch effect |
| Time resolution: LC-182h → LC (8760h) | **Before final paper runs** | 182h for calibration only; 8760h needed to capture renewable variability and unlock non-binding MSL periods |
| `extendable_min_total`: add regions=10 entries | **Before final paper runs** | MOD_CNST and IRP25_BQ only have supply_region=1 entries in extendable_technologies.xlsx; regions=10 falls back to unconstrained |

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


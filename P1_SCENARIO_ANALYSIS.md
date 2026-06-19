# P1 Scenario Analysis — Capacity & Dispatch Pathways 2025–2050
**Model:** PyPSA-RSA · Coal Flexibilisation · 1-bus · LC-182h  
**Date:** 2026-06-18  
**Scenarios:** P1_BASE, P1_BASE_R, P1_CT, P1_CT_R  
**extendable_min_total = UNC** (no IRP mandate, free investment)

---

## 1. Raw Results

### P1_BASE — No CT, No Recycling
| Period | Coal [GW] | Wind [GW] | Solar [GW] | Storage [GW] | Coal [TWh] | RE share |
|--------|-----------|-----------|------------|--------------|------------|----------|
| 2025   | 41.4      | 4.3       | 2.7        | 3.6          | 181.5      | 8.7%     |
| 2030   | 36.0      | 9.0       | 13.5       | 5.2          | 153.0      | 26.2%    |
| 2035   | 27.0      | 21.2      | 20.5       | 7.3          | 114.7      | 44.4%    |
| 2040   | 27.0      | 33.8      | 22.1       | 9.3          | 102.3      | 53.8%    |
| 2045   | 12.4      | 48.9      | 32.8       | 17.1         | 45.2       | 68.0%    |
| 2050   | 12.4      | 50.6      | 54.3       | 35.6         | 44.4       | 75.3%    |

### P1_BASE_R — No CT, With Revenue Recycling Constraint
| Period | Coal [GW] | Wind [GW] | Solar [GW] | Storage [GW] | Coal [TWh] | RE share |
|--------|-----------|-----------|------------|--------------|------------|----------|
| 2025   | 41.4      | 4.3       | 13.3       | 3.6          | 152.7      | 21.1%    |
| 2030   | 36.0      | 23.4      | 18.4       | 7.3          | 98.1       | 48.0%    |
| 2035   | 27.0      | 22.6      | 37.1       | 41.5         | 83.3       | 60.5%    |
| 2040   | 27.0      | 64.2      | 36.1       | 40.8         | 58.8       | 72.0%    |
| 2045   | 12.4      | 64.8      | 83.1       | 72.2         | 26.7       | 84.7%    |
| 2050   | 12.4      | 64.8      | 111.0      | 85.7         | 27.2       | 90.0%    |

### P1_CT — With CT, No Recycling
| Period | Coal [GW] | Wind [GW] | Solar [GW] | Storage [GW] | Coal [TWh] | RE share |
|--------|-----------|-----------|------------|--------------|------------|----------|
| 2025   | 41.4      | 4.3       | 2.7        | 3.6          | 181.3      | 8.8%     |
| 2030   | 36.0      | 17.5      | 17.0       | 4.5          | 117.1      | 40.4%    |
| 2035   | 27.0      | 35.0      | 24.0       | 12.8         | 81.7       | 60.4%    |
| 2040   | 27.0      | 45.8      | 30.9       | 19.7         | 74.2       | 66.9%    |
| 2045   | 12.4      | 50.8      | 61.6       | 52.4         | 34.7       | 81.3%    |
| 2050   | 12.4      | 54.0      | 83.9       | 70.6         | 33.8       | 87.2%    |

### P1_CT_R — With CT + Revenue Recycling
| Period | Coal [GW] | Wind [GW] | Solar [GW] | Storage [GW] | Coal [TWh] | RE share |
|--------|-----------|-----------|------------|--------------|------------|----------|
| 2025   | 41.4      | 4.3       | 13.3       | 3.6          | 152.5      | 21.2%    |
| 2030   | 36.0      | 26.9      | 21.1       | 9.3          | 87.5       | 52.7%    |
| 2035   | 27.0      | 26.1      | 46.4       | 34.6         | 64.7       | 67.0%    |
| 2040   | 27.0      | 63.2      | 45.4       | 33.9         | 57.7       | 72.3%    |
| 2045   | 12.4      | 63.6      | 94.3       | 72.5         | 26.3       | 84.8%    |
| 2050   | 12.4      | 63.6      | 116.4      | 88.2         | 26.8       | 90.1%    |

---

## 2. What is Happening — Explanation

### 2.1 Coal goes in discrete steps, not smoothly

Coal capacity is **identical across all 4 scenarios** in every period:
- 2025: 41.4 GW → 2030: 36.0 GW → 2035: 27.0 GW → 2040: 27.0 GW → 2045: 12.4 GW → 2050: 12.4 GW

This is by design: `phased_decom = DELAYED_ESKOM_2035` fixes a retirement schedule, and
`endogenous_coal_decom = 0` means the model cannot retire coal early — even if it would be
economically rational under high CT. The CT therefore affects **how much coal runs** (dispatch),
not when coal leaves the grid (capacity).

### 2.2 The CT effect works through dispatch, not capacity

Compare coal generation (TWh) in 2030:
- BASE: **153 TWh** (59% coal share)
- CT:   **117 TWh** (45% coal share)

Same coal capacity (36 GW), but CT makes coal expensive to run → coal is dispatched less,
wind+solar fill the gap. The CT rate in 2030 is 462 R/tCO₂ (IRP23 trajectory).

### 2.3 Why the big jump at 2035?

Two things happen simultaneously in 2035:
1. **Coal retires**: 36 → 27 GW (-9 GW) — the model must replace this capacity
2. **CT doubles**: 462 → 894 R/tCO₂ — coal dispatch becomes much more expensive

With `extendable_min_total = UNC`, the optimizer defers investment until necessary (perfect
foresight). It sees no reason to build RE in 2025–2030 beyond what is economically optimal
at low CT. In 2035, the combination of coal retirement + high CT forces a large RE build.
Result: wind jumps from 9 → 21 GW (BASE) or 17.5 → 35 GW (CT) in a single period.

This "lumpy" investment is a known artifact of perfect-foresight optimization with no annual
build rate constraint (`extendable_max_annual = UNC`). It is economically optimal but
unrealistic — in practice, grid infrastructure and supply chains cannot scale that fast.

### 2.4 Storage follows RE

Storage only becomes economic when there is enough variable RE to create mismatch between
generation and demand. This explains why storage grows slowly until 2035–2040, then
accelerates:
- BASE 2050:   35.6 GW storage | 75% RE
- CT 2050:     70.6 GW storage | 87% RE
- CT_R 2050:   88.2 GW storage | 90% RE

More RE → more variability → more storage needed. The CT_R scenario pushes solar to 116 GW
(vs 54 GW in BASE) — hence almost 3× more storage.

### 2.5 The recycling constraint (BASE_R and CT_R)

The `CT_REINVEST` constraint forces additional RE investment beyond what is economically
optimal without a carbon price. Even in BASE_R (no CT), the model builds 13.3 GW solar in
2025 vs. only 2.7 GW in BASE. By 2050, BASE_R reaches **90% RE share** — nearly identical
to CT_R (90.1%).

This raises an important question for the paper: **the recycling constraint has a stronger
effect than the CT itself**. Comparing:
- BASE → CT effect on RE share 2050: 75.3% → 87.2% (+12 pp)
- BASE → BASE_R recycling effect:    75.3% → 90.0% (+15 pp)
- CT → CT_R combined effect:         87.2% → 90.1% (+3 pp)

The reinvestment constraint dominates in the long run.

---

## 3. Key Numbers for Paper

### CT effect on coal dispatch (2030)
| | Coal TWh | Coal share |
|---|---|---|
| BASE | 153.0 | 59.4% |
| CT   | 117.1 | 45.3% |
| **Δ (CT effect)** | **-35.9 TWh** | **-14 pp** |

### RE capacity by 2050
| Scenario | Wind [GW] | Solar [GW] | Storage [GW] | RE share |
|---|---|---|---|---|
| BASE   | 50.6 | 54.3  | 35.6 | 75.3% |
| BASE_R | 64.8 | 111.0 | 85.7 | 90.0% |
| CT     | 54.0 | 83.9  | 70.6 | 87.2% |
| CT_R   | 63.6 | 116.4 | 88.2 | 90.1% |

---

## 4. Caveats / Limitations

- **Lumpy investment** at 2035: artifact of UNC annual build constraint + perfect foresight.
  Consider adding `extendable_max_annual` limits for more realistic pathways.
- **Coal capacity fixed**: model cannot respond to CT by retiring coal early. The CT signal
  works only through dispatch. This may understate the long-run CT effect.
- **VAR_HR** (optimistic coal efficiency) lowers coal marginal cost → CT needs to be higher
  to shift dispatch. A more realistic heat rate (BASE_PMR1b) would amplify the CT effect.
- **1-bus model**: no spatial heterogeneity, no transmission constraints. Results represent
  a system-average optimum, not regionally resolved investment.

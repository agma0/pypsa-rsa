# -*- coding: utf-8 -*-
# SPDX-FileCopyrightText: : 2017-2023 The PyPSA-Eur Authors
#
# SPDX-License-Identifier: MIT

"""
Plots map with pie charts and cost box bar charts.
Relevant Settings
-----------------
Inputs
------
Outputs
-------
Description
-----------
"""

import logging

import cartopy.crs as ccrs
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import geopandas as gpd
from _helpers import (
    aggregate_costs,
    aggregate_p,
)
from matplotlib.legend_handler import HandlerPatch
from matplotlib.patches import Circle, Ellipse


to_rgba = mpl.colors.colorConverter.to_rgba

logger = logging.getLogger(__name__)

# Carrier grouping for plots: detail → display group
CARRIER_REMAP = {
    'ocgt_gas':         'ocgt',
    'ocgt_gas_h2_40':   'ocgt',
    'ocgt_gas_h2_45':   'ocgt',
    'ocgt_gas_h2_50':   'ocgt',
    'ocgt_gas_h2_55':   'ocgt',
    'ocgt_gas_h2_60':   'ocgt',
    'ocgt_diesel':      'ocgt',
    'ocgt_blend':       'ocgt',
    'ocgt_avf':         'ocgt',
    'rmippp':           'ocgt',
    'sasol_gas':        'ocgt',
    'sasol_coal':       'coal',
    'battery_1h':       'battery',
    'battery_4h':       'battery',
    'battery_8h':       'battery',
    'solar_pv_low':     'solar_pv',
    'solar_pv_rooftop': 'solar_pv',
    'wind_low':         'wind',
}
CARRIER_DROP = {'hydro_import'}

# Display order: fossils → renewables → storage
CARRIER_ORDER = [
    'coal', 'ccgt_steam', 'ocgt', 'nuclear',
    'bioenergy', 'hydro', 'wind', 'solar_pv', 'solar_csp',
    'phs', 'battery',
]


def group_carriers(s, level=None):
    """Rename and re-aggregate carrier groups. Works on Series or DataFrame."""
    if level is not None:
        # MultiIndex Series (e.g. bus_sizes with levels [bus, carrier])
        buses = s.index.get_level_values(0)
        carriers = s.index.get_level_values(level).map(lambda c: CARRIER_REMAP.get(c, c))
        new_index = pd.MultiIndex.from_arrays([buses, carriers])
        s = pd.Series(s.values, index=new_index)
        mask = ~s.index.get_level_values(1).isin(CARRIER_DROP)
        return s[mask].groupby(level=[0, 1]).sum()
    else:
        s = s.rename(index=lambda c: CARRIER_REMAP.get(c, c))
        s = s[~s.index.isin(CARRIER_DROP)]
        return s.groupby(level=0).sum()


def make_handler_map_to_scale_circles_as_in(ax, dont_resize_actively=False):
    fig = ax.get_figure()

    def axes2pt():
        return np.diff(ax.transData.transform([(0, 0), (1, 1)]), axis=0)[0] * (
                72.0 / fig.dpi
        )

    ellipses = []
    if not dont_resize_actively:

        def update_width_height(event):
            dist = axes2pt()
            for e, radius in ellipses:
                e.width, e.height = 2.0 * radius * dist

        fig.canvas.mpl_connect("resize_event", update_width_height)
        ax.callbacks.connect("xlim_changed", update_width_height)
        ax.callbacks.connect("ylim_changed", update_width_height)

    def legend_circle_handler(
            legend, orig_handle, xdescent, ydescent, width, height, fontsize
    ):
        w, h = 2.0 * orig_handle.get_radius() * axes2pt()
        e = Ellipse(
            xy=(0.5 * width - 0.5 * xdescent, 0.5 * height - 0.5 * ydescent),
            width=w,
            height=w,
        )
        ellipses.append((e, orig_handle.get_radius()))
        return e

    return {Circle: HandlerPatch(patch_func=legend_circle_handler)}


def make_legend_circles_for(sizes, scale=1.0, **kw):
    return [Circle((0, 0), radius=(s / scale) ** 0.5, **kw) for s in sizes]


def set_plot_style():
    plt.style.use(
        [
            "classic",
            "seaborn-v0_8-whitegrid",
            # "seaborn-white",
            {
                "axes.grid": False,
                "grid.linestyle": "--",
                "grid.color": "0.6",
                "hatch.color": "white",
                "patch.linewidth": 0.5,
                "font.size": 12,
                "legend.fontsize": "medium",
                "lines.linewidth": 1.5,
                "pdf.fonttype": 42,
            },
        ]
    )


def plot_map(n, opts, ax=None, attribute="p_nom", boundaries=None, supply_regions_path=None, resarea_path=None):
    if ax is None:
        ax = plt.gca()

    ## DATA
    line_colors = {
        "cur": "#aec7e8",   # light blue — existing lines
        "exp": "#1f77b4",   # strong blue — expanded lines
    }
    tech_colors = opts["tech_colors"]

    if attribute == "p_nom":
        # bus_sizes = n.generators_t.p.sum().loc[n.generators.carrier == "load"].groupby(n.generators.bus).sum()
        n.generators.loc[n.generators.carrier.isin(["OCGT", "CCGT"]), "carrier"] = "gas"
        n.generators.loc[n.generators.carrier.isin(["hydro", "hydro-import", "hydro+PHS"]), "carrier"] = "hydro"
        if n.multi_invest and len(n.investment_periods) > 0:
            final_year = n.investment_periods[-1]
            active = (n.generators.build_year <= final_year) & \
                     (n.generators.build_year + n.generators.lifetime > final_year)
            gens_plot = n.generators[active]
        else:
            gens_plot = n.generators
        bus_sizes = group_carriers(pd.concat(
            (
                gens_plot.query('carrier != "load_shedding"')
                .groupby(["bus", "carrier"])
                .p_nom_opt.sum(),
                n.storage_units.groupby(["bus", "carrier"]).p_nom_opt.sum(),
            )
        ), level=1)
        line_widths_exp = n.lines.s_nom_opt
        line_widths_cur = n.lines.s_nom        # existing/original capacity
        link_widths_exp = n.links.p_nom_opt
        link_widths_cur = n.links.p_nom        # existing/original capacity
    else:
        raise "plotting of {} has not been implemented yet".format(attribute)

    ## FORMAT
    linewidth_factor = opts["map"][attribute]["linewidth_factor"]
    bus_size_factor = opts["map"][attribute]["bus_size_factor"]

    # Color each line/link: dark blue = expanded, light blue = existing
    color_exp = line_colors["exp"]   # dark blue  #1f77b4
    color_cur = line_colors["cur"]   # light blue #aec7e8
    expanded_lines = (n.lines.s_nom_opt - n.lines.s_nom) > 0.01 * n.lines.s_nom.clip(lower=1)
    line_colors_map = expanded_lines.map({True: color_exp, False: color_cur})
    expanded_links = (n.links.p_nom_opt - n.links.p_nom) > 0.01 * n.links.p_nom.clip(lower=1)
    link_colors_map = expanded_links.map({True: color_exp, False: color_cur})
    n_exp = expanded_links.sum()
    print(f"[plot_map] {n_exp}/{len(expanded_links)} links expanded; "
          f"p_nom range {n.links.p_nom.min():.0f}–{n.links.p_nom.max():.0f} MW, "
          f"p_nom_opt range {n.links.p_nom_opt.min():.0f}–{n.links.p_nom_opt.max():.0f} MW")

    if supply_regions_path is not None:
        supply_regions = gpd.read_file(supply_regions_path)
        supply_regions.plot(ax=ax, facecolor='none', edgecolor='black')
    if resarea_path is not None:
        resarea = gpd.read_file(resarea_path)
        resarea.plot(ax=ax, facecolor='gray', alpha=0.2)
    if boundaries is not None:
        ax.set_extent(boundaries, crs=ccrs.PlateCarree())

    ## PLOT — single pass: color by expansion status (green=existing, red=expanded)
    n.plot(
        line_widths=line_widths_exp / linewidth_factor,
        link_widths=link_widths_exp / linewidth_factor,
        line_colors=line_colors_map,
        link_colors=link_colors_map,
        bus_sizes=bus_sizes / bus_size_factor,
        bus_colors=tech_colors,
        boundaries=boundaries,
        color_geomap=True,
        geomap=True,
        ax=ax,
    )
    ax.set_aspect("equal")
    ax.axis("off")

    # Rasterize basemap
    for c in ax.collections[:2]:
        c.set_rasterized(True)

    # LEGEND — three side-by-side boxes, all at y=1.01 to avoid clipping
    # 1) Capacity circles
    cap_handles = make_legend_circles_for(
        [10e3, 1e3], scale=bus_size_factor, facecolor="w"
    )
    cap_labels = ["10 GW", "1 GW"]
    l2 = ax.legend(
        cap_handles,
        cap_labels,
        loc="upper left",
        bbox_to_anchor=(0.07, 1.01),
        frameon=False,
        labelspacing=0.8,
        fontsize=7,
        title="Capacity",
        title_fontsize=7,
        handler_map=make_handler_map_to_scale_circles_as_in(ax),
    )
    ax.add_artist(l2)

    # 2) Transmission line-width scale (10 GW = thick, 1 GW = thin)
    trans_handles = [
        plt.Line2D([0], [0], color=color_cur, linewidth=s * 1e3 / linewidth_factor)
        for s in (10, 1)
    ]
    trans_labels = ["10 GW", "1 GW"]
    l_width = ax.legend(
        trans_handles,
        trans_labels,
        loc="upper left",
        bbox_to_anchor=(0.26, 1.01),
        frameon=False,
        labelspacing=0.8,
        handletextpad=1.5,
        fontsize=7,
        title="Transmission",
        title_fontsize=7,
    )
    ax.add_artist(l_width)

    # 3) Netz: expanded (dark) vs existing (light)
    net_handles = [
        plt.Line2D([0], [0], color=color_exp, linewidth=3),
        plt.Line2D([0], [0], color=color_cur, linewidth=3),
    ]
    net_labels = ["Expanded", "Existing"]
    l1_1 = ax.legend(
        net_handles,
        net_labels,
        loc="upper left",
        bbox_to_anchor=(0.46, 1.01),
        frameon=False,
        labelspacing=0.8,
        fontsize=7,
        title="Grid",
        title_fontsize=7,
    )
    ax.add_artist(l1_1)

    # carriers present in data, sorted by CARRIER_ORDER
    present = set(bus_sizes.index.get_level_values(1).unique())
    techs = [c for c in CARRIER_ORDER if c in present and c in tech_colors]
    # append any remaining carriers not in CARRIER_ORDER
    techs += [c for c in present if c not in CARRIER_ORDER and c in tech_colors]

    handles = []
    labels = []
    for t in techs:
        handles.append(
            plt.Line2D(
                [0], [0], color=tech_colors[t], marker="o", markersize=14, linewidth=0
            )
        )
        labels.append(opts["nice_names"].get(t, t))

    l3 = ax.legend(
        handles,
        labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.1),
        handletextpad=1.0,
        columnspacing=2,
        handlelength=1.5,
        ncol=4,
        labelspacing=0.8,
    )

    return fig


def plot_total_energy_pie(n, opts, ax=None):
    if ax is None:
        ax = plt.gca()

    ax.set_title("Total Generation \nper Technology", fontdict=dict(fontsize="medium"))

    e_primary = aggregate_p(n).drop("load", errors="ignore")
    e_primary = group_carriers(e_primary)
    e_primary = e_primary.loc[e_primary > 0]
    e_primary = e_primary[e_primary.index.isin(opts["tech_colors"])]

    patches, texts, autotexts = ax.pie(
        e_primary,
        startangle=110,
        autopct="%.0f%%",
        pctdistance=1.3,
        shadow=False,
        colors=[opts["tech_colors"][tech] for tech in e_primary.index],
    )
    for autotext in autotexts:
        autotext.set_fontsize(8)

    for t2, i in zip(autotexts, e_primary.index):
        if e_primary.at[i] < 0.04 * e_primary.sum():
            t2.remove()


#############

def plot_total_cost_bar(n, opts, ax=None, gen_emissions_df=None, total_emissions=None):
    if ax is None:
        ax = plt.gca()

    tech_colors = opts["tech_colors"]
    nice_names = opts["nice_names"]

    fixed_cost, variable_cost = aggregate_costs(n)

    # sum over duplicate component rows and all investment periods, then group
    fc_raw = fixed_cost.groupby(level=0).sum()
    vc_raw = variable_cost.groupby(level=0).sum()

    # grid (AC line) capital cost — kept separate before grouping
    grid_fc = fc_raw.loc["AC line"].sum() if "AC line" in fc_raw.index else 0.0

    drop = {"load", "load_shedding", "AC transformer", "AC line", "AC-AC"}
    fc = group_carriers(fc_raw.sum(axis=1).drop(index=drop, errors="ignore"))
    vc = group_carriers(vc_raw.sum(axis=1).drop(index=drop, errors="ignore"))

    # Model stores costs in R/kW (capital) and R/kWh (marginal) instead of PyPSA's
    # expected R/MW and R/MWh — multiply by 1000 to get correct ZAR values for display.
    # CO2 bar is unaffected (calculated from physical kgCO2/MWh × R/tCO2 units).
    fc = fc * 1000
    vc = vc * 1000
    grid_fc = grid_fc * 1000

    from _helpers import get_as_dense
    load_p = get_as_dense(n, "Load", "p_set", n.snapshots).sum(axis=1)
    total_load = (n.snapshot_weightings.generators * load_p).sum()

    print(f"[cost bar] total_load={total_load/1e6:.1f} TWh, "
          f"FC={fc.sum()/1e9:.2f} bn ZAR, VC={vc.sum()/1e9:.2f} bn ZAR, "
          f"Grid={grid_fc/1e9:.2f} bn ZAR")
    fc_pmwh = fc / total_load
    vc_pmwh = vc / total_load
    print("[cost bar] FC by carrier [R/MWh]:")
    for c, v in fc_pmwh[fc_pmwh > 0].items():
        print(f"  {c}: {v:.1f}")
    print("[cost bar] VC by carrier [R/MWh]:")
    for c, v in vc_pmwh[vc_pmwh > 0].items():
        print(f"  {c}: {v:.1f}")

    all_carriers = fc.index.union(vc.index)
    present = [c for c in all_carriers if c in tech_colors
               and (fc.get(c, 0.0) + vc.get(c, 0.0)) > 0]
    carriers = [c for c in CARRIER_ORDER if c in present]
    carriers += [c for c in present if c not in CARRIER_ORDER]

    # bar x-positions: Capital, Marginal, CO2, Grid  width=0.22
    bw = 0.22
    x_cap, x_marg, x_co2, x_grid = 0.15, 0.42, 0.69, 0.96

    bottom_cap = 0.0
    bottom_marg = 0.0
    for c in carriers:
        cap  = fc.get(c, 0.0) / total_load
        marg = vc.get(c, 0.0) / total_load
        ax.bar([x_cap],  [cap],  bottom=bottom_cap,  color=tech_colors[c], width=bw, zorder=-1)
        ax.bar([x_marg], [marg], bottom=bottom_marg, color=tech_colors[c], width=bw, zorder=-1)
        if cap > 30:
            ax.text(x_cap,  bottom_cap  + 0.5 * cap,  nice_names.get(c, c),
                    ha="center", va="center", fontsize=7, color="white")
        if marg > 30:
            ax.text(x_marg, bottom_marg + 0.5 * marg, nice_names.get(c, c),
                    ha="center", va="center", fontsize=7, color="white")
        bottom_cap  += cap
        bottom_marg += marg

    # Bar 3: CO2 cost by carrier [R/MWh]
    co2_cost_bn = None
    if gen_emissions_df is not None:
        ct_rate = opts.get("carbon_tax_rate_2030", 462)
        energy_all = (
            n.generators_t.p
            .multiply(n.snapshot_weightings.generators, axis=0)
            .groupby(level=0).sum()
        )
        common = gen_emissions_df.columns.intersection(energy_all.columns)
        carrier_map = n.generators.loc[common, "carrier"].map(
            lambda c: CARRIER_REMAP.get(c, c)
        )
        co2_cost_total = pd.Series(0.0, index=carrier_map.unique())
        for y in n.investment_periods:
            if y not in gen_emissions_df.index:
                continue
            co2_cost_y = energy_all.loc[y, common] * gen_emissions_df.loc[y, common] * ct_rate / 1000
            co2_cost_total = co2_cost_total.add(
                co2_cost_y.groupby(carrier_map).sum(), fill_value=0
            )
        co2_by_carrier = co2_cost_total[
            (~co2_cost_total.index.isin(CARRIER_DROP)) & (co2_cost_total > 0)
        ] / total_load
        # Summary text: CO2 cost for target year only (consistent with total_emissions = co2_2030)
        target_y = n.investment_periods[-1] if len(n.investment_periods) > 0 else None
        if target_y is not None and target_y in gen_emissions_df.index:
            co2_target = energy_all.loc[target_y, common] * gen_emissions_df.loc[target_y, common] * ct_rate / 1000
            co2_cost_bn = co2_target.groupby(carrier_map).sum().sum() / 1e9
        else:
            co2_cost_bn = co2_by_carrier.sum() * total_load / 1e9
        print(f"[cost bar] CO2 bar={co2_by_carrier.sum():.1f} R/MWh  "
              f"({target_y} only: {co2_cost_bn:.1f} bn ZAR)")
        bottom_co2 = 0.0
        for c in CARRIER_ORDER:
            if c not in co2_by_carrier.index:
                continue
            val = co2_by_carrier[c]
            ax.bar([x_co2], [val], bottom=bottom_co2, color=tech_colors.get(c, "gray"),
                   width=bw, zorder=-1)
            if val > 30:
                ax.text(x_co2, bottom_co2 + 0.5 * val, nice_names.get(c, c),
                        ha="center", va="center", fontsize=7, color="white")
            bottom_co2 += val

    # Bar 4: Grid capital cost — split existing (light blue) vs expanded (dark blue)
    color_grid_cur = "#aec7e8"   # light blue — matches map existing
    color_grid_exp = "#1f77b4"   # dark blue  — matches map expanded
    ext = n.links[n.links.p_nom_extendable]
    if not ext.empty:
        existing_grid_fc = (ext.capital_cost * ext.p_nom_min).sum() * 1000
        expanded_grid_fc = (ext.capital_cost * (ext.p_nom_opt - ext.p_nom_min).clip(lower=0)).sum() * 1000
    else:
        existing_grid_fc = grid_fc
        expanded_grid_fc = 0.0
    grid_fc = existing_grid_fc + expanded_grid_fc   # update total for summary text
    existing_rmwh = existing_grid_fc / total_load if total_load > 0 else 0.0
    expanded_rmwh = expanded_grid_fc / total_load if total_load > 0 else 0.0
    ax.bar([x_grid], [existing_rmwh], color=color_grid_cur, width=bw, zorder=-1)
    ax.bar([x_grid], [expanded_rmwh], bottom=existing_rmwh, color=color_grid_exp, width=bw, zorder=-1)
    print(f"[cost bar] Grid existing={existing_rmwh:.1f} R/MWh, expanded={expanded_rmwh:.1f} R/MWh")

    ct_rate = opts.get("carbon_tax_rate_2030", 462)
    ax.set_xticks([x_cap, x_marg, x_co2, x_grid])
    ax.set_xticklabels(["Capital", "Marginal", f"CO₂\nTax\n({ct_rate} R/t)", "Grid"], fontsize=7)
    ax.set_ylabel("Avg system cost [R/MWh]")
    ax.set_xlim([0, 1.15])
    ax.set_title("System Cost", fontdict=dict(fontsize="medium"))
    ax.grid(True, axis="y", color="k", linestyle="dotted")

    # Cost summary text below bars
    fc_total = sum(fc.get(c, 0.0) for c in carriers)
    vc_total = sum(vc.get(c, 0.0) for c in carriers)
    co2_total = (co2_cost_bn * 1e9) if co2_cost_bn is not None else 0.0
    total_all = fc_total + vc_total + grid_fc + co2_total
    em_str = f"{total_emissions:.1f} MtCO₂/a" if total_emissions is not None else "n/a"
    ct_str = f"{co2_cost_bn:.0f} bn ZAR/a" if co2_cost_bn is not None else "n/a"
    summary = "\n".join([
        f"Total Emissions:  {em_str}",
        f"",
        f"Capital Costs:    {fc_total/1e9:.0f} bn ZAR/a",
        f"Marginal Costs:   {vc_total/1e9:.0f} bn ZAR/a",
        f"Carbon Tax:       {ct_str}",
        f"Total Costs:      {total_all/1e9:.0f} bn ZAR/a",
    ])
    ax.text(
        0.0, -0.30,
        summary,
        transform=ax.transAxes, ha="left", va="top", fontsize=7,
        linespacing=1.6,
    )


##########

def plot_pathway(n, opts, gen_emissions_df=None, scenario_name="", ct_rates=None):
    """8-panel pathway plot: capacity, generation, cost-by-carrier, CO2,
    emissions intensity, fossil+curtailment, battery storage, newbuild+CT revenue."""
    tech_colors = opts["tech_colors"]
    nice_names  = opts.get("nice_names", {})
    REINVEST_FRACTION = 0.5

    periods = list(n.investment_periods) if (n.multi_invest and len(n.investment_periods) > 0) \
              else [int(str(n.snapshots[0])[:4])]

    # ── 1. Capacity [GW] per period ────────────────────────────────────────────
    cap_rows = {}
    for y in periods:
        active = (
            (n.generators.build_year <= y)
            & (n.generators.build_year + n.generators.lifetime > y)
            & (~n.generators.carrier.isin(["load_shedding"]))
        )
        gy = n.generators[active].copy()
        gy["carrier"] = gy["carrier"].map(lambda c: CARRIER_REMAP.get(c, c))
        gy = gy[~gy["carrier"].isin(CARRIER_DROP)]
        cap_rows[y] = gy.groupby("carrier")["p_nom_opt"].sum() / 1e3  # GW
    cap_df = pd.DataFrame(cap_rows).T.fillna(0)

    # ── 2. Generation [TWh/a] per period ───────────────────────────────────────
    if n.multi_invest:
        ef = (n.generators_t.p
              .multiply(n.snapshot_weightings.generators, axis=0)
              .groupby(level=0).sum())
    else:
        ev = (n.generators_t.p
              .multiply(n.snapshot_weightings.generators, axis=0).sum())
        ef = pd.DataFrame([ev.values], index=pd.Index(periods), columns=ev.index)

    cmap = n.generators["carrier"].map(lambda c: CARRIER_REMAP.get(c, c))
    drop = cmap.isin(CARRIER_DROP | {"load_shedding"})
    gen_df = (ef.loc[:, ~drop].rename(columns=cmap[~drop])
               .T.groupby(level=0).sum().T / 1e6)       # TWh
    gen_df = gen_df.reindex(periods).fillna(0)

    # ── 3. System costs by carrier [bn ZAR/a] per period ──────────────────────
    cost_carrier_rows = {}
    for y in periods:
        active_mask = (
            (n.generators.build_year <= y)
            & (n.generators.build_year + n.generators.lifetime > y)
            & (~n.generators.carrier.isin(["load_shedding"]))
        )
        gy = n.generators[active_mask].copy()
        gy["dc"] = gy["carrier"].map(lambda c: CARRIER_REMAP.get(c, c))
        gy = gy[~gy["dc"].isin(CARRIER_DROP)]
        # capital: R/kW × MW × 1000 kW/MW / 1e9 = bn ZAR/a
        fc_per = (gy["capital_cost"] * gy["p_nom_opt"] * 1000).groupby(gy["dc"]).sum() / 1e9
        if y in ef.index:
            common_y = ef.columns.intersection(gy.index)
            dc_map = n.generators.loc[common_y, "carrier"].map(lambda c: CARRIER_REMAP.get(c, c))
            # marginal: R/kWh × MWh × 1000 kWh/MWh / 1e9 = bn ZAR/a
            vc_per = (ef.loc[y, common_y] * n.generators.loc[common_y, "marginal_cost"] * 1000
                      ).groupby(dc_map).sum() / 1e9
        else:
            vc_per = pd.Series(dtype=float)
        cost_carrier_rows[y] = fc_per.add(vc_per, fill_value=0)
    cost_carrier_df = pd.DataFrame(cost_carrier_rows).T.fillna(0)

    # ── 4. CO₂ [MtCO₂/a] per period ───────────────────────────────────────────
    co2_s = pd.Series(0.0, index=pd.Index(periods))
    if gen_emissions_df is not None:
        try:
            common = gen_emissions_df.columns.intersection(ef.columns)
            co2_s = (ef[common] * gen_emissions_df[common]).sum(axis=1) / 1e9
            co2_s = co2_s.reindex(periods).fillna(0)
        except Exception:
            pass

    # ── 5. Emissions intensity [tCO₂/MWh] ─────────────────────────────────────
    total_gen_twh = gen_df.sum(axis=1)
    ei_s = (co2_s * 1000 / total_gen_twh.replace(0, np.nan)).fillna(0)

    # ── 6. Fossil capacity [GW] + RE curtailment [TWh/a] ──────────────────────
    re_raw = {"solar_pv", "solar_pv_low", "solar_pv_rooftop", "wind", "wind_low", "solar_csp"}
    curtail_rows = {}
    for y in periods:
        try:
            active = (
                (n.generators.build_year <= y)
                & (n.generators.build_year + n.generators.lifetime > y)
                & n.generators.carrier.isin(re_raw)
            )
            re_idx = n.generators.index[active]
            if len(re_idx) == 0 or y not in ef.index:
                curtail_rows[y] = 0.0
                continue
            p_nom = n.generators.loc[re_idx, "p_nom_opt"]
            w = (n.snapshot_weightings.generators.loc[y] if n.multi_invest
                 else n.snapshot_weightings.generators)
            if n.multi_invest:
                p_act = n.generators_t.p.loc[y].reindex(columns=re_idx, fill_value=0)
            else:
                p_act = n.generators_t.p.reindex(columns=re_idx, fill_value=0)
            act_twh = p_act.multiply(w, axis=0).sum().sum() / 1e6
            t_pmu = n.generators_t.p_max_pu
            if not t_pmu.empty and n.multi_invest:
                pmu_y = (t_pmu.loc[y]
                         if y in t_pmu.index.get_level_values(0) else pd.DataFrame())
            elif not t_pmu.empty:
                pmu_y = t_pmu
            else:
                pmu_y = pd.DataFrame()
            common_re = re_idx.intersection(pmu_y.columns) if not pmu_y.empty else pd.Index([])
            avail_twh = 0.0
            if len(common_re) > 0:
                avail_twh += (pmu_y[common_re].multiply(w, axis=0)
                              .mul(p_nom[common_re]).sum().sum() / 1e6)
            fixed_re = re_idx.difference(common_re)
            if len(fixed_re) > 0:
                avail_twh += (n.generators.loc[fixed_re, "p_max_pu"]
                              * p_nom[fixed_re] * w.sum()).sum() / 1e6
            curtail_rows[y] = max(0.0, avail_twh - act_twh)
        except Exception:
            curtail_rows[y] = 0.0
    curtail_s = pd.Series(curtail_rows)

    # ── 7. Battery storage: power [GW] by type + energy [GWh] ─────────────────
    bat_carriers_raw = {"battery_1h", "battery_4h", "battery_8h"}
    bat_hours_map = {"battery_1h": 1, "battery_4h": 4, "battery_8h": 8}
    stor_by_type_rows = {}  # {y: {carrier: GW}}
    stor_energy_rows  = {}  # {y: GWh}

    for y in periods:
        by_type = {}
        energy = 0.0
        if not n.storage_units.empty:
            su = n.storage_units
            if "build_year" in su.columns and "lifetime" in su.columns:
                active_su = su[
                    (su.build_year <= y)
                    & (su.build_year + su.lifetime > y)
                    & su.carrier.isin(bat_carriers_raw)
                ]
            else:
                active_su = su[su.carrier.isin(bat_carriers_raw)]
            for c, grp in active_su.groupby("carrier"):
                gw = grp["p_nom_opt"].sum() / 1e3
                by_type[c] = by_type.get(c, 0.0) + gw
                energy += (grp["p_nom_opt"] * grp["max_hours"]).sum() / 1e3  # GWh
        # also catch batteries modelled as generators
        gen_active = (
            (n.generators.build_year <= y)
            & (n.generators.build_year + n.generators.lifetime > y)
            & n.generators.carrier.isin(bat_carriers_raw)
        )
        for c, grp in n.generators[gen_active].groupby("carrier"):
            gw = grp["p_nom_opt"].sum() / 1e3
            by_type[c] = by_type.get(c, 0.0) + gw
            energy += gw * bat_hours_map.get(c, 4)
        stor_by_type_rows[y] = by_type
        stor_energy_rows[y]  = energy

    stor_by_type_df = pd.DataFrame(stor_by_type_rows).T.fillna(0)
    stor_energy_s   = pd.Series(stor_energy_rows)

    # ── 8. New build per period [GW] by carrier + CT revenue [bn ZAR/a] ────────
    newbuild_rows = {}
    for y in periods:
        nb = {}
        # generators
        new_g = n.generators[
            (n.generators.build_year == y)
            & n.generators.p_nom_extendable
            & (~n.generators.carrier.isin(["load_shedding"]))
        ].copy()
        new_g["dc"] = new_g["carrier"].map(lambda c: CARRIER_REMAP.get(c, c))
        new_g = new_g[~new_g["dc"].isin(CARRIER_DROP)]
        for dc, grp in new_g.groupby("dc"):
            nb[dc] = nb.get(dc, 0.0) + grp["p_nom_opt"].sum() / 1e3
        # storage_units
        if not n.storage_units.empty and "build_year" in n.storage_units.columns:
            new_su = n.storage_units[
                (n.storage_units.build_year == y)
                & n.storage_units.p_nom_extendable
            ].copy()
            new_su["dc"] = new_su["carrier"].map(lambda c: CARRIER_REMAP.get(c, c))
            for dc, grp in new_su.groupby("dc"):
                nb[dc] = nb.get(dc, 0.0) + grp["p_nom_opt"].sum() / 1e3
        newbuild_rows[y] = nb
    newbuild_df = pd.DataFrame(newbuild_rows).T.fillna(0)

    ct_rev_list, reinvest_list = [], []
    for y in periods:
        if isinstance(ct_rates, dict):
            rate = ct_rates.get(y, 0.0)
        else:
            rate = float(ct_rates) if ct_rates is not None else 0.0
        rev = co2_s.get(y, 0.0) * 1e6 * rate / 1e9  # MtCO2 × t/Mt × R/t / bn = bn ZAR/a
        ct_rev_list.append(rev)
        reinvest_list.append(rev * REINVEST_FRACTION)
    ct_rev_s   = pd.Series(ct_rev_list, index=pd.Index(periods))
    reinvest_s = pd.Series(reinvest_list, index=pd.Index(periods))

    # ── PLOT ───────────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(4, 2, figsize=(14, 18))
    fig.suptitle(scenario_name, fontsize=13, fontweight="bold")
    ax_cap,  ax_gen  = axes[0, 0], axes[0, 1]
    ax_cost, ax_co2  = axes[1, 0], axes[1, 1]
    ax_ei,   ax_coal = axes[2, 0], axes[2, 1]
    ax_stor, ax_new  = axes[3, 0], axes[3, 1]
    x   = np.arange(len(periods))
    bw  = 0.65
    xlim = (-0.5, len(periods) - 0.5)

    def stacked_bars(ax, df, ylabel, title):
        order = [c for c in CARRIER_ORDER if c in df.columns]
        order += [c for c in df.columns if c not in CARRIER_ORDER]
        bottom = np.zeros(len(periods))
        for c in order:
            if c not in tech_colors or df[c].sum() < 0.01:
                continue
            vals = df[c].values
            ax.bar(x, vals, bottom=bottom, width=bw,
                   color=tech_colors[c], label=nice_names.get(c, c))
            bottom += vals
        ax.set_xlim(xlim)
        ax.set_xticks(x); ax.set_xticklabels(periods, rotation=45)
        ax.set_ylabel(ylabel); ax.set_title(title)
        ax.legend(loc="upper left", fontsize=7, ncol=2)

    # Panels 1–2: capacity & generation (unchanged)
    stacked_bars(ax_cap, cap_df,  "Installed Capacity [GW]", "Capacity")
    stacked_bars(ax_gen, gen_df,  "Generation [TWh/a]",      "Generation")

    # Panel 3: system cost stacked by carrier
    stacked_bars(ax_cost, cost_carrier_df, "System Cost [bn ZAR/a]", "System Cost by Carrier")

    # Panel 4: CO₂
    ax_co2.bar(x, co2_s.values, width=bw, color="#555555")
    ax_co2.set_xlim(xlim)
    ax_co2.set_xticks(x); ax_co2.set_xticklabels(periods, rotation=45)
    ax_co2.set_ylabel("CO₂ Emissions [MtCO₂/a]"); ax_co2.set_title("CO₂ Emissions")

    # Panel 5: emissions intensity
    ax_ei.plot(x, ei_s.values, color="#e74c3c", marker="o", linewidth=2)
    ax_ei.set_xlim(xlim)
    ax_ei.set_xticks(x); ax_ei.set_xticklabels(periods, rotation=45)
    ax_ei.set_ylabel("Emissions Intensity [tCO₂/MWh]")
    ax_ei.set_title("Emissions Intensity")
    ax_ei.set_ylim(bottom=0)

    # Panel 6: fossil capacity + RE curtailment
    fossil_carriers = [("coal", "Coal"), ("ccgt_steam", "CCGT"), ("ocgt", "OCGT/Gas")]
    bottom_fossil = np.zeros(len(periods))
    for carrier, label in fossil_carriers:
        vals = cap_df.get(carrier, pd.Series(0.0, index=pd.Index(periods))).reindex(periods).fillna(0).values
        ax_coal.bar(x, vals, bottom=bottom_fossil, width=bw,
                    color=tech_colors.get(carrier, "#bbbbbb"), alpha=0.85, label=label)
        bottom_fossil += vals
    ax_coal.set_xlim(xlim)
    ax_coal.set_ylabel("Fossil Capacity [GW]")
    ax_coal.set_title("Fossil Capacity & RE Curtailment")
    ax_coal.set_xticks(x); ax_coal.set_xticklabels(periods, rotation=45)
    ax_coal2 = ax_coal.twinx()
    ax_coal2.plot(x, curtail_s.reindex(periods).fillna(0).values,
                  color="#e67e22", marker="s", linewidth=2, label="RE curtailment")
    ax_coal2.set_ylabel("RE Curtailment [TWh/a]", color="#e67e22")
    ax_coal2.tick_params(axis="y", labelcolor="#e67e22")
    h1, l1 = ax_coal.get_legend_handles_labels()
    h2, l2 = ax_coal2.get_legend_handles_labels()
    ax_coal.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper center", ncol=2)

    # Panel 7: battery storage — stacked power [GW] by type + energy [GWh] line
    bat_order = ["battery_1h", "battery_4h", "battery_8h"]
    bottom_stor = np.zeros(len(periods))
    has_stor = False
    for c in bat_order:
        if c not in stor_by_type_df.columns or stor_by_type_df[c].sum() < 0.001:
            continue
        vals = stor_by_type_df[c].reindex(periods).fillna(0).values
        ax_stor.bar(x, vals, bottom=bottom_stor, width=bw,
                    color=tech_colors.get(c, "#7ac677"),
                    label=nice_names.get(c, c))
        bottom_stor += vals
        has_stor = True
    if not has_stor:
        # fallback: total battery from cap_df if individual types not resolved
        bat_total = cap_df.get("battery", pd.Series(0.0, index=pd.Index(periods))).reindex(periods).fillna(0)
        ax_stor.bar(x, bat_total.values, width=bw,
                    color=tech_colors.get("battery", "#7ac677"), label="Battery")
    ax_stor.set_xlim(xlim)
    ax_stor.set_xticks(x); ax_stor.set_xticklabels(periods, rotation=45)
    ax_stor.set_ylabel("Battery Power [GW]")
    ax_stor.set_title("Battery Storage")
    ax_stor2 = ax_stor.twinx()
    ax_stor2.plot(x, stor_energy_s.reindex(periods).fillna(0).values,
                  color="#c0392b", marker="^", linewidth=2, linestyle="--", label="Energy [GWh]")
    ax_stor2.set_ylabel("Battery Energy [GWh]", color="#c0392b")
    ax_stor2.tick_params(axis="y", labelcolor="#c0392b")
    h1, l1 = ax_stor.get_legend_handles_labels()
    h2, l2 = ax_stor2.get_legend_handles_labels()
    ax_stor.legend(h1 + h2, l1 + l2, fontsize=8, loc="upper left", ncol=2)

    # Panel 8: new build per period [GW] + CT revenue lines
    stacked_bars(ax_new, newbuild_df, "New Build [GW]", "New Build per Period & CT Revenue")
    ax_new2 = ax_new.twinx()
    if ct_rev_s.sum() > 0:
        ax_new2.plot(x, ct_rev_s.values, color="#8e44ad", marker="o",
                     linewidth=2, label="CT Revenue")
        ax_new2.plot(x, reinvest_s.values, color="#8e44ad", marker="o",
                     linewidth=2, linestyle="--",
                     label=f"Reinvested ({int(REINVEST_FRACTION * 100)}%)")
        ax_new2.set_ylabel("CT Revenue [bn ZAR/a]", color="#8e44ad")
        ax_new2.tick_params(axis="y", labelcolor="#8e44ad")
        ax_new2.annotate(
            f"50% of CT revenues reinvested in RE + storage",
            xy=(0.98, 0.02), xycoords="axes fraction",
            ha="right", va="bottom", fontsize=7, color="#8e44ad", style="italic",
        )
        h1, l1 = ax_new.get_legend_handles_labels()
        h2, l2 = ax_new2.get_legend_handles_labels()
        ax_new.legend(h1 + h2, l1 + l2, fontsize=7, loc="upper left", ncol=2)

    fig.tight_layout()
    return fig


##########

if __name__ == "__main__":
    if "snakemake" not in globals():
        from _helpers import mock_snakemake
        snakemake = mock_snakemake('plot_network', scenario='P0_BASE')
    import pypsa
    config = snakemake.config

    n = pypsa.Network(snakemake.input.network)
    n.loads["carrier"] = n.loads.bus.map(n.buses.carrier) + " load"
    n.stores["carrier"] = n.stores.bus.map(n.buses.carrier)
    n.lines["carrier"] = "AC line"
    n.links["carrier"] = "AC line"   # transmission links — same carrier for cost aggregation
    n.transformers["carrier"] = "AC transformer"

    set_plot_style()

    map_figsize = config["plotting"]["map"]["figsize"]
    map_boundaries = config["plotting"]["map"]["boundaries"]

    fig, ax = plt.subplots(
        figsize=map_figsize, subplot_kw={"projection": ccrs.PlateCarree()}
    )
    plot_map(
        n, config["plotting"], ax=ax, attribute="p_nom",
        boundaries=map_boundaries,
        supply_regions_path=snakemake.input.supply_regions,
        resarea_path=snakemake.input.resarea,
    )

    display_year = n.investment_periods[-1] if (n.multi_invest and len(n.investment_periods) > 0) else int(str(n.snapshots[0])[:4])
    ax.set_title(f"{snakemake.wildcards.scenario}  |  {display_year}", fontsize=11, pad=8)

    fig.savefig(snakemake.output.only_map, dpi=150, bbox_inches="tight")

    # Load generator emissions once — used for CO2 text and cost bar
    gen_em = None
    co2_2030 = 0.0
    try:
        gen_em = pd.read_csv(snakemake.input.gen_emissions, index_col=0)
        energy_all = (
            n.generators_t.p
            .multiply(n.snapshot_weightings.generators, axis=0)
            .groupby(level=0).sum()
        )
        common = gen_em.columns.intersection(energy_all.columns)
        co2_by_period = (energy_all[common] * gen_em[common]).sum(axis=1) / 1e9  # MtCO2
        co2_2030 = co2_by_period.get(2030, co2_by_period.iloc[-1])
        pass  # CO2 shown in cost bar text below
    except Exception:
        pass

    ax1 = fig.add_axes([-0.115, 0.5, 0.2, 0.2])
    plot_total_energy_pie(n, config["plotting"], ax=ax1)

    ax2 = fig.add_axes([-0.115, 0.15, 0.22, 0.30])
    plot_total_cost_bar(n, config["plotting"], ax=ax2, gen_emissions_df=gen_em, total_emissions=co2_2030)

    fig.savefig(snakemake.output.ext, transparent=True, bbox_inches='tight')

    scenario = snakemake.wildcards.scenario
    ct_rates = None
    if "CT" in scenario:
        base_rate = config["plotting"].get("carbon_tax_rate_2030", 462)
        inv_periods_plot = (list(n.investment_periods)
                            if (n.multi_invest and len(n.investment_periods) > 0)
                            else [int(str(n.snapshots[0])[:4])])
        ct_rates = {y: base_rate for y in inv_periods_plot}

    fig_pathway = plot_pathway(
        n, config["plotting"],
        gen_emissions_df=gen_em,
        scenario_name=scenario,
        ct_rates=ct_rates,
    )
    fig_pathway.savefig(snakemake.output.pathway, dpi=150, bbox_inches="tight")
    plt.close(fig_pathway)

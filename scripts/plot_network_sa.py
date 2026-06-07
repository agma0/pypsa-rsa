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
        bus_sizes = group_carriers(pd.concat(
            (
                n.generators.query('carrier != "load_shedding"')
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

    # Color each line: dark blue = expanded, light blue = existing
    color_exp = line_colors["exp"]   # dark blue
    color_cur = line_colors["cur"]   # light blue
    expanded_lines = (n.lines.s_nom_opt - n.lines.s_nom) > 0.01 * n.lines.s_nom.clip(lower=1)
    line_colors_map = expanded_lines.map({True: color_exp, False: color_cur})
    expanded_links = (n.links.p_nom_opt - n.links.p_nom) > 0.01 * n.links.p_nom.clip(lower=1)
    link_colors_map = expanded_links.map({True: color_exp, False: color_cur})

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
        co2_cost_bn = co2_by_carrier.sum() * total_load / 1e9
        print(f"[cost bar] CO2 total={co2_by_carrier.sum():.1f} R/MWh  ({co2_cost_bn:.1f} bn ZAR)")
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

    # Bar 3: Grid (AC line) capital cost [R/MWh]
    grid_color = opts["tech_colors"].get("AC line", "#6c9459")
    grid_rmwh = grid_fc / total_load if total_load > 0 else 0.0
    ax.bar([x_grid], [grid_rmwh], color=grid_color, width=bw, zorder=-1)
    if grid_rmwh > 30:
        ax.text(x_grid, 0.5 * grid_rmwh, "Grid",
                ha="center", va="center", fontsize=7, color="white")
    print(f"[cost bar] Grid={grid_rmwh:.1f} R/MWh")

    ct_rate = opts.get("carbon_tax_rate_2030", 462)
    ax.set_xticks([x_cap, x_marg, x_co2, x_grid])
    ax.set_xticklabels(["Capital", "Marginal", f"CO₂\n({ct_rate} R/t)", "Grid"], fontsize=8)
    ax.set_ylabel("Avg system cost [R/MWh]")
    ax.set_xlim([0, 1.15])
    ax.set_title("System Cost", fontdict=dict(fontsize="medium"))
    ax.grid(True, axis="y", color="k", linestyle="dotted")

    # Cost summary text below bars
    fc_total = sum(fc.get(c, 0.0) for c in carriers)
    vc_total = sum(vc.get(c, 0.0) for c in carriers)
    total_all = fc_total + vc_total + grid_fc
    em_str = f"{total_emissions:.1f} MtCO₂/a" if total_emissions is not None else "n/a"
    ct_str = f"{co2_cost_bn:.0f} bn ZAR" if co2_cost_bn is not None else "n/a"
    line1 = f"Total Emissions: {em_str}    |    Total Costs: {total_all/1e9:.0f} bn ZAR/a"
    line2 = (f"Capital Costs: {fc_total/1e9:.0f}    |    Marginal Costs: {vc_total/1e9:.0f}"
             f"    |    Carbon Tax: {ct_str}    [bn ZAR/a]")
    ax.text(
        0.5, -0.35,
        line1,
        transform=ax.transAxes, ha="center", va="top", fontsize=7,
    )
    ax.text(
        0.5, -0.45,
        line2,
        transform=ax.transAxes, ha="center", va="top", fontsize=7,
    )


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
        fig.text(0.18, 0.13, f"CO₂ 2030: {co2_2030:.1f} MtCO₂/a", fontsize=9)
    except Exception:
        pass

    ax1 = fig.add_axes([-0.115, 0.5, 0.2, 0.2])
    plot_total_energy_pie(n, config["plotting"], ax=ax1)

    ax2 = fig.add_axes([-0.115, 0.15, 0.22, 0.30])
    plot_total_cost_bar(n, config["plotting"], ax=ax2, gen_emissions_df=gen_em, total_emissions=co2_2030)

    fig.savefig(snakemake.output.ext, transparent=True, bbox_inches='tight')

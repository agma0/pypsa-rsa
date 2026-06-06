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
    'coal', 'nuclear', 'ccgt_steam', 'ocgt',
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
        "cur": "purple",
        "exp": mpl.colors.rgb2hex(to_rgba("red", 0.7), True),
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

    line_colors_with_alpha = (line_widths_cur > 1e-3).map(
        {True: line_colors["cur"], False: to_rgba(line_colors["cur"], 0.0)}
    )
    link_colors_with_alpha = (link_widths_cur > 1e-3).map(
        {True: line_colors["cur"], False: to_rgba(line_colors["cur"], 0.0)}
    )

    ## FORMAT
    linewidth_factor = opts["map"][attribute]["linewidth_factor"]
    bus_size_factor = opts["map"][attribute]["bus_size_factor"]

    if supply_regions_path is not None:
        supply_regions = gpd.read_file(supply_regions_path)
        supply_regions.plot(ax=ax, facecolor='none', edgecolor='black')
    if resarea_path is not None:
        resarea = gpd.read_file(resarea_path)
        resarea.plot(ax=ax, facecolor='gray', alpha=0.2)
    if boundaries is not None:
        ax.set_extent(boundaries, crs=ccrs.PlateCarree())

    ## PLOT — first pass: total optimal capacity (expansion shown in red)
    n.plot(
        line_widths=line_widths_exp / linewidth_factor,
        link_widths=link_widths_exp / linewidth_factor,
        line_colors=line_colors["exp"],
        link_colors=line_colors["exp"],
        bus_sizes=bus_sizes / bus_size_factor,
        bus_colors=tech_colors,
        boundaries=boundaries,
        color_geomap=True,
        geomap=True,
        ax=ax,
    )
    # Second pass: existing capacity overlaid in purple (hides red where no expansion)
    n.plot(
        line_widths=line_widths_cur / linewidth_factor,
        link_widths=link_widths_cur / linewidth_factor,
        line_colors=line_colors_with_alpha,
        link_colors=link_colors_with_alpha,
        bus_sizes=0,
        boundaries=boundaries,
        color_geomap=True,
        geomap=True,
        ax=ax,
    )
    ax.set_aspect("equal")
    ax.axis("off")

    # Rasterize basemap
    # TODO : Check if this also works with cartopy
    for c in ax.collections[:2]:
        c.set_rasterized(True)

    # LEGEND
    handles = []
    labels = []
    for s in (10, 1):
        handles.append(plt.Line2D([0], [0], color=line_colors["exp"],
                                  linewidth=s * 1e3 / linewidth_factor))
        labels.append("{} GW new".format(s))
    for s in (10, 1):
        handles.append(plt.Line2D([0], [0], color=line_colors["cur"],
                                  linewidth=s * 1e3 / linewidth_factor))
        labels.append("{} GW exist.".format(s))
    l1_1 = ax.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(0.3, 1.01),
        frameon=False,
        labelspacing=0.8,
        handletextpad=1.5,
        ncol=2,
        title="Transmission",
    )
    ax.add_artist(l1_1)

    handles = []
    labels = []
    for s in (10, 5):
        handles.append(
            plt.Line2D(
                [0], [0], color=line_colors["cur"], linewidth=s * 1e3 / linewidth_factor
            )
        )
        # labels.append("/")
    #    l1_2 = ax.legend(
    #        handles,
    #        labels,
    #        loc="upper left",
    #        bbox_to_anchor=(0.26, 1.01),
    #        frameon=False,
    #        labelspacing=0.8,
    #        handletextpad=0.5,
    #        title=" ",
    #    )
    #    ax.add_artist(l1_2)

    handles = make_legend_circles_for(
        [10e3, 5e3, 1e3], scale=bus_size_factor, facecolor="w"
    )
    labels = ["{} GW".format(s) for s in (10, 5, 3)]
    l2 = ax.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(0.02, 1.01),
        frameon=False,
        labelspacing=1.0,
        title="Capacity",
        handler_map=make_handler_map_to_scale_circles_as_in(ax),
    )
    ax.add_artist(l2)

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

def plot_total_cost_bar(n, opts, ax=None, gen_emissions_df=None):
    if ax is None:
        ax = plt.gca()

    tech_colors = opts["tech_colors"]
    nice_names = opts["nice_names"]

    fixed_cost, variable_cost = aggregate_costs(n)

    # sum over duplicate component rows and all investment periods, then group
    fc = group_carriers(fixed_cost.groupby(level=0).sum().sum(axis=1))
    vc = group_carriers(variable_cost.groupby(level=0).sum().sum(axis=1))

    total_load = (n.snapshot_weightings.generators * n.loads_t.p_set.sum(axis=1)).sum()

    all_carriers = fc.index.union(vc.index)
    drop = {"load", "load_shedding", "AC transformer", "AC line", "AC-AC"}
    present = [c for c in all_carriers if c in tech_colors and c not in drop
               and (fc.get(c, 0.0) + vc.get(c, 0.0)) > 0]
    carriers = [c for c in CARRIER_ORDER if c in present]
    carriers += [c for c in present if c not in CARRIER_ORDER]

    bottom_cap = 0.0
    bottom_marg = 0.0
    for c in carriers:
        cap  = fc.get(c, 0.0) / total_load
        marg = vc.get(c, 0.0) / total_load
        ax.bar([0.2], [cap],  bottom=bottom_cap,  color=tech_colors[c], width=0.3, zorder=-1)
        ax.bar([0.55], [marg], bottom=bottom_marg, color=tech_colors[c], width=0.3, zorder=-1)
        if cap > 30:
            ax.text(0.2, bottom_cap + 0.5 * cap, nice_names.get(c, c),
                    ha="center", va="center", fontsize=7, color="white")
        if marg > 30:
            ax.text(0.55, bottom_marg + 0.5 * marg, nice_names.get(c, c),
                    ha="center", va="center", fontsize=7, color="white")
        bottom_cap  += cap
        bottom_marg += marg

    # Bar 3: CO2 cost by carrier [R/MWh]
    if gen_emissions_df is not None:
        ct_rate = opts.get("carbon_tax_rate_2030", 462)
        y = 2030 if 2030 in gen_emissions_df.index else gen_emissions_df.index[-1]
        energy_y = (
            n.generators_t.p
            .multiply(n.snapshot_weightings.generators, axis=0)
            .groupby(level=0).sum()
            .loc[y]
        )
        common = gen_emissions_df.columns.intersection(energy_y.index)
        # CO2 cost per generator [R] = MWh × kgCO2/MWh × R/tCO2 / 1000
        co2_cost = energy_y[common] * gen_emissions_df.loc[y, common] * ct_rate / 1000
        carrier_map = n.generators.loc[common, "carrier"].map(
            lambda c: CARRIER_REMAP.get(c, c)
        )
        co2_by_carrier = co2_cost.groupby(carrier_map).sum()
        co2_by_carrier = co2_by_carrier[
            ~co2_by_carrier.index.isin(CARRIER_DROP) & (co2_by_carrier > 0)
        ] / total_load

        bottom_co2 = 0.0
        for c in CARRIER_ORDER:
            if c not in co2_by_carrier.index:
                continue
            val = co2_by_carrier[c]
            ax.bar([0.9], [val], bottom=bottom_co2, color=tech_colors.get(c, "gray"),
                   width=0.3, zorder=-1)
            if val > 30:
                ax.text(0.9, bottom_co2 + 0.5 * val, nice_names.get(c, c),
                        ha="center", va="center", fontsize=7, color="white")
            bottom_co2 += val

        ax.set_xticks([0.2, 0.55, 0.9])
        ax.set_xticklabels(["Capital", "Marginal", f"CO₂\n({ct_rate} R/t)"], fontsize=8)
    else:
        ax.set_xticks([0.2, 0.55])
        ax.set_xticklabels(["Capital", "Marginal"], fontsize=9)

    ax.set_ylabel("Avg system cost [R/MWh]")
    ax.set_xlim([0, 1.1])
    ax.set_title("System Cost", fontdict=dict(fontsize="medium"))
    ax.grid(True, axis="y", color="k", linestyle="dotted")


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
    plot_total_cost_bar(n, config["plotting"], ax=ax2, gen_emissions_df=gen_em)

    fig.savefig(snakemake.output.ext, transparent=True, bbox_inches='tight')

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
        bus_sizes = pd.concat(
            (
                n.generators.query('carrier != "load_shedding"')
                .groupby(["bus", "carrier"])
                .p_nom_opt.sum(),
                n.storage_units.groupby(["bus", "carrier"]).p_nom_opt.sum(),
            )
        )
        line_widths_exp = n.lines.s_nom_opt
        line_widths_cur = n.lines.s_nom_min
        link_widths_exp = n.links.p_nom_opt
        link_widths_cur = n.links.p_nom_min
    else:
        raise "plotting of {} has not been implemented yet".format(attribute)

    line_colors_with_alpha = (line_widths_cur / n.lines.s_nom > 1e-3).map(
        {True: line_colors["cur"], False: to_rgba(line_colors["cur"], 0.0)}
    )
    link_colors_with_alpha = (link_widths_cur / n.links.p_nom > 1e-3).map(
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

    ## PLOT
    n.plot(
        line_widths=line_widths_exp / linewidth_factor,
        link_widths=link_widths_exp / linewidth_factor,
        line_colors=line_colors["cur"],
        link_colors=line_colors["cur"],
        bus_sizes=bus_sizes / bus_size_factor,
        bus_colors=tech_colors,
        boundaries=boundaries,
        color_geomap=True,
        geomap=True,
        ax=ax,
    )
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
        handles.append(
            plt.Line2D(
                [0], [0], color=line_colors["cur"], linewidth=s * 1e3 / linewidth_factor
            )
        )
        labels.append("{} GW".format(s))
    l1_1 = ax.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(0.3, 1.01),
        frameon=False,
        labelspacing=0.8,
        handletextpad=1.5,
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

    techs = (bus_sizes.index.levels[1]).intersection(
        pd.Index(opts["vre_techs"] + opts["conv_techs"] + opts["storage_techs"])
    )

    custom_order = ['Coal', 'Nuclear', 'Gas', 'Wind', 'CSP', 'PV', 'Hydro', 'Battery']
    handles = []
    labels = []

    for t in techs:
        label = opts["nice_names"].get(t, t)

        if label == "Hydro+PS":
            continue  # Skip the rest of this iteration

        handles.append(
            plt.Line2D(
                [0], [0], color=tech_colors[t], marker="o", markersize=14, linewidth=0
            )
        )
        labels.append(label)

    ordered_handles = []
    ordered_labels = []

    # Order according to custom_order
    for lbl in custom_order:
        if lbl in labels:
            idx = labels.index(lbl)
            ordered_handles.append(handles[idx])
            ordered_labels.append(labels[idx])

    l3 = ax.legend(
        ordered_handles,
        ordered_labels,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.1),
        handletextpad=1.0,
        columnspacing=3,
        handlelength=1.5,
        ncol=4,
        labelspacing=1.0,
        # title="Technology",
    )

    return fig


def plot_total_energy_pie(n, opts, ax=None):
    if ax is None:
        ax = plt.gca()

    ax.set_title("Total Generation \nper Technology", fontdict=dict(fontsize="medium"))

    e_primary = aggregate_p(n).drop("load", errors="ignore").loc[lambda s: s > 0]
    # keep only carriers with a defined color
    e_primary = e_primary[e_primary.index.isin(opts["tech_colors"])]

    patches, texts, autotexts = ax.pie(
        e_primary,
        startangle=110,
        labels=e_primary.rename(opts["nice_names"]).index,
        autopct="%.0f%%",
        shadow=False,
        colors=[opts["tech_colors"][tech] for tech in e_primary.index],
    )
    for autotext in autotexts:
        x, y = autotext.get_position()
        dist = (x ** 2 + y ** 2) ** 0.5
        autotext.set_position((x / dist * 1.15, y / dist * 1.15))
        autotext.set_fontsize(9)

    for t1, t2, i in zip(texts, autotexts, e_primary.index):
        if e_primary.at[i] < 0.04 * e_primary.sum():
            t1.remove()
            t2.remove()


#############

def plot_total_cost_bar(n, opts, ax=None):
    if ax is None:
        ax = plt.gca()

    tech_colors = opts["tech_colors"]
    nice_names = opts["nice_names"]

    fixed_cost, variable_cost = aggregate_costs(n)

    # sum over duplicate component rows and all investment periods
    fc = fixed_cost.groupby(level=0).sum().sum(axis=1)
    vc = variable_cost.groupby(level=0).sum().sum(axis=1)

    total_load = (n.snapshot_weightings.generators * n.loads_t.p_set.sum(axis=1)).sum()

    all_carriers = fc.index.union(vc.index)
    carriers = [
        c for c in all_carriers
        if c in tech_colors
        and c not in ("load", "load_shedding", "AC transformer")
        and (fc.get(c, 0.0) + vc.get(c, 0.0)) > 0
    ]

    bottom_cap = 0.0
    bottom_marg = 0.0
    for c in carriers:
        cap = fc.get(c, 0.0) / total_load
        marg = vc.get(c, 0.0) / total_load
        ax.bar([0.3], [cap],  bottom=bottom_cap,  color=tech_colors[c], width=0.35, zorder=-1)
        ax.bar([0.7], [marg], bottom=bottom_marg, color=tech_colors[c], width=0.35, zorder=-1)
        if cap > 30:
            ax.text(0.3, bottom_cap + 0.5 * cap, nice_names.get(c, c),
                    ha="center", va="center", fontsize=7, color="white")
        if marg > 30:
            ax.text(0.7, bottom_marg + 0.5 * marg, nice_names.get(c, c),
                    ha="center", va="center", fontsize=7, color="white")
        bottom_cap  += cap
        bottom_marg += marg

    ax.set_ylabel("Avg system cost [R/MWh]")
    ax.set_xlim([0, 1])
    ax.set_xticks([0.3, 0.7])
    ax.set_xticklabels(["Capital", "Marginal"], fontsize=9)
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

    # CO2 emissions across all periods
    if "co2_emissions" in n.carriers.columns:
        co2_emi = (
            n.generators_t.p
            .multiply(n.snapshot_weightings.generators, axis=0)
            .sum()
            .div(n.generators.efficiency.replace(0, np.nan))
            .mul(n.generators.carrier.map(n.carriers.co2_emissions).fillna(0))
            .sum()
        )
        fig.text(0.18, 0.13, f"CO₂: {int(np.round(co2_emi/1e6))} MtCO₂/a",
                 fontsize=9)

    ax1 = fig.add_axes([-0.115, 0.5, 0.2, 0.2])
    plot_total_energy_pie(n, config["plotting"], ax=ax1)

    ax2 = fig.add_axes([-0.115, 0.15, 0.18, 0.30])
    plot_total_cost_bar(n, config["plotting"], ax=ax2)

    fig.savefig(snakemake.output.ext, transparent=True, bbox_inches='tight')

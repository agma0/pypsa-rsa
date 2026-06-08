configfile: "config.yaml"

from os.path import normpath, exists, isdir
import pandas as pd
import os
import re
import socket
import numpy as np

scenarios = pd.read_excel(
    os.path.join("scenarios",config["scenarios"]["working_folder"], config["scenarios"]["setup"]),
    sheet_name="scenario_definition", 
    index_col=0
)
scenarios_to_run = scenarios[
    scenarios["run_scenario"].astype(str).str.strip().str.lower().isin(["1", "true"])
]


############################################################################################################
# Rules to run through all scenarios specified in the scenarios_to_run.xlsx file
############################################################################################################
rule solve_all:
    input:
        "results/solve_all_scenarios",
        "results/plot_all_scenarios",

############################################################################################################
# Rules to produce network topology
############################################################################################################
rule build_topology:
    input:
        supply_regions = config["data_paths"]["bundle"] + "/rsa_supply_regions.gpkg",
        existing_lines = config["data_paths"]["bundle"] + "/bundle/Existing_Lines.shp",
        planned_lines = config["data_paths"]["bundle"] + "/tdp_digitised/TDP_2023_32.shp",
        gdp_pop_data = config["data_paths"]["bundle"] + "/bundle/Mesozones.shp",        
    output:
        buses = "resources/" + config["scenarios"]["working_folder"] + "/{scenario}/buses.geojson",
        lines = "resources/" + config["scenarios"]["working_folder"] + "/{scenario}/lines.geojson",
    script: "scripts/build_topology.py"


# Function to generate the input files based on the scenario and its respective years
def generate_networks():
    inputs = []
    for sc_id in scenarios_to_run.index:
        scenario = scenarios_to_run.loc[sc_id, "scenario"]
        inputs.append("networks/" + config["scenarios"]["working_folder"] + f"/{scenario}/elec.nc")
    return inputs

def generate_scenarios():
    inputs = []
    for sc_id in scenarios_to_run.index:
        scenario = scenarios_to_run.loc[sc_id, "scenario"]
        inputs.append("results/" + config["scenarios"]["working_folder"] + f"/{scenario}/networks/solved.nc")
    print(inputs)
    return inputs

rule build_all_scenarios:
    input:
        generate_networks()
    output:
        touch("results/build_all_scenarios")

rule solve_all_scenarios:
    input:
        generate_scenarios()
    output:
        touch("results/solve_all_scenarios")

def generate_plots():
    outputs = []
    for sc_id in scenarios_to_run.index:
        scenario = scenarios_to_run.loc[sc_id, "scenario"]
        outputs.append("results/" + config["scenarios"]["working_folder"] + f"/{scenario}/outputs/plots/map_only.png")
    return outputs

rule plot_all_scenarios:
    input:
        generate_plots()
    output:
        touch("results/plot_all_scenarios")

rule plot_network:
    input:
        network = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/networks/solved.nc",
        supply_regions = "data/Shapefiles/11-supply.shp",
        resarea = "data/bundle/REDZ_DEA_Unpublished_Draft_2015/REDZ_DEA_Unpublished_Draft_2015.shp",
        gen_emissions = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/generator_emissions.csv",
    output:
        only_map = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/plots/map_only.png",
        ext = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/plots/map_full.png",
    script:
        "scripts/plot_network_sa.py"

rule base_network:
    input:
        buses = "resources/" + config["scenarios"]["working_folder"] + "/{scenario}/buses.geojson",
        lines = "resources/" + config["scenarios"]["working_folder"] + "/{scenario}/lines.geojson",
    output: 
        "networks/" + config["scenarios"]["working_folder"] + "/{scenario}/base-network.nc",
    script: "scripts/base_network.py"


rule add_electricity:
    input:
        base_network = "networks/" + config["scenarios"]["working_folder"] + "/{scenario}/base-network.nc",
        supply_regions = "resources/" + config["scenarios"]["working_folder"] + "/{scenario}/buses.geojson",
        load = config["data_paths"]["bundle"] + "/bundle/SystemEnergy2009_22.csv",
        eskom_profiles = config["data_paths"]["bundle"] + "/eskom_pu_profiles.csv",
        renewable_profiles = config["data_paths"]["bundle"] + "/bundle/renewable_profiles_dcac_125_mar26.nc",
    output: 
        network = "networks/" + config["scenarios"]["working_folder"] + "/{scenario}/elec.nc",
        gen_emissions = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/generator_emissions.csv",
        gen_stand_by_emissions = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/generator_stand_by_emissions.csv",
    script: "scripts/add_electricity.py"

rule prepare_and_solve_network:
    input:
        network = "networks/"+ config["scenarios"]["working_folder"] + "/{scenario}/elec.nc",
        generator_emissions = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/generator_emissions.csv",
        # AM added: _R scenarios depend on their reference scenario being solved first
        base_network = lambda w: (
            "results/" + config["scenarios"]["working_folder"] + "/"
            + w.scenario.replace("_R", "") + "/networks/solved.nc"
            if w.scenario.endswith("_R") else []
        ),
        # AM added end
    output: 
        network = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/networks/solved.nc",
        network_stats = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/network_stats.csv",
        generators = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/generators.csv",
        storage_units = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/storage_units.csv",
        capacity_value = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/capacity_value.csv",
        decom_status = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/decom_status.csv",
        full_outages = "results/" + config["scenarios"]["working_folder"] + "/{scenario}/outputs/full_outages.csv",
    threads: 32
    resources:
        solver_slots=1,
        mem_mb=200000,
        runtime=20160,
    script:
        "scripts/prepare_and_solve_network.py"

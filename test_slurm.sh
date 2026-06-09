#!/bin/bash
# Test Python startup speed from scratch env on compute node.
# --time=5:00 gives 5 minutes - more than enough if env is accessible.

NEW_PY=/beegfs/scratch/agma/envs/pypsa-rsa/bin/python3.12

sbatch --partition=standard \
       --time=5:00 \
       --output=/beegfs/scratch/agma/pypsa-rsa/logs/test_python_%j.log \
       --wrap="
echo '=== start ===' && date

echo '--- test 1: plain python (no site-packages) ---'
date && $NEW_PY -S -c 'print(\"hello no-site\")' && date

echo '--- test 2: full python with site-packages ---'
date && $NEW_PY -c 'print(\"hello full\")' && date

echo '=== done ==='"

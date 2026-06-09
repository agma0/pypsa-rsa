#!/bin/bash
# Recreate the pypsa-rsa environment in scratch so compute nodes can access it.
# Run on the FRONTEND. Takes ~30-60 min.
# After this works, update PYPSA_ENV in Snakefile to the new path.

MICROMAMBA=/home/users/a/agma/.pixi/envs/micromamba/bin/micromamba
ENV_TARGET=/beegfs/scratch/agma/envs/pypsa-rsa
ENV_FILE=/beegfs/scratch/agma/pypsa-rsa/envs/environment.fixed.yaml

echo "Step 1: Export current environment packages to a lockfile..."
$MICROMAMBA env export -p /home/users/a/agma/.pixi/envs/pypsa-rsa \
    > /beegfs/scratch/agma/pypsa-rsa/envs/env_export.yaml
echo "Exported to envs/env_export.yaml"

echo ""
echo "Step 2: Create new environment in scratch..."
echo "Target: $ENV_TARGET"
$MICROMAMBA create -p $ENV_TARGET \
    --file /beegfs/scratch/agma/pypsa-rsa/envs/env_export.yaml \
    --yes

echo ""
echo "Done! New environment is at: $ENV_TARGET"
echo ""
echo "Next: update Snakefile line 10 to:"
echo "  PYPSA_ENV = \"$ENV_TARGET\""
echo ""
echo "And update your snakemake run command to use:"
echo "  $ENV_TARGET/bin/snakemake"

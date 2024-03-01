# Experiment 7.0: Smooth Grad to compute entropy -gefn 5

import argparse
import sys
import os

sys.path.append(os.getcwd())
from commands.experiment_7 import (
    experiment_master,
)
import commands.experiment_7


commands.experiment_7.alpha_mask_value = (
    "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0"  # DEBUG  
)

commands.experiment_7.ig_alpha_priors = {
    "ig_sg_u_x_0": "0.0",
}

# Method args
commands.experiment_7.combination_fns = [
    # "additive",
    "convex",
    # "damping",
]
commands.experiment_7.gather_stats_batch_size = 128  # DEBUG
commands.experiment_7.baseline_mask_type = "gaussian"

# commands.experiment_7.gather_stats_job_array = "0"
# commands.experiment_7.gather_stats_take_batch_size = "1"

if __name__ == "__main__":
    args = commands.experiment_7.parse_args()
    
    experiment_prefix = os.path.basename(__file__).split(".")[0].replace("experiment_", "")
    experiment_master(
        args, experiment_prefix=experiment_prefix
    )

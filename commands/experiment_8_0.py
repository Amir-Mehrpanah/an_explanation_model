# Experiment 8.0: Smooth Grad to compute entropy -gQ 5

import sys
import os

sys.path.append(os.getcwd())
from commands.experiment_8 import (
    experiment_master,
)
import commands.experiment_8


commands.experiment_8.alpha_mask_value = "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9"  # DEBUG

# Method args
commands.experiment_8.combination_fns = [
    # "additive",
    "convex",
    # "damping",
]
commands.experiment_8.ig_alpha_priors = {
    # "ig_sg_u_x_0": "0.0",
    # "none": None,
}

commands.experiment_8.baseline_mask_type = "gaussian-0.035"
# commands.experiment_8.baseline_mask_value = "0.0"
commands.experiment_8.q_baseline_masks = []
commands.experiment_8.q_directions = [
    # "deletion",
    # "insertion",
]
# commands.experiment_8.q_job_array = "0"

if __name__ == "__main__":
    args = commands.experiment_8.parse_args()

    experiment_prefix = (
        os.path.basename(__file__).split(".")[0].replace("experiment_", "")
    )
    experiment_master(args, experiment_prefix=experiment_prefix)

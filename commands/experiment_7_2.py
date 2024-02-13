# Experiment 7.2: Integrated gradients + Smooth Grad with different alpha priors

import argparse
import sys
import os

sys.path.append(os.getcwd())
from commands.experiment_7 import (
    experiment_master,
)
import commands.experiment_7


commands.experiment_7.alpha_mask_value = (
    "0.1 0.2"  # DEBUG 0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0
)

# Method args
commands.experiment_7.ig_alpha_priors = {  # DEBUG
    # "ig_sg_u_x_0_1.0": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0",
    # "ig_sg_u_x_0_0.8": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8",
    # "ig_sg_u_x_0_0.6": "0.0 0.1 0.2 0.3 0.4 0.5 0.6",
    # "ig_sg_u_x_0_0.4": "0.0 0.1 0.2 0.3 0.4",
    # "ig_sg_u_x_0_0.2": "0.0 0.1 0.2",
    # "ig_sg_u_x2_0_1.0": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0",
    # "ig_sg_u_x2_0_0.8": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8",
    # "ig_sg_u_x2_0_0.6": "0.0 0.1 0.2 0.3 0.4 0.5 0.6",
    # "ig_sg_u_x2_0_0.4": "0.0 0.1 0.2 0.3 0.4",
    # "ig_sg_u_x2_0_0.2": "0.0 0.1 0.2",
    # "ig_sg_i_u_x_0_1.0": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0",
    # "ig_sg_i_u_x_0_0.8": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8",
    # "ig_sg_i_u_x_0_0.6": "0.0 0.1 0.2 0.3 0.4 0.5 0.6",
    # "ig_sg_i_u_x_0_0.4": "0.0 0.1 0.2 0.3 0.4",
    # "ig_sg_i_u_x_0_0.2": "0.0 0.1 0.2",
    # "ig_sg_i_u_x2_0_1.0": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0",
    # "ig_sg_i_u_x2_0_0.8": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8",
    # "ig_sg_i_u_x2_0_0.6": "0.0 0.1 0.2 0.3 0.4 0.5 0.6",
    # "ig_sg_i_u_x2_0_0.4": "0.0 0.1 0.2 0.3 0.4",
    # "ig_sg_i_u_x2_0_0.2": "0.0 0.1 0.2",
    # "sl_u_x2_0_1.0": "0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0",
    # "sl_u_x2_0_0.8": "0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8",
    # "sl_u_x2_0_0.6": "0.1 0.2 0.3 0.4 0.5 0.6",
    # "sl_u_x2_0_0.4": "0.1 0.2 0.3 0.4",
    "sl_u_x2_0_0.2": "0.1 0.2",
}
commands.experiment_7.combination_fns = [
    "additive",
    # "convex",
    # "damping",
]

commands.experiment_7.batch_size = 128  # DEBUG
commands.experiment_7.baseline_mask_type = "gaussian-0.3"

if __name__ == "__main__":
    args = commands.experiment_7.parse_args()

    experiment_prefix = (
        os.path.basename(__file__).split(".")[0].replace("experiment_", "")
    )
    experiment_master(args, experiment_prefix=experiment_prefix)

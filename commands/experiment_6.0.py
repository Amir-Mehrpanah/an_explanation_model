from datetime import datetime
import json
from experiment_base import wait_in_queue, run_experiment, set_logging_level
import logging

import sys
import os

sys.path.append(os.getcwd())
from source.utils import Action

# Slurm args
job_array_image_index = "3,5"  # ,9,11
constraint = "gondor"

# Method args
path_prefix = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
set_logging_level(logging.DEBUG)
number_of_gpus = 4
alpha_mask_value = "0.3 0.5"  # 4
min_change = 5e-4
batch_size = 16
normalize_sample = True
method = "noise_interpolation"
architecture = "resnet50"
dataset = "imagenet"
baseline_mask_type = "gaussian"
projection_type = "prediction"
projection_top_k = 1
alpha_mask_type = "static"
demo = False
save_raw_data_dir = f"/local_storage/users/amirme/raw_data/experiment_6.0"
save_metadata_dir = f"/local_storage/users/amirme/metadata/experiment_6.0"
_args_pattern_state = {
    # "key": ["pattern", "compilation state"],
    "forward": ["i", "static"],
    "alpha_mask": ["i", "dynamic"],
    "projection": ["i", "static"],
    "image": ["i", "static"],
    "baseline_mask": ["i", "static"],
    "normalize_sample": ["i", "static"],
    "demo": ["i", "static,meta"],
}
args_state = json.dumps(
    {k: v[1] for k, v in _args_pattern_state.items()}, separators=(";", ":")
)
args_pattern = json.dumps(
    {k: v[0] for k, v in _args_pattern_state.items()}, separators=(";", ":")
)

run_experiment(
    job_array_image_index=job_array_image_index,
    constraint=constraint,
    path_prefix=path_prefix,
    method=method,
    architecture=architecture,
    dataset=dataset,
    min_change=min_change,
    alpha_mask_type=alpha_mask_type,
    alpha_mask_value=alpha_mask_value,
    projection_type=projection_type,
    projection_top_k=projection_top_k,
    baseline_mask_type=baseline_mask_type,
    demo=demo,
    batch_size=batch_size,
    args_state=args_state,
    args_pattern=args_pattern,
    normalize_sample=normalize_sample,
    save_raw_data_dir=save_raw_data_dir,
    save_metadata_dir=save_metadata_dir,
)

wait_in_queue(0)  # wait for all jobs to finish

# run_experiment(
#     constraint=constraint,
#     action=Action.compute_consistency,
#     path_prefix=path_prefix,
#     number_of_gpus=number_of_gpus,
#     save_raw_data_dir=save_raw_data_dir,
#     save_metadata_dir=save_metadata_dir,
# )

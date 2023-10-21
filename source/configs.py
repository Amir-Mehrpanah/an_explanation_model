import json
import logging
import os
import sys
from utils import Action

sys.path.append(os.getcwd())


class DefaultArgs:
    def __init__(self) -> None:
        raise NotImplementedError("This class is not meant to be instantiated")

    _args_pattern_state = {
        # "key": ["pattern", "compilation state"],
        # default behavior is to compile all args (all static)
        "alpha_mask": ["j", "dynamic"],
        "projection": ["i", "static"],
    }
    methods = ["noise_interpolation", "fisher_information"]
    logging_levels = [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR]
    architectures = ["resnet50"]
    output_layers = ["logits", "log_softmax", "softmax"]
    actions = [v for v in dir(Action) if "__" not in v]

    seed = 42
    write_demo = True
    input_shape = (1, 224, 224, 3)
    logging_level = logging.INFO
    stats_log_level = 0
    monitored_statistic = "meanx2"
    output_layer = output_layers[1]  # see paper for why
    monitored_stream = "vanilla_grad_mask"
    min_change = 1e-2
    batch_size = 32
    max_batches = 10000 // batch_size
    action = Action.gather_stats
    dataset = "imagenet"
    # args we don't want to be compiled by jax
    args_state = json.dumps(
        {k: v[1] for k, v in _args_pattern_state.items()}, separators=(";", ":")
    )
    args_pattern = json.dumps(
        {k: v[0] for k, v in _args_pattern_state.items()}, separators=(";", ":")
    )
    num_classes = 1000
    dataset_dir = "/local_storage/datasets/imagenet"
    save_raw_data_dir = "/local_storage/users/amirme/raw_data"
    save_metadata_dir = "/local_storage/users/amirme/metadata"
    jupyter_data_dir = "/local_storage/users/amirme/jupyter_data"
    visualizations_dir = os.path.join(jupyter_data_dir, "visualizations")
    profiler_dir = os.path.join(jupyter_data_dir, "profiler")

    image_height = input_shape[1]
    image_index = 0

# Experiment 7.2: Integrated gradients squared with Smooth Grad different alpha priors


import json
import logging
import argparse
from glob import glob
import sys
import os

sys.path.append(os.getcwd())
from source.utils import Action, Statistics
from commands.experiment_base import (
    remove_files,
    wait_in_queue,
    run_experiment,
    set_logging_level,
    save_raw_data_base_dir,
    save_metadata_base_dir,
    save_temp_base_dir,
)

# Slurm args
constraint = "thin"

# Method args
alpha_mask_value = "0.0 0.1 0.2 0.3 0.4 0.5"  # DEBUG  0.6 0.7 0.8 0.9 1.0
ig_alpha_priors = {  # DEBUG
    # "ig_sg_u_0_1.0": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0",
    # "ig_sg_u_0_0.9": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9",
    # "ig_sg_u_0_0.7": "0.0 0.1 0.2 0.3 0.4 0.5 0.6 0.7",
    "ig_sg_u_0_0.5": "0.0 0.1 0.2 0.3 0.4 0.5",
    # "ig_sg_u_0_0.3": "0.0 0.1 0.2 0.3",
    # "ig_sg_u_0_0.1": "0.0 0.1",
}
sl_alpha_priors = {  # DEBUG
    # "sl_u_0_1.0": "0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9 1.0",
    # "sl_u_0_0.9": "0.1 0.2 0.3 0.4 0.5 0.6 0.7 0.8 0.9",
    # "sl_u_0_0.7": "0.1 0.2 0.3 0.4 0.5 0.6 0.7",
    "sl_u_0_0.5": "0.1 0.2 0.3 0.4 0.5",
    # "sl_u_0_0.3": "0.1 0.2 0.3",
}
ig_stream_statistics = [  # DEBUG
    # Statistics.meanx,
    Statistics.meanx2,
]
sl_stream_statistics = [  # DEBUG
    # Statistics.meanx,
    Statistics.meanx2,
]
combination_fns = [
    "additive_combination",
    # "convex_combination",
    "damping_combination",
]
alpha_mask_type = "static"
logging_level = logging.DEBUG
set_logging_level(logging_level)
min_change = 5e-3  # DEBUG
batch_size = 128  # DEBUG
normalize_sample = "False"  # DEBUG
input_shape = (1, 224, 224, 3)
method = "noise_interpolation"
architecture = "resnet50"
dataset = "imagenet"
dataset_dir = "/proj/azizpour-group/datasets/imagenet"
baseline_mask_type = "gaussian-0.3"
projection_type = "prediction"
projection_top_k = 1
stats_log_level = 1
demo = False

_args_pattern_state = {
    # "key": ["pattern", "compilation state"],
    "alpha_mask": ["j", "dynamic"],
    "image": ["i", "dynamic"],
}
args_state = json.dumps(
    {k: v[1] for k, v in _args_pattern_state.items()},
    separators=(";", ":"),  # semi-colon is used to separate args
)
args_pattern = json.dumps(
    {k: v[0] for k, v in _args_pattern_state.items()}, separators=(";", ":")
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--gather_stats", "-g", action="store_true")
    parser.add_argument("--compute_integrated_grad", "-i", action="store_true")
    parser.add_argument("--compute_spectral_lens", "-s", action="store_true")
    parser.add_argument("--compute_accuracy_at_q", "-q", action="store_true")
    parser.add_argument("--remove_batch_data", "-r", action="store_true")
    parser.add_argument("--compute_entropy", "-e", action="store_true")
    parser.add_argument("--num_batches", "-n", type=int, default=1)

    args = parser.parse_args()
    if not any(vars(args).values()):
        parser.print_help()
        sys.exit(1)

    for batch in range(args.num_batches):
        for combination_fn in combination_fns:
            experiment_name = (
                os.path.basename(__file__).split(".")[0]
                + "_"
                + combination_fn
                + "_"
                + str(batch)
            )
            save_raw_data_dir = os.path.join(save_raw_data_base_dir, experiment_name)
            save_metadata_dir = os.path.join(save_metadata_base_dir, experiment_name)

            job_array = "0"  # DEBUG -990:10
            # image_index = "skip take" # skip num_elements (a very bad hack) todo clean up
            array_process = f'array_process="--image_index $((1000*{batch} + $SLURM_ARRAY_TASK_ID)) 10"'

            if args.gather_stats:
                job_name = experiment_name
                run_experiment(
                    experiment_name=job_name,
                    save_temp_base_dir=save_temp_base_dir,
                    job_array=job_array,
                    array_process=array_process,
                    constraint=constraint,
                    number_of_gpus=1,
                    action=Action.gather_stats,
                    logging_level=logging_level,
                    method=method,
                    architecture=architecture,
                    dataset=dataset,
                    min_change=min_change,
                    combination_fn=combination_fn,
                    alpha_mask_value=alpha_mask_value,
                    alpha_mask_type=alpha_mask_type,
                    projection_type=projection_type,
                    projection_top_k=projection_top_k,
                    baseline_mask_type=baseline_mask_type,
                    stats_log_level=stats_log_level,
                    demo=demo,
                    dataset_dir=dataset_dir,
                    batch_size=batch_size,
                    args_state=args_state,
                    args_pattern=args_pattern,
                    normalize_sample=normalize_sample,
                    save_raw_data_dir=save_raw_data_dir,
                    save_metadata_dir=save_metadata_dir,
                )

                wait_in_queue(0, jobnames=job_name)  # wait for all jobs to finish
                job_name = f"merge_{experiment_name}"
                run_experiment(
                    experiment_name=job_name,
                    constraint=constraint,
                    action=Action.merge_stats,
                    logging_level=logging_level,
                    save_metadata_dir=save_metadata_dir,
                )
                wait_in_queue(0, jobnames=job_name)  # wait for all jobs to finish
                remove_files(save_metadata_dir)

            if args.compute_spectral_lens or args.compute_integrated_grad:
                job_name = []

            if args.compute_spectral_lens:
                for k, (alpha_mask_name, alpha_prior) in enumerate(
                    sl_alpha_priors.items()
                ):
                    for j, stream_statistic in enumerate(sl_stream_statistics):
                        temp_name = alpha_mask_name + "_" + stream_statistic
                        job_name.append(f"sl_{experiment_name}_{k}_{j}")
                        run_experiment(
                            experiment_name=job_name[-1],
                            constraint=constraint,
                            action=Action.compute_spectral_lens,
                            logging_level=logging_level,
                            save_metadata_dir=save_metadata_dir,
                            save_raw_data_dir=save_raw_data_dir,
                            stream_statistic=stream_statistic,
                            alpha_mask_name=temp_name,
                            alpha_prior=alpha_prior,
                        )

            if args.compute_integrated_grad:
                for k, (alpha_mask_name, alpha_prior) in enumerate(
                    ig_alpha_priors.items()
                ):
                    for j, stream_statistic in enumerate(ig_stream_statistics):
                        temp_name = alpha_mask_name + "_" + stream_statistic
                        job_name.append(f"ig_{experiment_name}_{k}_{j}")
                        run_experiment(
                            experiment_name=job_name[-1],
                            constraint=constraint,
                            action=Action.compute_integrated_grad,
                            logging_level=logging_level,
                            save_metadata_dir=save_metadata_dir,
                            save_raw_data_dir=save_raw_data_dir,
                            stream_statistic=stream_statistic,
                            alpha_mask_name=temp_name,
                            alpha_prior=alpha_prior,
                        )

            if args.compute_spectral_lens or args.compute_integrated_grad:
                wait_in_queue(0, job_name)
                job_name = []

            if args.compute_integrated_grad:
                job_name.append(f"merge_ig_{experiment_name}")
                run_experiment(
                    experiment_name=job_name[-1],
                    constraint=constraint,
                    action=Action.merge_stats,
                    glob_path="ig_*.csv",
                    file_name="merged_ig_metadata.csv",
                    logging_level=logging_level,
                    save_metadata_dir=save_metadata_dir,
                )

            if args.compute_spectral_lens:
                job_name.append(f"merge_sl_{experiment_name}")
                run_experiment(
                    experiment_name=job_name[-1],
                    constraint=constraint,
                    action=Action.merge_stats,
                    glob_path="sl_*.csv",
                    file_name="merged_sl_metadata.csv",
                    logging_level=logging_level,
                    save_metadata_dir=save_metadata_dir,
                )

            if args.compute_spectral_lens or args.compute_integrated_grad:
                wait_in_queue(0, jobnames=job_name)  # wait for all jobs to finish
                remove_files(save_metadata_dir)

            if args.compute_accuracy_at_q:
                job_array = "10"  # DEBUG -90:20
                array_process = f'array_process="--q $SLURM_ARRAY_TASK_ID"'
                job_name = []
                files = glob(os.path.join(save_metadata_dir, "merged_??_metadata.csv"))
                for k, file in enumerate(files):
                    glob_path = os.path.basename(file)
                    prefix = glob_path.split("_")[1]
                    job_name.append(f"acc{k}_{experiment_name}")
                    run_experiment(
                        sweeper_name="_sweeper_torch.sbatch",
                        job_array=job_array,
                        array_process=array_process,
                        experiment_name=job_name[-1],
                        constraint=constraint,
                        number_of_gpus=1,
                        glob_path=glob_path,
                        save_file_name_prefix=f"{prefix}q",
                        action=Action.compute_accuracy_at_q,
                        logging_level=logging_level,
                        save_metadata_dir=save_metadata_dir,
                        batch_size=128,
                    )

                wait_in_queue(0, jobnames=job_name)  # wait for all jobs to finish
                job_name = []

                for k, file in enumerate(files):
                    prefix = os.path.basename(file).split("_")[1]
                    job_name.append(f"merge_{prefix}_{experiment_name}")
                    run_experiment(
                        experiment_name=job_name[-1],
                        constraint=constraint,
                        action=Action.merge_stats,
                        glob_path=f"{prefix}q_*.csv",
                        file_name=f"merged_{prefix}q_metadata.csv",
                        logging_level=logging_level,
                        save_metadata_dir=save_metadata_dir,
                    )
                wait_in_queue(0, jobnames=job_name)  # wait for all jobs to finish
                remove_files(save_metadata_dir)

            if args.compute_entropy:
                job_name = f"entropy_{experiment_name}"
                run_experiment(
                    experiment_name=job_name,
                    constraint=constraint,
                    action=Action.compute_entropy,
                    save_metadata_dir=save_metadata_dir,
                )

            if args.remove_batch_data and batch != 0:
                remove_files(save_raw_data_dir)
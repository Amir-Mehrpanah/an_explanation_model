import jax
import jax.numpy as jnp
from typing import Callable, Dict, List, Tuple
from tqdm import tqdm
import os
import sys

jax.config.update("jax_disable_jit", True)

sys.path.append(os.getcwd())
from source import neighborhoods, operations, explainers
from source.helpers import Stream, StreamNames, Statistics


@operations.FactoryFunction
def fisher_information(
    key,
    *,
    forward,
    input_shape,
    image,
    label,
):
    assert len(input_shape) == 4

    normal_mask = neighborhoods.normal_mask(
        key=key,
        shape=input_shape,
    )
    return normal_mask


@operations.FactoryFunction
def noise_interpolation(key, *, alpha, forward, num_classes, input_shape, image, label):
    assert len(input_shape) == 4

    alpha_mask = alpha * jnp.ones(shape=(1, 1, 1, 1))
    projection = (
        jnp.zeros(
            shape=(num_classes, 1),
            dtype=jnp.float32,
        )
        .at[label, 0]
        .set(1.0)
    )

    normal_mask = neighborhoods.normal_mask(
        key=key,
        shape=input_shape,
    )
    convex_combination_mask = operations.convex_combination_mask(
        source_mask=image,
        target_mask=normal_mask,
        alpha_mask=alpha_mask,
    )
    vanilla_grad_mask, results_at_projection, log_probs = explainers.vanilla_gradient(
        source_mask=convex_combination_mask,
        projection=projection,
        forward=forward,
    )

    return {
        StreamNames.vanilla_grad_mask: vanilla_grad_mask,
        StreamNames.results_at_projection: results_at_projection,
        StreamNames.log_probs: log_probs,
    }


def gather_stats(
    seed,
    abstract_sampling_process: operations.FactoryFunction,
    batch_size,
    max_batches,
    min_change,
    stats: Dict[Stream, jax.Array],
    monitored_statistic_source_key: Stream,
    monitored_statistic_key: Stream,
    batch_index_key,
):
    assert monitored_statistic_key.statistic == Statistics.abs_delta
    (
        loop_initials,
        concrete_stopping_condition,
        concrete_sample_and_update,
    ) = init_loop(
        seed,
        abstract_sampling_process,
        batch_size,
        max_batches,
        min_change,
        stats,
        monitored_statistic_source_key,
        monitored_statistic_key,
        batch_index_key,
    )

    stats = jax.lax.while_loop(
        cond_fun=concrete_stopping_condition,
        body_fun=concrete_sample_and_update,
        init_val=loop_initials,
    )
    return stats


def init_loop(
    seed,
    abstract_sampling_process: operations.FactoryFunction,
    batch_size,
    max_batches,
    min_change,
    stats: Stream,
    monitored_statistic_source_key: Stream,
    monitored_statistic_key: Stream,
    batch_index_key,
):
    # concretize abstract stopping condition
    concrete_stopping_condition = stopping_condition(
        max_batches=max_batches,
        min_change=min_change,
        monitored_statistic_key=monitored_statistic_key,
        batch_index_key=batch_index_key,
    ).concretize()

    # concretize abstract sampling process
    concrete_sampling_process = abstract_sampling_process.concretize()
    vectorized_concrete_sampling_process = jax.vmap(
        concrete_sampling_process,
        in_axes=(0),
    )

    # concretize abstract update stats
    concrete_update_stats = update_stats(
        stream_keys=tuple(stats.keys()),
        monitored_statistic_source_key=monitored_statistic_source_key,
        monitored_statistic_key=monitored_statistic_key,
    ).concretize()

    # concretize abstract sample and update
    concrete_sample_and_update_stats = sample_and_update_stats(
        seed=seed,
        batch_size=batch_size,
        concrete_vectorized_process=vectorized_concrete_sampling_process,
        concrete_update_stats=concrete_update_stats,
        batch_index_key=batch_index_key,
    ).concretize()

    return stats, concrete_stopping_condition, concrete_sample_and_update_stats


@operations.FactoryFunction
def sample_and_update_stats(
    stats,
    *,
    seed,
    batch_size,
    concrete_vectorized_process,
    concrete_update_stats,
    batch_index_key,
):
    stats[batch_index_key] += 1  # lookup
    batch_index = stats[batch_index_key]  # lookup

    key = jax.random.PRNGKey(seed + batch_index)
    batch_keys = jax.random.split(key, num=batch_size)

    sampled_batch = concrete_vectorized_process(batch_keys)
    stats = concrete_update_stats(sampled_batch, stats, batch_index)
    return stats


@operations.FactoryFunction
def stopping_condition(
    stats,
    *,
    max_batches,
    min_change,
    monitored_statistic_key: Stream,
    batch_index_key,
):
    print("stopping condition key", monitored_statistic_key)
    change = stats[monitored_statistic_key]  # lookup
    batch_index = stats[batch_index_key]  # lookup

    value_condition = change < min_change
    iteration_condition = batch_index < max_batches
    return value_condition & iteration_condition


@operations.FactoryFunction
def update_stats(
    sampled_batch: Dict[StreamNames, jax.Array],
    stats: Dict[Stream, jax.Array],
    batch_index: int,
    *,
    stream_keys: Tuple[Stream],
    monitored_statistic_source_key: Stream,
    monitored_statistic_key: Stream,
):
    monitored_statistic_old = stats[monitored_statistic_source_key]  # lookup

    for key in stream_keys:
        if key.statistic == Statistics.meanx:
            stats[key] = (1 / batch_index) * sampled_batch[key.name].mean(axis=0) + (
                (batch_index - 1) / batch_index
            ) * stats[key]
        elif key.statistic == Statistics.meanx2:
            stats[key] = (1 / batch_index) * (sampled_batch[key.name] ** 2).mean(
                axis=0
            ) + ((batch_index - 1) / batch_index) * stats[key]

    monitored_statistic_new = stats[monitored_statistic_source_key]  # lookup

    stats[monitored_statistic_key] = jnp.abs(
        monitored_statistic_new - monitored_statistic_old
    ).max()  # lookup
    return stats


# class SmoothGradient(Aggregator):
#     def __init__(
#         self,
#         model: torch.nn.Module,
#         input_shape: Tuple[int, int, int],
#         prediction_stats: Dict[str, Statistic],
#         explanation_stats: Dict[str, Statistic],
#         noise_level: float = 0.3,
#         # blur neighbor is not in the original paper but we found it to be helpful
#         # empirically, as it reduces the artifacts in the final explanation
#         blur_neighbor: bool = False,
#         batch_size: int = 32,
#     ) -> None:
#         """
#         Args:
#             model: model to explain
#             input_shape: shape of the input to the model (C,H,W)
#             noise_level: intensity of the noise to add to the baseline in (0,1) range
#             blur_neighbor: whether to blur the neighbor mask
#             batch_size: number of samples to draw from the distribution
#             explanation_stats: statistics to compute on the explanations
#             prediction_stats: statistics to compute on the predictions
#         An implementation of SmoothGrad from a probabilistic perspective.
#         """
#         assert 0 <= noise_level, "noise_level must be in (0,+inf)"
#         device = get_device(model)
#         alpha_source = torch.ones(1, 1, 1, 1)
#         alpha_target = noise_level * torch.ones(1, 1, 1, 1)
#         maybe_blur_neighbor: List[Distribution] = []
#         if blur_neighbor:
#             maybe_blur_neighbor.append(
#                 BlurMask(name="neighbor", source_name="neighbor", device=device)
#             )
#         distribution = Compose(
#             [
#                 DeterministicMask(alpha_source, name="alpha_source", device=device),
#                 DeterministicMask(alpha_target, name="alpha_target", device=device),
#                 NormalMask(
#                     shape=(batch_size, *input_shape),
#                     name="baseline",
#                     device=device,
#                 ),
#                 LinearCombination(
#                     device=device,
#                     name="neighbor",
#                     source_mask="input",
#                     alpha_source="alpha_source",
#                     target_mask="baseline",
#                     alpha_target="alpha_target",
#                 ),
#                 *maybe_blur_neighbor,
#             ]
#         )
#         deterministic_explainer = VanillaGradient(model, returns="probs")
#         probabilistic_explainer = ProbabilisticExplainer(
#             deterministic_explainer, distribution
#         )
#         super().__init__(
#             probabilistic_explainer,
#             prediction_stats=prediction_stats,
#             explanation_stats=explanation_stats,
#             batch_size=batch_size,
#         )


# class IntegratedGradient(Aggregator):
#     def __init__(
#         self,
#         model: torch.nn.Module,
#         input_shape: Tuple[int, int, int],
#         prediction_stats: Dict[str, Statistic],
#         explanation_stats: Dict[str, Statistic],
#         baseline: torch.Tensor = torch.zeros(1, 1, 1, 1),
#         batch_size: int = 32,
#     ) -> None:
#         assert baseline.ndim == 4, "baseline is expected to be of shape (N,C,H,W)"
#         device = get_device(model)
#         mask_shape = (batch_size, 1, 1, 1)
#         baseline_dist = DeterministicMask(name="baseline", mask=baseline, device=device)
#         maybe_resize_baseline: List[Distribution] = []
#         alpha_name = "alpha"
#         if baseline.shape[-2:] != input_shape[-2:] and baseline.shape[-2:] != (1, 1):
#             alpha_name = "resized_" + alpha_name
#             maybe_resize_baseline.append(
#                 ResizeMask(
#                     name=alpha_name,
#                     source_name="alpha",
#                     target_name="input",
#                     device=device,
#                 )
#             )

#         distribution = Compose(
#             [
#                 UniformMask(name="alpha", shape=mask_shape, device=device),
#                 baseline_dist,
#                 *maybe_resize_baseline,
#                 ConvexCombination(
#                     device=device,
#                     name="neighbor",
#                     source_mask="baseline",
#                     alpha_mask=alpha_name,
#                     target_mask="input",
#                 ),
#             ]
#         )
#         scale: Callable[[torch.Tensor], torch.Tensor] = lambda x: x - baseline_dist.mask
#         deterministic_explainer = ScaledVanillaGradient(
#             model, observation_mask=scale, returns="probs"
#         )
#         probabilistic_explainer = ProbabilisticExplainer(
#             deterministic_explainer, distribution
#         )
#         super().__init__(
#             probabilistic_explainer,
#             prediction_stats=prediction_stats,
#             explanation_stats=explanation_stats,
#             batch_size=batch_size,
#         )


# class OcclusionSensitivity(Aggregator):
#     def __init__(
#         self,
#         model: torch.nn.Module,
#         input_shape: Tuple[int, int, int],
#         explanation_stats: Dict[str, Statistic],
#         prediction_stats: Dict[str, Statistic],
#         baseline: torch.Tensor = torch.zeros(1, 1, 8, 8),
#         batch_size: int = 32,
#     ) -> None:
#         assert baseline.ndim == 4, "baseline is expected to be of shape (N,C,H,W)"
#         device = get_device(model)
#         for p in model.parameters():
#             p.requires_grad = False

#         maybe_resize_masks: List[Distribution] = []
#         alpha_name = "alpha"
#         baseline_name = "baseline"
#         if baseline.shape[-2:] != input_shape[-2:] and baseline.shape[-2:] != (1, 1):
#             alpha_name = "resized_" + alpha_name
#             baseline_name = "resized_" + baseline_name
#             maybe_resize_masks.append(
#                 ResizeMask(
#                     name=alpha_name,
#                     source_name="alpha",
#                     target_name="input",
#                     device=device,
#                 )
#             )
#             maybe_resize_masks.append(
#                 ResizeMask(
#                     name=baseline_name,
#                     source_name="baseline",
#                     target_name="input",
#                     device=device,
#                 ),
#             )

#         distribution = Compose(
#             [
#                 OneHotCategoricalMask(
#                     name="alpha", shape=(batch_size, *baseline.shape[1:]), device=device
#                 ),
#                 DeterministicMask(name="baseline", mask=baseline, device=device),
#                 *maybe_resize_masks,
#                 ConvexCombination(
#                     source_mask="input",
#                     alpha_mask=alpha_name,
#                     target_mask=baseline_name,
#                     name="neighbor",
#                     device=device,
#                 ),
#             ]
#         )
#         self.deterministic_explainer = FiniteDifference(model)
#         probabilistic_explainer = ProbabilisticExplainer(
#             self.deterministic_explainer,
#             distribution,
#             distribution_keys_to_explainer_args_mapping={
#                 alpha_name: "observation_mask",
#             },
#         )
#         super().__init__(
#             probabilistic_explainer,
#             explanation_stats=explanation_stats,
#             prediction_stats=prediction_stats,
#             batch_size=batch_size,
#         )

#     def __call__(self, x: torch.Tensor, dim: int = 0):
#         self.deterministic_explainer.reset()
#         return super().__call__(x, dim=dim)


# class RISE(Aggregator):
#     def __init__(
#         self,
#         model: torch.nn.Module,
#         input_shape: Tuple[int, int, int],
#         baseline: torch.Tensor,
#         prediction_stats: Dict[str, Statistic],
#         explanation_stats: Dict[str, Statistic],
#         p_keep: float = 0.1,
#         batch_size: int = 32,
#     ) -> None:
#         assert baseline.ndim == 4, "baseline is expected to be of shape (N,C,H,W)"
#         device = get_device(model)
#         for p in model.parameters():
#             p.requires_grad = False

#         maybe_resize_masks: List[Distribution] = []
#         alpha_name = "alpha"
#         baseline_name = "baseline"
#         if baseline.shape != input_shape and baseline.shape[-2:] != (1, 1):
#             alpha_name = "resized_" + alpha_name
#             baseline_name = "resized_" + baseline_name
#             mask_target_shape = (
#                 int(input_shape[-2] * (1 + 1 / baseline.shape[-2]) + 1),
#                 int(input_shape[-1] * (1 + 1 / baseline.shape[-1]) + 1),
#             )
#             maybe_resize_masks.append(
#                 ResizeMask(
#                     name=alpha_name,
#                     source_name="alpha",
#                     # according to the official implementation of RISE, which is different from the paper,
#                     # the alpha mask is resized to the a size a bit bigger than the input shape and then
#                     # cropped to the input shape. this helps removing the border artifacts.
#                     target_shape=mask_target_shape,
#                     device=device,
#                 )
#             )
#             maybe_resize_masks.append(
#                 RandomCropMask(
#                     name=alpha_name,
#                     source_name=alpha_name,
#                     target_name="input",
#                     device=device,
#                 )
#             )
#             maybe_resize_masks.append(
#                 ResizeMask(
#                     name=baseline_name,
#                     source_name="baseline",
#                     target_name="input",
#                     device=device,
#                 ),
#             )

#         distribution = Compose(
#             [
#                 BernoulliMask(
#                     name="alpha",
#                     shape=(batch_size, *baseline.shape[1:]),
#                     device=device,
#                     p=p_keep,
#                 ),
#                 DeterministicMask(name="baseline", mask=baseline, device=device),
#                 *maybe_resize_masks,
#                 ConvexCombination(
#                     source_mask=baseline_name,
#                     alpha_mask=alpha_name,
#                     target_mask="input",
#                     name="neighbor",
#                     device=device,
#                 ),
#             ]
#         )
#         # for seeing how it could be finite difference see our paper
#         deterministic_explainer = FiniteDifference(model)
#         probabilistic_explainer = ProbabilisticExplainer(
#             deterministic_explainer,
#             distribution,
#             distribution_keys_to_explainer_args_mapping={
#                 alpha_name: "observation_mask",
#             },
#         )
#         super().__init__(
#             probabilistic_explainer,
#             prediction_stats=prediction_stats,
#             explanation_stats=explanation_stats,
#             batch_size=batch_size,
#         )

import jax.numpy as jnp
import jax
import numpy as np
import logging
import sys
import os

sys.path.append(os.getcwd())
from source.utils import AbstractFunction

logger = logging.getLogger(__name__)


@AbstractFunction
def _measure_consistency_cosine_distance(
    image_batch: jnp.ndarray,
    downsampling_factor=10,
    downsampling_method=jax.image.ResizeMethod.LINEAR,
):
    assert image_batch.ndim == 5, (
        "image batched group should be 5D (B,A,H,W,C) "
        "where B is the batch size and A is the number of columns in pivot table."
    )
    B, T, H, W, _ = image_batch.shape
    new_H = H // downsampling_factor
    new_W = W // downsampling_factor
    downsampled: jax.Array = jax.image.resize(
        image_batch,
        shape=(
            B,
            T,
            new_H,
            new_W,
            1,  # collapse the color channels
        ),
        method=downsampling_method,
    )

    downsampled = jnp.squeeze(downsampled, axis=-1)
    downsampled_0 = downsampled[:, [0], ...].reshape((B, 1, -1))
    downsampled_gt0 = downsampled[:, 1:, ...].reshape((B, T - 1, -1))

    norm_0 = jnp.linalg.norm(downsampled_0, axis=-1, keepdims=True)
    norm_gt0 = jnp.linalg.norm(downsampled_gt0, axis=-1, keepdims=True)

    average_cosine_similarity = jnp.einsum(
        "bti,btj->b",
        downsampled_0 / norm_0,
        downsampled_gt0 / norm_gt0,
    ) / (new_H * new_W * (T - 1))

    return 1 - average_cosine_similarity


@AbstractFunction
def _measure_consistency_DSSIM(image_batch, l, s, v):
    """
    computes the DSSIM between two images
    DSSIM = (1-SSIM)/2
    SSIM stands for structural similarity index measure
    """
    raise NotImplementedError("DSSIM is not implemented yet")


def measure_consistency(numpy_iterator, concrete_consistency_measure):
    results = {"consistency": []}
    for batch in numpy_iterator:
        data = batch.pop("data")
        consistency = concrete_consistency_measure(data)
        results["consistency"].append(consistency)
        for k, v in batch.items():
            if k not in results:
                results[k] = []
            results[k].append(v)  # other keys are indices
    for k in results:
        logger.debug(f"concatenating {k}, {results[k]}")
        results[k] = np.concatenate(results[k])
    return results
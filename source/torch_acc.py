from datetime import datetime
from torch.utils.data import DataLoader
from torch.utils.data import Dataset
import torchvision
from PIL import Image
import numpy as np
import pandas as pd
import os
import logging
import torch
import sys

sys.path.append(os.getcwd())
from source.project_manager import load_experiment_metadata

logger = logging.getLogger(__name__)

preprocess = torchvision.transforms.Compose(
    [
        torchvision.transforms.CenterCrop(224),
        torchvision.transforms.ToTensor(),
        torchvision.transforms.Normalize(
            mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]
        ),
    ]
)


class SLQDataset(Dataset):
    """Face Landmarks dataset."""

    def __init__(self, sl_metadata, remove_q=0, verbose=False, q_direction="deletion"):
        """
        Arguments:
            sl_metadata (string): Path to the csv metadata file.
            q (float): The quantile value for the saliency mask to remove from the image.
        """
        self.sl_metadata = sl_metadata
        self.q = 100 - remove_q
        self.verbose = verbose
        self.q_direction = q_direction

    def __len__(self):
        return len(self.sl_metadata)

    def __getitem__(self, idx):
        original_image_path = self.sl_metadata.iloc[idx]["image_path"]
        image_index = self.sl_metadata.iloc[idx]["image_index"]
        saliency_image_path = self.sl_metadata.iloc[idx]["data_path"]
        label = self.sl_metadata.iloc[idx]["label"]
        alpha_mask_value = self.sl_metadata.iloc[idx]["alpha_mask_value"]

        original_image = Image.open(original_image_path).convert("RGB")
        original_image = preprocess(original_image)

        if self.q < 100 or self.verbose:
            saliency_image = np.load(saliency_image_path)
            saliency_image = torch.tensor(saliency_image)
            # (1, H, W, C) -> (1, H, W)
            saliency_image = torch.sum(
                saliency_image,
                axis=-1,
            )
            if self.q_direction == "deletion":
                mask = (saliency_image < np.percentile(saliency_image, self.q)) * 1.0
            else:
                mask = (saliency_image > np.percentile(saliency_image, self.q)) * 1.0
            masked_image = original_image * mask
        else:
            if self.q_direction == "deletion":
                masked_image = original_image
                mask = torch.ones_like(original_image)
            else:
                masked_image = torch.zeros_like(original_image)
                mask = torch.zeros_like(original_image)

        if self.verbose:
            sample = {
                "original_image": original_image,
                "saliency": saliency_image,
                "label": label,
                "mask": mask,
                "masked_image": masked_image,
                "image_index": image_index,
                "alpha_mask_value": alpha_mask_value,
            }
        else:
            sample = {
                "masked_image": masked_image,
                "label": label,
                "actual_q": mask.mean(),
            }
        return sample


def write_auxiliary_metadata(
    save_metadata_dir,
    save_file_name_prefix,
    glob_path,
):
    sl_metadata = load_experiment_metadata(save_metadata_dir, glob_path=glob_path)
    ids = sl_metadata["stream_name"] != "vanilla_grad_mask"
    sl_metadata = sl_metadata[ids]
    logger.info(
        f"Loaded auxillary metadata from {save_metadata_dir}/{glob_path} of shape"
        f" {sl_metadata.shape} "
    )
    file_name = f"{save_file_name_prefix}_auxillary_q.csv"
    sl_metadata.to_csv(os.path.join(save_metadata_dir, file_name), index=False)


def compute_accuracy_at_q(
    save_metadata_dir,
    prefetch_factor,
    batch_size,
    save_file_name_prefix,
    q,
    q_direction,
    glob_path,
):
    sl_metadata = load_experiment_metadata(save_metadata_dir, glob_path=glob_path)

    logger.info(
        f"Loaded metadata from {save_metadata_dir} of shape"
        f" {sl_metadata.shape} before filtering vanilla_grad_mask"
    )
    ids = sl_metadata["stream_name"] == "vanilla_grad_mask"
    sl_metadata = sl_metadata[ids]
    sl_metadata = sl_metadata.reset_index(drop=True)
    logger.info(
        f"Loaded metadata from {save_metadata_dir} of shape"
        f" {sl_metadata.shape} after filtering vanilla_grad_mask"
    )

    slqds = SLQDataset(
        sl_metadata,
        remove_q=q,
        q_direction=q_direction,
    )
    slqdl = DataLoader(
        slqds,
        batch_size=batch_size,
        shuffle=False,
        num_workers=4,
        pin_memory=True,
        prefetch_factor=prefetch_factor,
    )

    forward = torchvision.models.resnet50(
        weights=torchvision.models.ResNet50_Weights.IMAGENET1K_V2
    )
    forward.eval()
    preds = []
    actual_qs = []
    with torch.no_grad():
        for i, batch in enumerate(slqdl):
            logger.debug(f"batch: {i} of {len(slqdl)} time: {datetime.now()}")
            logits = forward(batch["masked_image"])
            logits = logits.argmax(axis=1)
            preds.append(logits == batch["label"])
            actual_qs.append(batch["actual_q"])

    # convert preds to dataframe
    preds = pd.DataFrame(
        {
            "preds": np.concatenate(preds, axis=0),
            "actual_q": np.concatenate(actual_qs, axis=0),
        },
    )
    preds["q"] = q
    preds["q_direction"] = q_direction

    logger.debug(f"preds shape: {preds.shape} (q results)")
    logger.debug(
        f"sl_metadata shape: {sl_metadata.shape} before concatenation of q results"
    )

    sl_metadata = pd.concat([sl_metadata, preds], axis=1)
    logger.debug(
        f"sl_metadata shape: {sl_metadata.shape} after concatenation of q results"
    )

    file_name = f"{save_file_name_prefix}_{q}.csv"
    sl_metadata.to_csv(os.path.join(save_metadata_dir, file_name), index=False)

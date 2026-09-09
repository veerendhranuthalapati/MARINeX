"""
Hard Negative Dataset Builder.
Re-samples and weights mined hard negatives to suppress false alarms during model retraining.
"""

from typing import List, Dict, Any

def build_hard_negative_augmented_train_set(
    base_train_samples: List[Dict[str, Any]],
    hard_negatives: List[Dict[str, Any]],
    oversample_factor: int = 2
) -> List[Dict[str, Any]]:
    """
    Creates an augmented training set with increased sampling probability for hard negative look-alikes.
    """
    augmented = list(base_train_samples)
    hn_ids = {hn["sample_id"] for hn in hard_negatives}

    # Find the corresponding full sample dicts for the hard negatives
    hn_samples = [s for s in base_train_samples if s["sample_id"] in hn_ids]

    for _ in range(oversample_factor - 1):
        augmented.extend(hn_samples)

    print(f"Base train samples: {len(base_train_samples)} -> Augmented with Hard Negatives: {len(augmented)}")
    return augmented

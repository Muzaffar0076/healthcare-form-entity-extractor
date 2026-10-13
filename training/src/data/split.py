"""
Dataset splitting for healthcare NER.

This module splits the processed healthcare NER dataset into reproducible,
leakage-safe train, validation, and test sets using a fixed random seed.
"""

import json
import random
from collections import Counter
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DATA_PATH = (
    PROJECT_ROOT / "data" / "processed" / "healthcare_ner_processed.json"
)
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

DEFAULT_SEED = 42
TRAIN_RATIO = 0.70
VAL_RATIO = 0.15
TEST_RATIO = 0.15


def load_processed_data(path: Path = PROCESSED_DATA_PATH) -> list[dict[str, Any]]:
    """
    Load the processed healthcare NER dataset.

    Args:
        path: Path to the processed JSON dataset.

    Returns:
        List of records with 'tokens' and 'labels'.
    """
    if not path.exists():
        raise FileNotFoundError(f"Processed dataset not found at: {path}")

    with path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    if not isinstance(records, list) or len(records) == 0:
        raise ValueError("Expected non-empty list of processed records.")

    return records


def compute_split_stats(records: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute token and entity counts for a set of records.
    """
    total_tokens = sum(len(r.get("tokens", [])) for r in records)
    label_counter = Counter()

    for r in records:
        for label in r.get("labels", []):
            label_counter[label] += 1

    return {
        "documents": len(records),
        "tokens": total_tokens,
        "entities": {
            "B-CONDITION": label_counter.get("B-CONDITION", 0),
            "I-CONDITION": label_counter.get("I-CONDITION", 0),
            "B-MEDICATION": label_counter.get("B-MEDICATION", 0),
            "I-MEDICATION": label_counter.get("I-MEDICATION", 0),
            "B-DATE": label_counter.get("B-DATE", 0),
            "I-DATE": label_counter.get("I-DATE", 0),
            "O": label_counter.get("O", 0),
        },
    }


def split_dataset(
    records: list[dict[str, Any]],
    train_ratio: float = TRAIN_RATIO,
    val_ratio: float = VAL_RATIO,
    test_ratio: float = TEST_RATIO,
    seed: int = DEFAULT_SEED,
) -> dict[str, list[dict[str, Any]]]:
    """
    Perform a document-level split into train, val, and test subsets.

    Args:
        records: List of processed document records.
        train_ratio: Fraction of records for training.
        val_ratio: Fraction of records for validation.
        test_ratio: Fraction of records for testing.
        seed: Random seed for reproducibility.

    Returns:
        Dictionary mapping 'train', 'val', and 'test' to their records.
    """
    if not abs((train_ratio + val_ratio + test_ratio) - 1.0) < 1e-6:
        raise ValueError("Split ratios must sum to 1.0")

    total_records = len(records)
    indices = list(range(total_records))

    rng = random.Random(seed)
    rng.shuffle(indices)

    num_train = int(total_records * train_ratio)
    num_val = int(total_records * val_ratio)

    train_indices = indices[:num_train]
    val_indices = indices[num_train : num_train + num_val]
    test_indices = indices[num_train + num_val :]

    splits = {
        "train": [records[i] for i in train_indices],
        "val": [records[i] for i in val_indices],
        "test": [records[i] for i in test_indices],
    }

    return splits


def save_splits(
    splits: dict[str, list[dict[str, Any]]],
    output_dir: Path = OUTPUT_DIR,
    seed: int = DEFAULT_SEED,
) -> dict[str, Path]:
    """
    Save train, val, and test splits to JSON files alongside metadata.

    Args:
        splits: Dictionary containing 'train', 'val', 'test' record lists.
        output_dir: Directory where split files should be written.
        seed: Random seed used for the split.

    Returns:
        Dictionary mapping split name to written file path.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths = {}
    metadata = {
        "seed": seed,
        "splits": {},
    }

    for split_name, split_records in splits.items():
        file_path = output_dir / f"{split_name}.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(split_records, f, ensure_ascii=False, indent=2)

        saved_paths[split_name] = file_path
        metadata["splits"][split_name] = compute_split_stats(split_records)

    metadata_path = output_dir / "split_metadata.json"
    with metadata_path.open("w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)

    saved_paths["metadata"] = metadata_path
    return saved_paths


def main() -> None:
    print(f"Loading processed dataset from: {PROCESSED_DATA_PATH}")
    records = load_processed_data(PROCESSED_DATA_PATH)
    print(f"Loaded {len(records)} records.")

    print(
        f"Splitting dataset with seed={DEFAULT_SEED} "
        f"(Train={TRAIN_RATIO:.0%}, Val={VAL_RATIO:.0%}, Test={TEST_RATIO:.0%})..."
    )
    splits = split_dataset(
        records,
        train_ratio=TRAIN_RATIO,
        val_ratio=VAL_RATIO,
        test_ratio=TEST_RATIO,
        seed=DEFAULT_SEED,
    )

    print("\nSplit summary:")
    for name, split_records in splits.items():
        stats = compute_split_stats(split_records)
        ents = stats["entities"]
        print(
            f"  {name.upper():5s}: {stats['documents']:3d} docs | "
            f"{stats['tokens']:6d} tokens | "
            f"B-CONDITION: {ents['B-CONDITION']:4d} | "
            f"B-MEDICATION: {ents['B-MEDICATION']:4d} | "
            f"B-DATE: {ents['B-DATE']:3d}"
        )

    saved_paths = save_splits(splits, OUTPUT_DIR, seed=DEFAULT_SEED)
    print("\nSaved files:")
    for key, path in saved_paths.items():
        print(f"  {key}: {path}")


if __name__ == "__main__":
    main()

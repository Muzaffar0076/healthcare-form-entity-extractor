"""Download the CoNLL-2003 dataset and save a local project copy."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from datasets import load_dataset


# Recent versions of Hugging Face Datasets no longer run the legacy
# `conll2003.py` dataset script. These are the maintained Parquet copies of
# the same official train, validation, and test splits.
DATASET_ID = "lhoestq/conll2003"
DATA_BASE_URL = (
    "https://huggingface.co/datasets/lhoestq/conll2003/resolve/main/data"
)
DATA_FILES = {
    "train": f"{DATA_BASE_URL}/train-00000-of-00001.parquet",
    "validation": f"{DATA_BASE_URL}/validation-00000-of-00001.parquet",
    "test": f"{DATA_BASE_URL}/test-00000-of-00001.parquet",
}
EXPECTED_SPLITS = {"train", "validation", "test"}
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "conll2003"


def main() -> None:
    """Fetch the official dataset splits and store metadata beside them."""
    dataset = load_dataset("parquet", data_files=DATA_FILES)
    actual_splits = set(dataset.keys())

    if actual_splits != EXPECTED_SPLITS:
        raise ValueError(
            f"Expected splits {sorted(EXPECTED_SPLITS)}, got {sorted(actual_splits)}."
        )

    OUTPUT_DIR.parent.mkdir(parents=True, exist_ok=True)
    dataset.save_to_disk(str(OUTPUT_DIR))

    metadata = {
        "dataset_id": DATASET_ID,
        "downloaded_at_utc": datetime.now(UTC).isoformat(),
        "splits": {split: len(dataset[split]) for split in sorted(dataset.keys())},
        "features": str(dataset["train"].features),
    }
    metadata_path = OUTPUT_DIR / "download-metadata.json"
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")

    print(f"Saved CoNLL-2003 to {OUTPUT_DIR}")
    print("Split sizes:", metadata["splits"])


if __name__ == "__main__":
    main()

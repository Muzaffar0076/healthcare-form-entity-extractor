"""
MACCROBAT2020-V2 dataset ingestion.

This module loads the raw MACCROBAT JSON dataset and provides
a simple function for accessing the dataset.
"""

import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "MACCROBAT2020-V2.json"


def load_raw_dataset(path: Path = RAW_DATA_PATH) -> dict[str, Any]:
    """
    Load the raw MACCROBAT2020-V2 JSON dataset.

    Args:
        path: Path to the raw JSON dataset.

    Returns:
        The loaded dataset as a dictionary.

    Raises:
        FileNotFoundError: If the dataset file does not exist.
        json.JSONDecodeError: If the JSON file is invalid.
        ValueError: If the loaded JSON is not a dictionary.
    """

    if not path.exists():
        raise FileNotFoundError(
            f"Dataset not found at: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        dataset = json.load(file)

    if not isinstance(dataset, dict):
        raise ValueError(
            "Expected the MACCROBAT dataset to be a JSON object."
        )

    return dataset


if __name__ == "__main__":
    dataset = load_raw_dataset()

    print("Dataset loaded successfully.")
    print(f"Dataset path: {RAW_DATA_PATH}")
    print(f"Top-level keys: {list(dataset.keys())}")
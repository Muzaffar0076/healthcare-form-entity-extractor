"""
Validation utilities for the MACCROBAT2020-V2 dataset.
"""

from pathlib import Path
from typing import Any

from ingestion import load_raw_dataset


PROJECT_ROOT = Path(__file__).resolve().parents[3]

RAW_DATA_PATH = PROJECT_ROOT / "data" / "raw" / "MACCROBAT2020-V2.json"

REQUIRED_LABELS = {
    "DATE",
    "MEDICATION",
    "DISEASE_DISORDER",
}


def validate_dataset(dataset: dict[str, Any]) -> None:
    """
    Perform basic validation checks on the MACCROBAT dataset.
    """

    print("Starting dataset validation...\n")

    # 1. Check required top-level fields
    required_keys = {
        "data",
        "all_ner_labels",
        "label_2_index",
        "index_2_label",
    }

    missing_keys = required_keys - set(dataset.keys())

    if missing_keys:
        raise ValueError(
            f"Missing required top-level keys: {missing_keys}"
        )

    print("✓ Required top-level keys are present.")

    # 2. Check data field
    records = dataset["data"]

    if not isinstance(records, list):
        raise ValueError(
            f"Expected 'data' to be a list, "
            f"but found {type(records).__name__}."
        )

    print(f"✓ 'data' field is a list.")
    print(f"✓ Number of records: {len(records)}")

    if len(records) == 0:
        raise ValueError("Dataset contains no records.")

    # 3. Check label list
    labels = dataset["all_ner_labels"]

    if not isinstance(labels, list):
        raise ValueError(
            "'all_ner_labels' should be a list."
        )

    print(f"✓ Total labels available: {len(labels)}")

    # 4. Check healthcare labels
    available_labels = set()

    for label in labels:
        if isinstance(label, str):
            # Remove BIO prefix if present.
            if label.startswith("B-") or label.startswith("I-"):
                available_labels.add(label[2:])
            else:
                available_labels.add(label)

    print("\nRequired healthcare labels:")

    for label in sorted(REQUIRED_LABELS):
        if label in available_labels:
            print(f"✓ {label}")
        else:
            print(f"✗ {label}")

    missing_target_labels = REQUIRED_LABELS - available_labels

    if missing_target_labels:
        raise ValueError(
            f"Required healthcare labels are missing: "
            f"{missing_target_labels}"
        )

    print("\n✓ All required healthcare labels are present.")

    # 5. Show first record structure
    first_record = records[0]

    print("\nFirst record inspection:")
    print(f"Type: {type(first_record).__name__}")

    if isinstance(first_record, dict):
        print(f"Keys: {list(first_record.keys())}")
    else:
        print(f"Preview: {str(first_record)[:500]}")

    print("\nDataset validation completed successfully.")


if __name__ == "__main__":
    dataset = load_raw_dataset(RAW_DATA_PATH)
    validate_dataset(dataset)
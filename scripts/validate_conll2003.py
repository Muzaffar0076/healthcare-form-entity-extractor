"""Validate the local CoNLL-2003 dataset and create a short report."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from datasets import load_from_disk


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "data" / "raw" / "conll2003"
REPORT_PATH = PROJECT_ROOT / "docs" / "data-validation-report.md"
EXPECTED_SPLITS = {"train", "validation", "test"}
REQUIRED_COLUMNS = {"id", "tokens", "pos_tags", "chunk_tags", "ner_tags"}
NER_LABELS = (
    "O",
    "B-PER",
    "I-PER",
    "B-ORG",
    "I-ORG",
    "B-LOC",
    "I-LOC",
    "B-MISC",
    "I-MISC",
)


def validate_split(split_name: str, rows: object) -> dict[str, object]:
    """Check one split and return the findings needed for the report."""
    label_counts: Counter[str] = Counter()
    seen_sentences: set[tuple[str, ...]] = set()
    duplicates = 0
    empty_sentences = 0
    empty_tokens = 0
    length_mismatches = 0
    invalid_label_ids = 0

    for row in rows:  # type: ignore[union-attr]
        tokens = row["tokens"]
        labels = row["ner_tags"]

        if not tokens:
            empty_sentences += 1
        if any(not token.strip() for token in tokens):
            empty_tokens += 1
        if len(tokens) != len(labels):
            length_mismatches += 1

        sentence = tuple(tokens)
        if sentence in seen_sentences:
            duplicates += 1
        else:
            seen_sentences.add(sentence)

        for label_id in labels:
            if 0 <= label_id < len(NER_LABELS):
                label_counts[NER_LABELS[label_id]] += 1
            else:
                invalid_label_ids += 1

    return {
        "rows": len(rows),  # type: ignore[arg-type]
        "duplicate_sentences": duplicates,
        "empty_sentences": empty_sentences,
        "empty_tokens": empty_tokens,
        "length_mismatches": length_mismatches,
        "invalid_label_ids": invalid_label_ids,
        "label_counts": label_counts,
    }


def write_report(results: dict[str, dict[str, object]]) -> None:
    """Write a readable validation report for the project documentation."""
    all_checks_passed = all(
        result[key] == 0
        for result in results.values()
        for key in (
            "empty_sentences",
            "empty_tokens",
            "length_mismatches",
            "invalid_label_ids",
        )
    )
    duplicate_total = sum(
        int(result["duplicate_sentences"]) for result in results.values()
    )
    if not all_checks_passed:
        status = "Needs attention"
    elif duplicate_total:
        status = "Passed with duplicate sentences documented"
    else:
        status = "Passed"

    lines = [
        "# CoNLL-2003 Data Validation Report",
        "",
        f"**Status:** {status}",
        "",
        "## Checks performed",
        "",
        "- Confirmed the required train, validation, and test splits.",
        "- Confirmed the required columns.",
        "- Checked that every token sequence has the same number of NER labels.",
        "- Checked for empty sentences, empty tokens, invalid label IDs, and duplicate sentences.",
        "",
        "## Split results",
        "",
        "| Split | Sentences | Duplicate sentences | Empty sentences | Empty tokens | Token/label mismatches | Invalid label IDs |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for split_name in ("train", "validation", "test"):
        result = results[split_name]
        lines.append(
            "| {split} | {rows} | {duplicates} | {empty_sentences} | "
            "{empty_tokens} | {mismatches} | {invalid_labels} |".format(
                split=split_name,
                rows=result["rows"],
                duplicates=result["duplicate_sentences"],
                empty_sentences=result["empty_sentences"],
                empty_tokens=result["empty_tokens"],
                mismatches=result["length_mismatches"],
                invalid_labels=result["invalid_label_ids"],
            )
        )

    lines.extend(["", "## Label counts", ""])
    for split_name in ("train", "validation", "test"):
        label_counts = results[split_name]["label_counts"]
        lines.extend([f"### {split_name}", "", "| Label | Tokens |", "| --- | ---: |"])
        for label in NER_LABELS:
            lines.append(f"| {label} | {label_counts[label]} |")  # type: ignore[index]
        lines.append("")

    lines.extend(
        [
            "## Note",
            "",
            "CoNLL-2003 uses person, organisation, location, and miscellaneous labels. "
            "It is the general NER baseline, not the final healthcare-labelled training data.",
            "",
            "Repeated sentence text is reported above for transparency. The official splits "
            "are kept unchanged, because removing rows would change the supplied evaluation data.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Load the saved dataset, validate it, and write the results."""
    if not DATASET_DIR.exists():
        raise FileNotFoundError(
            "Dataset not found. Run scripts/download_conll2003.py first."
        )

    dataset = load_from_disk(str(DATASET_DIR))
    actual_splits = set(dataset.keys())
    if actual_splits != EXPECTED_SPLITS:
        raise ValueError(
            f"Expected splits {sorted(EXPECTED_SPLITS)}, got {sorted(actual_splits)}."
        )

    results: dict[str, dict[str, object]] = {}
    for split_name in sorted(dataset.keys()):
        columns = set(dataset[split_name].column_names)
        missing_columns = REQUIRED_COLUMNS - columns
        if missing_columns:
            raise ValueError(
                f"{split_name} is missing columns: {sorted(missing_columns)}."
            )
        results[split_name] = validate_split(split_name, dataset[split_name])

    write_report(results)
    print(f"Validation report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()

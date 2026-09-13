"""Create a small exploratory data analysis report for CoNLL-2003."""

from __future__ import annotations

from collections import Counter
from math import ceil
from pathlib import Path
from statistics import median

from datasets import load_from_disk


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET_DIR = PROJECT_ROOT / "data" / "raw" / "conll2003"
REPORT_PATH = PROJECT_ROOT / "docs" / "eda-report.md"
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


def percentile(values: list[int], percent: int) -> int:
    """Return a simple nearest-rank percentile for non-empty values."""
    ordered = sorted(values)
    return ordered[ceil(percent / 100 * len(ordered)) - 1]


def analyse_split(rows: object) -> dict[str, object]:
    """Collect sentence, token, and entity statistics for one dataset split."""
    lengths: list[int] = []
    token_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    entity_counts: Counter[str] = Counter()

    for row in rows:  # type: ignore[union-attr]
        tokens = row["tokens"]
        labels = row["ner_tags"]
        lengths.append(len(tokens))
        token_counts.update(token.lower() for token in tokens)

        for label_id in labels:
            label = NER_LABELS[label_id]
            label_counts[label] += 1
            if label.startswith("B-"):
                entity_counts[label[2:]] += 1

    total_tokens = sum(lengths)
    return {
        "sentences": len(lengths),
        "tokens": total_tokens,
        "unique_tokens": len(token_counts),
        "mean_length": total_tokens / len(lengths),
        "median_length": median(lengths),
        "min_length": min(lengths),
        "max_length": max(lengths),
        "p95_length": percentile(lengths, 95),
        "label_counts": label_counts,
        "entity_counts": entity_counts,
        "top_tokens": token_counts.most_common(20),
    }


def write_report(results: dict[str, dict[str, object]]) -> None:
    """Write the EDA results in a form that is easy to review on GitHub."""
    lines = [
        "# CoNLL-2003 Exploratory Data Analysis",
        "",
        "This report describes the downloaded CoNLL-2003 splits before any model training. "
        "The dataset is used as a general NER baseline, so its labels are not healthcare labels.",
        "",
        "## Dataset size and sentence length",
        "",
        "| Split | Sentences | Tokens | Unique lower-case tokens | Average length | Median length | 95th percentile | Shortest | Longest |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]

    for split_name in ("train", "validation", "test"):
        result = results[split_name]
        lines.append(
            "| {split} | {sentences} | {tokens} | {unique_tokens} | {mean:.2f} | "
            "{median} | {p95} | {minimum} | {maximum} |".format(
                split=split_name,
                sentences=result["sentences"],
                tokens=result["tokens"],
                unique_tokens=result["unique_tokens"],
                mean=result["mean_length"],
                median=result["median_length"],
                p95=result["p95_length"],
                minimum=result["min_length"],
                maximum=result["max_length"],
            )
        )

    lines.extend(["", "## Entity counts", "", "Entity counts are based on `B-` tags, so each entity is counted once.", "", "| Split | PER | ORG | LOC | MISC | Total entities |", "| --- | ---: | ---: | ---: | ---: | ---: |"])
    for split_name in ("train", "validation", "test"):
        counts = results[split_name]["entity_counts"]
        total = sum(counts.values())  # type: ignore[union-attr]
        lines.append(
            f"| {split_name} | {counts['PER']} | {counts['ORG']} | {counts['LOC']} | "  # type: ignore[index]
            f"{counts['MISC']} | {total} |"  # type: ignore[index]
        )

    lines.extend(["", "## Label-token distribution", ""])
    for split_name in ("train", "validation", "test"):
        counts = results[split_name]["label_counts"]
        total = results[split_name]["tokens"]
        lines.extend([f"### {split_name}", "", "| Label | Tokens | Share of tokens |", "| --- | ---: | ---: |"])
        for label in NER_LABELS:
            count = counts[label]  # type: ignore[index]
            lines.append(f"| {label} | {count} | {count / total:.2%} |")
        lines.append("")

    lines.extend(["## Most common training tokens", "", "Token counts are lower-cased. Punctuation is kept because it is part of the original text.", "", "| Token | Count |", "| --- | ---: |"])
    for token, count in results["train"]["top_tokens"]:  # type: ignore[index]
        lines.append(f"| `{token}` | {count} |")

    train = results["train"]
    train_labels = train["label_counts"]  # type: ignore[assignment]
    outside_share = train_labels["O"] / train["tokens"]  # type: ignore[index]
    rare_entity = min(train["entity_counts"], key=train["entity_counts"].get)  # type: ignore[arg-type]

    lines.extend(
        [
            "",
            "## Findings",
            "",
            f"- The training split is mostly non-entity text: `O` makes up {outside_share:.2%} of its tokens. A model could look accurate while missing entities, so entity-level precision, recall, and F1 are important.",
            f"- {rare_entity} is the least frequent entity type in the training split. This class imbalance should be considered during model evaluation.",
            f"- Most training sentences are at most {train['p95_length']} tokens long, but the longest has {train['max_length']} tokens. Padding and batching should handle the longer tail safely.",
            "- The official train, validation, and test splits remain separate. Validation will be used for model choices, while test will be kept for final reporting.",
            "",
            "## Healthcare limitation",
            "",
            "CoNLL-2003 contains `PER`, `ORG`, `LOC`, and `MISC`. It does not contain `DATE`, `MEDICATION`, or `CONDITION`, so it cannot be presented as final healthcare training data.",
            "",
        ]
    )
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    """Load the local dataset, analyse every split, and write the report."""
    if not DATASET_DIR.exists():
        raise FileNotFoundError(
            "Dataset not found. Run scripts/download_conll2003.py first."
        )

    dataset = load_from_disk(str(DATASET_DIR))
    results = {
        split_name: analyse_split(dataset[split_name])
        for split_name in ("train", "validation", "test")
    }
    write_report(results)
    print(f"EDA report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()

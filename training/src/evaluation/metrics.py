"""
Entity-level evaluation metrics for Named Entity Recognition (NER).

Implements strict CoNLL-standard entity evaluation for Precision, Recall,
and F1 scores (micro and macro) without external dependencies.
"""

from collections import defaultdict
from typing import Any


def extract_entities_from_bio_labels(
    labels: list[str],
) -> set[tuple[str, int, int]]:
    """
    Extract entity spans from a list of BIO labels.

    Args:
        labels: List of BIO label strings (e.g. ['O', 'B-DATE', 'I-DATE', 'O']).

    Returns:
        Set of tuples: (entity_type, start_token_idx, end_token_idx) inclusive.
    """
    entities: set[tuple[str, int, int]] = set()
    current_type: str | None = None
    start_idx: int = -1

    for i, label in enumerate(labels):
        if label.startswith("B-"):
            if current_type is not None:
                entities.add((current_type, start_idx, i - 1))
            current_type = label[2:]
            start_idx = i
        elif label.startswith("I-"):
            ent_type = label[2:]
            if current_type == ent_type:
                # Continuation of current entity
                continue
            else:
                # Malformed transition or new entity without B-
                if current_type is not None:
                    entities.add((current_type, start_idx, i - 1))
                current_type = ent_type
                start_idx = i
        else:  # 'O' or other
            if current_type is not None:
                entities.add((current_type, start_idx, i - 1))
                current_type = None
                start_idx = -1

    if current_type is not None:
        entities.add((current_type, start_idx, len(labels) - 1))

    return entities


def compute_entity_metrics(
    y_true: list[list[str]],
    y_pred: list[list[str]],
) -> dict[str, Any]:
    """
    Compute entity-level precision, recall, and F1 metrics.

    Args:
        y_true: List of ground-truth BIO label lists per sentence.
        y_pred: List of predicted BIO label lists per sentence.

    Returns:
        Dictionary containing overall micro/macro metrics and per-class metrics.
    """
    if len(y_true) != len(y_pred):
        raise ValueError(
            f"Mismatched sequence count: y_true={len(y_true)}, y_pred={len(y_pred)}"
        )

    tp_by_class: dict[str, int] = defaultdict(int)
    fp_by_class: dict[str, int] = defaultdict(int)
    fn_by_class: dict[str, int] = defaultdict(int)
    support_by_class: dict[str, int] = defaultdict(int)

    all_classes: set[str] = set()

    for true_seq, pred_seq in zip(y_true, y_pred):
        true_entities = extract_entities_from_bio_labels(true_seq)
        pred_entities = extract_entities_from_bio_labels(pred_seq)

        for ent_type, _, _ in true_entities:
            all_classes.add(ent_type)
            support_by_class[ent_type] += 1

        for ent_type, _, _ in pred_entities:
            all_classes.add(ent_type)

        # Match predicted entities against ground truth
        for ent in pred_entities:
            ent_type = ent[0]
            if ent in true_entities:
                tp_by_class[ent_type] += 1
            else:
                fp_by_class[ent_type] += 1

        for ent in true_entities:
            ent_type = ent[0]
            if ent not in pred_entities:
                fn_by_class[ent_type] += 1

    per_class_results = {}
    total_tp = sum(tp_by_class.values())
    total_fp = sum(fp_by_class.values())
    total_fn = sum(fn_by_class.values())
    total_support = sum(support_by_class.values())

    precision_sum = 0.0
    recall_sum = 0.0
    f1_sum = 0.0
    eval_classes = sorted(all_classes)

    for ent_type in eval_classes:
        tp = tp_by_class[ent_type]
        fp = fp_by_class[ent_type]
        fn = fn_by_class[ent_type]
        supp = support_by_class[ent_type]

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        per_class_results[ent_type] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": supp,
            "tp": tp,
            "fp": fp,
            "fn": fn,
        }

        precision_sum += prec
        recall_sum += rec
        f1_sum += f1

    # Overall Micro metrics
    micro_prec = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    micro_rec = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    micro_f1 = (
        (2 * micro_prec * micro_rec) / (micro_prec + micro_rec)
        if (micro_prec + micro_rec) > 0
        else 0.0
    )

    # Overall Macro metrics
    n_classes = len(eval_classes) if eval_classes else 1
    macro_prec = precision_sum / n_classes
    macro_rec = recall_sum / n_classes
    macro_f1 = f1_sum / n_classes

    return {
        "micro": {
            "precision": round(micro_prec, 4),
            "recall": round(micro_rec, 4),
            "f1": round(micro_f1, 4),
            "total_tp": total_tp,
            "total_fp": total_fp,
            "total_fn": total_fn,
            "total_support": total_support,
        },
        "macro": {
            "precision": round(macro_prec, 4),
            "recall": round(macro_rec, 4),
            "f1": round(macro_f1, 4),
        },
        "per_class": per_class_results,
    }


def format_metrics_table(metrics: dict[str, Any]) -> str:
    """
    Format evaluation metrics as a clean text table.
    """
    lines = []
    header = f"{'Entity':<14} | {'Precision':<9} | {'Recall':<9} | {'F1-Score':<9} | {'Support':<7}"
    sep = "-" * len(header)
    lines.append(sep)
    lines.append(header)
    lines.append(sep)

    for ent_type, scores in metrics.get("per_class", {}).items():
        lines.append(
            f"{ent_type:<14} | {scores['precision']:<9.4f} | {scores['recall']:<9.4f} | "
            f"{scores['f1']:<9.4f} | {scores['support']:<7d}"
        )

    lines.append(sep)
    micro = metrics["micro"]
    macro = metrics["macro"]
    lines.append(
        f"{'Micro Avg':<14} | {micro['precision']:<9.4f} | {micro['recall']:<9.4f} | "
        f"{micro['f1']:<9.4f} | {micro['total_support']:<7d}"
    )
    lines.append(
        f"{'Macro Avg':<14} | {macro['precision']:<9.4f} | {macro['recall']:<9.4f} | "
        f"{macro['f1']:<9.4f} | {micro['total_support']:<7d}"
    )
    lines.append(sep)
    return "\n".join(lines)

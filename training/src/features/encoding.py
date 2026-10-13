"""
Sequence encoding and dataset preparation for healthcare NER.

Segments document-level records into sentence sequences, converts tokens and
labels to integer IDs using the trained vocabulary and label encoder, and saves
sentence-level datasets for model training and evaluation.
"""

import json
from pathlib import Path
from typing import Any

try:
    from .tokenizer import split_document_into_sentences
    from .vocabulary import (
        PAD_IDX,
        LabelEncoder,
        Vocabulary,
        build_and_save_vocabularies,
    )
except ImportError:
    from tokenizer import split_document_into_sentences
    from vocabulary import (
        PAD_IDX,
        LabelEncoder,
        Vocabulary,
        build_and_save_vocabularies,
    )

PROJECT_ROOT = Path(__file__).resolve().parents[3]
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"


def segment_dataset_into_sentences(
    records: list[dict[str, Any]],
    max_len: int = 120,
) -> list[dict[str, list[str]]]:
    """
    Segment document records into sentence-level chunks with aligned labels.
    """
    sentences: list[dict[str, list[str]]] = []
    for r in records:
        tokens = r.get("tokens", [])
        labels = r.get("labels", [])
        sents = split_document_into_sentences(tokens, labels, max_len=max_len)
        sentences.extend(sents)
    return sentences


def encode_sentence(
    tokens: list[str],
    labels: list[str] | None,
    vocab: Vocabulary,
    label_encoder: LabelEncoder | None = None,
) -> dict[str, Any]:
    """
    Encode tokens and optional labels into numerical ID lists.
    """
    token_ids = [vocab.token_to_id(t) for t in tokens]
    result: dict[str, Any] = {
        "tokens": tokens,
        "token_ids": token_ids,
        "length": len(tokens),
    }

    if labels is not None and label_encoder is not None:
        label_ids = [label_encoder.label_to_id(l) for l in labels]
        result["labels"] = labels
        result["label_ids"] = label_ids

    return result


def pad_sequences(
    sequences: list[list[int]],
    pad_val: int = PAD_IDX,
    max_len: int | None = None,
) -> list[list[int]]:
    """
    Pad a batch of integer sequences to the maximum length.
    """
    if max_len is None:
        max_len = max(len(s) for s in sequences) if sequences else 0

    padded = []
    for s in sequences:
        if len(s) < max_len:
            padded.append(s + [pad_val] * (max_len - len(s)))
        else:
            padded.append(s[:max_len])
    return padded


def prepare_and_save_sentence_datasets(
    data_dir: Path = PROCESSED_DIR,
    max_len: int = 120,
) -> dict[str, int]:
    """
    Transform train, val, and test document splits into sentence-level datasets,
    build the vocabulary strictly on train, and save all artifacts.
    """
    train_path = data_dir / "train.json"
    val_path = data_dir / "val.json"
    test_path = data_dir / "test.json"

    if not train_path.exists() or not val_path.exists() or not test_path.exists():
        raise FileNotFoundError(
            f"Expected train.json, val.json, and test.json in {data_dir}"
        )

    # 1. Build and save vocabulary on training split
    vocab, label_encoder = build_and_save_vocabularies(
        train_path=train_path,
        output_dir=data_dir,
    )

    counts = {}

    # 2. Process each split
    for split_name, split_file in [
        ("train", train_path),
        ("val", val_path),
        ("test", test_path),
    ]:
        with split_file.open("r", encoding="utf-8") as f:
            records = json.load(f)

        sentences = segment_dataset_into_sentences(records, max_len=max_len)
        encoded_sentences = [
            encode_sentence(
                s["tokens"],
                s.get("labels"),
                vocab,
                label_encoder,
            )
            for s in sentences
        ]

        out_path = data_dir / f"{split_name}_sentences.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(encoded_sentences, f, ensure_ascii=False, indent=2)

        counts[split_name] = len(encoded_sentences)
        lengths = [s["length"] for s in encoded_sentences]
        print(
            f"Split '{split_name}': {len(records)} docs -> {len(encoded_sentences)} sentences "
            f"(max_len={max(lengths)}, avg_len={sum(lengths)/len(lengths):.1f}) "
            f"saved to {out_path.name}"
        )

    return counts


if __name__ == "__main__":
    prepare_and_save_sentence_datasets()

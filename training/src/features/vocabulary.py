"""
Vocabulary and label encoding for healthcare NER.

Constructs word vocabularies and label mappings fitted strictly on the
training split to ensure zero data leakage.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TRAIN_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "train.json"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed"

PAD_TOKEN = "<PAD>"
UNK_TOKEN = "<UNK>"
PAD_IDX = 0
UNK_IDX = 1

CANONICAL_LABELS = [
    "O",
    "B-DATE",
    "I-DATE",
    "B-MEDICATION",
    "I-MEDICATION",
    "B-CONDITION",
    "I-CONDITION",
]


class Vocabulary:
    """
    Token vocabulary mapping words to integer IDs and vice versa.
    """

    def __init__(
        self,
        token_to_idx: dict[str, int] | None = None,
        lowercase: bool = False,
    ) -> None:
        self.lowercase = lowercase
        if token_to_idx is not None:
            self.token_to_idx = dict(token_to_idx)
            self.idx_to_token = {idx: tok for tok, idx in self.token_to_idx.items()}
        else:
            self.token_to_idx = {PAD_TOKEN: PAD_IDX, UNK_TOKEN: UNK_IDX}
            self.idx_to_token = {PAD_IDX: PAD_TOKEN, UNK_IDX: UNK_TOKEN}

    def __len__(self) -> int:
        return len(self.token_to_idx)

    def __contains__(self, token: str) -> bool:
        norm = token.lower() if self.lowercase else token
        return norm in self.token_to_idx

    def token_to_id(self, token: str) -> int:
        norm = token.lower() if self.lowercase else token
        return self.token_to_idx.get(norm, UNK_IDX)

    def id_to_token(self, idx: int) -> str:
        return self.idx_to_token.get(idx, UNK_TOKEN)

    @classmethod
    def from_tokens(
        cls,
        tokens: Iterable[str],
        min_freq: int = 1,
        lowercase: bool = False,
    ) -> "Vocabulary":
        """
        Build a vocabulary from an iterable of string tokens.
        """
        vocab = cls(lowercase=lowercase)
        counter = Counter(t.lower() if lowercase else t for t in tokens)

        next_idx = 2
        for token, count in counter.most_common():
            if count >= min_freq and token not in vocab.token_to_idx:
                vocab.token_to_idx[token] = next_idx
                vocab.idx_to_token[next_idx] = token
                next_idx += 1

        return vocab

    def to_dict(self) -> dict[str, Any]:
        return {
            "lowercase": self.lowercase,
            "token_to_idx": self.token_to_idx,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> "Vocabulary":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        vocab = cls(
            token_to_idx=data["token_to_idx"],
            lowercase=data.get("lowercase", False),
        )
        return vocab


class LabelEncoder:
    """
    Encoder for BIO sequence labels.
    """

    def __init__(self, labels: list[str] = CANONICAL_LABELS) -> None:
        self.labels = list(labels)
        self.label_to_idx = {label: idx for idx, label in enumerate(self.labels)}
        self.idx_to_label = {idx: label for idx, label in enumerate(self.labels)}

    def __len__(self) -> int:
        return len(self.labels)

    def label_to_id(self, label: str) -> int:
        if label not in self.label_to_idx:
            raise KeyError(f"Unknown label: {label}")
        return self.label_to_idx[label]

    def id_to_label(self, idx: int) -> str:
        if idx not in self.idx_to_label:
            raise KeyError(f"Unknown label id: {idx}")
        return self.idx_to_label[idx]

    def to_dict(self) -> dict[str, Any]:
        return {
            "labels": self.labels,
            "label_to_idx": self.label_to_idx,
        }

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, path: Path) -> "LabelEncoder":
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return cls(labels=data["labels"])


def build_and_save_vocabularies(
    train_path: Path = TRAIN_DATA_PATH,
    output_dir: Path = OUTPUT_DIR,
    min_freq: int = 1,
    lowercase: bool = False,
) -> tuple[Vocabulary, LabelEncoder]:
    """
    Build vocabulary strictly from training records and save artifacts.
    """
    if not train_path.exists():
        raise FileNotFoundError(f"Training data not found at: {train_path}")

    with train_path.open("r", encoding="utf-8") as f:
        records = json.load(f)

    train_tokens = [tok for r in records for tok in r.get("tokens", [])]
    vocab = Vocabulary.from_tokens(
        train_tokens,
        min_freq=min_freq,
        lowercase=lowercase,
    )
    label_encoder = LabelEncoder()

    vocab_path = output_dir / "vocab.json"
    labels_path = output_dir / "labels.json"

    vocab.save(vocab_path)
    label_encoder.save(labels_path)

    print(f"Vocabulary saved to: {vocab_path} (size={len(vocab)})")
    print(f"Labels saved to: {labels_path} (classes={len(label_encoder)})")

    return vocab, label_encoder


if __name__ == "__main__":
    vocab, label_enc = build_and_save_vocabularies()

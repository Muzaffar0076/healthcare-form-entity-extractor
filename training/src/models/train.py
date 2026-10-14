"""
Training and evaluation pipeline for BiLSTM-CRF healthcare NER.

Trains the neural model using the training split, performs validation after each epoch,
applies early stopping, saves versioned model checkpoints to models/, and conducts
final evaluation on the held-out test split (BR-005 / BR-006 / BR-007 / TR-007).
"""

import json
import time
from pathlib import Path
from typing import Any

import torch
from torch.utils.data import DataLoader, Dataset

import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.src.evaluation.metrics import (
    compute_entity_metrics,
    format_metrics_table,
)
from training.src.features.vocabulary import (
    PAD_IDX,
    LabelEncoder,
    Vocabulary,
)
from training.src.models.bilstm_crf import BiLSTMCRF

DATA_DIR = PROJECT_ROOT / "data" / "processed"
MODELS_DIR = PROJECT_ROOT / "models"
DOCS_DIR = PROJECT_ROOT / "docs"

TRAIN_PATH = DATA_DIR / "train_sentences.json"
VAL_PATH = DATA_DIR / "val_sentences.json"
TEST_PATH = DATA_DIR / "test_sentences.json"
VOCAB_PATH = DATA_DIR / "vocab.json"
LABELS_PATH = DATA_DIR / "labels.json"


class NERDataset(Dataset):
    """
    PyTorch Dataset for sentence-level NER.
    """

    def __init__(self, data_path: Path) -> None:
        with data_path.open("r", encoding="utf-8") as f:
            self.records = json.load(f)

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, idx: int) -> dict[str, Any]:
        return self.records[idx]


def collate_fn(batch: list[dict[str, Any]]) -> dict[str, torch.Tensor]:
    """
    Pad sequences dynamically to the maximum length in the batch.
    """
    lengths = [len(item["token_ids"]) for item in batch]
    max_len = max(lengths)

    input_ids_batch = []
    tags_batch = []
    mask_batch = []

    for item in batch:
        tok_ids = item["token_ids"]
        t_ids = item.get("label_ids", [0] * len(tok_ids))
        seq_len = len(tok_ids)
        pad_len = max_len - seq_len

        input_ids_batch.append(tok_ids + [PAD_IDX] * pad_len)
        tags_batch.append(t_ids + [0] * pad_len)
        mask_batch.append([True] * seq_len + [False] * pad_len)

    return {
        "input_ids": torch.tensor(input_ids_batch, dtype=torch.long),
        "tags": torch.tensor(tags_batch, dtype=torch.long),
        "mask": torch.tensor(mask_batch, dtype=torch.bool),
    }


def evaluate_model(
    model: BiLSTMCRF,
    data_path: Path,
    label_encoder: LabelEncoder,
    device: torch.device,
    batch_size: int = 32,
) -> dict[str, Any]:
    """
    Evaluate the model on a sentence dataset and compute entity-level metrics.
    """
    model.eval()
    dataset = NERDataset(data_path)
    loader = DataLoader(
        dataset, batch_size=batch_size, shuffle=False, collate_fn=collate_fn
    )

    all_preds: list[list[str]] = []
    all_trues: list[list[str]] = []

    with torch.no_grad():
        for i, batch in enumerate(loader):
            input_ids = batch["input_ids"].to(device)
            mask = batch["mask"].to(device)

            pred_paths = model.decode(input_ids, mask=mask)

            start_idx = i * batch_size
            end_idx = start_idx + len(pred_paths)
            batch_records = dataset.records[start_idx:end_idx]

            for path, rec in zip(pred_paths, batch_records):
                pred_labels = [label_encoder.id_to_label(pid) for pid in path]
                true_labels = rec["labels"]
                all_preds.append(pred_labels)
                all_trues.append(true_labels)

    return compute_entity_metrics(all_trues, all_preds)


def train_bilstm_crf(
    num_epochs: int = 12,
    batch_size: int = 32,
    learning_rate: float = 0.005,
    embedding_dim: int = 128,
    hidden_dim: int = 256,
    dropout: float = 0.33,
    early_stopping_patience: int = 4,
) -> dict[str, Any]:
    """
    Train BiLSTM-CRF model and evaluate on validation and test sets.
    """
    device = (
        torch.device("mps")
        if torch.backends.mps.is_available()
        else torch.device("cuda" if torch.cuda.is_available() else "cpu")
    )
    print(f"Using compute device: {device}")

    # 1. Load vocabulary and labels
    vocab = Vocabulary.load(VOCAB_PATH)
    label_encoder = LabelEncoder.load(LABELS_PATH)
    print(f"Loaded vocabulary: {len(vocab)} tokens")
    print(f"Loaded label set: {len(label_encoder)} classes")

    # 2. Datasets & Loaders
    train_dataset = NERDataset(TRAIN_PATH)
    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=collate_fn,
    )
    print(f"Training dataset: {len(train_dataset)} sentences ({len(train_loader)} batches/epoch)")

    # 3. Model & Optimizer
    model = BiLSTMCRF(
        vocab_size=len(vocab),
        num_tags=len(label_encoder),
        embedding_dim=embedding_dim,
        hidden_dim=hidden_dim,
        dropout=dropout,
        padding_idx=PAD_IDX,
    ).to(device)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=1e-4,
    )

    best_val_f1 = -1.0
    best_epoch = 0
    patience_counter = 0
    best_checkpoint_path = MODELS_DIR / "bilstm_crf_v1.pt"

    print("\n" + "=" * 65)
    print(f"{'Epoch':<6} | {'Loss':<9} | {'Val Prec':<9} | {'Val Rec':<9} | {'Val F1':<9} | {'Time':<6}")
    print("=" * 65)

    for epoch in range(1, num_epochs + 1):
        model.train()
        total_loss = 0.0
        start_time = time.time()

        for batch in train_loader:
            input_ids = batch["input_ids"].to(device)
            tags = batch["tags"].to(device)
            mask = batch["mask"].to(device)

            optimizer.zero_grad()
            loss = model(input_ids, tags, mask=mask)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
            optimizer.step()

            total_loss += loss.item()

        epoch_loss = total_loss / len(train_loader)
        epoch_time = time.time() - start_time

        # Validate
        val_metrics = evaluate_model(
            model, VAL_PATH, label_encoder, device, batch_size=batch_size
        )
        val_f1 = val_metrics["micro"]["f1"]
        val_p = val_metrics["micro"]["precision"]
        val_r = val_metrics["micro"]["recall"]

        is_best = val_f1 > best_val_f1
        mark = " *" if is_best else ""
        print(
            f"{epoch:<6d} | {epoch_loss:<9.4f} | {val_p:<9.4f} | {val_r:<9.4f} | "
            f"{val_f1:<9.4f} | {epoch_time:<5.1f}s{mark}"
        )

        if is_best:
            best_val_f1 = val_f1
            best_epoch = epoch
            patience_counter = 0
            # Save checkpoint
            meta = {
                "epoch": epoch,
                "val_metrics": val_metrics,
                "version": "bilstm-crf-v1",
                "embedding_dim": embedding_dim,
                "hidden_dim": hidden_dim,
                "vocab_size": len(vocab),
            }
            model.save_checkpoint(best_checkpoint_path, metadata=meta)
        else:
            patience_counter += 1
            if patience_counter >= early_stopping_patience:
                print(f"\nEarly stopping triggered at epoch {epoch} (best epoch: {best_epoch})")
                break

    print("=" * 65)
    print(f"\nBest model from Epoch {best_epoch} with Validation F1: {best_val_f1:.4f}")

    # 4. Final Evaluation on Held-Out Test Split
    print(f"\nLoading best checkpoint from: {best_checkpoint_path}")
    best_model, _ = BiLSTMCRF.load_checkpoint(best_checkpoint_path, device=device)

    print("\n--- Final Validation Metrics (Best Model) ---")
    final_val_metrics = evaluate_model(best_model, VAL_PATH, label_encoder, device)
    print(format_metrics_table(final_val_metrics))

    print("\n--- Final Test Metrics (Held-Out Evaluation) ---")
    test_metrics = evaluate_model(best_model, TEST_PATH, label_encoder, device)
    print(format_metrics_table(test_metrics))

    # 5. Save results to docs
    summary = {
        "model_version": "bilstm-crf-v1",
        "architecture": "BiLSTM-CRF",
        "best_epoch": best_epoch,
        "config": {
            "embedding_dim": embedding_dim,
            "hidden_dim": hidden_dim,
            "dropout": dropout,
            "vocab_size": len(vocab),
            "num_tags": len(label_encoder),
        },
        "validation_metrics": final_val_metrics,
        "test_metrics": test_metrics,
    }

    metrics_path = DOCS_DIR / "bilstm-metrics.json"
    with metrics_path.open("w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"\nSaved BiLSTM evaluation report to: {metrics_path}")

    return summary


if __name__ == "__main__":
    train_bilstm_crf()

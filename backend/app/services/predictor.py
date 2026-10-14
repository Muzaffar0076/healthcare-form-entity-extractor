"""
NER Predictor service for healthcare entity extraction.

Loads the trained BiLSTM-CRF PyTorch checkpoint, vocabulary, and label mappings
at startup and exposes high-throughput inference for patient-facing healthcare text.
"""

import json
from pathlib import Path
from typing import Any, Optional

import torch

import sys

# Ensure repository root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.src.features.tokenizer import tokenize_with_offsets
from training.src.features.vocabulary import LabelEncoder, Vocabulary
from training.src.models.bilstm_crf import BiLSTMCRF

DEFAULT_MODEL_PATH = PROJECT_ROOT / "models" / "bilstm_crf_v1.pt"
DEFAULT_VOCAB_PATH = PROJECT_ROOT / "data" / "processed" / "vocab.json"
DEFAULT_LABELS_PATH = PROJECT_ROOT / "data" / "processed" / "labels.json"
DEFAULT_METRICS_PATH = PROJECT_ROOT / "docs" / "bilstm-metrics.json"


class NERPredictor:
    """
    Inference service for Named Entity Recognition.
    """

    def __init__(
        self,
        model_path: Path = DEFAULT_MODEL_PATH,
        vocab_path: Path = DEFAULT_VOCAB_PATH,
        labels_path: Path = DEFAULT_LABELS_PATH,
        metrics_path: Path = DEFAULT_METRICS_PATH,
        device: Optional[torch.device] = None,
    ) -> None:
        self.model_path = model_path
        self.vocab_path = vocab_path
        self.labels_path = labels_path
        self.metrics_path = metrics_path

        if device is None:
            self.device = torch.device(
                "mps"
                if torch.backends.mps.is_available()
                else ("cuda" if torch.cuda.is_available() else "cpu")
            )
        else:
            self.device = device

        self.model: Optional[BiLSTMCRF] = None
        self.vocab: Optional[Vocabulary] = None
        self.label_encoder: Optional[LabelEncoder] = None
        self.model_version: str = "bilstm-crf-v1"
        self.metrics: dict[str, Any] = {}
        self.is_loaded: bool = False

    def load(self) -> None:
        """
        Load model checkpoint and feature mappings into memory.
        """
        if not self.model_path.exists():
            raise FileNotFoundError(f"Model checkpoint not found at: {self.model_path}")
        if not self.vocab_path.exists() or not self.labels_path.exists():
            raise FileNotFoundError("Vocab or labels JSON file not found in data/processed/")

        self.vocab = Vocabulary.load(self.vocab_path)
        self.label_encoder = LabelEncoder.load(self.labels_path)
        self.model, meta = BiLSTMCRF.load_checkpoint(self.model_path, device=self.device)
        self.model_version = meta.get("version", "bilstm-crf-v1")

        if self.metrics_path.exists():
            with self.metrics_path.open("r", encoding="utf-8") as f:
                self.metrics = json.load(f)

        self.is_loaded = True
        print(f"NERPredictor loaded successfully on device: {self.device}")

    def extract_entities(self, text: str) -> list[dict[str, Any]]:
        """
        Extract healthcare entity spans from raw text.

        Args:
            text: Input healthcare text string.

        Returns:
            List of dictionaries with: text, label, start, end, confidence.
        """
        if not self.is_loaded or self.model is None or self.vocab is None or self.label_encoder is None:
            raise RuntimeError("Model is not loaded. Call load() before predicting.")

        if not text or not text.strip():
            return []

        tokens_with_offsets = tokenize_with_offsets(text)
        if not tokens_with_offsets:
            return []

        tokens = [t for t, _, _ in tokens_with_offsets]
        input_ids = torch.tensor(
            [[self.vocab.token_to_id(t) for t in tokens]],
            dtype=torch.long,
            device=self.device,
        )

        with torch.no_grad():
            emissions = self.model._get_lstm_emissions(input_ids)
            probs = torch.softmax(emissions, dim=-1)
            paths = self.model.decode(input_ids)

        pred_tag_ids = paths[0]
        pred_labels = [self.label_encoder.id_to_label(pid) for pid in pred_tag_ids]
        token_probs = probs[0]

        entities: list[dict[str, Any]] = []
        curr_type: Optional[str] = None
        curr_start: int = -1
        curr_end: int = -1
        curr_confs: list[float] = []

        for (tok, start, end), label, pid in zip(
            tokens_with_offsets, pred_labels, pred_tag_ids
        ):
            conf = float(token_probs[start if False else len(curr_confs) - 1 if False else 0][pid].item())
            # Directly get confidence for this token position
            token_idx = len(entities) if False else None

        for idx, ((tok, start, end), label, pid) in enumerate(
            zip(tokens_with_offsets, pred_labels, pred_tag_ids)
        ):
            conf = float(token_probs[idx][pid].item())

            if label.startswith("B-"):
                if curr_type is not None:
                    avg_c = sum(curr_confs) / len(curr_confs)
                    entities.append(
                        {
                            "text": text[curr_start:curr_end],
                            "label": curr_type,
                            "start": curr_start,
                            "end": curr_end,
                            "confidence": round(avg_c, 2),
                        }
                    )
                curr_type = label[2:]
                curr_start = start
                curr_end = end
                curr_confs = [conf]

            elif label.startswith("I-"):
                ent_type = label[2:]
                if curr_type == ent_type:
                    curr_end = end
                    curr_confs.append(conf)
                else:
                    if curr_type is not None:
                        avg_c = sum(curr_confs) / len(curr_confs)
                        entities.append(
                            {
                                "text": text[curr_start:curr_end],
                                "label": curr_type,
                                "start": curr_start,
                                "end": curr_end,
                                "confidence": round(avg_c, 2),
                            }
                        )
                    curr_type = ent_type
                    curr_start = start
                    curr_end = end
                    curr_confs = [conf]

            else:  # 'O'
                if curr_type is not None:
                    avg_c = sum(curr_confs) / len(curr_confs)
                    entities.append(
                        {
                            "text": text[curr_start:curr_end],
                            "label": curr_type,
                            "start": curr_start,
                            "end": curr_end,
                            "confidence": round(avg_c, 2),
                        }
                    )
                    curr_type = None
                    curr_confs = []

        if curr_type is not None:
            avg_c = sum(curr_confs) / len(curr_confs)
            entities.append(
                {
                    "text": text[curr_start:curr_end],
                    "label": curr_type,
                    "start": curr_start,
                    "end": curr_end,
                    "confidence": round(avg_c, 2),
                }
            )

        return entities


# Singleton instance
predictor_instance = NERPredictor()

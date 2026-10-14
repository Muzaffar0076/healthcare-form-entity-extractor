"""
BiLSTM-CRF architecture for Named Entity Recognition.

Grounded in Lample et al., NAACL 2016 (Neural Architectures for Named Entity Recognition).
Combines word embeddings, a bidirectional LSTM contextual encoder, and a linear-chain
Conditional Random Field (CRF) for sequence decoding.
"""

from pathlib import Path
from typing import Any, Optional

import torch
import torch.nn as nn

try:
    from .crf import CRF
except ImportError:
    from crf import CRF


class BiLSTMCRF(nn.Module):
    """
    Bidirectional LSTM with a CRF output layer.

    Args:
        vocab_size: Size of token vocabulary.
        num_tags: Number of target BIO labels.
        embedding_dim: Dimensionality of token embeddings.
        hidden_dim: Total hidden dimension of BiLSTM (hidden_dim // 2 per direction).
        num_layers: Number of LSTM layers.
        dropout: Dropout probability.
        padding_idx: Index of the padding token.
    """

    def __init__(
        self,
        vocab_size: int,
        num_tags: int,
        embedding_dim: int = 128,
        hidden_dim: int = 256,
        num_layers: int = 1,
        dropout: float = 0.33,
        padding_idx: int = 0,
    ) -> None:
        super().__init__()
        self.vocab_size = vocab_size
        self.num_tags = num_tags
        self.embedding_dim = embedding_dim
        self.hidden_dim = hidden_dim
        self.num_layers = num_layers
        self.dropout_rate = dropout
        self.padding_idx = padding_idx

        self.embedding = nn.Embedding(
            vocab_size,
            embedding_dim,
            padding_idx=padding_idx,
        )
        self.dropout = nn.Dropout(dropout)
        self.lstm = nn.LSTM(
            embedding_dim,
            hidden_dim // 2,
            num_layers=num_layers,
            bidirectional=True,
            batch_first=True,
        )
        self.hidden2tag = nn.Linear(hidden_dim, num_tags)
        self.crf = CRF(num_tags)

    def _get_lstm_emissions(
        self,
        input_ids: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute emission scores from input token IDs.

        Args:
            input_ids: (batch_size, seq_len)

        Returns:
            Emissions tensor: (batch_size, seq_len, num_tags)
        """
        # (batch_size, seq_len, embedding_dim)
        embeds = self.dropout(self.embedding(input_ids))
        # (batch_size, seq_len, hidden_dim)
        lstm_out, _ = self.lstm(embeds)
        lstm_out = self.dropout(lstm_out)
        # (batch_size, seq_len, num_tags)
        emissions = self.hidden2tag(lstm_out)
        return emissions

    def forward(
        self,
        input_ids: torch.Tensor,
        tags: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Compute Negative Log-Likelihood loss for a batch.

        Args:
            input_ids: (batch_size, seq_len)
            tags: (batch_size, seq_len) ground-truth tag IDs
            mask: (batch_size, seq_len) boolean mask (True for real tokens)

        Returns:
            Scalar NLL loss.
        """
        if mask is None:
            mask = input_ids != self.padding_idx

        emissions = self._get_lstm_emissions(input_ids)
        return self.crf(emissions, tags, mask=mask)

    def decode(
        self,
        input_ids: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> list[list[int]]:
        """
        Predict best tag sequences via Viterbi decoding.

        Args:
            input_ids: (batch_size, seq_len)
            mask: (batch_size, seq_len) boolean mask

        Returns:
            List of unpadded predicted tag sequences.
        """
        if mask is None:
            mask = input_ids != self.padding_idx

        emissions = self._get_lstm_emissions(input_ids)
        return self.crf.decode(emissions, mask=mask)

    def save_checkpoint(
        self,
        path: Path,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """
        Save model weights and architectural hyperparameters.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint = {
            "model_state_dict": self.state_dict(),
            "config": {
                "vocab_size": self.vocab_size,
                "num_tags": self.num_tags,
                "embedding_dim": self.embedding_dim,
                "hidden_dim": self.hidden_dim,
                "num_layers": self.num_layers,
                "dropout": self.dropout_rate,
                "padding_idx": self.padding_idx,
            },
            "metadata": metadata or {},
        }
        torch.save(checkpoint, path)

    @classmethod
    def load_checkpoint(
        cls,
        path: Path,
        device: torch.device = torch.device("cpu"),
    ) -> tuple["BiLSTMCRF", dict[str, Any]]:
        """
        Load model from a saved checkpoint file.
        """
        checkpoint = torch.load(path, map_location=device)
        config = checkpoint["config"]
        model = cls(**config)
        model.load_state_dict(checkpoint["model_state_dict"])
        model.to(device)
        model.eval()
        return model, checkpoint.get("metadata", {})

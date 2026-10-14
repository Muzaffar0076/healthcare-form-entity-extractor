"""
Conditional Random Field (CRF) layer in pure PyTorch.

Implements linear-chain CRF negative log-likelihood loss (forward-backward algorithm)
and Viterbi decoding with sequence masking for variable-length batches.
"""

from typing import Optional

import torch
import torch.nn as nn


class CRF(nn.Module):
    """
    Linear-chain Conditional Random Field.

    Args:
        num_tags: Number of distinct target labels / tags.
    """

    def __init__(self, num_tags: int) -> None:
        super().__init__()
        self.num_tags = num_tags

        # transitions[i, j] = score of transitioning from tag i to tag j
        self.transitions = nn.Parameter(torch.empty(num_tags, num_tags))
        self.start_transitions = nn.Parameter(torch.empty(num_tags))
        self.end_transitions = nn.Parameter(torch.empty(num_tags))

        self.reset_parameters()

    def reset_parameters(self) -> None:
        """
        Initialize transition parameters uniformly.
        """
        nn.init.uniform_(self.transitions, -0.1, 0.1)
        nn.init.uniform_(self.start_transitions, -0.1, 0.1)
        nn.init.uniform_(self.end_transitions, -0.1, 0.1)

    def _forward_alg(self, emissions: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
        """
        Compute total log-partition score Z using the forward algorithm.

        Args:
            emissions: (seq_len, batch_size, num_tags)
            mask: (seq_len, batch_size) boolean mask

        Returns:
            Log-partition scores: (batch_size,)
        """
        seq_len, batch_size, _ = emissions.shape
        score = self.start_transitions + emissions[0]

        for i in range(1, seq_len):
            mask_i = mask[i].unsqueeze(1)
            emit_i = emissions[i].unsqueeze(1)
            # (batch_size, num_tags, num_tags)
            trans_score = score.unsqueeze(2) + self.transitions + emit_i
            next_score = torch.logsumexp(trans_score, dim=1)
            score = torch.where(mask_i, next_score, score)

        score = score + self.end_transitions
        return torch.logsumexp(score, dim=1)

    def _score_sentence(
        self,
        emissions: torch.Tensor,
        tags: torch.Tensor,
        mask: torch.Tensor,
    ) -> torch.Tensor:
        """
        Compute score of ground-truth tag sequence.

        Args:
            emissions: (seq_len, batch_size, num_tags)
            tags: (seq_len, batch_size) integer tag IDs
            mask: (seq_len, batch_size) boolean mask

        Returns:
            Sequence scores: (batch_size,)
        """
        seq_len, batch_size, _ = emissions.shape
        score = self.start_transitions[tags[0]] + emissions[
            0, torch.arange(batch_size), tags[0]
        ]

        for i in range(1, seq_len):
            mask_i = mask[i]
            prev_tags = tags[i - 1]
            curr_tags = tags[i]
            trans_score = self.transitions[prev_tags, curr_tags]
            emit_score = emissions[i, torch.arange(batch_size), curr_tags]
            step_score = trans_score + emit_score
            score = score + torch.where(mask_i, step_score, torch.zeros_like(score))

        last_valid_indices = mask.long().sum(dim=0) - 1
        last_tags = tags.gather(0, last_valid_indices.unsqueeze(0)).squeeze(0)
        score = score + self.end_transitions[last_tags]
        return score

    def forward(
        self,
        emissions: torch.Tensor,
        tags: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        """
        Compute negative log-likelihood loss.

        Args:
            emissions: (batch_size, seq_len, num_tags)
            tags: (batch_size, seq_len)
            mask: (batch_size, seq_len) boolean tensor (True for valid tokens, False for padding)

        Returns:
            Scalar NLL loss tensor.
        """
        if mask is None:
            mask = torch.ones(
                emissions.shape[:2], dtype=torch.bool, device=emissions.device
            )

        # Transpose to (seq_len, batch_size, ...) for sequential recursion
        emissions_t = emissions.transpose(0, 1)
        tags_t = tags.transpose(0, 1)
        mask_t = mask.transpose(0, 1)

        forward_score = self._forward_alg(emissions_t, mask_t)
        gold_score = self._score_sentence(emissions_t, tags_t, mask_t)

        return torch.mean(forward_score - gold_score)

    def decode(
        self,
        emissions: torch.Tensor,
        mask: Optional[torch.Tensor] = None,
    ) -> list[list[int]]:
        """
        Find optimal tag sequence via Viterbi decoding.

        Args:
            emissions: (batch_size, seq_len, num_tags)
            mask: (batch_size, seq_len) boolean mask

        Returns:
            List of best tag ID lists (one per sample in batch, unpadded).
        """
        if mask is None:
            mask = torch.ones(
                emissions.shape[:2], dtype=torch.bool, device=emissions.device
            )

        emissions_t = emissions.transpose(0, 1)
        mask_t = mask.transpose(0, 1)
        seq_len, batch_size, _ = emissions_t.shape

        score = self.start_transitions + emissions_t[0]
        history: list[torch.Tensor] = []

        for i in range(1, seq_len):
            mask_i = mask_t[i].unsqueeze(1)
            emit_i = emissions_t[i].unsqueeze(1)
            trans_score = score.unsqueeze(2) + self.transitions + emit_i
            next_score, best_tags = torch.max(trans_score, dim=1)
            score = torch.where(mask_i, next_score, score)
            history.append(best_tags)

        score = score + self.end_transitions
        best_last_tags = torch.argmax(score, dim=1).tolist()

        best_paths: list[list[int]] = []
        last_valid_indices = (mask_t.long().sum(dim=0) - 1).tolist()

        for b in range(batch_size):
            best_tag = best_last_tags[b]
            seq_l = last_valid_indices[b] + 1
            path = [best_tag]
            for hist in reversed(history[: seq_l - 1]):
                best_tag = hist[b, best_tag].item()
                path.append(best_tag)
            path.reverse()
            best_paths.append(path)

        return best_paths

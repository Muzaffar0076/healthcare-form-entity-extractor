"""
Tokenizer and sentence splitter utilities for healthcare NER.

Provides regex-based tokenization with character offsets and entity-aware
sentence segmentation that prevents splitting across multi-token entity spans.
"""

import re
from typing import Any

# Regex matches alphanumeric words (including hyphenated/apostrophe words)
# and individual punctuation characters.
TOKEN_PATTERN = re.compile(r"\w+(?:[-'][\w]+)*|[^\w\s]")
SENTENCE_PUNCTUATION = {".", "!", "?"}


def tokenize_with_offsets(text: str) -> list[tuple[str, int, int]]:
    """
    Tokenize text into tokens along with their start and end character offsets.

    Args:
        text: Input raw text string.

    Returns:
        List of tuples: (token_str, start_char_offset, end_char_offset).
    """
    return [
        (match.group(), match.start(), match.end())
        for match in TOKEN_PATTERN.finditer(text)
    ]


def split_document_into_sentences(
    tokens: list[str],
    labels: list[str] | None = None,
    max_len: int = 120,
) -> list[dict[str, list[str]]]:
    """
    Split a document's tokens (and optional BIO labels) into sentence chunks.

    Ensures that splitting never breaks a multi-token entity span (i.e. splitting
    is disallowed if the immediate next token begins with an 'I-' tag).

    Args:
        tokens: List of word tokens in the document.
        labels: Corresponding list of BIO labels (optional).
        max_len: Maximum target length before forcing a split at a safe boundary.

    Returns:
        List of dicts, each with 'tokens' and optionally 'labels'.
    """
    if labels is not None and len(tokens) != len(labels):
        raise ValueError(
            f"Token count ({len(tokens)}) does not match label count ({len(labels)})"
        )

    sentences: list[dict[str, list[str]]] = []
    curr_tokens: list[str] = []
    curr_labels: list[str] = []

    for i in range(len(tokens)):
        token = tokens[i]
        curr_tokens.append(token)
        if labels is not None:
            curr_labels.append(labels[i])

        is_last = i == len(tokens) - 1
        # Check if the next token is part of a continuation tag (I-*)
        next_is_continuation = False
        if not is_last and labels is not None:
            next_is_continuation = labels[i + 1].startswith("I-")

        # Conditions to end the current sentence chunk:
        # 1. Punctuation boundary (. ! ?) and next token is not an I- continuation
        # 2. Exceeded max_len and not inside an entity continuation
        reached_punct = token in SENTENCE_PUNCTUATION and not next_is_continuation
        exceeded_length = len(curr_tokens) >= max_len and not next_is_continuation

        if not is_last and (reached_punct or exceeded_length):
            entry: dict[str, Any] = {"tokens": curr_tokens}
            if labels is not None:
                entry["labels"] = curr_labels
            sentences.append(entry)
            curr_tokens = []
            curr_labels = []

    if curr_tokens:
        entry = {"tokens": curr_tokens}
        if labels is not None:
            entry["labels"] = curr_labels
        sentences.append(entry)

    return sentences


if __name__ == "__main__":
    sample = "Patient was prescribed Aspirin on 12 March 2026 for diabetes. Condition improved."
    tokens_offsets = tokenize_with_offsets(sample)
    print("Tokenized sample:")
    for t, s, e in tokens_offsets:
        print(f"  {t:15s} ({s}:{e})")

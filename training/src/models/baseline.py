"""
Rule-based / regex NER baseline for healthcare entity extraction.

Implements a deterministic lexicon and regex baseline fitted strictly on the
training split. Establishes the initial Precision, Recall, and F1 benchmarks
(BR-004 / TR-006) for comparison against the upcoming BiLSTM-CRF model.
"""

import json
import re
from pathlib import Path
from typing import Any

# Ensure parent directory is in sys.path for robust execution
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from training.src.evaluation.metrics import (
    compute_entity_metrics,
    format_metrics_table,
)

TRAIN_SENTENCES_PATH = PROJECT_ROOT / "data" / "processed" / "train_sentences.json"
VAL_SENTENCES_PATH = PROJECT_ROOT / "data" / "processed" / "val_sentences.json"
TEST_SENTENCES_PATH = PROJECT_ROOT / "data" / "processed" / "test_sentences.json"
MODELS_DIR = PROJECT_ROOT / "models"
DOCS_DIR = PROJECT_ROOT / "docs"

MONTH_NAMES = {
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "jan",
    "feb",
    "mar",
    "apr",
    "jun",
    "jul",
    "aug",
    "sep",
    "sept",
    "oct",
    "nov",
    "dec",
}

DATE_REGEX = re.compile(
    r"^(?:\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?|(?:19|20)\d\d)$"
)


class RuleBasedNERBaseline:
    """
    Rule-based baseline extractor using training lexicon lookup and regex patterns.
    """

    def __init__(self) -> None:
        self.lexicon: dict[str, list[list[str]]] = {
            "CONDITION": [],
            "MEDICATION": [],
            "DATE": [],
        }

    def fit(self, train_sentences: list[dict[str, Any]] | Path) -> "RuleBasedNERBaseline":
        """
        Fit baseline lexicon strictly from training sentences to avoid leakage.
        """
        if isinstance(train_sentences, (str, Path)):
            with Path(train_sentences).open("r", encoding="utf-8") as f:
                sentences = json.load(f)
        else:
            sentences = train_sentences

        phrases: dict[str, set[tuple[str, ...]]] = {
            "CONDITION": set(),
            "MEDICATION": set(),
            "DATE": set(),
        }

        for sent in sentences:
            tokens = sent.get("tokens", [])
            labels = sent.get("labels", [])
            curr_type: str | None = None
            curr_tokens: list[str] = []

            for token, label in zip(tokens, labels):
                if label.startswith("B-"):
                    if curr_type and curr_tokens:
                        phrases[curr_type].add(tuple(curr_tokens))
                    curr_type = label[2:]
                    curr_tokens = [token.lower()]
                elif label.startswith("I-"):
                    ent_type = label[2:]
                    if curr_type == ent_type:
                        curr_tokens.append(token.lower())
                    else:
                        if curr_type and curr_tokens:
                            phrases[curr_type].add(tuple(curr_tokens))
                        curr_type = ent_type
                        curr_tokens = [token.lower()]
                else:
                    if curr_type and curr_tokens:
                        phrases[curr_type].add(tuple(curr_tokens))
                    curr_type = None
                    curr_tokens = []

            if curr_type and curr_tokens:
                phrases[curr_type].add(tuple(curr_tokens))

        # Store sorted lists by token length descending (longest match first)
        for ent_type, phrase_set in phrases.items():
            self.lexicon[ent_type] = sorted(
                [list(p) for p in phrase_set],
                key=len,
                reverse=True,
            )

        print(
            f"Baseline fitted with training lexicons: "
            f"CONDITION={len(self.lexicon['CONDITION'])}, "
            f"MEDICATION={len(self.lexicon['MEDICATION'])}, "
            f"DATE={len(self.lexicon['DATE'])}"
        )
        return self

    def predict_sentence(self, tokens: list[str]) -> list[str]:
        """
        Predict BIO labels for a single list of tokens.
        """
        n = len(tokens)
        preds = ["O"] * n
        matched = [False] * n
        lower_tokens = [t.lower() for t in tokens]

        # 1. Lexicon match: multi-token expressions prioritized (longest first)
        for ent_type in ["CONDITION", "MEDICATION", "DATE"]:
            for phrase in self.lexicon[ent_type]:
                p_len = len(phrase)
                if p_len > n:
                    continue

                for i in range(n - p_len + 1):
                    if any(matched[i : i + p_len]):
                        continue
                    if lower_tokens[i : i + p_len] == phrase:
                        preds[i] = f"B-{ent_type}"
                        for j in range(i + 1, i + p_len):
                            preds[j] = f"I-{ent_type}"
                        for j in range(i, i + p_len):
                            matched[j] = True

        # 2. Regex and heuristic date patterns for unmatched tokens
        for i in range(n):
            if matched[i]:
                continue
            tok = lower_tokens[i]
            if tok in MONTH_NAMES or DATE_REGEX.match(tok):
                preds[i] = "B-DATE"
                matched[i] = True

        return preds

    def predict(self, sentences: list[dict[str, Any]]) -> list[list[str]]:
        """
        Predict BIO labels for a batch of sentence dictionaries.
        """
        return [self.predict_sentence(s["tokens"]) for s in sentences]

    def evaluate(
        self,
        eval_sentences: list[dict[str, Any]] | Path,
    ) -> dict[str, Any]:
        """
        Evaluate baseline on a dataset split and return entity-level metrics.
        """
        if isinstance(eval_sentences, (str, Path)):
            with Path(eval_sentences).open("r", encoding="utf-8") as f:
                sentences = json.load(f)
        else:
            sentences = eval_sentences

        y_true = [s["labels"] for s in sentences]
        y_pred = self.predict(sentences)

        return compute_entity_metrics(y_true, y_pred)

    def save(self, path: Path) -> None:
        """
        Save baseline lexicon artifact to JSON.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            json.dump(
                {
                    "model_type": "rule_based_lexicon_baseline",
                    "lexicon": self.lexicon,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        print(f"Saved baseline model artifact to: {path}")

    @classmethod
    def load(cls, path: Path) -> "RuleBasedNERBaseline":
        """
        Load baseline lexicon artifact from JSON.
        """
        baseline = cls()
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        baseline.lexicon = data.get("lexicon", {})
        return baseline


def run_baseline_pipeline() -> dict[str, Any]:
    print("=" * 60)
    print("HEALTHCARE NER BASELINE (BR-004 / TR-006)")
    print("=" * 60)

    # 1. Initialize and fit baseline strictly on training sentences
    print(f"\n1. Fitting baseline on training split: {TRAIN_SENTENCES_PATH.name}")
    baseline = RuleBasedNERBaseline()
    baseline.fit(TRAIN_SENTENCES_PATH)

    # 2. Save baseline artifact
    model_artifact_path = MODELS_DIR / "baseline_model.json"
    baseline.save(model_artifact_path)

    # 3. Evaluate on Validation Split
    print(f"\n2. Evaluating on Validation Split: {VAL_SENTENCES_PATH.name}")
    val_metrics = baseline.evaluate(VAL_SENTENCES_PATH)
    print("\n--- Validation Split Metrics ---")
    print(format_metrics_table(val_metrics))

    # 4. Evaluate on Test Split
    print(f"\n3. Evaluating on Test Split: {TEST_SENTENCES_PATH.name}")
    test_metrics = baseline.evaluate(TEST_SENTENCES_PATH)
    print("\n--- Test Split Metrics ---")
    print(format_metrics_table(test_metrics))

    # 5. Save results to docs for traceability and model comparison
    results_summary = {
        "model": "Rule-Based Lexicon & Regex Baseline",
        "description": "Deterministic dictionary lookup from training split + date regex patterns",
        "validation_metrics": val_metrics,
        "test_metrics": test_metrics,
    }

    metrics_doc_path = DOCS_DIR / "baseline-metrics.json"
    with metrics_doc_path.open("w", encoding="utf-8") as f:
        json.dump(results_summary, f, ensure_ascii=False, indent=2)
    print(f"\nSaved baseline evaluation report to: {metrics_doc_path}")

    return results_summary


if __name__ == "__main__":
    run_baseline_pipeline()

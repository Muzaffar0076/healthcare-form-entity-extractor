# Week 1: NER Research Notes

## What is NER?

Named Entity Recognition (NER) is a part of Natural Language Processing that finds important words or phrases in a sentence and gives them a label.

For this project, the final healthcare model will identify:

- DATE
- MEDICATION
- CONDITION

For example:

> The patient was prescribed Aspirin on 12 March 2026 for diabetes.

The model should identify:

- Aspirin → MEDICATION
- 12 March 2026 → DATE
- diabetes → CONDITION

---

## BIO Tags

NER models usually label each token using BIO tags.

- `B` means the beginning of an entity.
- `I` means the token is inside the same entity.
- `O` means the token is not part of an entity.

Example:

| Word | Label |
|---|---|
| Aspirin | B-MEDICATION |
| on | O |
| 12 | B-DATE |
| March | I-DATE |
| 2026 | I-DATE |
| diabetes | B-CONDITION |

For a multi-word entity, the first token gets a `B-` label and the remaining tokens get `I-` labels.

---

## BiLSTM-CRF Model

The main model for this project will be a BiLSTM-CRF model.

```text
Words
  ↓
Embeddings
  ↓
BiLSTM
  ↓
Linear Layer
  ↓
CRF
  ↓
Entity Labels
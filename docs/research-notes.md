# Week 1: NER Research Notes

## What is NER?

Named Entity Recognition (NER) is a part of Natural Language Processing that finds important words or phrases in a sentence and gives them a label.

For this project, the important labels are:

- DATE
- MEDICATION
- CONDITION

For example, in this sentence:

> The patient was prescribed Aspirin on 12 March 2026 for diabetes.

The model should identify:

- Aspirin as a MEDICATION
- 12 March 2026 as a DATE
- diabetes as a CONDITION

## BIO tags

NER models usually label each word using BIO tags:

- `B` means the beginning of an entity.
- `I` means the word is inside the same entity.
- `O` means the word is not part of an entity.

Example:

| Word | Label |
| --- | --- |
| Aspirin | B-MEDICATION |
| on | O |
| 12 | B-DATE |
| March | I-DATE |
| 2026 | I-DATE |
| diabetes | B-CONDITION |

## BiLSTM-CRF model

The main model for this project will be a BiLSTM-CRF model.

```text
Words → Embeddings → BiLSTM → Linear layer → CRF → Entity labels
```

First, each word is changed into numbers called embeddings. The BiLSTM then reads the sentence from left to right and right to left, so it can understand the context around each word. A linear layer gives a score to every possible label. Finally, the CRF chooses the best full sequence of labels.

## Why use a CRF?

A CRF helps the model make sensible label sequences. For example, `I-DATE` should normally come after `B-DATE`, not at the beginning of a sentence. This helps the model find complete entities and better boundaries.

## Main idea from the research paper

This project follows the paper *Neural Architectures for Named Entity Recognition* by Lample et al. (2016). The paper shows that a model can learn NER features from word representations, character information, a BiLSTM, and a CRF layer. Character-level information is useful because it can learn patterns such as capitalization, prefixes, suffixes, and spelling.

## How the model will be evaluated

The model will be evaluated with entity-level precision, recall, and F1-score.

- Precision tells us how many predicted entities are correct.
- Recall tells us how many real entities the model found.
- F1-score combines precision and recall.

Token accuracy alone is not enough because the model may correctly label many ordinary words as `O` while still missing important entities.

## Important dataset note

CoNLL-2003 will be used as the baseline dataset. Its labels are `PER`, `ORG`, `LOC`, and `MISC`, not healthcare labels. It can help us build a general NER baseline, but it cannot directly train the final healthcare model.

For the final project, we will need healthcare-labelled examples for:

```text
O
B-DATE / I-DATE
B-MEDICATION / I-MEDICATION
B-CONDITION / I-CONDITION
```

## Responsible use

The project is meant to highlight useful information in healthcare text. It does not diagnose a patient, suggest treatment, recommend medication, or replace a healthcare professional.

## Reference

Lample, G., Ballesteros, M., Subramanian, S., Kawakami, K., and Dyer, C. (2016). *Neural Architectures for Named Entity Recognition*. NAACL 2016.

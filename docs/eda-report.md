
---

### 3. `docs/eda-report.md`

```md
# Healthcare Dataset Exploratory Data Analysis

## Purpose

This report describes the exploratory analysis of the MACCROBAT2020-V2 healthcare NER dataset.

The purpose of EDA is to understand the dataset before model training.

## Dataset

The dataset contains healthcare-related text annotated using BIO-style NER labels.

The initial inspection identified project-relevant entities including:

- `DATE`
- `MEDICATION`
- `DISEASE_DISORDER`

## Initial entity distribution

The initial inspection found:

| Entity | Count |
| --- | ---: |
| DISEASE_DISORDER | 1309 |
| MEDICATION | 1072 |
| DATE | 725 |

This shows that all three initial target entity types are present in the dataset.

## Label structure

The dataset uses BIO-style labels.

For example:

```text
B-DATE
I-DATE

B-MEDICATION
I-MEDICATION

B-DISEASE_DISORDER
I-DISEASE_DISORDER
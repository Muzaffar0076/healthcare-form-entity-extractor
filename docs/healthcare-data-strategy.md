
---

### 4. `docs/healthcare-data-strategy.md`

```md
# Healthcare Data Strategy

## Purpose

The final model requires healthcare-specific NER data.

A general NER dataset is not sufficient because the product needs to identify healthcare information such as dates, medications, and diseases or disorders.

## Selected dataset

The project uses **MACCROBAT2020-V2** as the healthcare NER dataset.

The dataset contains healthcare-specific entity types and BIO-style annotations.

## Initial project entities

The initial project focus is:

```text
DATE
MEDICATION
DISEASE_DISORDER
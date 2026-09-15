# Data

## CoNLL-2003 general NER baseline

This project uses the CoNLL-2003 English NER dataset from Kaggle as a general named-entity-recognition (NER) baseline. The dataset is loaded and analysed in the project notebook; no downloaded dataset files are stored in this repository.

**Dataset source:**  
https://www.kaggle.com/datasets/juliangarratt/conll2003-dataset

Use the supplied official split files without mixing them:

| Kaggle file | Project split | Purpose |
| --- | --- | --- |
| `eng.train` | Training | Fit the general NER baseline. |
| `eng.testa` | Validation | Make model-development choices. |
| `eng.testb` | Test | Evaluate the completed baseline once. |

The original CoNLL-2003 entity categories are:

- `PER` — person
- `ORG` — organisation
- `LOC` — location
- `MISC` — miscellaneous

They use BIO-style labels such as `B-PER` and `I-PER`.

## Healthcare limitation

CoNLL-2003 does **not** include the final healthcare categories: `DATE`, `MEDICATION`, and `CONDITION`. It is used only to build and evaluate a general NER baseline.

The final healthcare model will use a separate, documented synthetic healthcare dataset with healthcare-specific BIO labels. It must be trained and evaluated separately from the CoNLL-2003 baseline.

## Repository policy

Raw datasets and generated datasets are ignored by Git. The repository stores the notebook, code, and documentation needed to reproduce the workflow, not downloaded data files.

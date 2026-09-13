# Data

## CoNLL-2003 baseline dataset

This project uses the CoNLL-2003 English NER dataset as its general NER baseline. The dataset has official training, validation, and test splits.

Its original entity categories are:

- `PER` — person
- `ORG` — organisation
- `LOC` — location
- `MISC` — miscellaneous

It does **not** include the final healthcare categories (`DATE`, `MEDICATION`, and `CONDITION`). We will use it to build and evaluate a general NER baseline only.

## Downloading the data

From the project root, run:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/python scripts/download_conll2003.py
```

The script downloads the dataset from Hugging Face and saves a local copy in `data/raw/conll2003/`. That folder is ignored by Git, so the repository stores the script and documentation, not a copy of the dataset.

## Source

- Dataset: [CoNLL-2003 Parquet conversion](https://huggingface.co/datasets/lhoestq/conll2003). The script loads its published Parquet files directly because new versions of the `datasets` library no longer run the legacy CoNLL loader script.
- Split policy: use the supplied `train`, `validation`, and `test` splits without mixing them.
- Download date: recorded by the download script in `data/raw/conll2003/download-metadata.json`.

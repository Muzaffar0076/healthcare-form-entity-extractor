# Data

## Dataset

This project uses the MACCROBAT2020 biomedical Named Entity Recognition
(NER) dataset for healthcare-related entity extraction.

### Dataset Source

Hugging Face:

`singh-aditya/MACCROBAT_biomedical_ner`

The raw dataset used in this project is:

`data/raw/MACCROBAT2020-V2.json`

## Required Entities

The dataset contains many biomedical entity types.

For this project, we focus on three required entities:

- `DISEASE_DISORDER` — diseases and disorders
- `DATE` — dates mentioned in medical text
- `MEDICATION` — medicines and drugs

These entities are relevant to the Healthcare Form Entity Extractor
because the project needs to identify medical conditions, dates, and
medications from healthcare form text.

## Entity Counts

During dataset inspection, the following required entities were found:

- `DISEASE_DISORDER` — 1309
- `DATE` — 725
- `MEDICATION` — 1072

## Data Directory

```text
data/
├── raw/
│   └── MACCROBAT2020-V2.json
└── README.md
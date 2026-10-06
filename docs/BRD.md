# Business Requirements Document

## Project

**Healthcare Form Entity Extractor**

## The problem

Healthcare forms can be hard to read, especially for people who are not fluent in English or are unfamiliar with medical terms. Important details can get lost in long sentences, such as a medicine name, a date, or a health condition.

Care navigators face a similar problem. They may need to scan forms quickly and find the same details manually.

This project will build a tool that finds important healthcare entities in text and highlights them. It is meant to make reading and information finding easier. It is not a tool for making medical decisions.

## People who may use it

| User | What they need | Current difficulty |
| --- | --- | --- |
| Patient | Understand important information in a form | Medical language can be confusing |
| Care navigator | Find key details quickly | Manual review takes time |
| Data scientist | Measure and improve the NER model | Needs repeatable data and metrics |
| Developer | Connect another app to the model | Needs a clear and stable API |

## Project goals

The project should:

1. Study the required NER research paper.
2. Select and document a healthcare NER dataset.
3. Validate and explore the dataset.
4. Build a healthcare NER baseline.
5. Build a BiLSTM-CRF NER model.
6. Define and document the healthcare entity schema.
7. Train, tune, and evaluate the model.
8. Report entity-level precision, recall, and F1-score.
9. Provide an API for text extraction.
10. Provide a web interface that highlights extracted entities.
11. Document the model, testing, limitations, and responsible use.

## Main business requirements

| ID | Requirement | Priority | Done when |
| --- | --- | --- | --- |
| BR-001 | Ingest the healthcare NER dataset | Must | Dataset source, version, and schema are documented |
| BR-002 | Validate the data | Must | Missing values, duplicates, labels, and invalid records are checked |
| BR-003 | Perform EDA | Must | Important findings and charts are documented |
| BR-004 | Build a baseline | Must | Baseline metrics are recorded |
| BR-005 | Build a BiLSTM-CRF model | Must | A versioned model artifact is produced |
| BR-006 | Tune and compare models | Must | Training choices and results are documented |
| BR-007 | Evaluate on held-out data | Must | Final test results are recorded |
| BR-008 | Extract healthcare entities from text | Must | Correct text spans and labels are returned |
| BR-009 | Provide an extraction API | Must | A validated API endpoint works |
| BR-010 | Build a React interface | Must | A user can submit text and view results |
| BR-011 | Highlight entities | Must | Extracted entities are clearly shown in the text |
| BR-012 | Create a model card | Must | Intended use, metrics, and limitations are explained |
| BR-013 | Test the project | Must | Core data, model, API, and UI tests pass |
| BR-014 | Track experiments | Should | Runs, settings, and metrics are recorded |
| BR-015 | Handle a basic user session | Should | Session handling is secure when the app is deployed |

## Healthcare dataset

The project uses the **MACCROBAT2020-V2** dataset as the healthcare NER data source.

The dataset contains healthcare-related entities and uses BIO-style labels.

During initial dataset inspection, the following project-relevant entity types were identified:

- `DATE`
- `MEDICATION`
- `DISEASE_DISORDER`

The inspected dataset also contains many other healthcare entity types. The final project label schema will be documented after the complete dataset validation and label-mapping step.

## Important limits

The tool extracts information. It does not:

- Diagnose illness
- Recommend treatment
- Validate prescriptions
- Replace a healthcare professional
- Make medical decisions

Real patient data must not be used in this student project. Public or synthetic data should be used according to the dataset's license and project requirements.

## Risks to keep in mind

Healthcare NER is different from general NER. The model must be evaluated using healthcare-specific entities rather than relying only on general NER performance.

The dataset may contain many entity types, while the product may focus on a smaller set of entities. Therefore, the project must clearly document:

- Which labels are present in the source dataset
- Which labels are used by the model
- Any label mapping or filtering
- The train, validation, and test splits
- The evaluation metrics

Good performance on one dataset does not guarantee good performance on real-world healthcare forms.
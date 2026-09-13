# Business Requirements Document

## Project

**Healthcare Form Entity Extractor**

## The problem

Healthcare forms can be hard to read, especially for people who are not fluent in English or are unfamiliar with medical terms. Important details can get lost in long sentences: a medicine name, a date, or a health condition.

Care navigators face a similar problem. They may need to scan forms quickly and pick out the same details by hand.

This project will build a tool that finds those details in text and highlights them. It is meant to make reading easier. It is not a tool for making medical decisions.

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
2. Download, validate, and explore the CoNLL-2003 dataset.
3. Build a simple NER baseline first.
4. Build a BiLSTM-CRF NER model.
5. Define a healthcare entity schema for dates, medications, and conditions.
6. Train, tune, and evaluate the model.
7. Report entity-level precision, recall, and F1-score.
8. Provide an API for text extraction.
9. Provide a web interface that highlights extracted entities.
10. Document the model, testing, limitations, and responsible use.

## Main business requirements

| ID | Requirement | Priority | Done when |
| --- | --- | --- | --- |
| BR-001 | Ingest the dataset | Must | Dataset source, version, and schema are documented |
| BR-002 | Validate the data | Must | Missing values, duplicates, labels, and bad records are checked |
| BR-003 | Perform EDA | Must | Important findings and charts are documented |
| BR-004 | Build a baseline | Must | Baseline metrics are recorded |
| BR-005 | Build a BiLSTM-CRF model | Must | A versioned model artifact is produced |
| BR-006 | Tune and compare models | Must | Training choices and results are documented |
| BR-007 | Evaluate on held-out data | Must | Final test results are recorded |
| BR-008 | Extract entities from text | Must | Correct text spans and labels are returned |
| BR-009 | Provide an extraction API | Must | A validated API endpoint works |
| BR-010 | Build a React interface | Must | A user can submit text and view results |
| BR-011 | Highlight entities | Must | Extracted entities are clearly shown in the text |
| BR-012 | Create a model card | Must | Intended use, metrics, and limitations are explained |
| BR-013 | Test the project | Must | Core data, model, API, and UI tests pass |
| BR-014 | Track experiments | Should | Runs, settings, and metrics are recorded |
| BR-015 | Handle a basic user session | Should | Session handling is secure when the app is deployed |

## Important limits

The tool extracts information. It does not diagnose illness, recommend treatment, validate prescriptions, or replace a healthcare professional.

Real patient data must not be used in this student project. Public datasets and synthetic examples are enough.

## Risks to keep in mind

There is a gap between the required CoNLL-2003 dataset and the final healthcare use case. CoNLL-2003 has person, organisation, location, and miscellaneous labels. It does not contain dates, medications, or conditions.

That means CoNLL-2003 is useful for a general NER baseline, but a healthcare-labelled dataset or an annotation plan will be needed later. This needs to be stated clearly throughout the project.


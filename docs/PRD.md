# Product Requirements Document

## Product idea

The Healthcare Form Entity Extractor lets a user paste patient-facing healthcare text into a web page. The system finds important entities, then highlights them so they are easier to notice.

The first target entity types are:

- DATE
- MEDICATION
- CONDITION

The product is an accessibility and reading-support tool. The user still decides what the information means.

## Example

Input:

> The patient was prescribed Aspirin on 12 March 2026 for a heart condition.

Expected result:

- Aspirin — MEDICATION
- 12 March 2026 — DATE
- heart condition — CONDITION

## Users and user stories

### Patient

As a patient, I want to paste healthcare text and see important details highlighted, so I can understand the form more easily.

### Care navigator

As a care navigator, I want to see dates, medications, and conditions in a summary, so I can review the text faster.

### Data scientist

As a data scientist, I want entity-level precision, recall, and F1-score, so I can judge whether the model is improving.

### Developer

As a developer, I want a REST API, so another application can use the extraction model.

## Core features

### Text extraction

The user can enter or paste text into a large text box and select **Extract**. The system sends the text to the model and returns the entities it finds.

### Highlighted results

The original text is shown again with entities highlighted. Each highlight must include a readable label, not only a colour.

### Entity list

The user can see a list of all extracted entities with their type. Confidence can be shown when the model supports it.

### Model information

The app should show the model version and a simple view of model performance. This makes the result less of a black box.

### API

The backend will provide a versioned endpoint for extraction:

```text
POST /api/v1/extract
```

It receives text and returns the original text, extracted entities, their character positions, confidence when available, and the model version.

## Product rules

- Extraction comes first; interpretation belongs to the user or a healthcare professional.
- The app must not present results as medical advice.
- Entity boundaries should be preserved as accurately as possible.
- The final evaluation set must stay separate from training and tuning.
- Every saved model should have a version.
- User-submitted text should not be written to application logs.

## What happens when things go wrong?

The product needs clear states for:

- Empty text
- Invalid or very large input
- Loading while extraction is running
- An API error
- The model being unavailable
- No entities being found

Errors should say what the user can do next. For example: “Enter some text before extracting.”

## Out of scope

For this MVP, the product will not:

- Diagnose a disease
- Recommend medicine or treatment
- Decide whether something is urgent
- Store a history of raw patient text
- Require a database for basic extraction


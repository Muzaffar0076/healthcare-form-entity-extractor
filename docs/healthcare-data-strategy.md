# Week 4: Healthcare Label and Data Strategy

## Why a separate strategy is needed

CoNLL-2003 was useful for learning the NER workflow and building a general baseline. Its labels are `PER`, `ORG`, `LOC`, and `MISC`.

That is not the same job as this healthcare project. A person's name is not a medication. A location is not a medical condition.

For the final healthcare model, we need text that is labelled for the things the product actually highlights.

## Target labels

The healthcare model will use BIO labels.

```text
O
B-DATE
I-DATE
B-MEDICATION
I-MEDICATION
B-CONDITION
I-CONDITION
```

- `B` means the first word in an entity.
- `I` means another word in the same entity.
- `O` means the word is not part of an entity.

## What each label means

| Entity type | Include | Do not include |
| --- | --- | --- |
| DATE | Appointment dates, prescription dates, follow-up dates, and written date ranges | Vague words such as “recently” unless a clear date is given |
| MEDICATION | Drug names, including brand and generic names | A dosage by itself when no medicine name is present |
| CONDITION | Named health conditions, symptoms, and diagnoses when they are explicitly mentioned | Advice, treatment plans, or a diagnosis inferred by the reader |

## Example annotation

Text:

> Take Aspirin on 12 March 2026 if your diabetes symptoms continue.

| Token | Label |
| --- | --- |
| Take | O |
| Aspirin | B-MEDICATION |
| on | O |
| 12 | B-DATE |
| March | I-DATE |
| 2026 | I-DATE |
| if | O |
| your | O |
| diabetes | B-CONDITION |
| symptoms | I-CONDITION |
| continue | O |
| . | O |

## Data decision

The project will not use real patient records. Instead, the final healthcare dataset will be a small, documented collection of synthetic patient-facing form and instruction examples, created or carefully adapted for this educational project.

Every example must be reviewed and labelled manually using the rules above. Synthetic text is safer for privacy, and it lets the project focus on the NER workflow without claiming access to clinical records.

The dataset documentation will clearly state that this is a student-created healthcare NER dataset. It should not be described as clinical data or used to make clinical claims.

## Annotation process

1. Write or collect safe, synthetic healthcare-style examples. Do not include real patient information.
2. Split each sentence into tokens.
3. Apply one BIO label to every token.
4. Check that every `I-` label follows the matching `B-` or `I-` label.
5. Review difficult cases, such as multi-word conditions and medicine names with numbers.
6. Store the source, annotation date, label guide version, and dataset version.

Before model training, a second reviewer should check a sample of the annotations. Disagreements should be discussed and the annotation guide updated when needed.

## Data split plan

The healthcare data will be split into training, validation, and test sets. The split method, random seed, and final row counts will be written down when the dataset is created.

- **Training split:** used to fit the model.
- **Validation split:** used for choices such as learning rate, epochs, and early stopping.
- **Test split:** used only once for final evaluation.

Very similar examples should stay in the same split. This reduces the risk that the model sees almost the same sentence during training and testing.

## Quality checks

Before using the healthcare data, check:

- Every token has one valid BIO label.
- Token and label counts match.
- Entity boundaries are consistent.
- Each target entity type is represented.
- The data has no real patient information.
- Duplicate or near-duplicate examples do not cross the train, validation, and test splits.

## Important limitation

The CoNLL-2003 model and the healthcare model are different stages of the project. Good results on CoNLL-2003 do not prove that the model will work well on medications, dates, or conditions.

The final model must be evaluated on the healthcare-labelled test split using entity-level precision, recall, and F1-score. Its output is information extraction only, not medical advice.

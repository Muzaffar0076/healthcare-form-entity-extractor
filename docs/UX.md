# UX Requirements

## Design goal

The interface should feel calm and easy to use. A person should be able to paste text, press one button, and quickly see the important information.

Medical forms can already feel overwhelming. The screen should not add to that feeling.

## Main user flow

```text
Open app → Enter text → Select Extract → View highlighted text and entity list
```

There should also be links or sections for model performance, the model card, and limitations.

## Extraction screen

The main screen needs:

- A clearly labelled text area
- A short example sentence users can try
- An **Extract** button
- A **Clear** button
- Input validation
- A loading message while the result is being prepared
- A helpful error message if something fails

The text area should tell the user what to paste. For example: “Paste healthcare form text here.”

## Results screen

After extraction, show:

- The original text with entities highlighted
- A label for every entity type
- A list of extracted entities
- Confidence score, if available
- Model version
- The time the result was created

Example display:

> Patient was prescribed [Aspirin — MEDICATION] on [12 March 2026 — DATE] for a [heart condition — CONDITION].

## Performance screen

The performance area should explain how the model is doing without assuming the user is a data scientist. It should include:

- Precision
- Recall
- F1-score
- Results for each entity type
- A brief error-analysis summary
- Dataset and evaluation-split information
- Model version

## Required states

The UI should handle these states clearly:

| State | What the user should see |
| --- | --- |
| Empty | A prompt to enter text |
| Loading | A simple message that extraction is running |
| Success | Highlighted text and entity list |
| Validation error | A clear explanation of the input problem |
| API error | A message to retry later |
| Model unavailable | A message that the service is temporarily unavailable |
| No entities found | The original text and a clear “No entities found” message |

## Accessibility requirements

- Everything should work with a keyboard.
- Form fields and buttons need clear semantic labels.
- Colours must have enough contrast.
- Entity type must be visible in text, not shown by colour alone.
- Error messages should be easy to read and understandable by screen readers.
- The layout should work on mobile and desktop screens.

## Tone of the interface

Use plain language. Avoid claims that sound too certain, such as “Your condition is…”. Prefer wording like “The system identified the following text as a possible condition.”

The app should also make its limitation visible: it highlights information and does not provide medical advice.

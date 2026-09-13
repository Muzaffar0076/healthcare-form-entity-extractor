# CoNLL-2003 Exploratory Data Analysis

This report describes the downloaded CoNLL-2003 splits before any model training. The dataset is used as a general NER baseline, so its labels are not healthcare labels.

## Dataset size and sentence length

| Split | Sentences | Tokens | Unique lower-case tokens | Average length | Median length | 95th percentile | Shortest | Longest |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 14041 | 203621 | 21009 | 14.50 | 10 | 37 | 1 | 113 |
| validation | 3250 | 51362 | 9002 | 15.80 | 11.0 | 39 | 1 | 109 |
| test | 3453 | 46435 | 8548 | 13.45 | 9 | 37 | 1 | 124 |

## Entity counts

Entity counts are based on `B-` tags, so each entity is counted once.

| Split | PER | ORG | LOC | MISC | Total entities |
| --- | ---: | ---: | ---: | ---: | ---: |
| train | 6600 | 6321 | 7140 | 3438 | 23499 |
| validation | 1842 | 1341 | 1837 | 922 | 5942 |
| test | 1617 | 1661 | 1668 | 702 | 5648 |

## Label-token distribution

### train

| Label | Tokens | Share of tokens |
| --- | ---: | ---: |
| O | 169578 | 83.28% |
| B-PER | 6600 | 3.24% |
| I-PER | 4528 | 2.22% |
| B-ORG | 6321 | 3.10% |
| I-ORG | 3704 | 1.82% |
| B-LOC | 7140 | 3.51% |
| I-LOC | 1157 | 0.57% |
| B-MISC | 3438 | 1.69% |
| I-MISC | 1155 | 0.57% |

### validation

| Label | Tokens | Share of tokens |
| --- | ---: | ---: |
| O | 42759 | 83.25% |
| B-PER | 1842 | 3.59% |
| I-PER | 1307 | 2.54% |
| B-ORG | 1341 | 2.61% |
| I-ORG | 751 | 1.46% |
| B-LOC | 1837 | 3.58% |
| I-LOC | 257 | 0.50% |
| B-MISC | 922 | 1.80% |
| I-MISC | 346 | 0.67% |

### test

| Label | Tokens | Share of tokens |
| --- | ---: | ---: |
| O | 38323 | 82.53% |
| B-PER | 1617 | 3.48% |
| I-PER | 1156 | 2.49% |
| B-ORG | 1661 | 3.58% |
| I-ORG | 835 | 1.80% |
| B-LOC | 1668 | 3.59% |
| I-LOC | 257 | 0.55% |
| B-MISC | 702 | 1.51% |
| I-MISC | 216 | 0.47% |

## Most common training tokens

Token counts are lower-cased. Punctuation is kept because it is part of the original text.

| Token | Count |
| --- | ---: |
| `the` | 8390 |
| `.` | 7374 |
| `,` | 7290 |
| `of` | 3815 |
| `in` | 3621 |
| `to` | 3424 |
| `a` | 3199 |
| `and` | 2872 |
| `(` | 2861 |
| `)` | 2861 |
| `"` | 2178 |
| `on` | 2092 |
| `said` | 1849 |
| `'s` | 1566 |
| `for` | 1465 |
| `1` | 1421 |
| `-` | 1243 |
| `at` | 1146 |
| `was` | 1095 |
| `2` | 973 |

## Findings

- The training split is mostly non-entity text: `O` makes up 83.28% of its tokens. A model could look accurate while missing entities, so entity-level precision, recall, and F1 are important.
- MISC is the least frequent entity type in the training split. This class imbalance should be considered during model evaluation.
- Most training sentences are at most 37 tokens long, but the longest has 113 tokens. Padding and batching should handle the longer tail safely.
- The official train, validation, and test splits remain separate. Validation will be used for model choices, while test will be kept for final reporting.

## Healthcare limitation

CoNLL-2003 contains `PER`, `ORG`, `LOC`, and `MISC`. It does not contain `DATE`, `MEDICATION`, or `CONDITION`, so it cannot be presented as final healthcare training data.

# CoNLL-2003 Data Validation Report

**Status:** Passed with duplicate sentences documented

## Checks performed

- Confirmed the required train, validation, and test splits.
- Confirmed the required columns.
- Checked that every token sequence has the same number of NER labels.
- Checked for empty sentences, empty tokens, invalid label IDs, and duplicate sentences.

## Split results

| Split | Sentences | Duplicate sentences | Empty sentences | Empty tokens | Token/label mismatches | Invalid label IDs |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| train | 14041 | 1350 | 0 | 0 | 0 | 0 |
| validation | 3250 | 180 | 0 | 0 | 0 | 0 |
| test | 3453 | 269 | 0 | 0 | 0 | 0 |

## Label counts

### train

| Label | Tokens |
| --- | ---: |
| O | 169578 |
| B-PER | 6600 |
| I-PER | 4528 |
| B-ORG | 6321 |
| I-ORG | 3704 |
| B-LOC | 7140 |
| I-LOC | 1157 |
| B-MISC | 3438 |
| I-MISC | 1155 |

### validation

| Label | Tokens |
| --- | ---: |
| O | 42759 |
| B-PER | 1842 |
| I-PER | 1307 |
| B-ORG | 1341 |
| I-ORG | 751 |
| B-LOC | 1837 |
| I-LOC | 257 |
| B-MISC | 922 |
| I-MISC | 346 |

### test

| Label | Tokens |
| --- | ---: |
| O | 38323 |
| B-PER | 1617 |
| I-PER | 1156 |
| B-ORG | 1661 |
| I-ORG | 835 |
| B-LOC | 1668 |
| I-LOC | 257 |
| B-MISC | 702 |
| I-MISC | 216 |

## Note

CoNLL-2003 uses person, organisation, location, and miscellaneous labels. It is the general NER baseline, not the final healthcare-labelled training data.

Repeated sentence text is reported above for transparency. The official splits are kept unchanged, because removing rows would change the supplied evaluation data.

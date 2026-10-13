import json
from collections import Counter

with open("data/raw/MACCROBAT2020-V2.json", "r") as f:
    data = json.load(f)

counter = Counter()

for record in data["data"]:
    for entity in record["ner_info"]:
        label = entity["label"]

        if label in ["DATE", "MEDICATION", "DISEASE_DISORDER"]:
            counter[label] += 1

print("Our required entities:")
print()

for label, count in counter.items():
    print(label, ":", count)
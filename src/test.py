import json

with open("./settings/candidates.json", "r", encoding="utf-8") as f:
    data = json.load(f)
    print(data)
    candidates = data.get("candidates", [])
    print(candidates)
    print(len(candidates))

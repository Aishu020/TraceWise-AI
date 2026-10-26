import json
from pathlib import Path

path = Path("experiments/tracewise_protocol.json")

# Accept the existing BOM, then rewrite as UTF-8 without a BOM.
data = json.loads(path.read_text(encoding="utf-8-sig"))
path.write_text(
    json.dumps(data, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8"
)

# Verify strict UTF-8 JSON parsing.
with path.open("r", encoding="utf-8") as f:
    verified = json.load(f)

print("JSON encoding: valid UTF-8 without BOM")
print("Project:", verified["project"])
print("Candidate:", verified["candidate_method"]["name"])
print("Scale floor:", verified["candidate_method"]["scale_floor_ratio"])
print("Status:", verified["status"])

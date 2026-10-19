import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
for path in (root / "n8n/workflows").glob("*.json"):
    workflow = json.loads(path.read_text())
    names = {n["name"] for n in workflow["nodes"]}
    assert len(names) == len(workflow["nodes"])
    assert not workflow["active"]
    for node in workflow["nodes"]:
        assert "credentials" not in node, "Credentials must be assigned after import"
    for name, output in workflow["connections"].items():
        assert name in names
        for branch in output["main"]:
            for edge in branch:
                assert edge["node"] in names
    print(f"Validated {path.name}: {len(names)} nodes")

def validate_json(path: str) -> str:
    import json

    with open(path, "r", encoding="utf-8") as f:
        json.load(f)
    return "✅ OK"

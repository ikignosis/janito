def validate_json(file_path: str) -> str:
    import json

    with open(file_path, "r", encoding="utf-8") as f:
        json.load(f)
    return "✅ Syntax valid"

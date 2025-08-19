def validate_yaml(path: str) -> str:
    import yaml

    with open(path, "r", encoding="utf-8") as f:
        yaml.safe_load(f)
    return "✅ OK"

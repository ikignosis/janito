def validate_yaml(file_path: str) -> str:
    import yaml

    with open(file_path, "r", encoding="utf-8") as f:
        yaml.safe_load(f)
    return "✅ Syntax valid"

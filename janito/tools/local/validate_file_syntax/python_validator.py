def validate_python(path: str) -> str:
    import py_compile

    py_compile.compile(path, doraise=True)
    return "✅ OK"

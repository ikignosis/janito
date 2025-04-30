def validate_python(file_path: str) -> str:
    import py_compile

    py_compile.compile(file_path, doraise=True)
    return "✅ Syntax valid"
